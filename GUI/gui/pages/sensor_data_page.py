#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QCheckBox,
    QGroupBox, QFrame, QScrollArea, QListWidget,
    QListWidgetItem, QSizePolicy, QSpinBox, QDoubleSpinBox,
    QFileDialog
)
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import os


class SensorDataPage(QWidget):
    """传感器数据页面，用于展示传感器数据曲线"""

    def __init__(self, main_window, sensor_data_manager):
        super().__init__()

        self.main_window = main_window
        self.sensor_data_manager = sensor_data_manager
        
        # 获取串口管理器引用，用于发送标定命令
        if hasattr(main_window, 'serial_manager'):
            self.serial_manager = main_window.serial_manager
        else:
            self.serial_manager = None

        # 选中的传感器ID列表
        self.selected_sensors = []

        # 曲线偏移参数
        self.offset_enabled = False  # 是否启用偏移
        self.offset_value = 0.5  # 默认偏移量

        # 创建图表数据和曲线字典
        self.plot_curves = {}  # {sensor_id: {'data1': curve, 'data2': curve, 'data3': curve}}
        self.plot_data = {}  # {sensor_id: {'data1': [], 'data2': [], 'data3': []}}

        # 最大数据点数量，用于限制绘图数据量
        self.max_data_points = 500

        # 创建UI
        self.setup_ui()

        # 连接信号
        self.connect_signals()

        # 创建定时器用于定期更新图表
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(100)  # 每100ms更新一次

    def setup_ui(self):
        """设置UI布局"""
        # 设置尺寸策略，使组件能够正确分配空间
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建标题标签
        self.title_label = QLabel("传感器数据监测")
        self.title_label.setObjectName("pageTitle")
        self.main_layout.addWidget(self.title_label)

        # 创建传感器当前值显示区域
        self.sensor_values_frame = QFrame()
        self.sensor_values_frame.setObjectName("sensorValuesFrame")
        self.sensor_values_layout = QHBoxLayout(self.sensor_values_frame)
        self.sensor_values_layout.setContentsMargins(5, 5, 5, 5)
        self.sensor_values_layout.setSpacing(10)

        # 添加当前值标签
        self.current_values_label = QLabel("当前传感器数值: 暂无数据")
        self.current_values_label.setObjectName("currentValuesLabel")
        self.sensor_values_layout.addWidget(self.current_values_label)
        
        # 添加标定按钮
        self.calibrate_btn = QPushButton("标定")
        self.calibrate_btn.setObjectName("primaryButton")
        self.calibrate_btn.setFixedWidth(80)
        self.sensor_values_layout.addWidget(self.calibrate_btn)

        # 添加到主布局
        self.main_layout.addWidget(self.sensor_values_frame)

        # 创建传感器选择区域
        self.sensor_select_frame = QFrame()
        self.sensor_select_frame.setObjectName("controlFrame")
        # 设置固定高度，防止随窗口变大而变大
        self.sensor_select_frame.setMaximumHeight(220)
        self.sensor_select_layout = QVBoxLayout(self.sensor_select_frame)
        self.sensor_select_layout.setContentsMargins(10, 10, 10, 10)
        self.sensor_select_layout.setSpacing(10)

        # 传感器选择标题
        self.sensor_select_label = QLabel("选择要监测的传感器:")
        self.sensor_select_layout.addWidget(self.sensor_select_label)
        self.sensor_select_label.setStyleSheet("background-color: transparent;")

        # 传感器列表区域
        self.sensor_list_widget = QListWidget()
        # 限制传感器列表的最大高度和最小高度，确保它不会随窗口变大而变大
        self.sensor_list_widget.setMinimumHeight(80)
        self.sensor_list_widget.setMaximumHeight(100)
        self.sensor_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # 设置传感器列表的样式，只通过字体颜色区分选择状态
        self.sensor_list_widget.setStyleSheet("""
            QListWidget::item:selected {
                color: #bd93f9;
                font-weight: bold;
            }
            QListWidget::item:hover {
                color: #8b6ec7;
            }
        """)
        
        self.sensor_select_layout.addWidget(self.sensor_list_widget)

        # 按钮区域
        self.button_layout = QHBoxLayout()

        # 刷新传感器列表按钮
        self.refresh_btn = QPushButton("刷新传感器列表")
        self.refresh_btn.setObjectName("secondaryButton")
        self.button_layout.addWidget(self.refresh_btn)

        # 清空数据按钮
        self.clear_btn = QPushButton("清空数据")
        self.clear_btn.setObjectName("secondaryButton")
        self.button_layout.addWidget(self.clear_btn)

        # 保存数据按钮
        self.save_btn = QPushButton("保存数据")
        self.save_btn.setObjectName("primaryButton")
        self.button_layout.addWidget(self.save_btn)

        self.sensor_select_layout.addLayout(self.button_layout)

        # 添加控制选项
        self.plot_options_layout = QHBoxLayout()

        # 显示选项
        self.show_x_check = QCheckBox("显示X轴数据")
        self.show_x_check.setChecked(True)
        self.show_x_check.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.show_x_check)

        self.show_y_check = QCheckBox("显示Y轴数据")
        self.show_y_check.setChecked(True)
        self.show_y_check.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.show_y_check)

        self.show_z_check = QCheckBox("显示Z轴数据")
        self.show_z_check.setChecked(True)
        self.show_z_check.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.show_z_check)

        # 自动缩放选项
        self.auto_scale_check = QCheckBox("自动缩放Y轴")
        self.auto_scale_check.setChecked(True)
        self.auto_scale_check.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.auto_scale_check)

        # 添加Y轴范围设置控件
        self.y_range_label = QLabel("Y轴范围:")
        self.y_range_label.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.y_range_label)
        
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1000, 1000)
        self.y_min_spin.setValue(-10)
        self.y_min_spin.setSingleStep(1)
        self.y_min_spin.setPrefix("最小值: ")
        self.y_min_spin.setEnabled(False)  # 默认禁用，因为自动缩放开启
        self.plot_options_layout.addWidget(self.y_min_spin)
        
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1000, 1000)
        self.y_max_spin.setValue(10)
        self.y_max_spin.setSingleStep(1)
        self.y_max_spin.setPrefix("最大值: ")
        self.y_max_spin.setEnabled(False)  # 默认禁用，因为自动缩放开启
        self.plot_options_layout.addWidget(self.y_max_spin)
        
        self.apply_y_range_btn = QPushButton("应用")
        self.apply_y_range_btn.setEnabled(False)  # 默认禁用
        self.apply_y_range_btn.setObjectName("secondaryButton")
        self.plot_options_layout.addWidget(self.apply_y_range_btn)

        # 添加重置Y轴范围按钮
        self.reset_y_range_btn = QPushButton("重置")
        self.reset_y_range_btn.setEnabled(False)  # 默认禁用
        self.reset_y_range_btn.setObjectName("secondaryButton")
        self.plot_options_layout.addWidget(self.reset_y_range_btn)

        # 曲线偏移选项
        self.offset_check = QCheckBox("启用曲线偏移")
        self.offset_check.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.offset_check)

        # 偏移量设置
        self.offset_label = QLabel("偏移量:")
        self.offset_label.setStyleSheet("background-color: transparent;")
        self.plot_options_layout.addWidget(self.offset_label)
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(0.1, 5.0)
        self.offset_spin.setValue(0.5)
        self.offset_spin.setSingleStep(0.1)
        self.offset_spin.setEnabled(False)  # 默认禁用
        self.plot_options_layout.addWidget(self.offset_spin)

        self.plot_options_layout.addStretch()

        self.sensor_select_layout.addLayout(self.plot_options_layout)

        # 添加传感器选择区域到主布局
        self.main_layout.addWidget(self.sensor_select_frame)

        # 创建图表区域
        self.plots_frame = QFrame()
        self.plots_frame.setObjectName("plotsFrame")
        self.plots_frame.setMinimumHeight(400)
        # 设置垂直尺寸策略为Expanding，让绘图区域占用尽可能多的空间
        self.plots_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.plots_layout = QVBoxLayout(self.plots_frame)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(0)

        # 创建图表窗口
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2D2D2D')
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time (samples)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setTitle("传感器数据")
        self.plot_widget.addLegend()

        # 添加图表到布局
        self.plots_layout.addWidget(self.plot_widget)

        # 添加图表区域到主布局
        self.main_layout.addWidget(self.plots_frame)

        # 添加状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.main_layout.addWidget(self.status_label)

    def connect_signals(self):
        """连接信号和槽"""
        # 按钮事件
        self.refresh_btn.clicked.connect(self.refresh_sensor_list)
        self.clear_btn.clicked.connect(self.clear_data)
        self.save_btn.clicked.connect(self.save_data)
        self.calibrate_btn.clicked.connect(self.send_calibration_command)

        # 复选框事件
        self.show_x_check.stateChanged.connect(self.update_curve_visibility)
        self.show_y_check.stateChanged.connect(self.update_curve_visibility)
        self.show_z_check.stateChanged.connect(self.update_curve_visibility)
        self.auto_scale_check.stateChanged.connect(self.toggle_auto_scale)
        self.offset_check.stateChanged.connect(self.on_offset_changed)
        self.offset_spin.valueChanged.connect(self.on_offset_value_changed)
        
        # 添加Y轴范围控件的信号连接
        self.apply_y_range_btn.clicked.connect(self.apply_custom_y_range)
        self.reset_y_range_btn.clicked.connect(self.reset_y_range)
        
        # 传感器列表选择变化信号
        self.sensor_list_widget.itemSelectionChanged.connect(self.on_sensor_selection_changed)

        # 传感器数据更新事件
        self.sensor_data_manager.data_updated_signal.connect(self.on_sensor_data_updated)

    def refresh_sensor_list(self):
        """刷新传感器列表"""
        # 保存当前选择
        current_selected = []
        for i in range(self.sensor_list_widget.count()):
            item = self.sensor_list_widget.item(i)
            if item.isSelected():
                current_selected.append(item.text())

        # 清空列表
        self.sensor_list_widget.clear()

        # 获取可用传感器ID
        sensors = self.sensor_data_manager.get_all_sensors()

        if not sensors:
            self.status_label.setText("未检测到任何传感器")
            return

        # 添加传感器到列表
        for sensor_id in sensors:
            item = QListWidgetItem(f"传感器 {sensor_id}")
            item.setData(Qt.ItemDataRole.UserRole, sensor_id)
            self.sensor_list_widget.addItem(item)

            # 恢复选择状态
            if f"传感器 {sensor_id}" in current_selected:
                item.setSelected(True)

        self.status_label.setText(f"已检测到 {len(sensors)} 个传感器")

    def on_sensor_selection_changed(self):
        """传感器选择变化时调用"""
        # 清空选中列表
        self.selected_sensors.clear()

        # 获取当前选中的传感器ID
        for item in self.sensor_list_widget.selectedItems():
            sensor_id = item.data(Qt.ItemDataRole.UserRole)
            self.selected_sensors.append(sensor_id)

        # 更新图表
        self.update_plot_curves()

        # 更新当前值显示
        self.update_current_values_display()

    def update_current_values_display(self):
        """更新当前传感器数值显示"""
        if not self.selected_sensors:
            self.current_values_label.setText("当前传感器数值: 暂无数据")
            return

        # 构建显示文本
        display_text = "当前传感器数值: "

        for sensor_id in self.selected_sensors:
            sensor_data = self.sensor_data_manager.get_sensor_data(sensor_id)
            if sensor_data:
                latest_values = sensor_data.get_latest_values()
                display_text += f"传感器{sensor_id}[X:{latest_values[0]:.2f}, Y:{latest_values[1]:.2f}, Z:{latest_values[2]:.2f}] "

        # 更新标签文本
        self.current_values_label.setText(display_text)

    def update_plot_curves(self):
        """更新图表曲线"""
        # 清空当前曲线
        self.plot_widget.clear()
        self.plot_widget.addLegend()

        # 颜色列表，用于区分不同传感器
        colors = [
            (255, 0, 0),  # 红色
            (0, 255, 0),  # 绿色
            (0, 0, 255),  # 蓝色
            (255, 255, 0),  # 黄色
            (0, 255, 255),  # 青色
            (255, 0, 255),  # 洋红色
            (128, 128, 0),  # 橄榄色
            (128, 0, 128),  # 紫色
            (0, 128, 128),  # 蓝绿色
            (255, 128, 0)  # 橙色
        ]

        # 重新创建曲线字典
        self.plot_curves = {}

        # 为每个选中的传感器创建曲线
        for i, sensor_id in enumerate(self.selected_sensors):
            color_index = i % len(colors)
            color = colors[color_index]

            # 计算偏移量
            offset = i * self.offset_value if self.offset_enabled else 0

            # 创建数据结构
            if sensor_id not in self.plot_data:
                self.plot_data[sensor_id] = {
                    'data1': [],
                    'data2': [],
                    'data3': []
                }

            # 获取数据
            data1 = np.array(self.plot_data[sensor_id]['data1'])
            data2 = np.array(self.plot_data[sensor_id]['data2'])
            data3 = np.array(self.plot_data[sensor_id]['data3'])

            # 应用偏移
            if self.offset_enabled and len(data1) > 0:
                data1 = data1 + offset
                data2 = data2 + offset
                data3 = data3 + offset

            # 创建X轴数据
            x_data = list(range(len(data1)))

            # 创建曲线
            self.plot_curves[sensor_id] = {
                'data1': self.plot_widget.plot(
                    x_data, data1,
                    pen=pg.mkPen(color=color, width=2),
                    name=f"传感器{sensor_id}-X轴"
                ),
                'data2': self.plot_widget.plot(
                    x_data, data2,
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                    name=f"传感器{sensor_id}-Y轴"
                ),
                'data3': self.plot_widget.plot(
                    x_data, data3,
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DotLine),
                    name=f"传感器{sensor_id}-Z轴"
                )
            }

        # 更新曲线可见性
        self.update_curve_visibility()

        # 更新状态标签
        if self.selected_sensors:
            self.status_label.setText(f"监测中: {', '.join([f'传感器{id}' for id in self.selected_sensors])}")
        else:
            self.status_label.setText("未选择传感器")

        # 如果取消了自动缩放，应用固定范围
        if not self.auto_scale_check.isChecked():
            # 获取当前 Y 轴范围作为固定范围
            y_range = self.plot_widget.getPlotItem().getViewBox().viewRange()[1]
            self.plot_widget.getPlotItem().getViewBox().setYRange(y_range[0], y_range[1], padding=0)

    def update_curve_visibility(self):
        """更新曲线可见性"""
        for sensor_id in self.plot_curves:
            # 根据复选框状态设置曲线可见性
            self.plot_curves[sensor_id]['data1'].setVisible(self.show_x_check.isChecked())
            self.plot_curves[sensor_id]['data2'].setVisible(self.show_y_check.isChecked())
            self.plot_curves[sensor_id]['data3'].setVisible(self.show_z_check.isChecked())

    def toggle_auto_scale(self, state):
        """切换自动缩放"""
        if state == Qt.CheckState.Checked.value:
            # 开启 Y 轴自动缩放
            self.plot_widget.getPlotItem().getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis)
            
            # 禁用Y轴范围控件
            self.y_min_spin.setEnabled(False)
            self.y_max_spin.setEnabled(False)
            self.apply_y_range_btn.setEnabled(False)
            self.reset_y_range_btn.setEnabled(False)
        else:
            # 关闭 Y 轴自动缩放并设置固定范围
            self.plot_widget.getPlotItem().getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)

            # 获取当前 Y 轴范围作为固定范围
            y_range = self.plot_widget.getPlotItem().getViewBox().viewRange()[1]
            self.plot_widget.getPlotItem().getViewBox().setYRange(y_range[0], y_range[1], padding=0)
            
            # 更新Y轴范围控件的值，显示当前实际范围
            self.y_min_spin.setValue(y_range[0])
            self.y_max_spin.setValue(y_range[1])
            
            # 启用Y轴范围控件
            self.y_min_spin.setEnabled(True)
            self.y_max_spin.setEnabled(True)
            self.apply_y_range_btn.setEnabled(True)
            self.reset_y_range_btn.setEnabled(True)

    def apply_custom_y_range(self):
        """应用自定义Y轴范围"""
        # 确保自动缩放被关闭
        if self.auto_scale_check.isChecked():
            return
            
        # 获取用户设置的Y轴范围
        y_min = self.y_min_spin.value()
        y_max = self.y_max_spin.value()
        
        # 验证最小值小于最大值
        if y_min >= y_max:
            self.status_label.setText("错误：Y轴最小值必须小于最大值")
            return
            
        # 应用自定义Y轴范围
        self.plot_widget.getPlotItem().getViewBox().setYRange(y_min, y_max, padding=0)
        self.status_label.setText(f"已设置Y轴范围: [{y_min}, {y_max}]")

    def on_offset_changed(self, state):
        """偏移启用状态变化时调用"""
        self.offset_enabled = state == Qt.CheckState.Checked.value
        self.offset_spin.setEnabled(self.offset_enabled)
        self.update_plot_curves()

    def on_offset_value_changed(self, value):
        """偏移量变化时调用"""
        self.offset_value = value
        if self.offset_enabled:
            self.update_plot_curves()

    @pyqtSlot(int, list)
    def on_sensor_data_updated(self, sensor_id, values):
        """接收到传感器数据更新时调用"""
        # 确保传感器ID在数据字典中
        if sensor_id not in self.plot_data:
            self.plot_data[sensor_id] = {
                'data1': [],
                'data2': [],
                'data3': []
            }

        # 添加数据
        self.plot_data[sensor_id]['data1'].append(values[0])
        self.plot_data[sensor_id]['data2'].append(values[1])
        self.plot_data[sensor_id]['data3'].append(values[2])

        # 限制数据点数量
        if len(self.plot_data[sensor_id]['data1']) > self.max_data_points:
            self.plot_data[sensor_id]['data1'] = self.plot_data[sensor_id]['data1'][-self.max_data_points:]
            self.plot_data[sensor_id]['data2'] = self.plot_data[sensor_id]['data2'][-self.max_data_points:]
            self.plot_data[sensor_id]['data3'] = self.plot_data[sensor_id]['data3'][-self.max_data_points:]

        # 更新传感器当前值显示（只有当该传感器被选中时才更新显示）
        if sensor_id in self.selected_sensors:
            self.update_current_values_display()

        # 如果是新传感器，刷新传感器列表
        if sensor_id not in [item.data(Qt.ItemDataRole.UserRole) for index in range(self.sensor_list_widget.count())
                             for item in [self.sensor_list_widget.item(index)]]:
            self.refresh_sensor_list()

    def update_plots(self):
        """更新图表"""
        # 只更新选中的传感器图表
        for sensor_id in self.selected_sensors:
            if sensor_id in self.plot_curves and sensor_id in self.plot_data:
                # 获取数据
                data1 = np.array(self.plot_data[sensor_id]['data1'])
                data2 = np.array(self.plot_data[sensor_id]['data2'])
                data3 = np.array(self.plot_data[sensor_id]['data3'])

                # 应用偏移
                if self.offset_enabled and len(data1) > 0:
                    # 计算当前传感器的偏移量
                    sensor_index = self.selected_sensors.index(sensor_id)
                    offset = sensor_index * self.offset_value
                    
                    data1 = data1 + offset
                    data2 = data2 + offset
                    data3 = data3 + offset

                # 创建X轴数据（样本索引）
                x_data = list(range(len(data1)))

                # 更新曲线
                if len(data1) > 0:
                    self.plot_curves[sensor_id]['data1'].setData(x_data, data1)
                    self.plot_curves[sensor_id]['data2'].setData(x_data, data2)
                    self.plot_curves[sensor_id]['data3'].setData(x_data, data3)

        # 每次更新图表时也更新当前值显示
        self.update_current_values_display()

    def clear_data(self):
        """清空数据"""
        # 清空所有传感器数据
        for sensor_id in self.selected_sensors:
            if sensor_id in self.plot_data:
                self.plot_data[sensor_id]['data1'].clear()
                self.plot_data[sensor_id]['data2'].clear()
                self.plot_data[sensor_id]['data3'].clear()

            # 清空传感器管理器中的数据
            self.sensor_data_manager.clear_sensor_data(sensor_id)

        # 更新状态标签
        self.status_label.setText("数据已清空")

    def save_data(self):
        """保存数据"""
        if not self.selected_sensors:
            self.status_label.setText("请先选择传感器")
            return

        try:
            # 创建默认文件名
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            
            if len(self.selected_sensors) == 1:
                default_filename = f"sensor{self.selected_sensors[0]}_data_{timestamp}.csv"
            else:
                default_filename = f"all_sensors_data_{timestamp}.csv"
                
            # 打开文件选择对话框
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "保存传感器数据",
                os.path.join(self.sensor_data_manager.data_dir, default_filename),
                "CSV文件 (*.csv);;所有文件 (*.*)"
            )
            
            # 如果用户取消了对话框，filepath 为空
            if not filepath:
                return
                
            # 通过传感器数据管理器保存数据
            if len(self.selected_sensors) == 1:
                # 保存单个传感器数据
                success, save_path = self.sensor_data_manager.save_to_csv(
                    sensor_id=self.selected_sensors[0], 
                    filepath=filepath
                )
            else:
                # 保存多个传感器数据
                success, save_path = self.sensor_data_manager.save_to_csv(
                    filepath=filepath
                )
                
            if success:
                self.status_label.setText(f"数据保存成功: {save_path}")
            else:
                self.status_label.setText("数据保存失败")
                
        except Exception as e:
            self.status_label.setText(f"数据保存错误: {str(e)}")

    def reset_y_range(self):
        """重置Y轴范围到默认值"""
        # 确保自动缩放被关闭
        if self.auto_scale_check.isChecked():
            return
            
        # 设置默认的Y轴范围
        default_min = -10
        default_max = 10
        
        # 应用默认Y轴范围
        self.y_min_spin.setValue(default_min)
        self.y_max_spin.setValue(default_max)
        self.plot_widget.getPlotItem().getViewBox().setYRange(default_min, default_max, padding=0)
        self.status_label.setText(f"已重置Y轴范围: [{default_min}, {default_max}]")

    def send_calibration_command(self):
        """发送标定命令到下位机"""
        if not self.serial_manager or not self.serial_manager.is_connected():
            self.status_label.setText("错误：串口未连接，无法发送标定命令")
            return
            
        # 发送标定命令，16进制数据 0xFF
        success = self.serial_manager.send_data("FF", is_hex=True)
        
        if success:
            self.status_label.setText("已发送标定命令到下位机")
        else:
            self.status_label.setText("发送标定命令失败")