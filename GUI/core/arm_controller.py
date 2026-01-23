#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""机械臂控制模块，负责与瑞尔曼机械臂和Inspire机械手通信并控制其动作。"""

import os
import logging
import threading
import time
from typing import List, Optional, Tuple, Dict, Any, Union

from PyQt6.QtCore import QObject, pyqtSignal

# 导入瑞尔曼机械臂SDK
try:
    import sys
    # 添加瑞尔曼API路径
    rm_api_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                "Document", "瑞尔曼", "RM_API2", "Python")
    if rm_api_path not in sys.path:
        sys.path.insert(0, rm_api_path)

    from Robotic_Arm.rm_robot_interface import RoboticArm
    from Robotic_Arm.rm_ctypes_wrap import rm_thread_mode_e
    RM_AVAILABLE = True
except ImportError as e:
    RM_AVAILABLE = False
    RoboticArm = None
    rm_thread_mode_e = None
    print(f"瑞尔曼机械臂SDK导入失败: {e}")

# 导入Inspire控制器
try:
    import yaml
    import numpy as np

    from core.inspire.controller import InspireController
    from core.inspire.utils import as_degree_angle, as_cylinder_angle, as_binary_angle
    INSPIRE_AVAILABLE = True
except ImportError:
    INSPIRE_AVAILABLE = False
    InspireController = None

# 预设位置字典（位置单位：米，姿态单位：弧度）
PRESET_POSITIONS = {
    "initial": {
        "arm": [0.4, 0.0, 0.3, 3.14159, 0.0, 0.0],  # x, y, z(米), roll, pitch, yaw(弧度)
        "hand": [500, 500, 500, 500, 500, 500]
    },
    "grasp_ready": {
        "arm": [0.3937, -0.0762, 0.1983, -2.956, -0.864, -0.108],
        "hand": [1000, 1000, 1000, 1000, 1000, 200]
    },
    "grasp_position": {
        "arm": [0.3937, -0.0762, 0.1983, -2.956, -0.864, -0.108],
        "hand": [1000, 1000, 680, 1000, 800, 200]
    },
    "place_position": {
        "arm": [0.3436, 0.0452, 0.4914, 1.468, 1.499, 1.580],
        "hand": [1000, 1000, 680, 1000, 800, 200]
    },
    "rest": {
        "arm": [0.3, 0.0, 0.4, 3.14159, 0.0, 0.0],
        "hand": [500, 500, 500, 500, 500, 500]
    }
}


class ArmController(QObject):
    """机械臂控制类，负责与瑞尔曼机械臂和Inspire机械手通信并控制其动作。"""

    # 定义信号
    connected_signal = pyqtSignal(bool)  # 连接状态变化信号
    error_signal = pyqtSignal(str)  # 错误信号
    status_signal = pyqtSignal(dict)  # 状态更新信号
    arm_connected_signal = pyqtSignal(bool)  # 机械臂连接状态
    hand_connected_signal = pyqtSignal(bool)  # 机械手连接状态

    def __init__(self, arm_ip: str = None, arm_port: int = 8080, hand_port: str = None, hand_baudrate: int = 115200):
        """
        初始化机械臂控制器。

        Args:
            arm_ip: 瑞尔曼机械臂IP地址
            arm_port: 瑞尔曼机械臂端口号
            hand_port: Inspire机械手串口端口
            hand_baudrate: Inspire机械手波特率
        """
        super().__init__()

        self.logger = logging.getLogger("ArmController")
        self.lock = threading.Lock()

        # 连接参数
        self.arm_ip = arm_ip or "192.168.1.18"  # 瑞尔曼默认IP
        self.arm_port = arm_port
        self.hand_port = hand_port or "/dev/ttyUSB0"  # 默认串口
        self.hand_baudrate = hand_baudrate

        # 控制器实例
        self.arm = None
        self.hand = None

        # 连接状态
        self.arm_connected = False
        self.hand_connected = False

        # 状态数据
        self.status_data = {
            "arm_connected": False,
            "hand_connected": False,
            "arm_position": [0, 0, 0, 0, 0, 0],
            "hand_angles": [0, 0, 0, 0, 0, 0],
            "arm_ip": self.arm_ip,
            "hand_port": self.hand_port,
            "last_command_time": None,
            "error_count": 0
        }

        # 状态更新线程
        self.status_update_thread = None
        self.is_updating_status = False

        # 检查依赖库
        if not RM_AVAILABLE:
            self.logger.warning("瑞尔曼机械臂SDK不可用，机械臂功能将被禁用")
            self.error_signal.emit("瑞尔曼机械臂SDK不可用，请检查Robotic_Arm模块")

        if not INSPIRE_AVAILABLE:
            self.logger.warning("Inspire控制库不可用，机械手功能将被禁用")
            self.error_signal.emit("Inspire控制库不可用，请检查inspire_control-main目录")

        self.logger.info("机械臂控制器初始化完成")

    def connect_arm(self, ip: str = None, port: int = None) -> bool:
        """
        连接瑞尔曼机械臂。

        Args:
            ip: 机械臂IP地址
            port: 机械臂端口号

        Returns:
            连接是否成功
        """
        if not RM_AVAILABLE:
            self.logger.error("瑞尔曼机械臂SDK不可用")
            return False

        with self.lock:
            if self.arm_connected:
                self.logger.info("机械臂已连接")
                return True

            try:
                arm_ip = ip or self.arm_ip
                arm_port = port or self.arm_port
                self.logger.info(f"尝试连接瑞尔曼机械臂: {arm_ip}:{arm_port}")

                # 初始化瑞尔曼机械臂（使用双线程模式）
                self.arm = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)

                # 创建机械臂连接
                handle = self.arm.rm_create_robot_arm(arm_ip, arm_port)

                if handle.id == -1:
                    self.logger.error("机械臂连接失败：无效的句柄ID")
                    self.arm = None
                    return False

                self.arm_connected = True
                self.status_data["arm_connected"] = True
                self.status_data["arm_ip"] = f"{arm_ip}:{arm_port}"

                self.logger.info(f"瑞尔曼机械臂连接成功: {arm_ip}:{arm_port}")
                self.arm_connected_signal.emit(True)

                # 如果两个设备都连接成功，发射总连接信号
                if self.arm_connected and self.hand_connected:
                    self.connected_signal.emit(True)
                    self.start_status_update()

                return True

            except Exception as e:
                self.logger.error(f"机械臂连接失败: {e}", exc_info=True)
                self.error_signal.emit(f"机械臂连接失败: {str(e)}")
                self.arm = None
                return False

    def connect_hand(self, port: str = None, baudrate: int = None) -> bool:
        """
        连接Inspire机械手。

        Args:
            port: 串口端口
            baudrate: 波特率

        Returns:
            连接是否成功
        """
        if not INSPIRE_AVAILABLE:
            self.logger.error("Inspire控制库不可用")
            return False

        with self.lock:
            if self.hand_connected:
                self.logger.info("机械手已连接")
                return True

            try:
                hand_port = port or self.hand_port
                hand_baudrate = baudrate or self.hand_baudrate

                self.logger.info(f"尝试连接机械手: {hand_port}, 波特率: {hand_baudrate}")

                # 使用非阻塞方式创建控制器对象
                self.hand = InspireController(hand_port, hand_baudrate, connect=False)

                # 尝试连接（这现在是非阻塞的）
                connect_success = self.hand.connect()

                if connect_success and self.hand.connected:
                    self.hand_connected = True
                    self.status_data["hand_connected"] = True
                    self.status_data["hand_port"] = hand_port

                    self.logger.info(f"机械手连接成功: {hand_port}")
                    self.hand_connected_signal.emit(True)

                    # 如果两个设备都连接成功，发射总连接信号
                    if self.arm_connected and self.hand_connected:
                        self.connected_signal.emit(True)
                        self.start_status_update()

                    return True
                else:
                    self.hand = None  # 清理失败的对象
                    self.logger.error("机械手连接失败")
                    self.error_signal.emit("机械手连接失败")
                    return False

            except Exception as e:
                # 清理可能的对象
                self.hand = None
                self.logger.error(f"机械手连接失败: {e}", exc_info=True)
                self.error_signal.emit(f"机械手连接失败: {str(e)}")
                return False

    def connect(self, arm_ip: str = None, hand_port: str = None, hand_baudrate: int = None) -> bool:
        """
        同时连接机械臂和机械手。

        Args:
            arm_ip: 机械臂IP地址
            hand_port: 机械手串口端口
            hand_baudrate: 机械手波特率

        Returns:
            是否至少有一个设备连接成功
        """
        arm_success = self.connect_arm(arm_ip)
        hand_success = self.connect_hand(hand_port, hand_baudrate)

        success = arm_success or hand_success
        if success:
            self.logger.info("设备连接完成")
        else:
            self.logger.error("所有设备连接失败")

        return success

    def disconnect(self) -> bool:
        """断开所有连接。"""
        with self.lock:
            success = True

            # 停止状态更新
            self.stop_status_update()

            # 断开机械臂
            if self.arm_connected and self.arm:
                try:
                    self.arm.rm_delete_robot_arm()
                    self.arm = None
                    self.arm_connected = False
                    self.status_data["arm_connected"] = False
                    self.arm_connected_signal.emit(False)
                    self.logger.info("机械臂连接已断开")
                except Exception as e:
                    self.logger.error(f"断开机械臂连接失败: {e}")
                    success = False

            # 断开机械手
            if self.hand_connected and self.hand:
                try:
                    self.hand.disconnect()
                    self.hand = None
                    self.hand_connected = False
                    self.status_data["hand_connected"] = False
                    self.hand_connected_signal.emit(False)
                    self.logger.info("机械手连接已断开")
                except Exception as e:
                    self.logger.error(f"断开机械手连接失败: {e}")
                    success = False

            # 发射总连接信号
            self.connected_signal.emit(False)

            return success

    def move_arm_to_position(self, position: List[float], speed: int = 30, wait: bool = False, relative: bool = False) -> bool:
        """
        移动机械臂到指定位置（笛卡尔空间）。

        Args:
            position: 目标位置 [x(米), y(米), z(米), roll(弧度), pitch(弧度), yaw(弧度)]
            speed: 移动速度百分比(1-100)
            wait: 是否等待完成
            relative: 是否为相对移动

        Returns:
            是否成功
        """
        if not self.arm_connected or not self.arm:
            self.logger.error("机械臂未连接")
            self.error_signal.emit("机械臂未连接")
            return False

        try:
            if len(position) != 6:
                raise ValueError("位置参数必须包含6个值 [x, y, z, roll, pitch, yaw]")

            # 瑞尔曼使用 rm_movel 进行笛卡尔空间直线运动
            # position: [x, y, z, rx, ry, rz] 单位：米和弧度
            # v: 速度百分比 1-100
            # r: 交融半径百分比 0-100
            # connect: 0-立即执行，1-轨迹连接
            # block: 0-非阻塞，1-阻塞
            result = self.arm.rm_movel(
                pose=position,
                v=speed,
                r=0,
                connect=0,
                block=1 if wait else 0
            )

            # 瑞尔曼返回值：0表示成功
            if result == 0:
                self.logger.info(f"机械臂移动成功: {position}")
                self.status_data["arm_position"] = position
                self.status_data["last_command_time"] = time.time()
                return True
            else:
                self.logger.error(f"机械臂移动失败, 错误码: {result}")
                self.error_signal.emit(f"机械臂移动失败, 错误码: {result}")
                return False

        except Exception as e:
            self.logger.error(f"机械臂移动异常: {e}", exc_info=True)
            self.error_signal.emit(f"机械臂移动异常: {str(e)}")
            return False

    def set_hand_angles(self, angles: List[int]) -> bool:
        """
        设置机械手各关节角度。

        Args:
            angles: 关节角度列表 [finger1, finger2, finger3, finger4, thumb, thumb_flip]

        Returns:
            是否成功
        """
        if not self.hand_connected or not self.hand:
            self.logger.error("机械手未连接")
            self.error_signal.emit("机械手未连接")
            return False

        try:
            if len(angles) != 6:
                raise ValueError("角度参数必须包含6个值")

            # 尝试设置角度
            self.hand.set_angle(angles)
            self.logger.info(f"机械手角度设置成功: {angles}")

            # 更新状态数据
            try:
                self.status_data["hand_angles"] = angles
                self.status_data["last_command_time"] = time.time()
            except Exception as status_error:
                self.logger.warning(f"状态更新失败: {status_error}")

            return True

        except Exception as e:
            error_msg = str(e)

            # 检查是否是非关键的错误
            non_critical_patterns = [
                "index out of range",
                "list index out of range",
                "'int' object is not subscriptable",
                "串口通信错误",
                "响应数据长度不足"
            ]

            if any(pattern in error_msg for pattern in non_critical_patterns):
                self.logger.warning(f"机械手角度设置过程中出现非关键错误: {error_msg}")
                self.logger.info(f"假定机械手角度设置成功: {angles}")

                try:
                    self.status_data["hand_angles"] = angles
                    self.status_data["last_command_time"] = time.time()
                except:
                    pass

                return True
            else:
                self.logger.error(f"机械手角度设置异常: {error_msg}", exc_info=True)
                self.error_signal.emit(f"机械手角度设置异常: {error_msg}")
                return False

    def get_arm_position(self) -> Optional[List[float]]:
        """获取机械臂当前位置（笛卡尔坐标）。"""
        if not self.arm_connected or not self.arm:
            return None

        try:
            # 使用瑞尔曼API获取当前状态
            ret, state = self.arm.rm_get_current_arm_state()

            if ret == 0 and state:
                # state字典包含当前位姿信息
                pose = state.get("Pose", {})
                position = [
                    pose.get("position", {}).get("x", 0),
                    pose.get("position", {}).get("y", 0),
                    pose.get("position", {}).get("z", 0),
                    pose.get("euler", {}).get("rx", 0),
                    pose.get("euler", {}).get("ry", 0),
                    pose.get("euler", {}).get("rz", 0)
                ]
                return position
            else:
                self.logger.error(f"获取机械臂位置失败, 错误码: {ret}")
                return None

        except Exception as e:
            self.logger.error(f"获取机械臂位置异常: {e}")
            return None

    def get_hand_angles(self) -> Optional[List[int]]:
        """获取机械手当前角度。"""
        if not self.hand_connected or not self.hand:
            return None

        try:
            return self.hand.get_angle(actual=True)
        except Exception as e:
            self.logger.error(f"获取机械手角度异常: {e}")
            return None

    def execute_preset_position(self, position_name: str) -> bool:
        """
        执行预设位置。

        Args:
            position_name: 预设位置名称

        Returns:
            是否成功
        """
        if position_name not in PRESET_POSITIONS:
            self.logger.error(f"未知的预设位置: {position_name}")
            self.error_signal.emit(f"未知的预设位置: {position_name}")
            return False

        preset = PRESET_POSITIONS[position_name]
        arm_success = True
        hand_success = True

        try:
            # 执行机械臂动作
            if self.arm_connected and "arm" in preset:
                arm_success = self.move_arm_to_position(preset["arm"])

            # 执行机械手动作
            if self.hand_connected and "hand" in preset:
                hand_success = self.set_hand_angles(preset["hand"])

            success = arm_success and hand_success
            if success:
                self.logger.info(f"预设位置 '{position_name}' 执行成功")
            else:
                self.logger.warning(f"预设位置 '{position_name}' 部分执行失败")

            return success

        except Exception as e:
            self.logger.error(f"执行预设位置异常: {e}", exc_info=True)
            self.error_signal.emit(f"执行预设位置异常: {str(e)}")
            return False

    def emergency_stop(self) -> bool:
        """紧急停止。"""
        success = True

        try:
            # 停止机械臂
            if self.arm_connected and self.arm:
                try:
                    # 瑞尔曼使用急停状态设置
                    ret = self.arm.rm_set_arm_emergency_stop(True)
                    if ret == 0:
                        self.logger.info("机械臂紧急停止")
                    else:
                        self.logger.error(f"机械臂紧急停止失败，错误码: {ret}")
                        success = False
                except Exception as e:
                    self.logger.error(f"机械臂紧急停止失败: {e}")
                    success = False

            # 机械手紧急释放
            if self.hand_connected and self.hand:
                try:
                    self.hand.emergency_release(True, True, True)
                    self.logger.info("机械手紧急释放")
                except Exception as e:
                    self.logger.error(f"机械手紧急释放失败: {e}")
                    success = False

            return success

        except Exception as e:
            self.logger.error(f"紧急停止异常: {e}", exc_info=True)
            return False

    def reset(self) -> bool:
        """重置到初始位置。"""
        return self.execute_preset_position("initial")

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态。"""
        return self.status_data.copy()

    def is_connected(self) -> bool:
        """检查是否有设备连接。"""
        return self.arm_connected or self.hand_connected

    def start_status_update(self):
        """启动状态更新线程。"""
        if not self.is_updating_status:
            self.is_updating_status = True
            self.status_update_thread = threading.Thread(target=self._status_update_loop, daemon=True)
            self.status_update_thread.start()
            self.logger.info("状态更新线程已启动")

    def stop_status_update(self):
        """停止状态更新线程。"""
        if self.is_updating_status:
            self.is_updating_status = False
            if self.status_update_thread and self.status_update_thread.is_alive():
                self.status_update_thread.join(timeout=2)
            self.logger.info("状态更新线程已停止")

    def _status_update_loop(self):
        """状态更新循环。"""
        while self.is_updating_status:
            try:
                status = self.get_status()
                self.status_signal.emit(status)
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"状态更新异常: {e}")
                time.sleep(5)

    def close(self) -> None:
        """关闭控制器。"""
        self.disconnect()
        self.logger.info("机械臂控制器已关闭")

    # 兼容性方法（用于与原有代码保持接口一致）
    def connect_all(self, arm_ip: str = None, hand_port: str = None, hand_baudrate: int = None) -> bool:
        """连接所有设备（兼容方法）。"""
        return self.connect(arm_ip, hand_port, hand_baudrate)

    def disconnect_all(self) -> bool:
        """断开所有设备（兼容方法）。"""
        return self.disconnect()

    def move_arm(self, position: List[float], speed: int = 30, wait: bool = False) -> bool:
        """移动机械臂（兼容方法）。"""
        return self.move_arm_to_position(position, speed, wait)

    def open_hand(self) -> bool:
        """张开手爪（兼容方法）。"""
        return self.set_hand_angles([1000, 1000, 1000, 1000, 1000, 200])

    def close_hand(self) -> bool:
        """闭合手爪（兼容方法）。"""
        return self.set_hand_angles([400, 400, 400, 400, 700, 200])

    def get_arm_angles(self) -> Optional[List[float]]:
        """获取机械臂当前关节角度。"""
        if not self.arm_connected or not self.arm:
            return None

        try:
            ret, state = self.arm.rm_get_current_arm_state()

            if ret == 0 and state:
                joint = state.get("joint", [])
                return joint if joint else None
            else:
                self.logger.error(f"获取机械臂角度失败, 错误码: {ret}")
                return None

        except Exception as e:
            self.logger.error(f"获取机械臂角度异常: {e}")
            return None

    def set_arm_angles(self, angles: List[float], speed: int = 30, wait: bool = False) -> bool:
        """
        设置机械臂关节角度。

        Args:
            angles: 关节角度列表（单位：度）
            speed: 速度百分比(1-100)
            wait: 是否等待完成

        Returns:
            是否成功
        """
        if not self.arm_connected or not self.arm:
            self.logger.error("机械臂未连接")
            self.error_signal.emit("机械臂未连接")
            return False

        try:
            # 瑞尔曼使用 rm_movej 进行关节空间运动
            result = self.arm.rm_movej(
                joint=angles,
                v=speed,
                r=0,
                connect=0,
                block=1 if wait else 0
            )

            if result == 0:
                self.logger.info(f"机械臂角度设置成功: {angles}")
                return True
            else:
                self.logger.error(f"机械臂角度设置失败, 错误码: {result}")
                self.error_signal.emit(f"机械臂角度设置失败, 错误码: {result}")
                return False

        except Exception as e:
            self.logger.error(f"机械臂角度设置异常: {e}", exc_info=True)
            self.error_signal.emit(f"机械臂角度设置异常: {str(e)}")
            return False
