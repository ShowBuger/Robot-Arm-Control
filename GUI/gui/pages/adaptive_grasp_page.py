#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自适应抓取页面
提供参数配置和控制界面
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFrame, QProgressBar, QTextEdit,
    QCheckBox, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QComboBox
)
from PyQt6.QtGui import QFont


class AdaptiveGraspPage(QWidget):
    """自适应抓取页面"""

    def __init__(self, main_window, adaptive_grasp_controller):
        super().__init__()

        self.main_window = main_window
        self.controller = adaptive_grasp_controller

        # 获取传感器数据管理器
        if hasattr(main_window, 'sensor_data_manager'):
            self.sensor_data_manager = main_window.sensor_data_manager
        else:
            self.sensor_data_manager = None

        # 获取动作管理器
        if hasattr(main_window, 'action_manager'):
            self.action_manager = main_window.action_manager
        else:
            self.action_manager = None

        # 创建UI
        self.setup_ui()

        # 连接信号
        self.connect_signals()

        # 刷新传感器列表
        self.refresh_sensor_list()

        # 刷新动作列表
        self.refresh_action_list()

        # 设置自适应抓取回调
        if self.action_manager:
            self.action_manager.set_adaptive_grasp_callback(self.execute_adaptive_config)

        # 从全局设置加载上次保存的参数（如果有）
        try:
            self.load_saved_parameters()
        except Exception:
            pass

    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ========== 标题 ==========
        title_label = QLabel("自适应抓取控制")
        title_label.setObjectName("pageTitle")
        main_layout.addWidget(title_label)

        # ========== 传感器选择区域 ==========
        sensor_group = QGroupBox("传感器选择")
        sensor_layout = QVBoxLayout(sensor_group)

        # 传感器列表
        sensor_list_layout = QHBoxLayout()
        sensor_list_layout.addWidget(QLabel("选择传感器:"))

        self.sensor_list = QListWidget()
        self.sensor_list.setMaximumHeight(100)
        self.sensor_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        sensor_list_layout.addWidget(self.sensor_list)

        self.refresh_sensor_btn = QPushButton("刷新")
        self.refresh_sensor_btn.setObjectName("secondaryButton")
        self.refresh_sensor_btn.setMaximumWidth(80)
        sensor_list_layout.addWidget(self.refresh_sensor_btn)

        sensor_layout.addLayout(sensor_list_layout)

        # 当前传感器值显示
        self.sensor_value_label = QLabel("当前力值: 未选择传感器")
        sensor_layout.addWidget(self.sensor_value_label)

        main_layout.addWidget(sensor_group)

        # ========== 参数配置区域 ==========
        config_group = QGroupBox("参数配置")
        config_layout = QGridLayout(config_group)
        config_layout.setColumnStretch(1, 1)
        config_layout.setColumnStretch(3, 1)

        row = 0

        # 初始动作
        config_layout.addWidget(QLabel("初始动作:"), row, 0)
        action_layout = QHBoxLayout()
        self.initial_action_combo = QComboBox()
        self.initial_action_combo.addItem("无 (不执行初始动作)", "")
        action_layout.addWidget(self.initial_action_combo)

        self.refresh_action_btn = QPushButton("刷新动作")
        self.refresh_action_btn.setObjectName("secondaryButton")
        self.refresh_action_btn.setMaximumWidth(100)
        action_layout.addWidget(self.refresh_action_btn)

        # 应用初始动作按钮（立即将所选动作应用到机械臂与机械手）
        self.apply_action_btn = QPushButton("应用初始动作")
        self.apply_action_btn.setObjectName("secondaryButton")
        self.apply_action_btn.setMaximumWidth(120)
        action_layout.addWidget(self.apply_action_btn)

        config_layout.addLayout(action_layout, row, 1, 1, 3)
        row += 1

        # 手指选择
        config_layout.addWidget(QLabel("选择手指:"), row, 0)
        finger_layout = QHBoxLayout()
        self.finger_checkboxes = []
        for i in range(6):
            cb = QCheckBox(f"F{i}")
            cb.setChecked(i < 5)  # 默认选择前5个手指
            self.finger_checkboxes.append(cb)
            finger_layout.addWidget(cb)
        finger_layout.addStretch()
        config_layout.addLayout(finger_layout, row, 1, 1, 3)
        row += 1

        # 释放模式
        config_layout.addWidget(QLabel("释放模式:"), row, 0)
        self.release_mode_checkbox = QCheckBox("启用释放模式（达到阈值后动态平衡：力大则释放，力小则闭合）")
        self.release_mode_checkbox.setChecked(False)
        config_layout.addWidget(self.release_mode_checkbox, row, 1, 1, 3)
        row += 1

        # 闭合步长
        config_layout.addWidget(QLabel("闭合步长 (°):"), row, 0)
        self.close_step_spin = QSpinBox()
        self.close_step_spin.setRange(1, 100)
        self.close_step_spin.setValue(10)
        self.close_step_spin.setSuffix(" °")
        config_layout.addWidget(self.close_step_spin, row, 1)

        # 释放步长
        config_layout.addWidget(QLabel("释放步长 (°):"), row, 2)
        self.release_step_spin = QSpinBox()
        self.release_step_spin.setRange(1, 100)
        self.release_step_spin.setValue(10)
        self.release_step_spin.setSuffix(" °")
        config_layout.addWidget(self.release_step_spin, row, 3)
        row += 1

        # 闭合速度
        config_layout.addWidget(QLabel("闭合速度:"), row, 0)
        self.close_speed_spin = QSpinBox()
        self.close_speed_spin.setRange(100, 2000)
        self.close_speed_spin.setValue(1000)
        config_layout.addWidget(self.close_speed_spin, row, 1)
        row += 1

        # 步骤间隔
        config_layout.addWidget(QLabel("步骤间隔 (s):"), row, 0)
        self.step_interval_spin = QDoubleSpinBox()
        self.step_interval_spin.setRange(0.1, 5.0)
        self.step_interval_spin.setValue(0.5)
        self.step_interval_spin.setSingleStep(0.1)
        self.step_interval_spin.setSuffix(" s")
        config_layout.addWidget(self.step_interval_spin, row, 1)

        # 最大迭代次数
        config_layout.addWidget(QLabel("最大迭代次数:"), row, 2)
        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(10, 500)
        self.max_iterations_spin.setValue(100)
        config_layout.addWidget(self.max_iterations_spin, row, 3)
        row += 1

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        config_layout.addWidget(line, row, 0, 1, 4)
        row += 1

        # 力阈值标题
        threshold_title = QLabel("力阈值设置 (N)")
        threshold_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        config_layout.addWidget(threshold_title, row, 0, 1, 4)
        row += 1

        # X轴力阈值
        config_layout.addWidget(QLabel("X 轴阈值:"), row, 0)
        self.threshold_x_spin = QDoubleSpinBox()
        self.threshold_x_spin.setRange(0.01, 50.0)
        self.threshold_x_spin.setValue(2.0)
        self.threshold_x_spin.setSingleStep(0.1)
        self.threshold_x_spin.setSuffix(" N")
        config_layout.addWidget(self.threshold_x_spin, row, 1)

        # Y轴力阈值
        config_layout.addWidget(QLabel("Y 轴阈值:"), row, 2)
        self.threshold_y_spin = QDoubleSpinBox()
        self.threshold_y_spin.setRange(0.01, 50.0)
        self.threshold_y_spin.setValue(2.0)
        self.threshold_y_spin.setSingleStep(0.1)
        self.threshold_y_spin.setSuffix(" N")
        config_layout.addWidget(self.threshold_y_spin, row, 3)
        row += 1

        # Z轴力阈值
        config_layout.addWidget(QLabel("Z 轴阈值:"), row, 0)
        self.threshold_z_spin = QDoubleSpinBox()
        self.threshold_z_spin.setRange(0.01, 50.0)
        self.threshold_z_spin.setValue(2.0)
        self.threshold_z_spin.setSingleStep(0.1)
        self.threshold_z_spin.setSuffix(" N")
        config_layout.addWidget(self.threshold_z_spin, row, 1)
        row += 1

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        config_layout.addWidget(line2, row, 0, 1, 4)
        row += 1

        # 稳定性判断标题
        stable_title = QLabel("稳定性判断参数")
        stable_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        config_layout.addWidget(stable_title, row, 0, 1, 4)
        row += 1

        # 稳定持续时间
        config_layout.addWidget(QLabel("稳定持续时间:"), row, 0)
        self.stable_duration_spin = QDoubleSpinBox()
        self.stable_duration_spin.setRange(0.5, 10.0)
        self.stable_duration_spin.setValue(2.0)
        self.stable_duration_spin.setSingleStep(0.5)
        self.stable_duration_spin.setSuffix(" s")
        config_layout.addWidget(self.stable_duration_spin, row, 1)

        # 稳定性标准差阈值
        config_layout.addWidget(QLabel("标准差阈值:"), row, 2)
        self.stable_std_spin = QDoubleSpinBox()
        self.stable_std_spin.setRange(0.01, 1.0)
        self.stable_std_spin.setValue(0.1)
        self.stable_std_spin.setSingleStep(0.01)
        self.stable_std_spin.setDecimals(3)
        config_layout.addWidget(self.stable_std_spin, row, 3)
        row += 1

        # 采样窗口大小
        config_layout.addWidget(QLabel("采样窗口大小:"), row, 0)
        self.sample_window_spin = QSpinBox()
        self.sample_window_spin.setRange(5, 100)
        self.sample_window_spin.setValue(20)
        config_layout.addWidget(self.sample_window_spin, row, 1)
        row += 1

        # 分隔线
        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.HLine)
        line3.setFrameShadow(QFrame.Shadow.Sunken)
        config_layout.addWidget(line3, row, 0, 1, 4)
        row += 1

        # 保存参数为动作
        save_label = QLabel("保存配置:")
        save_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        config_layout.addWidget(save_label, row, 0)

        save_layout = QHBoxLayout()
        self.save_name_edit = QLineEdit()
        self.save_name_edit.setPlaceholderText("输入动作名称")
        save_layout.addWidget(self.save_name_edit)

        # 配置下拉：显示已保存的配置
        self.config_combo = QComboBox()
        self.config_combo.setMinimumWidth(180)
        save_layout.addWidget(self.config_combo)

        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setObjectName("secondaryButton")
        self.save_config_btn.setMaximumWidth(120)
        save_layout.addWidget(self.save_config_btn)

        # 应用所选配置按钮
        self.apply_config_btn = QPushButton("应用配置")
        self.apply_config_btn.setObjectName("secondaryButton")
        self.apply_config_btn.setMaximumWidth(120)
        save_layout.addWidget(self.apply_config_btn)

        config_layout.addLayout(save_layout, row, 1, 1, 3)

        main_layout.addWidget(config_group)

        # ========== 控制按钮区域 ==========
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout(control_group)

        # 按钮行
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始自适应抓取")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.setMinimumHeight(40)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        self.emergency_btn = QPushButton("紧急停止")
        self.emergency_btn.setObjectName("dangerButton")
        self.emergency_btn.setMinimumHeight(40)
        button_layout.addWidget(self.emergency_btn)

        control_layout.addLayout(button_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        control_layout.addLayout(progress_layout)

        # 状态显示
        self.state_label = QLabel("状态: 空闲")
        self.state_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        control_layout.addWidget(self.state_label)

        main_layout.addWidget(control_group)

        # ========== 日志显示区域 ==========
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        # 清除日志按钮
        self.clear_log_btn = QPushButton("清除日志")
        self.clear_log_btn.setObjectName("secondaryButton")
        self.clear_log_btn.setMaximumWidth(100)
        log_layout.addWidget(self.clear_log_btn)

        main_layout.addWidget(log_group)

        # 添加弹性空间
        main_layout.addStretch()

    def connect_signals(self):
        """连接信号和槽"""
        # 按钮信号
        self.refresh_sensor_btn.clicked.connect(self.refresh_sensor_list)
        self.refresh_action_btn.clicked.connect(self.refresh_action_list)
        self.apply_action_btn.clicked.connect(self.apply_initial_action)
        self.save_config_btn.clicked.connect(self.save_config)
        self.apply_config_btn.clicked.connect(self.apply_selected_config)
        self.start_btn.clicked.connect(self.start_grasp)
        self.stop_btn.clicked.connect(self.stop_grasp)
        self.emergency_btn.clicked.connect(self.emergency_stop)
        self.clear_log_btn.clicked.connect(self.clear_log)

        # 传感器列表选择变化
        self.sensor_list.itemSelectionChanged.connect(self.on_sensor_selection_changed)

        # 控制器信号
        if self.controller:
            self.controller.status_signal.connect(self.on_status_update)
            self.controller.progress_signal.connect(self.on_progress_update)
            self.controller.completed_signal.connect(self.on_completed)
            self.controller.force_update_signal.connect(self.on_force_update)

        # 传感器数据更新
        if self.sensor_data_manager:
            self.sensor_data_manager.data_updated_signal.connect(self.on_sensor_data_updated)

    def refresh_sensor_list(self):
        """刷新传感器列表"""
        # 保存当前选择
        selected_ids = []
        if self.sensor_list.selectedItems():
            for item in self.sensor_list.selectedItems():
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))

        # 清空列表
        self.sensor_list.clear()

        if not self.sensor_data_manager:
            self.add_log("传感器数据管理器未初始化")
            return

        # 获取可用传感器
        sensors = self.sensor_data_manager.get_all_sensors()

        if not sensors:
            self.add_log("未检测到任何传感器")
            return

        # 添加传感器到列表
        for sensor_id in sensors:
            item = QListWidgetItem(f"传感器 {sensor_id}")
            item.setData(Qt.ItemDataRole.UserRole, sensor_id)
            self.sensor_list.addItem(item)

            # 恢复选择状态
            if sensor_id in selected_ids:
                item.setSelected(True)

        self.add_log(f"已检测到 {len(sensors)} 个传感器")

    def refresh_action_list(self):
        """刷新动作列表"""
        # 保存当前选择
        current_action = self.initial_action_combo.currentData()

        # 清空列表
        self.initial_action_combo.clear()

        # 添加"无"选项
        self.initial_action_combo.addItem("无 (不执行初始动作)", "")

        if not self.action_manager:
            self.add_log("动作管理器未初始化")
            return

        # 获取所有动作（返回的是动作名称列表）
        actions = self.action_manager.get_all_actions()

        if not actions:
            self.add_log("未找到任何已保存的动作")
            return

        # 添加动作到下拉列表
        for action_name in sorted(actions):
            self.initial_action_combo.addItem(action_name, action_name)

        # 恢复选择
        if current_action:
            index = self.initial_action_combo.findData(current_action)
            if index >= 0:
                self.initial_action_combo.setCurrentIndex(index)

        self.add_log(f"已加载 {len(actions)} 个动作")
        # 同步刷新已保存的自适应配置列表
        try:
            self.refresh_config_list()
        except Exception:
            pass

    def refresh_config_list(self):
        """刷新配置下拉列表"""
        self.config_combo.clear()
        if not self.action_manager:
            return
        configs = []
        try:
            configs = self.action_manager.get_all_configs()
        except Exception:
            configs = []

        # 添加一个空项
        self.config_combo.addItem("-- 选择配置 --", "")
        for name in sorted(configs):
            self.config_combo.addItem(name, name)

    def on_sensor_selection_changed(self):
        """传感器选择变化"""
        selected_items = self.sensor_list.selectedItems()
        if not selected_items:
            self.sensor_value_label.setText("当前力值: 未选择传感器")
            return

        sensor_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        self.add_log(f"已选择 {len(sensor_ids)} 个传感器: {sensor_ids}")

    @pyqtSlot(int, list)
    def on_sensor_data_updated(self, sensor_id, values):
        """传感器数据更新"""
        # 如果当前选中的传感器包含更新的传感器ID，则更新显示
        selected_items = self.sensor_list.selectedItems()
        if not selected_items:
            return

        selected_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        if sensor_id in selected_ids:
            self.update_sensor_display(selected_ids)

    def update_sensor_display(self, sensor_ids):
        """更新传感器显示"""
        if not self.sensor_data_manager or not sensor_ids:
            return

        # 获取并显示多个传感器的平均数据
        total_x, total_y, total_z = 0.0, 0.0, 0.0
        valid_count = 0

        for sensor_id in sensor_ids:
            sensor_data = self.sensor_data_manager.get_sensor_data(sensor_id)
            if sensor_data and len(sensor_data.data1) > 0:
                values = sensor_data.get_latest_values()
                total_x += values[0]
                total_y += values[1]
                total_z += values[2]
                valid_count += 1

        if valid_count > 0:
            avg_x = total_x / valid_count
            avg_y = total_y / valid_count
            avg_z = total_z / valid_count
            self.sensor_value_label.setText(
                f"当前力值: X={avg_x:.2f}N, Y={avg_y:.2f}N, Z={avg_z:.2f}N"
            )

    def start_grasp(self):
        """开始自适应抓取"""
        if not self.controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        # 检查机械手是否连接 - 更加健壮地检查多个可能的控制器引用
        # 候选控制器：main_window.arm_controller, self.controller.arm_controller, rm_inspire_page.controller
        candidates = []
        main_ctrl = getattr(self.main_window, 'arm_controller', None)
        if main_ctrl is not None:
            candidates.append(('main_window.arm_controller', main_ctrl))

        adaptive_ctrl_arm = getattr(self.controller, 'arm_controller', None)
        if adaptive_ctrl_arm is not None and adaptive_ctrl_arm is not main_ctrl:
            candidates.append(('adaptive_grasp.arm_controller', adaptive_ctrl_arm))

        xarm_page = getattr(self.main_window, 'xarm_inspire_page', None)
        xarm_page_ctrl = getattr(xarm_page, 'controller', None) if xarm_page is not None else None
        if xarm_page_ctrl is not None and xarm_page_ctrl not in [c for _, c in candidates]:
            candidates.append(('xarm_inspire_page.controller', xarm_page_ctrl))

        # 也检查 action_manager 中的 arm_controller（某些页面可能覆盖了动作管理器的控制器）
        action_mgr = getattr(self.main_window, 'action_manager', None)
        action_arm_ctrl = None
        if action_mgr is not None:
            action_arm_ctrl = getattr(action_mgr, 'arm_controller', None)
            if action_arm_ctrl is not None and action_arm_ctrl not in [c for _, c in candidates]:
                candidates.append(('action_manager.arm_controller', action_arm_ctrl))

        # 检查每个候选控制器的hand对象或hand_connected标志
        hand_available = False
        debug_msgs = []
        for name, ctrl in candidates:
            try:
                hand_obj = getattr(ctrl, 'hand', None)
                flag = getattr(ctrl, 'hand_connected', None)
                # 如果hand对象存在，优先使用hand.connected属性（如果有）判断
                if hand_obj is not None:
                    hand_connected_attr = getattr(hand_obj, 'connected', None)
                    if hand_connected_attr is None:
                        is_conn = bool(flag)
                    else:
                        is_conn = bool(hand_connected_attr)
                else:
                    is_conn = bool(flag)

                debug_msgs.append(f"{name}: hand_obj={hand_obj}, hand_connected_flag={flag}, hand.connected={getattr(hand_obj, 'connected', None)}")

                if is_conn:
                    hand_available = True
                    break
            except Exception as e:
                debug_msgs.append(f"{name}: error_checking={e}")

        # 输出调试信息到页面日志，方便排查
        try:
            for m in debug_msgs:
                self.add_log("DEBUG: " + m)
        except Exception:
            for m in debug_msgs:
                print("DEBUG:", m)

        if not hand_available:
            QMessageBox.warning(self, "错误", "请先在瑞尔曼机械臂页面连接机械手")
            return

        # 获取选中的传感器
        selected_items = self.sensor_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请至少选择一个传感器")
            return

        sensor_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]

        # 获取选中的手指
        selected_fingers = []
        for i, cb in enumerate(self.finger_checkboxes):
            if cb.isChecked():
                selected_fingers.append(i)

        if not selected_fingers:
            QMessageBox.warning(self, "错误", "请至少选择一个手指")
            return

        # 获取选中的初始动作
        initial_action = self.initial_action_combo.currentData()

        # 更新控制器配置
        config = {
            "initial_action": initial_action if initial_action else "",
            "finger_indices": selected_fingers,
            "close_step": self.close_step_spin.value(),
            "release_step": self.release_step_spin.value(),
            "close_speed": self.close_speed_spin.value(),
            "step_interval": self.step_interval_spin.value(),
            "force_threshold_x": self.threshold_x_spin.value(),
            "force_threshold_y": self.threshold_y_spin.value(),
            "force_threshold_z": self.threshold_z_spin.value(),
            "stable_duration": self.stable_duration_spin.value(),
            "stable_std_threshold": self.stable_std_spin.value(),
            "sample_window": self.sample_window_spin.value(),
            "max_iterations": self.max_iterations_spin.value(),
            "release_mode": self.release_mode_checkbox.isChecked(),
        }

        self.controller.set_config(config)

        # 启动抓取
        success = self.controller.start_adaptive_grasp(sensor_ids)

        if success:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.add_log("=" * 50)
            self.add_log("开始自适应抓取")
            if initial_action:
                self.add_log(f"初始动作: {initial_action}")
            else:
                self.add_log("初始动作: 无")
            self.add_log(f"传感器: {sensor_ids}")
            self.add_log(f"手指: {selected_fingers}")
            self.add_log("=" * 50)

    def load_saved_parameters(self):
        """从全局设置加载自适应抓取页面的参数并应用到UI控件上"""
        try:
            if not hasattr(self.main_window, 'settings'):
                return

            saved = self.main_window.settings.settings.get('adaptive_grasp', {})
            if not isinstance(saved, dict):
                return

            # 手指索引
            finger_indices = saved.get('finger_indices', None)
            if isinstance(finger_indices, (list, tuple)):
                for i, cb in enumerate(self.finger_checkboxes):
                    cb.setChecked(i in finger_indices)

            # 数值型参数
            if 'close_step' in saved:
                self.close_step_spin.setValue(saved.get('close_step', self.close_step_spin.value()))
            if 'release_step' in saved:
                self.release_step_spin.setValue(saved.get('release_step', self.release_step_spin.value()))
            if 'close_speed' in saved:
                self.close_speed_spin.setValue(saved.get('close_speed', self.close_speed_spin.value()))
            if 'step_interval' in saved:
                self.step_interval_spin.setValue(saved.get('step_interval', self.step_interval_spin.value()))
            if 'force_threshold_x' in saved:
                self.threshold_x_spin.setValue(saved.get('force_threshold_x', self.threshold_x_spin.value()))
            if 'force_threshold_y' in saved:
                self.threshold_y_spin.setValue(saved.get('force_threshold_y', self.threshold_y_spin.value()))
            if 'force_threshold_z' in saved:
                self.threshold_z_spin.setValue(saved.get('force_threshold_z', self.threshold_z_spin.value()))
            if 'stable_duration' in saved:
                self.stable_duration_spin.setValue(saved.get('stable_duration', self.stable_duration_spin.value()))
            if 'stable_std_threshold' in saved:
                self.stable_std_spin.setValue(saved.get('stable_std_threshold', self.stable_std_spin.value()))
            if 'sample_window' in saved:
                self.sample_window_spin.setValue(saved.get('sample_window', self.sample_window_spin.value()))
            if 'max_iterations' in saved:
                self.max_iterations_spin.setValue(saved.get('max_iterations', self.max_iterations_spin.value()))

            # 释放模式
            if 'release_mode' in saved:
                self.release_mode_checkbox.setChecked(saved.get('release_mode', False))

            # 初始动作: 使用显示文本或data匹配
            initial_action = saved.get('initial_action', None)
            if initial_action is not None and hasattr(self, 'initial_action_combo'):
                # 优先按data匹配
                idx = self.initial_action_combo.findData(initial_action)
                if idx >= 0:
                    self.initial_action_combo.setCurrentIndex(idx)
                else:
                    # 尝试按文本匹配
                    t_idx = self.initial_action_combo.findText(initial_action)
                    if t_idx >= 0:
                        self.initial_action_combo.setCurrentIndex(t_idx)

        except Exception as e:
            try:
                self.add_log(f"加载自适应参数失败: {e}")
            except Exception:
                pass

    def save_parameters(self):
        """将当前UI参数保存到全局设置（在应用退出时MainWindow会写入文件）"""
        try:
            if not hasattr(self.main_window, 'settings'):
                return False

            saved = {}
            # 手指索引
            selected = [i for i, cb in enumerate(self.finger_checkboxes) if cb.isChecked()]
            saved['finger_indices'] = selected

            # 数值型参数
            saved['close_step'] = self.close_step_spin.value()
            saved['release_step'] = self.release_step_spin.value()
            saved['close_speed'] = self.close_speed_spin.value()
            saved['step_interval'] = self.step_interval_spin.value()
            saved['force_threshold_x'] = self.threshold_x_spin.value()
            saved['force_threshold_y'] = self.threshold_y_spin.value()
            saved['force_threshold_z'] = self.threshold_z_spin.value()
            saved['stable_duration'] = self.stable_duration_spin.value()
            saved['stable_std_threshold'] = self.stable_std_spin.value()
            saved['sample_window'] = self.sample_window_spin.value()
            saved['max_iterations'] = self.max_iterations_spin.value()

            # 释放模式
            saved['release_mode'] = self.release_mode_checkbox.isChecked()

            # 初始动作
            if hasattr(self, 'initial_action_combo'):
                current_data = self.initial_action_combo.currentData()
                if current_data:
                    saved['initial_action'] = current_data
                else:
                    saved['initial_action'] = self.initial_action_combo.currentText()

            # 写入主设置并保存
            self.main_window.settings.settings['adaptive_grasp'] = saved
            # 不立即保存文件，这由MainWindow.closeEvent统一处理
            return True
        except Exception as e:
            try:
                self.add_log(f"保存自适应参数失败: {e}")
            except Exception:
                pass
            return False

    def stop_grasp(self):
        """停止抓取"""
        if self.controller:
            self.controller.stop_grasp()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def emergency_stop(self):
        """紧急停止"""
        reply = QMessageBox.question(
            self,
            '确认紧急停止',
            '确定要紧急停止当前操作吗？\n这将立即中断所有动作！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.controller:
                self.controller.emergency_stop()
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.add_log("!!! 紧急停止已触发 !!!")

    @pyqtSlot(str)
    def on_status_update(self, status):
        """状态更新"""
        self.add_log(status)
        if self.controller:
            state_name = self.controller.get_state_name()
            self.state_label.setText(f"状态: {state_name}")

    @pyqtSlot(int, int)
    def on_progress_update(self, current, total):
        """进度更新"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    @pyqtSlot(bool, str)
    def on_completed(self, success, message):
        """完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        self.add_log("=" * 50)
        if success:
            self.add_log(f"✓ 抓取成功: {message}")
        else:
            self.add_log(f"✗ 抓取未完成: {message}")
        self.add_log("=" * 50)

    @pyqtSlot(dict)
    def on_force_update(self, force_data):
        """力值更新"""
        # 在传感器显示标签中更新（如果没有其他更新）
        pass

    def add_log(self, message):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.add_log("日志已清除")

    def save_config_as_action(self):
        """保存当前配置为动作"""
        # 获取动作名称
        action_name = self.save_name_edit.text().strip()

        if not action_name:
            QMessageBox.warning(self, "错误", "请输入动作名称")
            return

        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        # 获取选中的传感器
        selected_items = self.sensor_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请至少选择一个传感器")
            return

        sensor_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]

        # 获取选中的手指
        selected_fingers = []
        for i, cb in enumerate(self.finger_checkboxes):
            if cb.isChecked():
                selected_fingers.append(i)

        if not selected_fingers:
            QMessageBox.warning(self, "错误", "请至少选择一个手指")
            return

        # 获取初始动作
        initial_action = self.initial_action_combo.currentData()

        # 收集所有参数
        adaptive_config = {
            "type": "adaptive_grasp",  # 标记这是一个自适应抓取动作
            "sensor_ids": sensor_ids,
            "initial_action": initial_action if initial_action else "",
            "finger_indices": selected_fingers,
            "close_step": self.close_step_spin.value(),
            "close_speed": self.close_speed_spin.value(),
            "step_interval": self.step_interval_spin.value(),
            "force_threshold_x": self.threshold_x_spin.value(),
            "force_threshold_y": self.threshold_y_spin.value(),
            "force_threshold_z": self.threshold_z_spin.value(),
            "stable_duration": self.stable_duration_spin.value(),
            "stable_std_threshold": self.stable_std_spin.value(),
            "sample_window": self.sample_window_spin.value(),
            "max_iterations": self.max_iterations_spin.value(),
        }

        # 将配置保存为特殊的动作
        # 使用空的arm_position和hand_angles，因为这是一个特殊类型的动作
        try:
            # 保存动作（使用空数据，实际参数存储在配置中）
            success = self.action_manager.save_action(
                name=action_name,
                arm_position=[0, 0, 0, 0, 0, 0],
                hand_angles=[0, 0, 0, 0, 0, 0],
                arm_velocity=0,
                hand_velocity=0
            )

            if success:
                # 获取保存的动作对象，添加自适应配置
                action = self.action_manager.get_action(action_name)
                if action:
                    # 将自适应配置存储为动作的额外属性
                    action.adaptive_config = adaptive_config

                    # 重新保存动作文件
                    self.action_manager.save_actions_to_file()

                    # 刷新动作列表
                    self.refresh_action_list()

                    # 清空名称输入框
                    self.save_name_edit.clear()

                    # 显示成功消息
                    self.add_log(f"✓ 自适应抓取配置已保存为动作: {action_name}")
                    QMessageBox.information(
                        self,
                        "保存成功",
                        f"自适应抓取配置已保存为动作: {action_name}\n\n"
                        f"传感器: {sensor_ids}\n"
                        f"手指: {selected_fingers}\n"
                        f"力阈值: X={adaptive_config['force_threshold_x']}N, "
                        f"Y={adaptive_config['force_threshold_y']}N, "
                        f"Z={adaptive_config['force_threshold_z']}N"
                    )
                else:
                    QMessageBox.warning(self, "错误", "保存配置失败：无法获取动作对象")
            else:
                QMessageBox.warning(self, "错误", "保存动作失败")

        except Exception as e:
            self.add_log(f"✗ 保存配置错误: {e}")
            QMessageBox.warning(self, "错误", f"保存配置时发生错误: {e}")

    def save_config(self):
        """将当前UI配置保存为一个命名的自适应配置（通过 ActionManager 管理）"""
        try:
            config_name = self.save_name_edit.text().strip()
            if not config_name:
                QMessageBox.warning(self, "错误", "请输入配置名称")
                return False

            # 收集当前配置
            selected_items = self.sensor_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "错误", "请至少选择一个传感器")
                return False

            sensor_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
            selected_fingers = [i for i, cb in enumerate(self.finger_checkboxes) if cb.isChecked()]

            adaptive_config = {
                "type": "adaptive_grasp",
                "sensor_ids": sensor_ids,
                "initial_action": self.initial_action_combo.currentData() if self.initial_action_combo.currentData() else "",
                "finger_indices": selected_fingers,
                "close_step": self.close_step_spin.value(),
                "release_step": self.release_step_spin.value(),
                "close_speed": self.close_speed_spin.value(),
                "step_interval": self.step_interval_spin.value(),
                "force_threshold_x": self.threshold_x_spin.value(),
                "force_threshold_y": self.threshold_y_spin.value(),
                "force_threshold_z": self.threshold_z_spin.value(),
                "stable_duration": self.stable_duration_spin.value(),
                "stable_std_threshold": self.stable_std_spin.value(),
                "sample_window": self.sample_window_spin.value(),
                "max_iterations": self.max_iterations_spin.value(),
                "release_mode": self.release_mode_checkbox.isChecked(),
            }

            if not self.action_manager:
                QMessageBox.warning(self, "错误", "动作管理器未初始化，无法保存配置")
                return False

            ok = self.action_manager.save_config(config_name, adaptive_config)
            if ok:
                self.add_log(f"✓ 已保存配置: {config_name}")
                QMessageBox.information(self, "保存成功", f"配置已保存: {config_name}")
                # 刷新配置下拉
                self.refresh_config_list()
                return True
            else:
                self.add_log(f"✗ 保存配置失败: {config_name}")
                QMessageBox.warning(self, "错误", "保存配置失败")
                return False

        except Exception as e:
            self.add_log(f"✗ 保存配置出错: {e}")
            QMessageBox.warning(self, "错误", f"保存配置时发生错误: {e}")
            return False

    def apply_initial_action(self):
        """将当前在下拉框中选择的初始动作立即应用到机械臂/机械手（通过 ActionManager 执行）。"""
        try:
            action_name = self.initial_action_combo.currentData()
            if not action_name:
                QMessageBox.information(self, "提示", "请先选择一个初始动作")
                return False

            if not self.action_manager:
                QMessageBox.warning(self, "错误", "动作管理器未初始化，无法执行动作")
                return False

            self.add_log(f"尝试应用初始动作: {action_name}")

            # 调用动作管理器执行动作（execute_action 返回 bool）
            try:
                result = self.action_manager.execute_action(action_name)
            except Exception as e:
                self.add_log(f"✗ 执行动作时出错: {e}")
                QMessageBox.warning(self, "错误", f"执行初始动作时出错: {e}")
                return False

            if result:
                self.add_log(f"✓ 初始动作已应用: {action_name}")
                return True
            else:
                self.add_log(f"✗ 初始动作执行失败: {action_name}")
                QMessageBox.warning(self, "错误", f"初始动作执行失败: {action_name}")
                return False

        except Exception as e:
            self.add_log(f"✗ 应用初始动作出错: {e}")
            return False

    def execute_adaptive_config(self, adaptive_config):
        """
        执行保存的自适应抓取配置

        Args:
            adaptive_config: 自适应抓取配置字典

        Returns:
            执行是否成功
        """
        try:
            self.add_log("=" * 50)
            self.add_log("执行保存的自适应抓取配置")
            self.add_log(f"配置类型: {adaptive_config.get('type', 'unknown')}")

            # 应用配置到UI（可选，用于显示）
            if 'sensor_ids' in adaptive_config:
                self.add_log(f"传感器: {adaptive_config['sensor_ids']}")

            if 'finger_indices' in adaptive_config:
                self.add_log(f"手指: {adaptive_config['finger_indices']}")

            if 'force_threshold_x' in adaptive_config:
                self.add_log(f"力阈值: X={adaptive_config['force_threshold_x']}N, "
                           f"Y={adaptive_config['force_threshold_y']}N, "
                           f"Z={adaptive_config['force_threshold_z']}N")

            # 设置控制器配置
            if self.controller:
                # 获取传感器ID（不放入config）
                sensor_ids = adaptive_config.get('sensor_ids', [])

                # 直接使用保存的配置（去掉type和sensor_ids字段）
                config = {k: v for k, v in adaptive_config.items()
                         if k not in ['type', 'sensor_ids']}
                self.controller.set_config(config)

                # 启动自适应抓取
                success = self.controller.start_adaptive_grasp(sensor_ids)

                if success:
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.add_log("自适应抓取已启动")
                    self.add_log("=" * 50)
                    return True
                else:
                    self.add_log("✗ 自适应抓取启动失败")
                    self.add_log("=" * 50)
                    return False
            else:
                self.add_log("✗ 控制器未初始化")
                self.add_log("=" * 50)
                return False

        except Exception as e:
            self.add_log(f"✗ 执行自适应配置错误: {e}")
            self.add_log("=" * 50)
            import traceback
            traceback.print_exc()
            return False

    def apply_selected_config(self):
        """应用配置下拉中所选的配置：将参数应用到 UI，并可选择立即启动"""
        try:
            if not self.action_manager:
                QMessageBox.warning(self, "错误", "动作管理器未初始化，无法获取配置")
                return False

            name = self.config_combo.currentData()
            if not name:
                QMessageBox.information(self, "提示", "请先选择一个配置")
                return False

            config = self.action_manager.get_config(name)
            if not config:
                QMessageBox.warning(self, "错误", f"未找到配置: {name}")
                return False

            # 将配置应用到 UI
            try:
                # 传感器选择
                sensor_ids = config.get('sensor_ids', [])
                # 取消所有选择
                for i in range(self.sensor_list.count()):
                    item = self.sensor_list.item(i)
                    item.setSelected(item.data(Qt.ItemDataRole.UserRole) in sensor_ids)

                # 手指选择
                fingers = config.get('finger_indices', [])
                for i, cb in enumerate(self.finger_checkboxes):
                    cb.setChecked(i in fingers)

                # 数值参数
                if 'close_step' in config:
                    self.close_step_spin.setValue(config.get('close_step', self.close_step_spin.value()))
                if 'release_step' in config:
                    self.release_step_spin.setValue(config.get('release_step', self.release_step_spin.value()))
                if 'close_speed' in config:
                    self.close_speed_spin.setValue(config.get('close_speed', self.close_speed_spin.value()))
                if 'step_interval' in config:
                    self.step_interval_spin.setValue(config.get('step_interval', self.step_interval_spin.value()))
                if 'force_threshold_x' in config:
                    self.threshold_x_spin.setValue(config.get('force_threshold_x', self.threshold_x_spin.value()))
                if 'force_threshold_y' in config:
                    self.threshold_y_spin.setValue(config.get('force_threshold_y', self.threshold_y_spin.value()))
                if 'force_threshold_z' in config:
                    self.threshold_z_spin.setValue(config.get('force_threshold_z', self.threshold_z_spin.value()))
                if 'stable_duration' in config:
                    self.stable_duration_spin.setValue(config.get('stable_duration', self.stable_duration_spin.value()))
                if 'stable_std_threshold' in config:
                    self.stable_std_spin.setValue(config.get('stable_std_threshold', self.stable_std_spin.value()))
                if 'sample_window' in config:
                    self.sample_window_spin.setValue(config.get('sample_window', self.sample_window_spin.value()))
                if 'max_iterations' in config:
                    self.max_iterations_spin.setValue(config.get('max_iterations', self.max_iterations_spin.value()))

                # 释放模式
                if 'release_mode' in config:
                    self.release_mode_checkbox.setChecked(config.get('release_mode', False))

                # 初始动作选择：尝试匹配 data 或文本
                initial_action = config.get('initial_action', None)
                if initial_action is not None:
                    idx = self.initial_action_combo.findData(initial_action)
                    if idx >= 0:
                        self.initial_action_combo.setCurrentIndex(idx)
                    else:
                        t_idx = self.initial_action_combo.findText(initial_action)
                        if t_idx >= 0:
                            self.initial_action_combo.setCurrentIndex(t_idx)

                self.add_log(f"已应用配置: {name}")

            except Exception as e:
                self.add_log(f"✗ 应用配置到UI失败: {e}")
                QMessageBox.warning(self, "错误", f"应用配置失败: {e}")
                return False

            # 询问是否立即启动
            reply = QMessageBox.question(self, "启动配置", "是否立即使用该配置启动自适应抓取？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # 使用execute_adaptive_config启动
                self.execute_adaptive_config(config)

            return True

        except Exception as e:
            self.add_log(f"✗ 应用选中配置出错: {e}")
            return False
