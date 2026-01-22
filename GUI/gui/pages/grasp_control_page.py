#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDoubleSpinBox,
    QFrame, QProgressBar, QGroupBox
)
import pyqtgraph as pg
from core.grasp_controller import GraspController


class GraspControlPage(QWidget):
    """抓取控制页面，用于控制机械手抓取物体"""

    def __init__(self, main_window, sensor_data_manager):
        super().__init__()

        self.main_window = main_window
        self.sensor_data_manager = sensor_data_manager

        # 创建抓取控制器
        self.grasp_controller = GraspController(sensor_data_manager)

        # 创建UI
        self.setup_ui()

        # 连接信号
        self.connect_signals()

    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建标题标签
        self.title_label = QLabel("抓取控制")
        self.title_label.setObjectName("pageTitle")
        self.main_layout.addWidget(self.title_label)

        # 创建控制参数区域
        self.control_group = QGroupBox("抓取参数")
        self.control_layout = QVBoxLayout(self.control_group)

        # 力阈值设置
        self.threshold_layout = QHBoxLayout()
        self.threshold_label = QLabel("抓取力阈值 (N):")
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 10.0)
        self.threshold_spin.setValue(2.0)
        self.threshold_spin.setSingleStep(0.1)
        self.threshold_layout.addWidget(self.threshold_label)
        self.threshold_layout.addWidget(self.threshold_spin)
        self.control_layout.addLayout(self.threshold_layout)

        # 稳定时间设置
        self.stable_time_layout = QHBoxLayout()
        self.stable_time_label = QLabel("稳定时间 (s):")
        self.stable_time_spin = QDoubleSpinBox()
        self.stable_time_spin.setRange(0.1, 2.0)
        self.stable_time_spin.setValue(0.5)
        self.stable_time_spin.setSingleStep(0.1)
        self.stable_time_layout.addWidget(self.stable_time_label)
        self.stable_time_layout.addWidget(self.stable_time_spin)
        self.control_layout.addLayout(self.stable_time_layout)

        self.main_layout.addWidget(self.control_group)

        # 创建状态显示区域
        self.status_group = QGroupBox("抓取状态")
        self.status_layout = QVBoxLayout(self.status_group)

        # 当前力值显示
        self.force_layout = QHBoxLayout()
        self.force_label = QLabel("当前力值:")
        self.force_value_label = QLabel("0.0 N")
        self.force_layout.addWidget(self.force_label)
        self.force_layout.addWidget(self.force_value_label)
        self.status_layout.addLayout(self.force_layout)

        # 抓取状态显示
        self.grasp_status_layout = QHBoxLayout()
        self.grasp_status_label = QLabel("抓取状态:")
        self.grasp_status_value_label = QLabel("未开始")
        self.grasp_status_value_label.setStyleSheet("color: gray;")
        self.grasp_status_layout.addWidget(self.grasp_status_label)
        self.grasp_status_layout.addWidget(self.grasp_status_value_label)
        self.status_layout.addLayout(self.grasp_status_layout)

        # 稳定度进度条
        self.stability_layout = QHBoxLayout()
        self.stability_label = QLabel("稳定度:")
        self.stability_progress = QProgressBar()
        self.stability_progress.setRange(0, 100)
        self.stability_progress.setValue(0)
        self.stability_layout.addWidget(self.stability_label)
        self.stability_layout.addWidget(self.stability_progress)
        self.status_layout.addLayout(self.stability_layout)

        self.main_layout.addWidget(self.status_group)

        # 创建控制按钮区域
        self.button_layout = QHBoxLayout()

        # 开始抓取按钮
        self.start_btn = QPushButton("开始抓取")
        self.start_btn.setObjectName("primaryButton")
        self.button_layout.addWidget(self.start_btn)

        # 停止抓取按钮
        self.stop_btn = QPushButton("停止抓取")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.setEnabled(False)
        self.button_layout.addWidget(self.stop_btn)

        self.main_layout.addLayout(self.button_layout)

        # 创建力值图表
        self.plot_group = QGroupBox("力值曲线")
        self.plot_layout = QVBoxLayout(self.plot_group)

        # 创建图表窗口
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2D2D2D')
        self.plot_widget.setLabel('left', 'Force (N)')
        self.plot_widget.setLabel('bottom', 'Time (samples)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()

        # 创建力值曲线
        self.force_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(0, 255, 0), width=2),
            name="力值"
        )
        # 创建阈值线
        self.threshold_line = self.plot_widget.plot(
            pen=pg.mkPen(color=(255, 0, 0), width=1, style=Qt.PenStyle.DashLine),
            name="阈值"
        )

        self.plot_layout.addWidget(self.plot_widget)
        self.main_layout.addWidget(self.plot_group)

    def connect_signals(self):
        """连接信号和槽"""
        # 按钮事件
        self.start_btn.clicked.connect(self.start_grasp)
        self.stop_btn.clicked.connect(self.stop_grasp)

        # 参数变化事件
        self.threshold_spin.valueChanged.connect(self.on_threshold_changed)
        self.stable_time_spin.valueChanged.connect(self.on_stable_time_changed)

        # 抓取控制器信号
        self.grasp_controller.grasp_status_changed.connect(self.on_grasp_status_changed)
        self.grasp_controller.force_threshold_changed.connect(self.on_force_threshold_changed)

    def start_grasp(self):
        """开始抓取"""
        # 更新控制器参数
        self.grasp_controller.set_force_threshold(self.threshold_spin.value())
        self.grasp_controller.set_stable_time(self.stable_time_spin.value())

        # 开始抓取
        self.grasp_controller.start_grasp()

        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.grasp_status_value_label.setText("抓取中...")
        self.grasp_status_value_label.setStyleSheet("color: orange;")

    def stop_grasp(self):
        """停止抓取"""
        # 停止抓取
        self.grasp_controller.stop_grasp()

        # 更新UI状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.grasp_status_value_label.setText("未开始")
        self.grasp_status_value_label.setStyleSheet("color: gray;")
        self.stability_progress.setValue(0)

    def on_threshold_changed(self, value):
        """力阈值变化时调用"""
        self.grasp_controller.set_force_threshold(value)
        self.update_threshold_line()

    def on_stable_time_changed(self, value):
        """稳定时间变化时调用"""
        self.grasp_controller.set_stable_time(value)

    def on_grasp_status_changed(self, success):
        """抓取状态变化时调用"""
        if success:
            self.grasp_status_value_label.setText("抓取成功")
            self.grasp_status_value_label.setStyleSheet("color: green;")
        else:
            self.grasp_status_value_label.setText("抓取中...")
            self.grasp_status_value_label.setStyleSheet("color: orange;")

    def on_force_threshold_changed(self, value):
        """力阈值变化时调用"""
        self.update_threshold_line()

    def update_threshold_line(self):
        """更新阈值线"""
        threshold = self.grasp_controller.force_threshold
        self.threshold_line.setData([0, 100], [threshold, threshold])

    def update_force_display(self):
        """更新力值显示"""
        # 获取当前力值
        force = self.grasp_controller.get_current_force()
        
        # 更新力值标签
        self.force_value_label.setText(f"{force:.2f} N")
        
        # 更新稳定度进度条
        if self.grasp_controller.is_grasping:
            stability = min(100, int((self.grasp_controller.stable_samples / 
                                   self.grasp_controller.required_stable_samples) * 100))
            self.stability_progress.setValue(stability)
        
        # 更新力值曲线
        if hasattr(self, 'force_data'):
            self.force_data.append(force)
            if len(self.force_data) > 100:  # 只显示最近100个数据点
                self.force_data.pop(0)
        else:
            self.force_data = [force]
            
        self.force_curve.setData(self.force_data) 