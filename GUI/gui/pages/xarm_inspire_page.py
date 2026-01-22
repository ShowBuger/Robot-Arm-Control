#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""xArm机械臂和Inspire机械手集成控制页面。"""

import os
import time
import threading
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QProgressBar, QTextEdit, QFrame,
    QSizePolicy, QMessageBox, QInputDialog
)

# 导入串口扫描模块
try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from core.xarm_inspire_controller import XArmInspireController


class XArmInspirePage(QWidget):
    """xArm机械臂和Inspire机械手集成控制页面。"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        # 使用main_window的共享控制器,而不是创建新的
        self.controller = main_window.arm_controller if hasattr(main_window, 'arm_controller') else XArmInspireController()
        
        # 设置UI
        self.setup_ui()
        
        # 连接信号
        self.connect_signals()
        
        # 状态更新定时器（降低频率）
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒更新一次，大幅减少性能压力
        
        # 加载上次的连接配置并自动连接
        QTimer.singleShot(1000, self.auto_connect_last_config)

    def setup_ui(self):
        """设置UI布局。"""
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建标题
        self.title_label = QLabel("xArm机械臂 & Inspire机械手 集成控制")
        self.title_label.setObjectName("pageTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.title_label.setFont(font)
        self.main_layout.addWidget(self.title_label)

        # 创建连接控制区域
        self.create_connection_group()
        
        # 创建设备控制区域
        self.create_control_group()
        
        # 创建状态显示区域
        self.create_status_group()

    def create_connection_group(self):
        """创建连接控制组。"""
        group = QGroupBox("设备连接")
        layout = QGridLayout(group)
        
        # xArm连接
        layout.addWidget(QLabel("xArm IP:"), 0, 0)
        self.arm_ip_input = QComboBox()
        self.arm_ip_input.setEditable(True)
        self.arm_ip_input.addItems(["192.168.1.215", "192.168.1.100", "127.0.0.1"])
        layout.addWidget(self.arm_ip_input, 0, 1)
        
        # Inspire连接
        layout.addWidget(QLabel("Inspire串口:"), 1, 0)
        self.hand_port_input = QComboBox()
        self.hand_port_input.setEditable(True)
        # 初始化时扫描可用串口
        self.refresh_serial_ports()
        layout.addWidget(self.hand_port_input, 1, 1)
        
        # 刷新串口按钮
        self.refresh_ports_btn = QPushButton("刷新串口")
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        layout.addWidget(self.refresh_ports_btn, 1, 2)
        
        # 统一的连接/断开切换按钮
        self.toggle_connection_btn = QPushButton("连接设备")
        self.toggle_connection_btn.clicked.connect(self.toggle_connection)
        self.toggle_connection_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        layout.addWidget(self.toggle_connection_btn, 2, 0, 1, 3)
        
        self.main_layout.addWidget(group)

    def create_control_group(self):
        """创建设备控制组。"""
        group = QGroupBox("设备控制")
        layout = QHBoxLayout(group)
        
        # xArm控制
        arm_group = QGroupBox("xArm机械臂")
        arm_layout = QGridLayout(arm_group)
        
        # 位置控制
        arm_layout.addWidget(QLabel("X:"), 0, 0)
        self.arm_x = QDoubleSpinBox()
        self.arm_x.setRange(-1000, 1000)
        self.arm_x.setValue(400.0)
        self.arm_x.setDecimals(1)
        self.arm_x.setSingleStep(1.0)
        self.arm_x.setSuffix(" mm")
        self.arm_x.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_x, 0, 1)
        
        arm_layout.addWidget(QLabel("Y:"), 1, 0)
        self.arm_y = QDoubleSpinBox()
        self.arm_y.setRange(-1000, 1000)
        self.arm_y.setValue(0.0)
        self.arm_y.setDecimals(1)
        self.arm_y.setSingleStep(1.0)
        self.arm_y.setSuffix(" mm")
        self.arm_y.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_y, 1, 1)
        
        arm_layout.addWidget(QLabel("Z:"), 2, 0)
        self.arm_z = QDoubleSpinBox()
        self.arm_z.setRange(-1000, 1000)
        self.arm_z.setValue(300.0)
        self.arm_z.setDecimals(1)
        self.arm_z.setSingleStep(1.0)
        self.arm_z.setSuffix(" mm")
        self.arm_z.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_z, 2, 1)
        
        arm_layout.addWidget(QLabel("Roll:"), 3, 0)
        self.arm_roll = QDoubleSpinBox()
        self.arm_roll.setRange(-180, 180)
        self.arm_roll.setValue(180.0)
        self.arm_roll.setDecimals(1)
        self.arm_roll.setSingleStep(1.0)
        self.arm_roll.setSuffix("°")
        self.arm_roll.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_roll, 3, 1)
        
        arm_layout.addWidget(QLabel("Pitch:"), 4, 0)
        self.arm_pitch = QDoubleSpinBox()
        self.arm_pitch.setRange(-180, 180)
        self.arm_pitch.setValue(0.0)
        self.arm_pitch.setDecimals(1)
        self.arm_pitch.setSingleStep(1.0)
        self.arm_pitch.setSuffix("°")
        self.arm_pitch.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_pitch, 4, 1)
        
        arm_layout.addWidget(QLabel("Yaw:"), 5, 0)
        self.arm_yaw = QDoubleSpinBox()
        self.arm_yaw.setRange(-180, 180)
        self.arm_yaw.setValue(0.0)
        self.arm_yaw.setDecimals(1)
        self.arm_yaw.setSingleStep(1.0)
        self.arm_yaw.setSuffix("°")
        self.arm_yaw.setKeyboardTracking(False)  # 禁用键盘实时跟踪，减少信号触发
        arm_layout.addWidget(self.arm_yaw, 5, 1)
        
        self.move_arm_btn = QPushButton("移动机械臂")
        self.move_arm_btn.clicked.connect(self.move_arm)
        arm_layout.addWidget(self.move_arm_btn, 6, 0, 1, 2)
        
        layout.addWidget(arm_group)
        
        # Inspire控制
        hand_group = QGroupBox("Inspire机械手")
        hand_layout = QGridLayout(hand_group)
        
        # 手指角度控制
        finger_names = ["小指", "无名指", "中指", "食指", "拇指", "拇指翻转"]
        self.hand_angles = []
        
        for i, name in enumerate(finger_names):
            hand_layout.addWidget(QLabel(f"{name}:"), i, 0)
            angle_spin = QSpinBox()
            angle_spin.setRange(-1, 1000)
            angle_spin.setValue(500)
            hand_layout.addWidget(angle_spin, i, 1)
            self.hand_angles.append(angle_spin)
        
        self.set_hand_btn = QPushButton("设置手指角度")
        self.set_hand_btn.clicked.connect(self.set_hand_angles)
        hand_layout.addWidget(self.set_hand_btn, len(finger_names), 0, 1, 2)
        
        # 快捷按钮
        self.open_hand_btn = QPushButton("张开手爪")
        self.open_hand_btn.clicked.connect(self.open_hand)
        hand_layout.addWidget(self.open_hand_btn, len(finger_names) + 1, 0, 1, 2)
        
        self.close_hand_btn = QPushButton("闭合手爪")
        self.close_hand_btn.clicked.connect(self.close_hand)
        hand_layout.addWidget(self.close_hand_btn, len(finger_names) + 2, 0, 1, 2)
        
        # 保存动作按钮
        self.save_action_btn = QPushButton("保存当前姿态为动作")
        self.save_action_btn.setStyleSheet("""
            QPushButton {
                background-color: #bd93f9;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #caa9fa;
            }
        """)
        self.save_action_btn.clicked.connect(self.save_current_action)
        hand_layout.addWidget(self.save_action_btn, len(finger_names) + 3, 0, 1, 2)
        
        layout.addWidget(hand_group)
        
        self.main_layout.addWidget(group)

    def create_status_group(self):
        """创建状态显示组。"""
        group = QGroupBox("设备状态")
        layout = QVBoxLayout(group)
        
        # 连接状态
        status_layout = QHBoxLayout()
        self.arm_status_label = QLabel("xArm: 未连接")
        self.hand_status_label = QLabel("Inspire: 未连接")
        status_layout.addWidget(self.arm_status_label)
        status_layout.addWidget(self.hand_status_label)
        layout.addLayout(status_layout)
        
        # 实时位置显示
        self.position_label = QLabel("机械臂位置: [0, 0, 0, 0, 0, 0]")
        self.angles_label = QLabel("手指角度: [0, 0, 0, 0, 0, 0]")
        layout.addWidget(self.position_label)
        layout.addWidget(self.angles_label)
        
        # 日志显示
        layout.addWidget(QLabel("操作日志:"))
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.main_layout.addWidget(group)

    def connect_signals(self):
        """连接信号槽。"""
        self.controller.connected_signal.connect(self.on_connected)
        self.controller.error_signal.connect(self.on_error)

    def refresh_serial_ports(self):
        """刷新可用串口列表。"""
        # 保存当前选择
        current_port = self.hand_port_input.currentText() if hasattr(self, 'hand_port_input') else ""
        
        # 清空列表
        if hasattr(self, 'hand_port_input'):
            self.hand_port_input.clear()
        
        available_ports = []
        
        if SERIAL_AVAILABLE:
            try:
                # 扫描所有可用串口
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    # 在Windows上显示COM端口，在Linux上显示设备路径
                    if os.name == 'nt':  # Windows
                        port_name = port.device
                        description = f"{port.device} - {port.description}"
                    else:  # Linux/Unix
                        port_name = port.device
                        description = f"{port.device} - {port.description}"
                    
                    available_ports.append((port_name, description))
                    
                # 按端口名称排序
                available_ports.sort(key=lambda x: x[0])
                
            except Exception as e:
                # 安全记录错误，如果log_text还未初始化则只输出到控制台
                error_msg = f"扫描串口失败: {str(e)}"
                if hasattr(self, 'log_text') and self.log_text is not None:
                    self.log_message(error_msg)
                else:
                    print(error_msg)
        
        # 如果没有找到串口或者模块不可用，添加常见的默认选项
        if not available_ports:
            if os.name == 'nt':  # Windows
                default_ports = [
                    ("COM1", "COM1"),
                    ("COM3", "COM3"), 
                    ("COM4", "COM4"),
                    ("COM5", "COM5"),
                    ("COM6", "COM6"),
                    ("COM7", "COM7"),
                    ("COM8", "COM8"),
                ]
            else:  # Linux/Unix
                default_ports = [
                    ("/dev/ttyUSB0", "/dev/ttyUSB0"),
                    ("/dev/ttyUSB1", "/dev/ttyUSB1"),
                    ("/dev/ttyACM0", "/dev/ttyACM0"),
                    ("/dev/ttyACM1", "/dev/ttyACM1"),
                ]
            available_ports = default_ports
            
        # 添加到下拉框
        if hasattr(self, 'hand_port_input'):
            for port_name, description in available_ports:
                self.hand_port_input.addItem(description, port_name)
            
            # 尝试恢复之前的选择
            if current_port:
                index = self.hand_port_input.findData(current_port)
                if index >= 0:
                    self.hand_port_input.setCurrentIndex(index)
                else:
                    # 如果找不到完全匹配，尝试部分匹配
                    for i in range(self.hand_port_input.count()):
                        if current_port in self.hand_port_input.itemData(i):
                            self.hand_port_input.setCurrentIndex(i)
                            break
            
            # 安全记录扫描结果
            scan_msg = f"已扫描到 {len(available_ports)} 个串口"
            if hasattr(self, 'log_text') and self.log_text is not None:
                self.log_message(scan_msg)
            else:
                print(scan_msg)
        
        return available_ports

    def get_selected_serial_port(self):
        """获取当前选择的串口名称。"""
        if hasattr(self, 'hand_port_input'):
            # 获取选中项的实际端口名（data），而不是显示文本
            current_data = self.hand_port_input.currentData()
            if current_data:
                return current_data
            else:
                # 如果没有data，则返回当前文本
                return self.hand_port_input.currentText()
        return ""

    # 连接控制方法
    def connect_arm(self):
        """连接xArm机械臂。"""
        ip = self.arm_ip_input.currentText()
        self.arm_connect_btn.setEnabled(False)
        self.log_message(f"正在连接xArm: {ip}...")
        
        def connect_thread():
            try:
                if self.controller.connect_arm(ip):
                    self.log_message(f"xArm连接成功: {ip}")
                else:
                    self.log_message(f"xArm连接失败: {ip}")
            except Exception as e:
                self.log_message(f"xArm连接异常: {str(e)}")
            finally:
                self.arm_connect_btn.setEnabled(True)
                # 更新连接状态UI
                self.update_connection_status_ui()
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def connect_hand(self):
        """连接Inspire机械手。"""
        port = self.get_selected_serial_port()
        if not port:
            self.log_message("请先选择一个串口")
            return
            
        self.hand_connect_btn.setEnabled(False)
        self.log_message(f"正在连接Inspire: {port}...")
        
        def connect_thread():
            try:
                # 首先检查串口是否存在
                import os
                if os.name == 'nt':  # Windows
                    import serial.tools.list_ports
                    available_ports = [port.device for port in serial.tools.list_ports.comports()]
                    if port not in available_ports:
                        self.log_message(f"串口 {port} 不存在或已被占用")
                        self.log_message("提示：请检查设备连接或尝试刷新串口列表")
                        return
                
                if self.controller.connect_hand(port):
                    self.log_message(f"Inspire连接成功: {port}")
                else:
                    self.log_message(f"Inspire连接失败: {port}")
                    self.log_message("提示：请检查串口号、波特率设置和设备连接")
                    
            except PermissionError as pe:
                self.log_message(f"串口访问权限错误: {port}")
                self.log_message("提示：串口可能被其他程序占用，请关闭相关程序后重试")
                
            except FileNotFoundError as fe:
                self.log_message(f"串口设备未找到: {port}")
                self.log_message("提示：请检查设备是否正确连接，或尝试刷新串口列表")
                
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"Inspire连接异常: {error_msg}")
                
                # 提供针对性的解决建议
                if "Permission" in error_msg or "Access" in error_msg:
                    self.log_message("建议：检查串口权限或关闭占用该串口的程序")
                elif "FileNotFound" in error_msg or "cannot open port" in error_msg:
                    self.log_message("建议：检查设备连接或尝试其他串口")
                elif "timeout" in error_msg.lower():
                    self.log_message("建议：检查设备是否正确启动或尝试重新插拔USB")
                else:
                    self.log_message("建议：检查设备连接和驱动程序")
                    
            finally:
                self.hand_connect_btn.setEnabled(True)
                # 更新连接状态UI
                self.update_connection_status_ui()
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def toggle_connection(self):
        """切换连接状态：如果已连接则断开，如果未连接则连接。"""
        # 检查当前连接状态
        arm_connected = hasattr(self.controller, 'arm_connected') and self.controller.arm_connected
        hand_connected = hasattr(self.controller, 'hand_connected') and self.controller.hand_connected
        
        if arm_connected or hand_connected:
            # 如果有任何设备连接，则断开所有连接
            self.disconnect_all_devices()
        else:
            # 如果没有设备连接，则连接所有设备
            self.connect_all_devices()

    def connect_all_devices(self):
        """连接所有设备。"""
        ip = self.arm_ip_input.currentText()
        port = self.get_selected_serial_port()
        self.toggle_connection_btn.setEnabled(False)
        self.toggle_connection_btn.setText("连接中...")
        self.log_message("正在连接设备...")
        
        def connect_thread():
            try:
                if self.controller.connect_all(ip, port):
                    self.log_message("设备连接完成")
                    # 保存连接配置
                    self.save_connection_config(ip, port)
                else:
                    self.log_message("设备连接失败")
            except Exception as e:
                self.log_message(f"设备连接异常: {str(e)}")
            finally:
                self.toggle_connection_btn.setEnabled(True)
                # 更新连接状态UI
                self.update_connection_status_ui()
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def disconnect_all_devices(self):
        """断开所有连接。"""
        self.toggle_connection_btn.setEnabled(False)
        self.toggle_connection_btn.setText("断开中...")
        self.log_message("正在断开连接...")
        
        def disconnect_thread():
            try:
                if self.controller.disconnect_all():
                    self.log_message("所有设备已断开连接")
                else:
                    self.log_message("断开连接时出现错误")
            except Exception as e:
                self.log_message(f"断开连接异常: {str(e)}")
            finally:
                self.toggle_connection_btn.setEnabled(True)
                # 更新连接状态UI
                self.update_connection_status_ui()
        
        thread = threading.Thread(target=disconnect_thread, daemon=True)
        thread.start()

    def connect_all(self):
        """兼容性方法，重定向到新的连接方法。"""
        self.connect_all_devices()

    def disconnect_all(self):
        """兼容性方法，重定向到新的断开方法。"""
        self.disconnect_all_devices()

    # 设备控制方法
    def move_arm(self):
        """移动机械臂。"""
        position = [
            self.arm_x.value(),
            self.arm_y.value(),
            self.arm_z.value(),
            self.arm_roll.value(),
            self.arm_pitch.value(),
            self.arm_yaw.value()
        ]
        if self.controller.move_arm(position):
            self.log_message(f"机械臂移动到: {position}")
        else:
            self.log_message("机械臂移动失败")

    def set_hand_angles(self):
        """设置手指角度。"""
        angles = [spin.value() for spin in self.hand_angles]
        if self.controller.set_hand_angles(angles):
            self.log_message(f"手指角度设置为: {angles}")
        else:
            self.log_message("手指角度设置失败")

    def open_hand(self):
        """张开手爪。"""
        if self.controller.open_hand():
            self.log_message("手爪已张开")
            # 更新UI显示
            open_angles = [1000, 1000, 1000, 1000, 1000, 200]
            for i, angle in enumerate(open_angles):
                self.hand_angles[i].setValue(angle)

    def close_hand(self):
        """闭合手爪。"""
        if self.controller.close_hand():
            self.log_message("手爪已闭合")
            # 更新UI显示
            close_angles = [400, 400, 400, 400, 700, 200]
            for i, angle in enumerate(close_angles):
                self.hand_angles[i].setValue(angle)

    def save_current_action(self):
        """保存当前UI设置的姿态为动作（不获取硬件状态）"""
        # 检查连接状态（仅检查基础连接，不获取硬件数据）
        if not hasattr(self.controller, 'arm_connected') or not self.controller.arm_connected:
            QMessageBox.warning(self, "警告", "请先连接机械臂")
            return
            
        # 获取动作名称
        name, ok = QInputDialog.getText(self, "保存动作", "请输入动作名称:")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        
        try:
            # 直接使用UI中设置的值，不调用硬件获取方法
            self.log_message("使用UI设置的值保存动作（不获取硬件状态）")
            
            # 使用UI控件中的机械臂位置值（如果有的话）
            arm_position = [
                getattr(self, 'arm_x', QDoubleSpinBox()).value() if hasattr(self, 'arm_x') else 400.0,
                getattr(self, 'arm_y', QDoubleSpinBox()).value() if hasattr(self, 'arm_y') else 0.0,
                getattr(self, 'arm_z', QDoubleSpinBox()).value() if hasattr(self, 'arm_z') else 300.0,
                getattr(self, 'arm_roll', QDoubleSpinBox()).value() if hasattr(self, 'arm_roll') else 180.0,
                getattr(self, 'arm_pitch', QDoubleSpinBox()).value() if hasattr(self, 'arm_pitch') else 0.0,
                getattr(self, 'arm_yaw', QDoubleSpinBox()).value() if hasattr(self, 'arm_yaw') else 0.0
            ]
            
            # 直接使用UI中设置的手指角度值
            hand_angles = [int(angle.value()) for angle in self.hand_angles]
            
            self.log_message(f"UI机械臂位置: {arm_position}")
            self.log_message(f"UI手指角度: {hand_angles}")
            
            # 构建动作数据
            action_data = {
                "name": name,
                "arm_position": arm_position,
                "hand_angles": hand_angles,
                "timestamp": time.time(),
                "source": "UI设置值（未获取硬件状态）"
            }
            
            # 保存到JSON文件
            import json
            import os
            
            actions_dir = "saved_actions"
            if not os.path.exists(actions_dir):
                os.makedirs(actions_dir)
                
            file_path = os.path.join(actions_dir, f"{name}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(action_data, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"动作 '{name}' 已保存到 {file_path}")
            QMessageBox.information(self, "成功", f"动作 '{name}' 保存成功！\n数据来源：UI设置值")
            
        except Exception as e:
            error_msg = f"保存动作失败: {str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    # 状态更新方法
    def update_status(self):
        """定期更新状态显示（优化版：只更新连接状态，不获取角度）。"""
        if hasattr(self, 'controller') and self.controller:
            # 只更新连接状态显示，不进行角度查询
            try:
                self.update_connection_status_ui()
            except Exception as e:
                self.log_message(f"更新连接状态时出错: {e}")
        
        # 重新启动定时器，但增加间隔到10秒
        QTimer.singleShot(10000, self.update_status)

    def log_message(self, message):
        """添加日志消息。"""
        # 安全检查：确保log_text组件存在
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
            
            # 限制日志行数
            if self.log_text.document().blockCount() > 50:
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
        else:
            # 如果log_text不存在，则将消息输出到控制台
            print(f"[{time.strftime('%H:%M:%S')}] {message}")

    # 信号槽方法
    @pyqtSlot(bool)
    def on_connected(self, connected):
        """设备连接状态变化。"""
        status = "已连接" if connected else "已断开"
        self.log_message(f"设备连接状态: {status}")
        
        # 更新UI状态标签
        self.update_connection_status_ui()

    @pyqtSlot(str)
    def on_error(self, error_msg):
        """处理错误信息。"""
        self.log_message(f"错误: {error_msg}")
        QMessageBox.warning(self, "错误", error_msg)

    def update_connection_status_ui(self):
        """更新连接状态UI显示"""
        try:
            # 检查连接状态
            arm_connected = hasattr(self.controller, 'arm_connected') and self.controller.arm_connected
            hand_connected = hasattr(self.controller, 'hand_connected') and self.controller.hand_connected
            
            # 更新机械臂状态显示
            if arm_connected:
                arm_ip = getattr(self.controller, 'arm_ip', self.arm_ip_input.currentText())
                self.arm_status_label.setText(f"xArm: 已连接 ({arm_ip})")
                self.arm_status_label.setStyleSheet("color: green;")
            else:
                self.arm_status_label.setText("xArm: 未连接")
                self.arm_status_label.setStyleSheet("color: red;")
            
            # 更新机械手状态显示
            if hand_connected:
                hand_port = self.get_selected_serial_port()
                self.hand_status_label.setText(f"Inspire: 已连接 ({hand_port})")
                self.hand_status_label.setStyleSheet("color: green;")
            else:
                self.hand_status_label.setText("Inspire: 未连接")
                self.hand_status_label.setStyleSheet("color: red;")
            
            # 更新统一切换按钮的状态
            if arm_connected or hand_connected:
                self.toggle_connection_btn.setText("断开")
                self.toggle_connection_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                    QPushButton:pressed {
                        background-color: #b71c1c;
                    }
                """)
            else:
                self.toggle_connection_btn.setText("连接")
                self.toggle_connection_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                """)
                
        except Exception as e:
            self.log_message(f"更新连接状态UI时出错: {e}")



    def save_connection_config(self, ip, port):
        """保存连接配置到文件"""
        try:
            import json
            import os
            
            config = {
                'arm_ip': ip,
                'hand_port': port
            }
            
            # 确保配置目录存在
            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            config_file = os.path.join(config_dir, "connection_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"连接配置已保存: IP={ip}, 串口={port}")
            
        except Exception as e:
            self.log_message(f"保存连接配置失败: {str(e)}")

    def load_connection_config(self):
        """加载连接配置"""
        try:
            import json
            import os
            
            config_file = os.path.join("config", "connection_config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                arm_ip = config.get('arm_ip', '')
                hand_port = config.get('hand_port', '')
                
                # 设置到UI控件中
                if arm_ip:
                    # 如果IP不在列表中，添加到列表
                    if self.arm_ip_input.findText(arm_ip) == -1:
                        self.arm_ip_input.addItem(arm_ip)
                    self.arm_ip_input.setCurrentText(arm_ip)
                
                if hand_port:
                    # 如果串口不在列表中，添加到列表
                    if self.hand_port_input.findText(hand_port) == -1:
                        self.hand_port_input.addItem(hand_port)
                    self.hand_port_input.setCurrentText(hand_port)
                
                self.log_message(f"已加载连接配置: IP={arm_ip}, 串口={hand_port}")
                return arm_ip, hand_port
            
        except Exception as e:
            self.log_message(f"加载连接配置失败: {str(e)}")
        
        return None, None

    def auto_connect_last_config(self):
        """自动连接上次的配置"""
        try:
            arm_ip, hand_port = self.load_connection_config()
            
            if arm_ip or hand_port:
                self.log_message("检测到上次连接配置，准备自动连接...")
                
                # 延迟2秒后自动连接，给界面一些时间完成初始化
                QTimer.singleShot(2000, lambda: self.connect_all_devices())
            else:
                self.log_message("未找到上次连接配置")
                
        except Exception as e:
            self.log_message(f"自动连接失败: {str(e)}") 