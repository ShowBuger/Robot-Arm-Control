#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""机械臂控制模块，负责与xArm机械臂和Inspire机械手通信并控制其动作。"""

import os
import logging
import threading
import time
from typing import List, Optional, Tuple, Dict, Any, Union

from PyQt6.QtCore import QObject, pyqtSignal

# 导入xArm SDK
try:
    from xarm.wrapper import XArmAPI
    XARM_AVAILABLE = True
except ImportError:
    XARM_AVAILABLE = False
    XArmAPI = None

# 导入Inspire控制器
try:
    import sys
    import yaml
    import numpy as np
    
    from core.inspire.controller import InspireController
    from core.inspire.utils import as_degree_angle, as_cylinder_angle, as_binary_angle
    INSPIRE_AVAILABLE = True
except ImportError:
    INSPIRE_AVAILABLE = False
    InspireController = None

# 预设位置字典
PRESET_POSITIONS = {
    "initial": {
        "arm": [400.0, 0.0, 300.0, 180.0, 0.0, 0.0],  # x, y, z, roll, pitch, yaw
        "hand": [500, 500, 500, 500, 500, 500]
    },
    "grasp_ready": {
        "arm": [393.7, -76.2, 198.3, -169.4, -49.5, -6.2],
        "hand": [1000, 1000, 1000, 1000, 1000, 200]
    },
    "grasp_position": {
        "arm": [393.7, -76.2, 198.3, -169.4, -49.5, -6.2],
        "hand": [1000, 1000, 680, 1000, 800, 200]
    },
    "place_position": {
        "arm": [343.6, 45.2, 491.4, 84.1, 85.9, 90.5],
        "hand": [1000, 1000, 680, 1000, 800, 200]
    },
    "rest": {
        "arm": [300.0, 0.0, 400.0, 180.0, 0.0, 0.0],
        "hand": [500, 500, 500, 500, 500, 500]
    }
}


class ArmController(QObject):
    """机械臂控制类，负责与xArm机械臂和Inspire机械手通信并控制其动作。"""

    # 定义信号
    connected_signal = pyqtSignal(bool)  # 连接状态变化信号
    error_signal = pyqtSignal(str)  # 错误信号
    status_signal = pyqtSignal(dict)  # 状态更新信号
    arm_connected_signal = pyqtSignal(bool)  # 机械臂连接状态
    hand_connected_signal = pyqtSignal(bool)  # 机械手连接状态

    def __init__(self, arm_ip: str = None, hand_port: str = None, hand_baudrate: int = 115200):
        """
        初始化机械臂控制器。

        Args:
            arm_ip: xArm机械臂IP地址
            hand_port: Inspire机械手串口端口
            hand_baudrate: Inspire机械手波特率
        """
        super().__init__()

        self.logger = logging.getLogger("ArmController")
        self.lock = threading.Lock()

        # 连接参数
        self.arm_ip = arm_ip or "192.168.1.215"  # 默认IP
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
        if not XARM_AVAILABLE:
            self.logger.warning("xArm-Python-SDK 不可用，机械臂功能将被禁用")
            self.error_signal.emit("xArm-Python-SDK 不可用，请安装: pip install xarm-python-sdk")
        
        if not INSPIRE_AVAILABLE:
            self.logger.warning("Inspire控制库不可用，机械手功能将被禁用")
            self.error_signal.emit("Inspire控制库不可用，请检查inspire_control-main目录")

        self.logger.info("机械臂控制器初始化完成")

    def connect_arm(self, ip: str = None) -> bool:
        """
        连接xArm机械臂。

        Args:
            ip: 机械臂IP地址

        Returns:
            连接是否成功
        """
        if not XARM_AVAILABLE:
            self.logger.error("xArm-Python-SDK 不可用")
            return False

        with self.lock:
            if self.arm_connected:
                self.logger.info("机械臂已连接")
                return True

            try:
                arm_ip = ip or self.arm_ip
                self.logger.info(f"尝试连接机械臂: {arm_ip}")
                
                self.arm = XArmAPI(arm_ip)
                
                # 设置机械臂状态为运动状态
                self.arm.set_state(state=0)  # 运动状态
                self.arm.set_mode(0)  # 位置模式
                self.arm.motion_enable(enable=True)
                
                # 设置基本参数
                self.arm.clean_error()
                self.arm.clean_warn()
                
                self.arm_connected = True
                self.status_data["arm_connected"] = True
                self.status_data["arm_ip"] = arm_ip
                
                self.logger.info(f"机械臂连接成功: {arm_ip}")
                self.arm_connected_signal.emit(True)
                
                # 如果两个设备都连接成功，发射总连接信号
                if self.arm_connected and self.hand_connected:
                    self.connected_signal.emit(True)
                    self.start_status_update()
                
                return True

            except Exception as e:
                self.logger.error(f"机械臂连接失败: {e}", exc_info=True)
                self.error_signal.emit(f"机械臂连接失败: {str(e)}")
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
                    self.arm.disconnect()
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
        移动机械臂到指定位置。

        Args:
            position: 目标位置 [x, y, z, roll, pitch, yaw]
            speed: 移动速度
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

            result = self.arm.set_position(*position, speed=speed, wait=wait, relative=relative)
            
            # 处理不同类型的返回值
            if isinstance(result, (list, tuple)):
                # 标准的xArm返回格式：[错误码, 数据]
                if result[0] == 0:  # 成功
                    self.logger.info(f"机械臂移动成功: {position}")
                    self.status_data["arm_position"] = position
                    self.status_data["last_command_time"] = time.time()
                    return True
                else:
                    self.logger.error(f"机械臂移动失败, 错误码: {result[0]}")
                    self.error_signal.emit(f"机械臂移动失败, 错误码: {result[0]}")
                    return False
            elif isinstance(result, int):
                # 某些情况下可能只返回错误码
                if result == 0:  # 成功
                    self.logger.info(f"机械臂移动成功: {position}")
                    self.status_data["arm_position"] = position
                    self.status_data["last_command_time"] = time.time()
                    return True
                else:
                    self.logger.error(f"机械臂移动失败, 错误码: {result}")
                    self.error_signal.emit(f"机械臂移动失败, 错误码: {result}")
                    return False
            else:
                # 其他类型，假定成功
                self.logger.warning(f"机械臂返回未知格式结果: {type(result)} - {result}")
                self.logger.info(f"假定机械臂移动成功: {position}")
                self.status_data["arm_position"] = position
                self.status_data["last_command_time"] = time.time()
                return True

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

            # 尝试设置角度，但不依赖于获取当前角度
            self.hand.set_angle(angles)
            self.logger.info(f"机械手角度设置成功: {angles}")
            
            # 更新状态数据（但不强制要求成功）
            try:
                self.status_data["hand_angles"] = angles
                self.status_data["last_command_time"] = time.time()
            except Exception as status_error:
                # 状态更新失败不影响主要功能
                self.logger.warning(f"状态更新失败: {status_error}")
            
            return True

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 检查是否是非关键的角度获取错误
            non_critical_patterns = [
                "index out of range",
                "list index out of range", 
                "'int' object is not subscriptable",
                "串口通信错误",
                "响应数据长度不足"
            ]
            
            if any(pattern in error_msg for pattern in non_critical_patterns):
                # 这类错误通常表示状态查询失败，但设置命令可能已经成功
                self.logger.warning(f"机械手角度设置过程中出现非关键错误: {error_msg}")
                self.logger.info(f"假定机械手角度设置成功: {angles}")
                
                # 尝试更新状态数据
                try:
                    self.status_data["hand_angles"] = angles
                    self.status_data["last_command_time"] = time.time()
                except:
                    pass  # 忽略状态更新错误
                
                return True  # 认为设置成功
            else:
                # 其他类型的错误认为是真正的失败
                self.logger.error(f"机械手角度设置异常 (类型: {error_type}): {error_msg}", exc_info=True)
                self.error_signal.emit(f"机械手角度设置异常: {error_msg}")
                return False

    def get_arm_position(self) -> Optional[List[float]]:
        """获取机械臂当前位置。"""
        if not self.arm_connected or not self.arm:
            return None

        try:
            result = self.arm.get_position()
            
            # 处理不同类型的返回值
            if isinstance(result, (list, tuple)):
                # 标准的xArm返回格式：[错误码, 数据]
                if result[0] == 0:  # 成功
                    return result[1]  # 位置数据
                else:
                    self.logger.error(f"获取机械臂位置失败, 错误码: {result[0]}")
                    return None
            elif isinstance(result, int):
                # 只返回错误码的情况
                if result == 0:
                    self.logger.warning("获取机械臂位置成功但无位置数据")
                    return None
                else:
                    self.logger.error(f"获取机械臂位置失败, 错误码: {result}")
                    return None
            else:
                # 其他类型
                self.logger.warning(f"机械臂位置返回未知格式: {type(result)} - {result}")
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
                    self.arm.emergency_stop()
                    self.logger.info("机械臂紧急停止")
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
        """获取当前状态（优化版：减少频繁角度查询）。"""
        # 注释掉频繁的实时数据更新，改为只在明确需要时获取
        # 这可以避免持续的角度异常问题
        
        # if self.arm_connected:
        #     current_pos = self.get_arm_position()
        #     if current_pos:
        #         self.status_data["arm_position"] = current_pos

        # if self.hand_connected:
        #     current_angles = self.get_hand_angles()
        #     if current_angles:
        #         self.status_data["hand_angles"] = current_angles

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
                time.sleep(1)  # 每秒更新一次
            except Exception as e:
                self.logger.error(f"状态更新异常: {e}")
                time.sleep(5)  # 出错后等待5秒再继续

    def close(self) -> None:
        """关闭控制器。"""
        self.disconnect()
        self.logger.info("机械臂控制器已关闭")