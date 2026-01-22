#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
    QListWidget, QListWidgetItem, QSizePolicy,
    QCheckBox, QGroupBox, QGridLayout, QComboBox
)
import matplotlib

matplotlib.use('QtAgg')  # 使用QtAgg后端，兼容PyQt6
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
import numpy as np
import os
import sys

# 配置matplotlib字体，避免中文显示问题和负号问题
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# 优化matplotlib性能设置
matplotlib.rcParams['path.simplify'] = True
matplotlib.rcParams['path.simplify_threshold'] = 0.1
matplotlib.rcParams['agg.path.chunksize'] = 10000
matplotlib.rcParams['figure.max_open_warning'] = 0

# 使用更安全的方式检测Windows系统，避免WMI查询超时
if sys.platform.startswith('win'):
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']


class MplCanvas(FigureCanvas):
    """Matplotlib画布类"""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # 创建一个Figure对象，并设置背景色
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#282a36')

        # 创建3D子图
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#282a36')

        # 设置文本颜色为白色
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.zaxis.label.set_color('white')
        self.ax.title.set_color('white')

        # 设置刻度标签颜色为白色
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.tick_params(axis='z', colors='white')

        # 设置网格颜色
        self.ax.grid(True, linestyle='--', alpha=0.3, color='white')

        # 性能优化设置
        self.ax.mouse_init()  # 初始化鼠标交互
        
        # 调用父类构造函数
        super(MplCanvas, self).__init__(self.fig)
        
        # 设置canvas的性能优化选项
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
    def resizeEvent(self, event):
        """重写调整大小事件以优化性能"""
        # 延迟处理resize事件以避免频繁重绘
        super().resizeEvent(event)
        self.draw_idle()


class ForceVisualizationPage(QWidget):
    """力场变形网格可视化页面"""

    def __init__(self, main_window, sensor_data_manager):
        super().__init__()

        self.main_window = main_window
        self.sensor_data_manager = sensor_data_manager

        # 选中的传感器ID
        self.selected_sensor = None

        # 网格参数
        self.resolution = 20
        self.grid_range = 5

        # 创建基础网格
        self.create_base_grid()

        # 3D表面对象
        self.surf = None
        self.force_arrow = None
        self.cbar = None

        # 性能优化相关变量
        self.last_force_data = [0, 0, 0]
        self.force_change_threshold = 0.01  # 力值变化阈值
        self.skip_frame_count = 0
        self.max_skip_frames = 2  # 最多跳过的帧数

        # 创建UI
        self.setup_ui()

        # 连接信号
        self.connect_signals()

        # 创建更新定时器 - 提高刷新率到20fps
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_visualization)
        self.update_timer.start(50)  # 每50毫秒更新一次（20fps）

    def create_base_grid(self):
        """创建基础网格"""
        x = np.linspace(-self.grid_range, self.grid_range, self.resolution)
        y = np.linspace(-self.grid_range, self.grid_range, self.resolution)
        self.X, self.Y = np.meshgrid(x, y)
        self.Z = np.zeros_like(self.X)

        # 当前力数据
        self.force_data = [0, 0, 0]

        # 力历史记录（用于平滑动画）
        self.force_history = np.zeros((10, 3))

    def setup_ui(self):
        """设置UI布局"""
        # 设置尺寸策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建标题标签
        self.title_label = QLabel("3D力场可视化")
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

        # 添加到主布局
        self.main_layout.addWidget(self.sensor_values_frame)

        # 创建内容区域
        self.content_layout = QHBoxLayout()

        # 创建左侧控制面板
        self.control_frame = QFrame()
        self.control_frame.setObjectName("controlFrame")
        self.control_frame.setMinimumWidth(200)
        self.control_frame.setMaximumWidth(250)
        self.control_layout = QVBoxLayout(self.control_frame)

        # 传感器选择组
        self.sensor_group = QGroupBox("传感器选择")
        self.sensor_group.setObjectName("groupBox")
        self.sensor_group_layout = QVBoxLayout(self.sensor_group)

        # 传感器列表
        self.sensor_list = QListWidget()
        self.sensor_list.setMinimumHeight(100)
        self.sensor_list.setMaximumHeight(150)
        self.sensor_group_layout.addWidget(self.sensor_list)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新传感器列表")
        self.refresh_btn.setObjectName("secondaryButton")
        self.sensor_group_layout.addWidget(self.refresh_btn)

        self.control_layout.addWidget(self.sensor_group)

        # 可视化参数组
        self.visual_group = QGroupBox("可视化参数")
        self.visual_group.setObjectName("groupBox")
        self.visual_group_layout = QVBoxLayout(self.visual_group)

        # 参数网格布局
        self.params_grid = QGridLayout()

        # 变形强度滑块（简化为复选框）
        self.show_arrow_check = QCheckBox("显示力向量")
        self.show_arrow_check.setChecked(True)
        self.params_grid.addWidget(self.show_arrow_check, 0, 0)

        self.auto_rotate_check = QCheckBox("自动旋转视角")
        self.auto_rotate_check.setChecked(True)
        self.params_grid.addWidget(self.auto_rotate_check, 1, 0)

        # 添加刷新率设置
        self.refresh_rate_label = QLabel("刷新率:")
        self.params_grid.addWidget(self.refresh_rate_label, 2, 0)
        
        self.refresh_rate_combo = QComboBox()
        self.refresh_rate_combo.addItems([
            "10 FPS (100ms)", 
            "20 FPS (50ms)", 
            "30 FPS (33ms)", 
            "60 FPS (16ms)"
        ])
        self.refresh_rate_combo.setCurrentIndex(1)  # 默认20 FPS
        self.refresh_rate_combo.currentIndexChanged.connect(self.on_refresh_rate_changed)
        self.params_grid.addWidget(self.refresh_rate_combo, 2, 1)

        self.visual_group_layout.addLayout(self.params_grid)

        # 视角控制按钮
        self.view_control_layout = QGridLayout()

        self.reset_view_btn = QPushButton("重置视角")
        self.reset_view_btn.setObjectName("secondaryButton")
        self.view_control_layout.addWidget(self.reset_view_btn, 0, 0, 1, 2)

        self.view_top_btn = QPushButton("俯视图")
        self.view_top_btn.setObjectName("secondaryButton")
        self.view_control_layout.addWidget(self.view_top_btn, 1, 0)

        self.view_side_btn = QPushButton("侧视图")
        self.view_side_btn.setObjectName("secondaryButton")
        self.view_control_layout.addWidget(self.view_side_btn, 1, 1)

        self.visual_group_layout.addLayout(self.view_control_layout)

        self.control_layout.addWidget(self.visual_group)

        # 添加伸缩空间
        self.control_layout.addStretch()

        # 添加左侧控制面板到内容布局
        self.content_layout.addWidget(self.control_frame)

        # 创建右侧可视化区域
        self.visualization_frame = QFrame()
        self.visualization_frame.setObjectName("plotsFrame")
        self.visualization_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.visualization_layout = QVBoxLayout(self.visualization_frame)
        self.visualization_layout.setContentsMargins(0, 0, 0, 0)

        # 创建Matplotlib画布
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.visualization_layout.addWidget(self.canvas)

        # 添加右侧可视化区域到内容布局
        self.content_layout.addWidget(self.visualization_frame)

        # 添加内容布局到主布局
        self.main_layout.addLayout(self.content_layout)

        # 添加状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.main_layout.addWidget(self.status_label)

        # 初始化可视化
        self.initialize_visualization()

    def connect_signals(self):
        """连接信号和槽"""
        # 按钮事件
        self.refresh_btn.clicked.connect(self.refresh_sensor_list)
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.view_top_btn.clicked.connect(self.set_top_view)
        self.view_side_btn.clicked.connect(self.set_side_view)

        # 传感器选择事件
        self.sensor_list.itemClicked.connect(self.on_sensor_selected)

        # 传感器数据更新事件
        self.sensor_data_manager.data_updated_signal.connect(self.on_sensor_data_updated)

    def initialize_visualization(self):
        """初始化可视化"""
        # 清除当前图形
        self.canvas.ax.clear()

        # 设置标题和标签
        self.canvas.ax.set_title('三轴力传感器变形网格可视化', color='white')
        self.canvas.ax.set_xlabel('X轴', color='white')
        self.canvas.ax.set_ylabel('Y轴', color='white')
        self.canvas.ax.set_zlabel('Z轴', color='white')

        # 设置视角和范围
        self.canvas.ax.set_xlim(-self.grid_range, self.grid_range)
        self.canvas.ax.set_ylim(-self.grid_range, self.grid_range)
        self.canvas.ax.set_zlim(-self.grid_range, self.grid_range)
        self.canvas.ax.view_init(elev=30, azim=45)

        # 绘制初始平面 - 使用优化参数
        self.surf = self.canvas.ax.plot_surface(
            self.X, self.Y, self.Z,
            cmap=cm.coolwarm,
            linewidth=0.3,  # 减少线宽
            antialiased=False,  # 关闭抗锯齿
            alpha=0.7,
            rcount=15,  # 减少网格密度
            ccount=15
        )

        # 添加颜色条
        if self.cbar is None:
            self.cbar = self.canvas.fig.colorbar(self.surf, ax=self.canvas.ax, shrink=0.5, aspect=5)
            #self.cbar.set_label('变形强度', color='white')
            self.cbar.ax.yaxis.set_tick_params(color='white')
            self.cbar.outline.set_edgecolor('white')
            for label in self.cbar.ax.get_yticklabels():
                label.set_color('white')

        # 添加力向量箭头
        self.force_arrow = self.canvas.ax.quiver(
            0, 0, 0, 0, 0, 0,
            color='red', linewidth=3,
            arrow_length_ratio=0.15
        )

        # 添加坐标原点
        self.canvas.ax.scatter([0], [0], [0], color='black', s=50)

        # 更新画布
        self.canvas.draw_idle()  # 使用draw_idle而不是draw

    def refresh_sensor_list(self):
        """刷新传感器列表"""
        # 保存当前选择
        current_selected = None
        if self.sensor_list.currentItem():
            current_selected = self.sensor_list.currentItem().data(Qt.ItemDataRole.UserRole)

        # 清空列表
        self.sensor_list.clear()

        # 获取可用传感器ID
        sensors = self.sensor_data_manager.get_all_sensors()

        if not sensors:
            self.status_label.setText("未检测到任何传感器")
            return

        # 添加传感器到列表
        for sensor_id in sensors:
            item = QListWidgetItem(f"传感器 {sensor_id}")
            item.setData(Qt.ItemDataRole.UserRole, sensor_id)
            self.sensor_list.addItem(item)

            # 恢复选择状态
            if current_selected == sensor_id:
                self.sensor_list.setCurrentItem(item)

        self.status_label.setText(f"已检测到 {len(sensors)} 个传感器")

    def on_sensor_selected(self, item):
        """传感器选择事件处理"""
        sensor_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_sensor = sensor_id

        # 更新状态标签
        self.status_label.setText(f"已选择传感器 {sensor_id}")

        # 更新当前值显示
        self.update_current_values_display()

    def update_current_values_display(self):
        """更新当前传感器数值显示"""
        if self.selected_sensor is None:
            self.current_values_label.setText("当前传感器数值: 暂无数据")
            return

        # 获取传感器数据
        sensor_data = self.sensor_data_manager.get_sensor_data(self.selected_sensor)
        if sensor_data:
            latest_values = sensor_data.get_latest_values()
            # 更新内部力数据
            self.force_data = latest_values

            # 更新显示标签
            display_text = f"当前传感器数值: 传感器{self.selected_sensor} "
            display_text += f"[X:{latest_values[0]:.2f}, Y:{latest_values[1]:.2f}, Z:{latest_values[2]:.2f}]"
            self.current_values_label.setText(display_text)

    @pyqtSlot(int, list)
    def on_sensor_data_updated(self, sensor_id, values):
        """接收到传感器数据更新时调用"""
        # 如果是所选传感器，更新数据和显示
        if sensor_id == self.selected_sensor:
            self.force_data = values

            # 更新力历史记录
            self.force_history = np.roll(self.force_history, 1, axis=0)
            self.force_history[0] = values

            # 更新当前值显示
            self.update_current_values_display()

        # 如果是新传感器，刷新传感器列表
        for i in range(self.sensor_list.count()):
            if self.sensor_list.item(i).data(Qt.ItemDataRole.UserRole) == sensor_id:
                break
        else:
            # 未找到该传感器，刷新列表
            self.refresh_sensor_list()

    def update_visualization(self):
        """更新可视化效果 - 优化性能版本"""
        if self.selected_sensor is None:
            return

        # 检查力值是否有显著变化，如果变化很小则跳过部分帧以提高性能
        current_force = np.array(self.force_data)
        last_force = np.array(self.last_force_data)
        force_change = np.linalg.norm(current_force - last_force)
        
        if force_change < self.force_change_threshold:
            self.skip_frame_count += 1
            if self.skip_frame_count < self.max_skip_frames:
                return
            else:
                self.skip_frame_count = 0
        else:
            self.skip_frame_count = 0
            self.last_force_data = current_force.copy()

        # 计算平均力（平滑动画效果）
        avg_force = np.mean(self.force_history[:3], axis=0)
        fx, fy, fz = avg_force

        # 只有在力值变化显著时才完全重绘
        need_full_redraw = force_change > self.force_change_threshold * 10

        if need_full_redraw or self.surf is None:
            # 完全重绘
            self.canvas.ax.clear()

            # 重新设置标题和标签
            self.canvas.ax.set_title('三轴力传感器变形网格可视化', color='white')
            self.canvas.ax.set_xlabel('X轴', color='white')
            self.canvas.ax.set_ylabel('Y轴', color='white')
            self.canvas.ax.set_zlabel('Z轴', color='white')

            # 设置视角和范围
            self.canvas.ax.set_xlim(-self.grid_range, self.grid_range)
            self.canvas.ax.set_ylim(-self.grid_range, self.grid_range)
            self.canvas.ax.set_zlim(-self.grid_range, self.grid_range)

            # 计算到原点的距离
            distance = np.sqrt(self.X ** 2 + self.Y ** 2)

            # 衰减函数 - 使用高斯衰减
            sigma = 3.0  # 控制衰减范围
            decay = np.exp(-(distance ** 2) / (2 * sigma ** 2))

            # XY平面变形（基于X和Y分量）
            X_new = self.X + fx * decay * 0.5
            Y_new = self.Y + fy * decay * 0.5

            # Z方向变形（基于Z分量）
            Z_new = fz * decay * 1.0

            # 绘制新的表面
            self.surf = self.canvas.ax.plot_surface(
                X_new, Y_new, Z_new,
                cmap=cm.coolwarm,
                linewidth=0.3,  # 减少线宽以提高性能
                antialiased=False,  # 关闭抗锯齿以提高性能
                alpha=0.7,
                rcount=15,  # 减少网格密度以提高性能
                ccount=15
            )

            # 添加坐标原点
            self.canvas.ax.scatter([0], [0], [0], color='black', s=50)

            # 如果选中显示力向量，则绘制箭头
            if self.show_arrow_check.isChecked():
                # 更新箭头（从原点指向力向量方向）
                scale = 2.0  # 箭头缩放因子
                self.force_arrow = self.canvas.ax.quiver(
                    0, 0, 0,
                    fx * scale,
                    fy * scale,
                    fz * scale,
                    color='red', linewidth=3,
                    arrow_length_ratio=0.15
                )
        else:
            # 仅更新必要元素，不完全重绘
            if self.surf is not None:
                self.surf.remove()
                
            # 计算到原点的距离
            distance = np.sqrt(self.X ** 2 + self.Y ** 2)
            
            # 衰减函数 - 使用高斯衰减
            sigma = 3.0
            decay = np.exp(-(distance ** 2) / (2 * sigma ** 2))
            
            # XY平面变形（基于X和Y分量）
            X_new = self.X + fx * decay * 0.5
            Y_new = self.Y + fy * decay * 0.5
            
            # Z方向变形（基于Z分量）
            Z_new = fz * decay * 1.0
            
            # 重新绘制表面
            self.surf = self.canvas.ax.plot_surface(
                X_new, Y_new, Z_new,
                cmap=cm.coolwarm,
                linewidth=0.3,
                antialiased=False,
                alpha=0.7,
                rcount=15,
                ccount=15
            )

            # 更新力向量箭头
            if self.show_arrow_check.isChecked() and self.force_arrow is not None:
                self.force_arrow.remove()
                scale = 2.0
                self.force_arrow = self.canvas.ax.quiver(
                    0, 0, 0,
                    fx * scale,
                    fy * scale,
                    fz * scale,
                    color='red', linewidth=3,
                    arrow_length_ratio=0.15
                )

        # 动态调整视角
        if self.auto_rotate_check.isChecked():
            force_magnitude = np.linalg.norm(avg_force)
            if force_magnitude > 0.1:
                current_elev, current_azim = self.canvas.ax.elev, self.canvas.ax.azim
                if hasattr(self.canvas.ax, 'elev') and hasattr(self.canvas.ax, 'azim'):
                    elev = current_elev + (30 + fz * 5 - current_elev) * 0.1
                    azim = current_azim + (45 + fx * 3 + fy * 3 - current_azim) * 0.1
                    self.canvas.ax.view_init(elev=elev, azim=azim)

        # 只绘制画布，不重新布局
        self.canvas.draw_idle()  # 使用draw_idle而不是draw以提高性能

    def reset_view(self):
        """重置视角"""
        self.canvas.ax.view_init(elev=30, azim=45)
        self.canvas.draw_idle()  # 使用draw_idle提高性能
        self.status_label.setText("视角已重置")

    def set_top_view(self):
        """设置俯视图"""
        self.canvas.ax.view_init(elev=90, azim=0)
        self.canvas.draw_idle()  # 使用draw_idle提高性能
        self.status_label.setText("已切换到俯视图")

    def set_side_view(self):
        """设置侧视图"""
        self.canvas.ax.view_init(elev=0, azim=0)
        self.canvas.draw_idle()  # 使用draw_idle提高性能
        self.status_label.setText("已切换到侧视图")

    def on_refresh_rate_changed(self, index):
        """刷新率改变时的处理函数"""
        refresh_rates = [100, 50, 33, 16]  # 对应的毫秒数
        if index < len(refresh_rates):
            new_interval = refresh_rates[index]
            self.update_timer.setInterval(new_interval)
            fps = 1000 // new_interval
            self.status_label.setText(f"刷新率已设置为 {fps} FPS")