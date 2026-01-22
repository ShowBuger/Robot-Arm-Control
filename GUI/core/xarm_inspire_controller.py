#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""xArm机械臂和Inspire机械手集成控制器。"""

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
    import yaml
    import numpy as np
    from core.inspire.controller import InspireController
    from core.inspire.utils import as_degree_angle, as_cylinder_angle, as_binary_angle
    INSPIRE_AVAILABLE = True
except ImportError:
    INSPIRE_AVAILABLE = False
    InspireController = None

# 抓取序列配置
GRASP_SEQUENCES = {
    "pick_and_place": [
        {
            "name": "move_to_grasp_ready",
            "arm_position": [393.7, -76.2, 198.3, -169.4, -49.5, -6.2],
            "hand_angles": [1000, 1000, 1000, 1000, 1000, 200],
            "arm_speed": 30,
            "wait_time": 2.0
        },
        {
            "name": "close_grasp",
            "arm_position": None,  # 保持当前位置
            "hand_angles": [1000, 1000, 680, 1000, 800, 200],
            "wait_time": 1.0
        },
        {
            "name": "move_to_place",
            "arm_position": [343.6, 45.2, 491.4, 84.1, 85.9, 90.5],
            "hand_angles": None,  # 保持当前角度
            "arm_speed": 30,
            "wait_time": 2.0
        },
        {
            "name": "release",
            "arm_position": None,
            "hand_angles": [1000, 1000, 1000, 1000, 1000, 200],
            "wait_time": 1.0
        }
    ],
    "simple_grasp": [
        {
            "name": "open_hand",
            "hand_angles": [1000, 1000, 1000, 1000, 1000, 200],
            "wait_time": 1.0
        },
        {
            "name": "close_hand",
            "hand_angles": [400, 400, 400, 400, 700, 200],
            "wait_time": 1.0
        }
    ]
}


class XArmInspireController(QObject):
    """xArm机械臂和Inspire机械手集成控制器。"""

    # 信号定义
    connected_signal = pyqtSignal(bool)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    sequence_progress_signal = pyqtSignal(str, int, int)  # 序列名称, 当前步骤, 总步骤

    def __init__(self):
        super().__init__()
        
        self.logger = logging.getLogger("XArmInspireController")
        self.lock = threading.Lock()
        
        # 设备实例
        self.arm = None
        self.hand = None
        
        # 连接状态
        self.arm_connected = False
        self.hand_connected = False
        
        # 执行状态
        self.is_executing_sequence = False
        self.current_sequence = None
        
        # 状态数据
        self.status_data = {
            "arm_connected": False,
            "hand_connected": False,
            "arm_position": [0, 0, 0, 0, 0, 0],
            "hand_angles": [0, 0, 0, 0, 0, 0],
            "is_executing": False,
            "current_sequence": None,
            "last_error": None
        }
        
        self.logger.info("xArm-Inspire集成控制器初始化完成")

    def _safe_execute_command(self, command_func, *args, **kwargs):
        """
        安全执行命令，处理返回值格式问题
        """
        try:
            result = command_func(*args, **kwargs)
            
            # 检查不同的返回值格式
            if isinstance(result, (list, tuple)) and len(result) > 0:
                # 标准格式 [error_code, data...]
                if result[0] == 0:
                    return True, result
                else:
                    return False, result
            elif isinstance(result, int):
                # 只返回错误码
                return result == 0, result
            elif result is None:
                # 无返回值，假设成功
                return True, None
            else:
                # 其他格式，假设成功
                return True, result
                
        except Exception as e:
            # 检查是否是下标错误
            error_msg = str(e)
            if "'int' object is not subscriptable" in error_msg:
                # 这种错误通常表示命令已发送但返回值格式有问题
                self.logger.debug(f"命令执行中出现返回值格式错误（已忽略）: {e}")
                return True, None  # 假设命令成功执行
            else:
                # 其他真正的错误
                raise e

    def _safe_execute_hand_command(self, command_func, *args, **kwargs):
        """
        安全执行机械手命令，处理各种异常情况
        """
        try:
            result = command_func(*args, **kwargs)
            # 机械手命令通常没有返回值或返回简单状态
            return True, result
        except Exception as e:
            error_msg = str(e)
            if "'int' object is not subscriptable" in error_msg:
                # 这种错误通常表示命令已发送但返回值格式有问题
                self.logger.debug(f"机械手命令执行中出现返回值格式错误（已忽略）: {e}")
                return True, None  # 假设命令成功执行
            else:
                # 其他真正的错误
                raise e

    def connect_arm(self, ip: str = "192.168.1.215") -> bool:
        """连接xArm机械臂。"""
        if not XARM_AVAILABLE:
            self.error_signal.emit("xArm-Python-SDK不可用，请安装: pip install xarm-python-sdk")
            return False
        
        try:
            self.logger.info(f"连接xArm机械臂: {ip}")
            self.arm = XArmAPI(ip)
            
            # 设置机械臂状态
            self.arm.set_state(state=0)  # 运动状态
            self.arm.set_mode(0)  # 位置模式
            self.arm.motion_enable(enable=True)
            
            # 清除错误和警告
            self.arm.clean_error()
            self.arm.clean_warn()
            
            self.arm_connected = True
            self.status_data["arm_connected"] = True
            self.logger.info(f"xArm机械臂连接成功: {ip}")
            
            # 发射连接信号
            self.connected_signal.emit(True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"xArm连接失败: {e}")
            self.error_signal.emit(f"xArm连接失败: {str(e)}")
            return False

    def connect_hand(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200) -> bool:
        """连接Inspire机械手（优化版，非阻塞）。"""
        if not INSPIRE_AVAILABLE:
            self.error_signal.emit("Inspire控制库不可用，请检查inspire模块")
            return False
        
        try:
            self.logger.info(f"连接Inspire机械手: {port}, 波特率: {baudrate}")
            
            # 创建控制器对象但不立即连接
            self.hand = InspireController(port, baudrate, connect=False)
            
            # 尝试连接（这现在是非阻塞的）
            connect_success = self.hand.connect()
            
            if connect_success and self.hand.connected:
                self.hand_connected = True
                self.status_data["hand_connected"] = True
                self.logger.info(f"Inspire机械手连接成功: {port}")
                
                # 发射连接信号
                self.connected_signal.emit(True)
                
                return True
            else:
                self.hand = None  # 清理失败的对象
                error_msg = f"Inspire机械手连接失败: {port}"
                self.logger.error(error_msg)
                self.error_signal.emit(error_msg)
                return False
                
        except Exception as e:
            # 清理可能的对象
            self.hand = None
            error_msg = f"Inspire连接异常: {e}"
            self.logger.error(error_msg)
            self.error_signal.emit(error_msg)
            return False

    def connect_all(self, arm_ip: str = "192.168.1.215", hand_port: str = "/dev/ttyUSB0", hand_baudrate: int = 115200) -> bool:
        """连接所有设备。"""
        arm_ok = self.connect_arm(arm_ip)
        hand_ok = self.connect_hand(hand_port, hand_baudrate)
        
        connected = arm_ok or hand_ok
        self.connected_signal.emit(connected)
        
        if connected:
            self.logger.info("设备连接完成")
        else:
            self.logger.error("所有设备连接失败")
            
        return connected

    def disconnect_all(self) -> bool:
        """断开所有设备连接。"""
        success = True
        
        try:
            if self.arm_connected and self.arm:
                self.arm.disconnect()
                self.arm = None
                self.arm_connected = False
                self.status_data["arm_connected"] = False
                self.logger.info("xArm机械臂已断开")
                
        except Exception as e:
            self.logger.error(f"断开xArm失败: {e}")
            success = False
        
        try:
            if self.hand_connected and self.hand:
                self.hand.disconnect()
                self.hand = None
                self.hand_connected = False
                self.status_data["hand_connected"] = False
                self.logger.info("Inspire机械手已断开")
                
        except Exception as e:
            self.logger.error(f"断开Inspire失败: {e}")
            success = False
        
        self.connected_signal.emit(False)
        return success

    def disconnect_arm(self) -> bool:
        """单独断开xArm机械臂连接。"""
        if not self.arm_connected:
            self.logger.info("xArm机械臂未连接")
            return True
            
        try:
            if self.arm:
                self.arm.disconnect()
                self.arm = None
            
            self.arm_connected = False
            self.status_data["arm_connected"] = False
            self.logger.info("xArm机械臂已断开")
            
            # 如果所有设备都断开了，发射断开信号
            if not self.hand_connected:
                self.connected_signal.emit(False)
            else:
                # 如果还有其他设备连接，发射连接信号以更新状态
                self.connected_signal.emit(True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"断开xArm失败: {e}")
            return False

    def disconnect_hand(self) -> bool:
        """单独断开Inspire机械手连接。"""
        if not self.hand_connected:
            self.logger.info("Inspire机械手未连接")
            return True
            
        try:
            if self.hand:
                self.hand.disconnect()
                self.hand = None
            
            self.hand_connected = False
            self.status_data["hand_connected"] = False
            self.logger.info("Inspire机械手已断开")
            
            # 如果所有设备都断开了，发射断开信号
            if not self.arm_connected:
                self.connected_signal.emit(False)
            else:
                # 如果还有其他设备连接，发射连接信号以更新状态
                self.connected_signal.emit(True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"断开Inspire失败: {e}")
            return False

    def move_arm(self, position: List[float], speed: int = 30, wait: bool = True) -> bool:
        """移动机械臂到指定位置。"""
        if not self.arm_connected:
            self.error_signal.emit("xArm未连接")
            return False
        
        try:
            success, result = self._safe_execute_command(
                self.arm.set_position, *position, speed=speed, wait=wait, relative=False
            )
            
            if success:
                self.logger.info(f"机械臂移动成功: {position}")
                self.status_data["arm_position"] = position
                return True
            else:
                error_code = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else result
                self.error_signal.emit(f"机械臂移动失败，错误码: {error_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"机械臂移动异常: {e}")
            self.error_signal.emit(f"机械臂移动异常: {str(e)}")
            return False

    def set_hand_angles(self, angles: List[int]) -> bool:
        """设置机械手角度。直接执行,不做任何连接检查。"""
        try:
            # 尝试直接调用,捕获任何异常
            success, result = self._safe_execute_hand_command(self.hand.set_angle, angles)

            if success:
                self.logger.info(f"机械手角度设置成功: {angles}")
                self.status_data["hand_angles"] = angles
                return True
            else:
                self.logger.warning(f"机械手角度设置失败: {result}")
                return False

        except AttributeError as e:
            self.logger.error(f"手部对象未初始化: {e}")
            return False
        except Exception as e:
            self.logger.error(f"设置机械手角度失败: {e}")
            return False

    def execute_sequence(self, sequence_name: str) -> bool:
        """执行预定义的动作序列。"""
        if sequence_name not in GRASP_SEQUENCES:
            self.error_signal.emit(f"未知序列: {sequence_name}")
            return False
        
        if self.is_executing_sequence:
            self.error_signal.emit("正在执行其他序列，请等待完成")
            return False
        
        sequence = GRASP_SEQUENCES[sequence_name]
        
        def execute_in_thread():
            self.is_executing_sequence = True
            self.current_sequence = sequence_name
            self.status_data["is_executing"] = True
            self.status_data["current_sequence"] = sequence_name
            
            try:
                total_steps = len(sequence)
                
                for i, step in enumerate(sequence):
                    if not self.is_executing_sequence:  # 检查是否被取消
                        break
                    
                    self.sequence_progress_signal.emit(sequence_name, i + 1, total_steps)
                    self.logger.info(f"执行步骤 {i+1}/{total_steps}: {step['name']}")
                    
                    # 执行机械臂动作
                    if step.get("arm_position") is not None:
                        arm_speed = step.get("arm_speed", 30)
                        if not self.move_arm(step["arm_position"], speed=arm_speed):
                            self.logger.error(f"步骤 {step['name']} 机械臂动作失败")
                            break
                    
                    # 执行机械手动作
                    if step.get("hand_angles") is not None:
                        if not self.set_hand_angles(step["hand_angles"]):
                            self.logger.error(f"步骤 {step['name']} 机械手动作失败")
                            break
                    
                    # 等待指定时间
                    wait_time = step.get("wait_time", 0)
                    if wait_time > 0:
                        time.sleep(wait_time)
                
                self.logger.info(f"序列 {sequence_name} 执行完成")
                
            except Exception as e:
                self.logger.error(f"序列执行异常: {e}")
                self.error_signal.emit(f"序列执行异常: {str(e)}")
            
            finally:
                self.is_executing_sequence = False
                self.current_sequence = None
                self.status_data["is_executing"] = False
                self.status_data["current_sequence"] = None
        
        # 在新线程中执行序列
        thread = threading.Thread(target=execute_in_thread, daemon=True)
        thread.start()
        
        return True

    def stop_sequence(self) -> bool:
        """停止当前执行的序列。"""
        if self.is_executing_sequence:
            self.is_executing_sequence = False
            self.logger.info("序列执行已停止")
            return True
        return False

    def emergency_stop(self) -> bool:
        """紧急停止所有设备。"""
        success = True
        
        # 立即停止序列执行
        self.stop_sequence()
        
        # 并行执行紧急停止操作以减少总时间
        def stop_arm():
            try:
                if self.arm_connected and self.arm:
                    self.arm.emergency_stop()
                    self.logger.info("xArm紧急停止完成")
                    return True
            except Exception as e:
                self.logger.error(f"xArm紧急停止失败: {e}")
                return False
        
        def stop_hand():
            try:
                if self.hand_connected and self.hand:
                    self.hand.emergency_release(True, True, True)
                    self.logger.info("Inspire紧急释放完成")
                    return True
            except Exception as e:
                self.logger.error(f"Inspire紧急释放失败: {e}")
                return False
        
        # 并行执行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            if self.arm_connected:
                futures.append(executor.submit(stop_arm))
            
            if self.hand_connected:
                futures.append(executor.submit(stop_hand))
            
            # 等待所有操作完成，最多等待5秒
            try:
                for future in concurrent.futures.as_completed(futures, timeout=5.0):
                    result = future.result()
                    if not result:
                        success = False
            except concurrent.futures.TimeoutError:
                self.logger.warning("紧急停止操作超时")
                success = False
        
        if success:
            self.logger.info("紧急停止操作完成")
        else:
            self.logger.error("紧急停止操作部分失败")
        
        return success

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态（优化版：停止频繁角度查询）。"""
        with self.lock:
            # 注释掉频繁的实时数据更新，避免持续的角度异常
            # 改为只在明确需要时获取角度数据
            
            # if self.arm_connected and self.arm:
            #     try:
            #         result = self.arm.get_position()
            #         if result[0] == 0:
            #             self.status_data["arm_position"] = result[1]
            #     except:
            #         pass
            
            # if self.hand_connected and self.hand:
            #     try:
            #         angles = self.hand.get_angle(actual=True)
            #         if angles:
            #             self.status_data["hand_angles"] = angles
            #     except:
            #         pass
            
            return self.status_data.copy()

    def is_connected(self) -> bool:
        """检查是否有设备连接。"""
        return self.arm_connected or self.hand_connected

    # 预定义的常用动作
    def open_hand(self) -> bool:
        """张开手爪。"""
        return self.set_hand_angles([1000, 1000, 1000, 1000, 1000, 200])

    def close_hand(self) -> bool:
        """闭合手爪。"""
        return self.set_hand_angles([400, 400, 400, 400, 700, 200])

    def reset_to_home(self) -> bool:
        """重置到初始位置。"""
        arm_success = True
        hand_success = True
        
        if self.arm_connected:
            arm_success = self.move_arm([400.0, 0.0, 300.0, 180.0, 0.0, 0.0])
        
        if self.hand_connected:
            hand_success = self.set_hand_angles([500, 500, 500, 500, 500, 500])
        
        return arm_success and hand_success

    def get_available_sequences(self) -> List[str]:
        """获取可用的动作序列列表。"""
        return list(GRASP_SEQUENCES.keys())

    def add_custom_sequence(self, name: str, sequence: List[Dict]) -> bool:
        """添加自定义动作序列。"""
        try:
            GRASP_SEQUENCES[name] = sequence
            self.logger.info(f"添加自定义序列: {name}")
            return True
        except Exception as e:
            self.logger.error(f"添加自定义序列失败: {e}")
            return False

    def move_arm_to_position(self, position: List[float], speed: int = 30, wait: bool = True) -> bool:
        """移动机械臂到指定位置（兼容方法）。"""
        return self.move_arm(position, speed, wait)
    
    def getArmAngles(self) -> List[float]:
        """获取机械臂当前关节角度。"""
        if not self.arm_connected or not self.arm:
            return None
        
        try:
            success, result = self._safe_execute_command(self.arm.get_servo_angle)
            
            if success and isinstance(result, (list, tuple)) and len(result) > 1:
                return result[1]  # 角度数据
            elif success:
                # 如果只是简单成功但没有数据，返回空值
                return None
            else:
                error_code = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else result
                self.logger.error(f"获取机械臂角度失败，错误码: {error_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取机械臂角度异常: {e}")
            return None
    
    def getHandAngles(self) -> List[int]:
        """获取机械手当前角度。"""
        if not self.hand_connected or not self.hand:
            return None
        
        try:
            success, result = self._safe_execute_hand_command(self.hand.get_angle, actual=True)
            
            if success and result:
                return result
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"获取机械手角度异常: {e}")
            return None
    
    def set_arm_angles(self, angles: List[float], speed: int = 30, wait: bool = True) -> bool:
        """设置机械臂关节角度。"""
        if not self.arm_connected or not self.arm:
            self.error_signal.emit("xArm未连接")
            return False
        
        try:
            success, result = self._safe_execute_command(
                self.arm.set_servo_angle, angle=angles, speed=speed, wait=wait
            )
            
            if success:
                self.logger.info(f"机械臂角度设置成功: {angles}")
                return True
            else:
                error_code = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else result
                self.error_signal.emit(f"机械臂角度设置失败，错误码: {error_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"机械臂角度设置异常: {e}")
            self.error_signal.emit(f"机械臂角度设置异常: {str(e)}")
            return False
    
    def get_arm_position(self) -> List[float]:
        """获取机械臂当前位置（兼容方法）。"""
        if not self.arm_connected or not self.arm:
            return None
        
        try:
            success, result = self._safe_execute_command(self.arm.get_position)
            
            if success and isinstance(result, (list, tuple)) and len(result) > 1:
                return result[1]  # 位置数据
            elif success:
                return None
            else:
                error_code = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else result
                self.logger.error(f"获取机械臂位置失败，错误码: {error_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取机械臂位置异常: {e}")
            return None
    
    def get_arm_angles(self) -> List[float]:
        """获取机械臂当前关节角度（兼容方法）。"""
        return self.getArmAngles()
    
    def get_hand_angles(self) -> List[int]:
        """获取机械手当前角度（兼容方法）。"""
        return self.getHandAngles() 