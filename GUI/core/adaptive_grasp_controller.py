#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自适应抓取控制器
实现基于力传感器反馈的智能抓取控制
"""

import time
import numpy as np
from typing import List, Optional, Dict, Any
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class AdaptiveGraspController(QObject):
    """自适应抓取控制器类"""

    # 定义信号
    status_signal = pyqtSignal(str)  # 状态信号
    progress_signal = pyqtSignal(int, int)  # 进度信号 (当前步骤, 总步骤)
    completed_signal = pyqtSignal(bool, str)  # 完成信号 (是否成功, 消息)
    force_update_signal = pyqtSignal(dict)  # 力值更新信号 {sensor_id: [x, y, z]}

    # 抓取状态枚举
    IDLE = 0          # 空闲状态
    INITIALIZING = 1  # 初始化中
    CLOSING = 2       # 手爪闭合中
    ANALYZING = 3     # 分析传感器数据中
    RELEASING = 4     # 释放手指中
    COMPLETED = 5     # 抓取完成
    STOPPED = 6       # 已停止

    def __init__(self, arm_controller=None, sensor_data_manager=None, action_manager=None):
        """
        初始化自适应抓取控制器

        Args:
            arm_controller: 机械臂控制器实例
            sensor_data_manager: 传感器数据管理器实例
        """
        super().__init__()

        # 存储控制器引用
        self.arm_controller = arm_controller
        self.sensor_data_manager = sensor_data_manager
        self.action_manager = action_manager

        # 获取日志器
        self.logger = logging.getLogger(__name__)

        # 抓取配置参数
        self.config = {
            # 初始动作名称（可选，为空则不执行初始动作）
            "initial_action": "",

            # 手指闭合参数
            "finger_indices": [0, 1, 2, 3, 4],  # 要闭合的手指索引列表（0-5）
            "close_step": 10,  # 每次闭合步长（角度）
            "release_step": 10,  # 每次释放步长（角度）
            "close_speed": 1000,  # 闭合速度
            "step_interval": 0.5,  # 每步间隔时间（秒）

            # 力阈值参数（三个轴，最小值0.01N）
            "force_threshold_x": 2.0,  # X轴力阈值（N，范围0.01-50.0）
            "force_threshold_y": 2.0,  # Y轴力阈值（N，范围0.01-50.0）
            "force_threshold_z": 2.0,  # Z轴力阈值（N，范围0.01-50.0）

            # 稳定性判断参数
            "stable_duration": 2.0,  # 稳定持续时间（秒）
            "stable_std_threshold": 0.1,  # 稳定性标准差阈值
            "sample_window": 20,  # 数据采样窗口大小

            # 释放模式
            "release_mode": False,  # 是否启用释放模式（达到阈值后动态平衡：力值>=阈值则释放，力值<阈值则闭合）

            # 安全限制
            "max_iterations": 100,  # 最大迭代次数
            "max_finger_angle": 1000,  # 最大手指角度
            "min_finger_angle": 0,     # 最小手指角度（闭合极限）
        }

        # 当前状态
        self.state = self.IDLE
        self.is_grasping = False
        self.emergency_stopped = False

        # 运行时数据
        self.selected_sensors = []  # 选中的传感器ID列表
        self.current_hand_angles = [0] * 6  # 当前手指角度
        self.iteration_count = 0  # 当前迭代次数
        self.force_history = {  # 力值历史数据
            "x": [],
            "y": [],
            "z": []
        }
        self.stable_start_time = None  # 稳定状态开始时间

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grasp_state_machine)

    def set_config(self, config_dict: Dict[str, Any]):
        """
        更新配置参数

        Args:
            config_dict: 配置字典
        """
        self.config.update(config_dict)
        self.logger.info(f"配置已更新: {config_dict}")

    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置

        Returns:
            配置字典
        """
        return self.config.copy()

    def start_adaptive_grasp(self, sensor_ids: List[int]) -> bool:
        """
        开始自适应抓取

        Args:
            sensor_ids: 要使用的传感器ID列表

        Returns:
            是否成功启动
        """
        if self.is_grasping:
            self.logger.warning("已有抓取过程在进行中")
            self.status_signal.emit("抓取进行中，请等待完成或停止当前抓取")
            return False

        if not self.arm_controller:
            self.logger.warning("机械臂控制器未初始化")
            self.status_signal.emit("机械臂控制器未初始化")
            return False

        # 检查机械手控制方法是否可用
        if not hasattr(self.arm_controller, 'set_hand_angles'):
            self.logger.warning("机械臂控制器不支持手指控制")
            self.status_signal.emit("机械臂控制器不支持手指控制")
            return False

        self.logger.info("机械臂控制器检查通过")

        if not self.sensor_data_manager:
            self.logger.warning("传感器数据管理器未初始化")
            self.status_signal.emit("传感器数据管理器未初始化")
            return False

        if not sensor_ids:
            self.logger.warning("未选择传感器")
            self.status_signal.emit("请至少选择一个传感器")
            return False

        # 检查传感器是否存在
        available_sensors = self.sensor_data_manager.get_all_sensors()
        for sensor_id in sensor_ids:
            if sensor_id not in available_sensors:
                self.logger.warning(f"传感器 {sensor_id} 不存在")
                self.status_signal.emit(f"传感器 {sensor_id} 不存在")
                return False

        # 初始化抓取过程
        self.selected_sensors = sensor_ids
        self.is_grasping = True
        self.emergency_stopped = False
        self.state = self.INITIALIZING
        self.iteration_count = 0

        # 清空历史数据
        self.force_history = {"x": [], "y": [], "z": []}
        self.stable_start_time = None

        # 获取当前手指角度
        try:
            if hasattr(self.arm_controller, 'getHandAngles'):
                hand_angles = self.arm_controller.getHandAngles()
                if isinstance(hand_angles, (list, tuple)) and len(hand_angles) >= 6:
                    self.current_hand_angles = list(hand_angles)
                    self.logger.info(f"当前手指角度: {self.current_hand_angles}")
                else:
                    self.logger.warning(f"获取手指角度格式错误: {hand_angles}")
                    self.current_hand_angles = [500, 500, 500, 500, 500, 500]
            else:
                self.logger.warning("机械臂控制器不支持getHandAngles方法")
                self.current_hand_angles = [500, 500, 500, 500, 500, 500]
        except Exception as e:
            self.logger.error(f"获取当前手指角度失败: {e}")
            self.current_hand_angles = [500, 500, 500, 500, 500, 500]

        # 启动状态机
        self.status_signal.emit("开始自适应抓取")
        self.logger.info(f"开始自适应抓取，传感器: {sensor_ids}")
        self.timer.start(100)  # 100ms 轮询

        return True

    def stop_grasp(self) -> bool:
        """
        停止抓取过程

        Returns:
            是否成功停止
        """
        if not self.is_grasping:
            return False

        self.timer.stop()
        self.is_grasping = False
        self.state = self.STOPPED
        self.status_signal.emit("抓取已停止")
        self.completed_signal.emit(False, "用户手动停止")
        self.logger.info("抓取已停止")

        return True

    def emergency_stop(self) -> bool:
        """
        紧急停止

        Returns:
            是否成功停止
        """
        self.emergency_stopped = True
        result = self.stop_grasp()

        if result:
            self.status_signal.emit("紧急停止已触发")
            self.logger.warning("紧急停止已触发")

        return result

    def _grasp_state_machine(self):
        """状态机主循环"""
        try:
            if self.state == self.INITIALIZING:
                self._handle_initializing()
            elif self.state == self.CLOSING:
                self._handle_closing()
            elif self.state == self.ANALYZING:
                self._handle_analyzing()
            elif self.state == self.RELEASING:
                self._handle_releasing()
            elif self.state == self.COMPLETED:
                self._handle_completed()
        except Exception as e:
            self.logger.error(f"状态机执行错误: {e}", exc_info=True)
            self.status_signal.emit(f"执行错误: {str(e)}")
            self.stop_grasp()

    def _handle_initializing(self):
        """处理初始化状态"""
        # 执行初始动作（如果配置了）
        initial_action = self.config.get("initial_action", "").strip()

        if initial_action:
            # 如果有动作管理器，使用它执行初始动作
            if self.action_manager and hasattr(self.action_manager, 'execute_action'):
                try:
                    self.status_signal.emit(f"执行初始动作: {initial_action}")
                    self.logger.info(f"执行初始动作: {initial_action}")

                    # execute_action 返回 bool，表示是否执行成功或开始执行
                    exec_result = self.action_manager.execute_action(initial_action)
                    if exec_result:
                        self.logger.info(f"初始动作执行返回成功: {initial_action}")
                        # 给动作一点时间稳定（动作管理器内部有延时）
                        time.sleep(0.2)
                    else:
                        self.logger.warning(f"初始动作执行失败或返回False: {initial_action}")
                        self.status_signal.emit(f"初始动作执行失败: {initial_action}")
                except Exception as e:
                    self.logger.error(f"执行初始动作时出错: {e}")
                    self.status_signal.emit(f"初始动作执行出错: {str(e)}")
            else:
                # 如果没有动作管理器，也尝试通过arm_controller直接执行（仅作为降级）
                if hasattr(self.arm_controller, 'execute_action'):
                    try:
                        self.status_signal.emit(f"执行初始动作(降级): {initial_action}")
                        self.logger.info(f"执行初始动作(降级): {initial_action}")
                        try:
                            # 某些控制器可能实现execute_action
                            self.arm_controller.execute_action(initial_action)
                        except Exception:
                            # 降级路径不保证成功，仅记录
                            self.logger.debug("arm_controller.execute_action 未成功执行或不可用")
                    except Exception as e:
                        self.logger.error(f"降级执行初始动作出错: {e}")
                        self.status_signal.emit(f"初始动作执行出错: {str(e)}")

        # 进入闭合状态
        self.state = self.CLOSING
        self.status_signal.emit("开始手指闭合")
        self.logger.info("进入闭合状态")

    def _handle_closing(self):
        """处理手指闭合状态"""
        # 检查是否达到最大迭代次数
        if self.iteration_count >= self.config["max_iterations"]:
            self.status_signal.emit("达到最大迭代次数，停止闭合")
            self.state = self.COMPLETED
            self.completed_signal.emit(False, "达到最大迭代次数")
            return

        # 获取当前力值
        force_data = self._get_current_force()

        if force_data is None:
            self.status_signal.emit("无法获取传感器数据")
            return

        # 检查是否超过力阈值
        threshold_x = self.config["force_threshold_x"]
        threshold_y = self.config["force_threshold_y"]
        threshold_z = self.config["force_threshold_z"]

        if (abs(force_data["x"]) >= threshold_x or
            abs(force_data["y"]) >= threshold_y or
            abs(force_data["z"]) >= threshold_z):

            self.status_signal.emit(f"力值超过阈值: X={force_data['x']:.2f}N, Y={force_data['y']:.2f}N, Z={force_data['z']:.2f}N")

            # 根据释放模式决定下一个状态
            if self.config.get("release_mode", False):
                self.logger.info(f"力值超过阈值，启动释放模式")
                self.state = self.RELEASING
                self.status_signal.emit("进入释放模式，开始释放手指")
            else:
                self.logger.info(f"力值超过阈值，开始稳定性分析")
                self.state = self.ANALYZING
                self.stable_start_time = time.time()
            return

        # 执行手指闭合
        self._close_fingers()

        # 更新进度
        self.iteration_count += 1
        self.progress_signal.emit(self.iteration_count, self.config["max_iterations"])

    def _handle_analyzing(self):
        """处理分析状态"""
        # 获取当前力值
        force_data = self._get_current_force()

        if force_data is None:
            return

        # 添加到历史数据
        self.force_history["x"].append(force_data["x"])
        self.force_history["y"].append(force_data["y"])
        self.force_history["z"].append(force_data["z"])

        # 保持窗口大小
        window_size = self.config["sample_window"]
        for axis in ["x", "y", "z"]:
            if len(self.force_history[axis]) > window_size:
                self.force_history[axis].pop(0)

        # 检查是否已经稳定足够时间
        elapsed_time = time.time() - self.stable_start_time

        # 每次都计算并显示标准差（如果有足够的数据）
        if len(self.force_history["x"]) >= 5:  # 至少5个数据点才计算标准差
            std_x = np.std(self.force_history["x"])
            std_y = np.std(self.force_history["y"])
            std_z = np.std(self.force_history["z"])

            # 每次都打印标准差
            std_msg = f"标准差: X={std_x:.4f}, Y={std_y:.4f}, Z={std_z:.4f} ({elapsed_time:.1f}s / {self.config['stable_duration']}s)"
            self.status_signal.emit(std_msg)
            self.logger.info(std_msg)

        if elapsed_time < self.config["stable_duration"]:
            return

        # 达到稳定持续时间后，进行最终判断
        if len(self.force_history["x"]) >= window_size:
            std_x = np.std(self.force_history["x"])
            std_y = np.std(self.force_history["y"])
            std_z = np.std(self.force_history["z"])

            std_threshold = self.config["stable_std_threshold"]

            final_msg = f"最终标准差: X={std_x:.4f}, Y={std_y:.4f}, Z={std_z:.4f} (阈值={std_threshold})"
            self.status_signal.emit(final_msg)
            self.logger.info(final_msg)

            if std_x <= std_threshold and std_y <= std_threshold and std_z <= std_threshold:
                self.status_signal.emit("力值稳定，抓取成功")
                self.logger.info("力值稳定，抓取成功")
                self.state = self.COMPLETED
                self.completed_signal.emit(True, "抓取成功")
            else:
                self.status_signal.emit("力值不稳定，继续闭合")
                self.logger.info("力值不稳定，继续闭合")
                self.state = self.CLOSING
                self.force_history = {"x": [], "y": [], "z": []}
                self.stable_start_time = None

    def _handle_releasing(self):
        """处理释放状态 - 动态平衡控制：力值>=阈值则释放，力值<阈值则闭合，直到达到最大迭代次数"""
        # 检查是否达到最大迭代次数
        if self.iteration_count >= self.config["max_iterations"]:
            # 检查最终力值状态
            force_data = self._get_current_force()

            if force_data:
                threshold_x = self.config["force_threshold_x"]
                threshold_y = self.config["force_threshold_y"]
                threshold_z = self.config["force_threshold_z"]

                if (abs(force_data["x"]) < threshold_x and
                    abs(force_data["y"]) < threshold_y and
                    abs(force_data["z"]) < threshold_z):
                    self.status_signal.emit(f"达到最大迭代次数，力值低于阈值: X={force_data['x']:.2f}N, Y={force_data['y']:.2f}N, Z={force_data['z']:.2f}N")
                    self.logger.info("释放完成，力值低于阈值")
                    self.completed_signal.emit(True, "释放成功")
                else:
                    self.status_signal.emit(f"达到最大迭代次数，但力值仍超过阈值: X={force_data['x']:.2f}N, Y={force_data['y']:.2f}N, Z={force_data['z']:.2f}N")
                    self.logger.info("达到最大迭代次数，但力值仍超过阈值")
                    self.completed_signal.emit(False, "达到最大迭代次数，力值仍超过阈值")
            else:
                self.status_signal.emit("达到最大迭代次数")
                self.completed_signal.emit(False, "达到最大迭代次数")

            self.state = self.COMPLETED
            return

        # 获取当前力值
        force_data = self._get_current_force()

        if force_data is None:
            self.status_signal.emit("无法获取传感器数据")
            return

        # 检查力值
        threshold_x = self.config["force_threshold_x"]
        threshold_y = self.config["force_threshold_y"]
        threshold_z = self.config["force_threshold_z"]

        # 根据力值动态调整：力大则释放，力小则闭合
        if (abs(force_data["x"]) >= threshold_x or
            abs(force_data["y"]) >= threshold_y or
            abs(force_data["z"]) >= threshold_z):
            # 力值超过阈值，执行释放
            self._release_fingers()
            self.status_signal.emit(f"力值超过阈值，执行释放: X={force_data['x']:.2f}N, Y={force_data['y']:.2f}N, Z={force_data['z']:.2f}N")
        else:
            # 力值低于阈值，执行闭合
            self._close_fingers()
            self.status_signal.emit(f"力值低于阈值，执行闭合: X={force_data['x']:.2f}N, Y={force_data['y']:.2f}N, Z={force_data['z']:.2f}N")

        # 更新进度
        self.iteration_count += 1
        self.progress_signal.emit(self.iteration_count, self.config["max_iterations"])

    def _handle_completed(self):
        """处理完成状态"""
        self.timer.stop()
        self.is_grasping = False
        self.status_signal.emit("自适应抓取完成")
        self.logger.info("自适应抓取流程完成")

    def _get_current_force(self) -> Optional[Dict[str, float]]:
        """
        获取当前力值（多传感器平均）

        Returns:
            力值字典 {"x": float, "y": float, "z": float} 或 None
        """
        if not self.selected_sensors:
            return None

        total_x, total_y, total_z = 0.0, 0.0, 0.0
        valid_count = 0

        for sensor_id in self.selected_sensors:
            sensor_data = self.sensor_data_manager.get_sensor_data(sensor_id)
            if sensor_data and sensor_data.get_data_count() > 0:
                values = sensor_data.get_latest_values()
                total_x += values[0]
                total_y += values[1]
                total_z += values[2]
                valid_count += 1

        if valid_count == 0:
            return None

        force_data = {
            "x": total_x / valid_count,
            "y": total_y / valid_count,
            "z": total_z / valid_count
        }

        # 发送力值更新信号
        self.force_update_signal.emit(force_data)

        return force_data

    def _close_fingers(self):
        """执行手指闭合"""
        if not self.arm_controller or not hasattr(self.arm_controller, 'set_hand_angles'):
            self.logger.warning("机械臂控制器不支持set_hand_angles方法")
            return

        # 更新选定手指的角度
        finger_indices = self.config["finger_indices"]
        close_step = self.config["close_step"]
        max_angle = self.config["max_finger_angle"]

        new_angles = self.current_hand_angles.copy()

        min_angle = self.config.get("min_finger_angle", 0)

        for idx in finger_indices:
            if 0 <= idx < 6:
                # 闭合应使角度减小（设备中较小数值表示闭合），因此减去步长并下限为 min_angle
                new_angles[idx] = max(new_angles[idx] - close_step, min_angle)

        # 执行手指闭合
        try:
            # 注意：set_hand_angles方法不接受speed参数
            self.arm_controller.set_hand_angles(new_angles)
            self.current_hand_angles = new_angles

            fingers_str = ", ".join([f"F{i}:{new_angles[i]}" for i in finger_indices])
            self.status_signal.emit(f"闭合手指 [{fingers_str}] (角度减小)")
            self.logger.debug(f"手指闭合(减小角度): {new_angles}")

            # 等待间隔
            time.sleep(self.config["step_interval"])

        except Exception as e:
            self.logger.error(f"手指闭合失败: {e}")
            self.status_signal.emit(f"手指闭合失败: {str(e)}")

    def _release_fingers(self):
        """执行手指释放（与闭合相反）"""
        if not self.arm_controller or not hasattr(self.arm_controller, 'set_hand_angles'):
            self.logger.warning("机械臂控制器不支持set_hand_angles方法")
            return

        # 更新选定手指的角度
        finger_indices = self.config["finger_indices"]
        release_step = self.config["release_step"]  # 使用独立的释放步长
        max_angle = self.config["max_finger_angle"]

        new_angles = self.current_hand_angles.copy()

        for idx in finger_indices:
            if 0 <= idx < 6:
                # 释放应使角度增大（与闭合相反），因此加上步长并上限为 max_angle
                new_angles[idx] = min(new_angles[idx] + release_step, max_angle)

        # 执行手指释放
        try:
            # 注意：set_hand_angles方法不接受speed参数
            self.arm_controller.set_hand_angles(new_angles)
            self.current_hand_angles = new_angles

            fingers_str = ", ".join([f"F{i}:{new_angles[i]}" for i in finger_indices])
            self.status_signal.emit(f"释放手指 [{fingers_str}] (角度增大)")
            self.logger.debug(f"手指释放(增大角度): {new_angles}")

            # 等待间隔
            time.sleep(self.config["step_interval"])

        except Exception as e:
            self.logger.error(f"手指释放失败: {e}")
            self.status_signal.emit(f"手指释放失败: {str(e)}")

    def get_state_name(self) -> str:
        """
        获取当前状态名称

        Returns:
            状态名称字符串
        """
        state_names = {
            self.IDLE: "空闲",
            self.INITIALIZING: "初始化中",
            self.CLOSING: "手指闭合中",
            self.ANALYZING: "稳定性分析中",
            self.RELEASING: "动态平衡控制中",
            self.COMPLETED: "已完成",
            self.STOPPED: "已停止"
        }
        return state_names.get(self.state, "未知状态")

    def is_running(self) -> bool:
        """
        检查是否正在运行

        Returns:
            是否正在运行
        """
        return self.is_grasping
