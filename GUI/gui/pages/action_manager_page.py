#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QTime
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QTabWidget, QSplitter, QDialog, QDialogButtonBox,
    QFormLayout, QDoubleSpinBox, QMessageBox, QMenu, QInputDialog,
    QSpinBox, QTextEdit, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCheckBox, QComboBox,
    QFileDialog, QProgressBar, QSlider, QAbstractSpinBox
)

from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import csv
import os
import math

from core.action_manager import Action, ActionSequence
from core.arm_controller import ArmController


class ActionDialog(QDialog):
    """动作编辑对话框"""

    def __init__(self, parent=None, action=None, action_manager=None):
        """
        初始化动作对话框

        Args:
            parent: 父窗口
            action: 要编辑的动作对象，如果为None则创建新动作
            action_manager: 动作管理器实例
        """
        super().__init__(parent)
        self.action_manager = action_manager
        self.action = action
        self.is_edit_mode = action is not None

        self.setWindowTitle("编辑动作" if self.is_edit_mode else "新建动作")
        self.setMinimumWidth(400)

        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)

        # 表单布局
        form_layout = QFormLayout()

        # 动作名称
        self.name_input = QLineEdit()
        if self.is_edit_mode:
            self.name_input.setText(self.action.name)
            # 编辑模式下不允许修改名称，防止引用混乱
            self.name_input.setEnabled(False)
        form_layout.addRow("动作名称:", self.name_input)

        # 机械臂参数
        arm_group = QGroupBox("机械臂参数")
        arm_layout = QGridLayout(arm_group)

        # 关节角度参数标签和输入框
        joint_labels = ["关节1 (°)", "关节2 (°)", "关节3 (°)", "关节4 (°)", "关节5 (°)", "关节6 (°)"]
        self.arm_positions = []

        for i, label_text in enumerate(joint_labels):
            label = QLabel(label_text)
            spinbox = QDoubleSpinBox()

            # 设置关节角度范围
            spinbox.setRange(-180, 180)
            spinbox.setSuffix("°")

            spinbox.setDecimals(1)
            spinbox.setSingleStep(1.0)

            # 设置默认值
            if self.is_edit_mode:
                spinbox.setValue(self.action.arm_position[i])
            else:
                # 默认关节角度值（零位）
                default_values = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                spinbox.setValue(default_values[i])
                
            arm_layout.addWidget(label, i, 0)
            arm_layout.addWidget(spinbox, i, 1)
            self.arm_positions.append(spinbox)

        # 机械臂速度
        arm_speed_label = QLabel("速度:")
        self.arm_speed = QSpinBox()
        self.arm_speed.setRange(1, 100)
        if self.is_edit_mode:
            self.arm_speed.setValue(self.action.arm_velocity)
        else:
            self.arm_speed.setValue(20)  # 默认速度
        arm_layout.addWidget(arm_speed_label, 6, 0)
        arm_layout.addWidget(self.arm_speed, 6, 1)

        form_layout.addRow(arm_group)

        # 手爪参数
        hand_group = QGroupBox("手爪参数")
        hand_layout = QGridLayout(hand_group)

        self.hand_angles = []
        for i in range(6):
            label = QLabel(f"手爪 {i + 1}:")
            spinbox = QSpinBox()
            spinbox.setRange(0, 1000)
            spinbox.setSingleStep(10)
            if self.is_edit_mode:
                spinbox.setValue(self.action.hand_angles[i])
            else:
                spinbox.setValue(500)  # 默认值
            hand_layout.addWidget(label, i, 0)
            hand_layout.addWidget(spinbox, i, 1)
            self.hand_angles.append(spinbox)

        # 手爪速度
        hand_speed_label = QLabel("速度:")
        self.hand_speed = QSpinBox()
        self.hand_speed.setRange(1, 2000)
        self.hand_speed.setSingleStep(100)
        if self.is_edit_mode:
            self.hand_speed.setValue(self.action.hand_velocity)
        else:
            self.hand_speed.setValue(1000)  # 默认速度
        hand_layout.addWidget(hand_speed_label, 6, 0)
        hand_layout.addWidget(self.hand_speed, 6, 1)

        form_layout.addRow(hand_group)

        layout.addLayout(form_layout)

        # 按钮
        button_layout = QHBoxLayout()

        # 获取当前位置按钮
        self.current_pose_btn = QPushButton("获取当前位置")
        self.current_pose_btn.clicked.connect(self.get_current_pose)
        button_layout.addWidget(self.current_pose_btn)

        # 测试执行按钮
        self.test_btn = QPushButton("测试执行")
        self.test_btn.clicked.connect(self.test_action)
        button_layout.addWidget(self.test_btn)

        button_layout.addStretch()

        # 标准按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)

    def get_current_pose(self):
        """获取当前机械臂和手爪姿态"""
        QMessageBox.information(self, "提示", "请使用集成控制界面获取当前姿态")
        return
        
        # 原有功能已迁移到集成控制界面
        # if not self.action_manager or not self.action_manager.arm_controller:
        #     QMessageBox.warning(self, "警告", "机械臂控制器未连接")
        #     return

        # if not self.action_manager.arm_controller.is_connected:
        #     QMessageBox.warning(self, "警告", "请先连接机械臂")
        #     return

        # try:
        #     # 获取当前机械臂角度 - 修复：添加错误检查
        #     arm_angles = self.action_manager.arm_controller.getArmAngles()
        #     if not isinstance(arm_angles, (list, tuple)) or len(arm_angles) < 6:
        #         QMessageBox.warning(self, "错误", f"获取机械臂角度失败: {arm_angles}")
        #         return
            
        #     # 获取当前手爪角度 - 修复：添加错误检查
        #     hand_angles = self.action_manager.arm_controller.getHandAngles()
        #     if not isinstance(hand_angles, (list, tuple)) or len(hand_angles) < 6:
        #         QMessageBox.warning(self, "错误", f"获取手爪角度失败: {hand_angles}")
        #         return
            
        #     # 更新输入框
        #     for i, angle in enumerate(arm_angles):
        #         if i < len(self.arm_angles):
        #             self.arm_angles[i].setValue(angle)

        #     for i, angle in enumerate(hand_angles):
        #         if i < len(self.hand_angles):
        #             self.hand_angles[i].setValue(angle)
                    
        # except Exception as e:
        #     QMessageBox.critical(self, "错误", f"获取当前姿态失败: {str(e)}")
        #     print(f"获取当前姿态错误: {e}")

    def test_action(self):
        """测试当前设置的动作"""
        QMessageBox.information(self, "提示", "测试功能暂时不可用，请使用集成控制界面进行测试")
        return
        
        # 原有的测试代码已注释，因为需要使用新的集成控制器
        # if not self.action_manager or not self.action_manager.arm_controller:
        #     QMessageBox.warning(self, "错误", "机械臂控制器未初始化")
        #     return

        # if not self.action_manager.arm_controller.is_connected:
        #     QMessageBox.warning(self, "错误", "机械臂未连接")
        #     return

        # # 获取当前设置的参数
        # arm_angles = [spinbox.value() for spinbox in self.arm_angles]
        # hand_angles = [spinbox.value() for spinbox in self.hand_angles]
        # arm_velocity = self.arm_speed.value()
        # hand_velocity = self.hand_speed.value()

        # # 执行机械臂动作 - 修复：使用正确的方法名，传入关节角度
        # self.action_manager.arm_controller.set_arm_angles(arm_angles, arm_velocity)

        # # 执行手爪动作 - 修复：使用正确的方法名
        # self.action_manager.arm_controller.set_hand_angles(hand_angles)

        # QMessageBox.information(self, "成功", "动作测试执行成功")

    def get_action_data(self):
        """获取对话框中设置的动作数据"""
        name = self.name_input.text().strip()
        arm_positions = [spinbox.value() for spinbox in self.arm_positions]
        hand_angles = [spinbox.value() for spinbox in self.hand_angles]
        arm_velocity = self.arm_speed.value()
        hand_velocity = self.hand_speed.value()

        return {
            "name": name,
            "arm_positions": arm_positions,
            "hand_angles": hand_angles,
            "arm_velocity": arm_velocity,
            "hand_velocity": hand_velocity
        }


class SequenceDialog(QDialog):
    """序列编辑对话框"""

    def __init__(self, parent=None, sequence: ActionSequence = None, action_manager=None):
        super().__init__(parent)
        self.action_manager = action_manager
        self.sequence = sequence or ActionSequence("新序列")
        self.is_edit_mode = sequence is not None
        
        self.setWindowTitle("编辑序列" if self.is_edit_mode else "新建序列")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.sequence.name)
        if self.is_edit_mode:
            self.name_edit.setEnabled(False)  # 编辑模式下不允许修改名称
        self.description_edit = QTextEdit(self.sequence.description)
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setRange(1, 9999)
        self.repeat_spinbox.setValue(self.sequence.repeat_count)
        
        info_layout.addRow("名称:", self.name_edit)
        info_layout.addRow("描述:", self.description_edit)
        info_layout.addRow("执行次数:", self.repeat_spinbox)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 动作列表
        actions_group = QGroupBox("动作列表")
        actions_layout = QVBoxLayout()
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧可用动作列表
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_label = QLabel("可用动作:")
        left_layout.addWidget(left_label)
        
        self.actions_list = QListWidget()
        self.actions_list.setDragEnabled(True)
        self.actions_list.setAcceptDrops(False)
        self.actions_list.setDropIndicatorShown(True)
        self.actions_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.actions_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.refresh_actions_list()
        left_layout.addWidget(self.actions_list)
        
        splitter.addWidget(left_frame)
        
        # 右侧序列动作列表
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_label = QLabel("序列动作:")
        right_layout.addWidget(right_label)
        
        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(3)
        self.sequence_table.setHorizontalHeaderLabels(["序号", "动作名称", "延迟(秒)"])
        self.sequence_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sequence_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.sequence_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sequence_table.verticalHeader().setVisible(False)
        
        if self.is_edit_mode:
            self.refresh_sequence_table()
            
        right_layout.addWidget(self.sequence_table)
        
        # 序列操作按钮
        seq_button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_action_to_sequence)
        seq_button_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("删除")
        self.remove_btn.clicked.connect(self.remove_action_from_sequence)
        seq_button_layout.addWidget(self.remove_btn)
        
        self.move_up_btn = QPushButton("上移")
        self.move_up_btn.clicked.connect(self.move_action_up)
        seq_button_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("下移")
        self.move_down_btn.clicked.connect(self.move_action_down)
        seq_button_layout.addWidget(self.move_down_btn)
        
        right_layout.addLayout(seq_button_layout)
        
        splitter.addWidget(right_frame)
        
        # 设置分割器比例
        splitter.setSizes([200, 400])
        actions_layout.addWidget(splitter)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

    def refresh_actions_list(self):
        """刷新可用动作列表"""
        self.actions_list.clear()
        
        if not self.action_manager:
            return
            
        try:
            for action_name in self.action_manager.get_all_actions():
                item = QListWidgetItem(action_name)
                item.setData(Qt.ItemDataRole.UserRole, action_name)
                self.actions_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新动作列表失败: {str(e)}")

    def refresh_sequence_table(self):
        """刷新序列动作表格"""
        self.sequence_table.setRowCount(0)
        
        if not self.is_edit_mode or not self.sequence:
            return
            
        try:
            for i, action_name in enumerate(self.sequence.actions):
                row = self.sequence_table.rowCount()
                self.sequence_table.insertRow(row)
                
                # 序号
                index_item = QTableWidgetItem(str(i + 1))
                index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.sequence_table.setItem(row, 0, index_item)
                
                # 动作名称
                name_item = QTableWidgetItem(action_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.sequence_table.setItem(row, 1, name_item)
                
                # 延迟时间
                delay_spinbox = QDoubleSpinBox()
                delay_spinbox.setRange(0, 10)
                delay_spinbox.setSingleStep(0.1)
                delay_spinbox.setDecimals(1)
                delay_spinbox.setValue(self.sequence.delays[i])
                delay_spinbox.valueChanged.connect(self.update_delay)
                self.sequence_table.setCellWidget(row, 2, delay_spinbox)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新序列表格失败: {str(e)}")

    def add_action_to_sequence(self):
        """添加选中的动作到序列"""
        try:
            selected_items = self.actions_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选择一个动作")
                return
                
            action_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
            
            # 添加到表格
            row = self.sequence_table.rowCount()
            self.sequence_table.insertRow(row)
            
            # 序号
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(row, 0, index_item)
            
            # 动作名称
            name_item = QTableWidgetItem(action_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sequence_table.setItem(row, 1, name_item)
            
            # 延迟时间
            delay_spinbox = QDoubleSpinBox()
            delay_spinbox.setRange(0, 10)
            delay_spinbox.setSingleStep(0.1)
            delay_spinbox.setDecimals(1)
            delay_spinbox.setValue(1.0)  # 默认延迟1秒
            delay_spinbox.valueChanged.connect(self.update_delay)
            self.sequence_table.setCellWidget(row, 2, delay_spinbox)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加动作失败: {str(e)}")

    def remove_action_from_sequence(self):
        """从序列中删除选中的动作"""
        try:
            selected_rows = self.sequence_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "警告", "请先选择要删除的动作")
                return
                
            # 从后往前删除，避免索引变化
            rows = sorted([index.row() for index in selected_rows], reverse=True)
            for row in rows:
                self.sequence_table.removeRow(row)
                
            # 更新序号
            self.update_sequence_numbers()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除动作失败: {str(e)}")

    def move_action_up(self):
        """将选中的动作向上移动"""
        try:
            selected_rows = self.sequence_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "警告", "请先选择要移动的动作")
                return
                
            # 只处理单选情况
            row = selected_rows[0].row()
            if row <= 0:
                return  # 已经是第一行
                
            # 交换行
            self.swap_rows(row, row - 1)
            
            # 更新选中行
            self.sequence_table.selectRow(row - 1)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"移动动作失败: {str(e)}")

    def move_action_down(self):
        """将选中的动作向下移动"""
        try:
            selected_rows = self.sequence_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "警告", "请先选择要移动的动作")
                return
                
            # 只处理单选情况
            row = selected_rows[0].row()
            if row >= self.sequence_table.rowCount() - 1:
                return  # 已经是最后一行
                
            # 交换行
            self.swap_rows(row, row + 1)
            
            # 更新选中行
            self.sequence_table.selectRow(row + 1)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"移动动作失败: {str(e)}")

    def swap_rows(self, row1, row2):
        """交换表格中的两行"""
        try:
            # 保存第一行数据
            action_name1 = self.sequence_table.item(row1, 1).text()
            delay_widget1 = self.sequence_table.cellWidget(row1, 2)
            delay1 = delay_widget1.value()
            
            # 保存第二行数据
            action_name2 = self.sequence_table.item(row2, 1).text()
            delay_widget2 = self.sequence_table.cellWidget(row2, 2)
            delay2 = delay_widget2.value()
            
            # 交换数据
            self.sequence_table.item(row1, 1).setText(action_name2)
            delay_widget1.setValue(delay2)
            
            self.sequence_table.item(row2, 1).setText(action_name1)
            delay_widget2.setValue(delay1)
            
            # 更新序号
            self.update_sequence_numbers()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"交换行失败: {str(e)}")

    def update_sequence_numbers(self):
        """更新序列中的序号"""
        try:
            for i in range(self.sequence_table.rowCount()):
                index_item = self.sequence_table.item(i, 0)
                if index_item:
                    index_item.setText(str(i + 1))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新序号失败: {str(e)}")

    def update_delay(self):
        """更新延迟时间"""
        # 这个函数会在用户修改延迟时自动调用
        pass

    def get_sequence_data(self):
        """获取对话框中设置的序列数据"""
        try:
            name = self.name_edit.text().strip()
            description = self.description_edit.toPlainText().strip()
            
            actions = []
            delays = []
            
            for i in range(self.sequence_table.rowCount()):
                action_name = self.sequence_table.item(i, 1).text()
                delay_widget = self.sequence_table.cellWidget(i, 2)
                delay = delay_widget.value()
                
                actions.append(action_name)
                delays.append(delay)
                
            return {
                "name": name,
                "description": description,
                "actions": actions,
                "delays": delays,
                "repeat_count": self.repeat_spinbox.value()
            }
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取序列数据失败: {str(e)}")
            return None

    def accept(self):
        """保存序列并关闭对话框"""
        try:
            sequence_data = self.get_sequence_data()
            if not sequence_data:
                return
                
            # 更新序列对象
            self.sequence.name = sequence_data["name"]
            self.sequence.description = sequence_data["description"]
            self.sequence.repeat_count = sequence_data["repeat_count"]
            
            # 清空原序列动作
            self.sequence.actions.clear()
            self.sequence.delays.clear()
            
            # 添加新动作
            for action_name, delay in zip(sequence_data["actions"], sequence_data["delays"]):
                self.sequence.add_action(action_name, delay)
                
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存序列失败: {str(e)}")


class ActionManagerPage(QWidget):
    """动作管理器页面"""

    def __init__(self, parent=None, action_manager=None):
        """
        初始化动作管理器页面

        Args:
            parent: 父窗口
            action_manager: 动作管理器实例
        """
        super().__init__(parent)

        self.parent = parent
        self.action_manager = action_manager
        
        # 获取传感器数据管理器引用
        self.sensor_data_manager = None
        if hasattr(parent, 'sensor_data_manager'):
            self.sensor_data_manager = parent.sensor_data_manager
        
        # 添加集成控制器：优先复用父窗口（main_window）已有的 arm_controller，避免创建多个实例
        if hasattr(parent, 'arm_controller') and parent.arm_controller is not None:
            self.integrated_controller = parent.arm_controller
        else:
            self.integrated_controller = ArmController()

        # 让动作管理器使用集成控制器（如果提供了动作管理器的话）
        if self.action_manager:
            self.action_manager.set_arm_controller(self.integrated_controller)

        # 设置UI
        self.setup_ui()

        # 连接信号
        self.connect_signals()

    def setup_ui(self):
        """设置UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 标题
        self.title_label = QLabel("动作管理器")
        self.title_label.setObjectName("pageTitle")
        main_layout.addWidget(self.title_label)

        # 选项卡控件
        self.tab_widget = QTabWidget()

        # 机械手连接选项卡
        self.hand_connection_tab = QWidget()
        self.setup_hand_connection_tab()
        self.tab_widget.addTab(self.hand_connection_tab, "集成控制")

        # 动作管理选项卡
        self.actions_tab = QWidget()
        self.setup_actions_tab()
        self.tab_widget.addTab(self.actions_tab, "动作管理")

        # 序列管理选项卡
        self.sequences_tab = QWidget()
        self.setup_sequences_tab()
        self.tab_widget.addTab(self.sequences_tab, "序列管理")

        # 抓取控制选项卡
        self.grasp_control_tab = QWidget()
        self.setup_grasp_control_tab()
        self.tab_widget.addTab(self.grasp_control_tab, "抓取控制")

        main_layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_label = QLabel("就绪")


    def setup_actions_tab(self):
        """设置动作管理选项卡"""
        layout = QVBoxLayout(self.actions_tab)

        # 工具栏
        toolbar = QHBoxLayout()

        self.new_action_btn = QPushButton("新建动作")
        self.new_action_btn.clicked.connect(self.create_action)
        toolbar.addWidget(self.new_action_btn)

        self.save_current_btn = QPushButton("保存当前位置")
        self.save_current_btn.clicked.connect(self.save_current_position)
        toolbar.addWidget(self.save_current_btn)

        self.execute_action_btn = QPushButton("执行动作")
        self.execute_action_btn.clicked.connect(self.execute_selected_action)
        toolbar.addWidget(self.execute_action_btn)

        self.edit_action_btn = QPushButton("编辑动作")
        self.edit_action_btn.clicked.connect(self.edit_selected_action)
        toolbar.addWidget(self.edit_action_btn)

        self.delete_action_btn = QPushButton("删除动作")
        self.delete_action_btn.clicked.connect(self.delete_selected_action)
        toolbar.addWidget(self.delete_action_btn)

        self.refresh_actions_btn = QPushButton("刷新")
        self.refresh_actions_btn.clicked.connect(self.refresh_actions_list)
        toolbar.addWidget(self.refresh_actions_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 动作列表
        self.actions_list = QTableWidget()
        self.actions_list.setColumnCount(4)
        self.actions_list.setHorizontalHeaderLabels(["动作名称", "创建时间", "最后修改", "参数"])
        self.actions_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.actions_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.actions_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.actions_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.actions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.actions_list.customContextMenuRequested.connect(self.show_actions_context_menu)

        layout.addWidget(self.actions_list)
        # 完全隐藏垂直表头（行号）
        self.actions_list.verticalHeader().setVisible(False)

        # 初始加载动作列表
        self.refresh_actions_list()

    def setup_sequences_tab(self):
        """设置序列管理选项卡"""
        layout = QVBoxLayout(self.sequences_tab)

        # 工具栏
        toolbar = QHBoxLayout()

        self.new_sequence_btn = QPushButton("新建序列")
        self.new_sequence_btn.clicked.connect(self.create_sequence)
        toolbar.addWidget(self.new_sequence_btn)

        self.execute_sequence_btn = QPushButton("执行序列")
        self.execute_sequence_btn.clicked.connect(self.execute_selected_sequence)
        toolbar.addWidget(self.execute_sequence_btn)

        self.edit_sequence_btn = QPushButton("编辑序列")
        self.edit_sequence_btn.clicked.connect(self.edit_selected_sequence)
        toolbar.addWidget(self.edit_sequence_btn)

        self.delete_sequence_btn = QPushButton("删除序列")
        self.delete_sequence_btn.clicked.connect(self.delete_selected_sequence)
        toolbar.addWidget(self.delete_sequence_btn)

        self.refresh_sequences_btn = QPushButton("刷新")
        self.refresh_sequences_btn.clicked.connect(self.refresh_sequences_list)
        toolbar.addWidget(self.refresh_sequences_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 序列列表
        self.sequences_list = QTableWidget()
        self.sequences_list.setColumnCount(4)
        self.sequences_list.setHorizontalHeaderLabels(["序列名称", "创建时间", "最后修改", "动作数量"])
        self.sequences_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sequences_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sequences_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sequences_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sequences_list.customContextMenuRequested.connect(self.show_sequences_context_menu)

        layout.addWidget(self.sequences_list)
        self.sequences_list.verticalHeader().setVisible(False)

        # 序列详情
        details_group = QGroupBox("序列详情")
        details_layout = QVBoxLayout(details_group)

        # 序列描述
        self.sequence_description = QLabel("选择一个序列查看详情")
        details_layout.addWidget(self.sequence_description)

        # 序列动作列表
        self.sequence_actions_table = QTableWidget()
        self.sequence_actions_table.setColumnCount(3)
        self.sequence_actions_table.setHorizontalHeaderLabels(["序号", "动作名称", "延迟(秒)"])
        self.sequence_actions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sequence_actions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sequence_actions_table.verticalHeader().setVisible(False)
        details_layout.addWidget(self.sequence_actions_table)

        layout.addWidget(details_group)
        # 在创建表格后添加这行代码

        # 执行状态
        status_group = QGroupBox("执行状态")
        status_layout = QVBoxLayout(status_group)

        self.execution_progress = QProgressBar()
        self.execution_progress.setRange(0, 100)
        self.execution_progress.setValue(0)
        status_layout.addWidget(self.execution_progress)

        self.execution_status = QLabel("未执行")
        status_layout.addWidget(self.execution_status)

        execution_controls = QHBoxLayout()

        self.start_execution_btn = QPushButton("执行选中序列")
        self.start_execution_btn.clicked.connect(self.execute_selected_sequence)
        execution_controls.addWidget(self.start_execution_btn)

        self.stop_execution_btn = QPushButton("停止执行")
        self.stop_execution_btn.clicked.connect(self.stop_execution)
        self.stop_execution_btn.setEnabled(False)
        execution_controls.addWidget(self.stop_execution_btn)

        status_layout.addLayout(execution_controls)

        layout.addWidget(status_group)

        # 初始加载序列列表
        self.refresh_sequences_list()

    def setup_hand_connection_tab(self):
        """设置集成控制选项卡（原机械手连接选项卡）"""
        layout = QVBoxLayout(self.hand_connection_tab)

        # 1. 设备连接区域
        connection_group = QGroupBox("设备连接")
        connection_layout = QGridLayout(connection_group)
        
        # 瑞尔曼连接
        connection_layout.addWidget(QLabel("瑞尔曼IP:"), 0, 0)
        self.arm_ip_input = QComboBox()
        self.arm_ip_input.setEditable(True)
        self.arm_ip_input.addItems(["192.168.1.18", "192.168.1.100", "127.0.0.1"])
        connection_layout.addWidget(self.arm_ip_input, 0, 1)
        
        self.arm_connect_btn = QPushButton("连接瑞尔曼")
        self.arm_connect_btn.clicked.connect(self.connect_arm)
        connection_layout.addWidget(self.arm_connect_btn, 0, 2)
        
        # Inspire连接
        connection_layout.addWidget(QLabel("Inspire串口:"), 1, 0)
        self.hand_port_input = QComboBox()
        self.hand_port_input.setEditable(True)
        # 初始化时扫描可用串口
        self.refresh_serial_ports()
        connection_layout.addWidget(self.hand_port_input, 1, 1)
        
        self.hand_connect_btn = QPushButton("连接Inspire")
        self.hand_connect_btn.clicked.connect(self.connect_hand)
        connection_layout.addWidget(self.hand_connect_btn, 1, 2)
        
        # 刷新串口按钮
        self.refresh_ports_btn = QPushButton("刷新串口")
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        connection_layout.addWidget(self.refresh_ports_btn, 1, 3)
        
        # 一键连接所有设备
        self.connect_all_btn = QPushButton("连接所有设备")
        self.connect_all_btn.clicked.connect(self.connect_all)
        connection_layout.addWidget(self.connect_all_btn, 2, 0, 1, 4)
        
        # 断开连接
        self.disconnect_btn = QPushButton("断开所有连接")
        self.disconnect_btn.clicked.connect(self.disconnect_all)
        connection_layout.addWidget(self.disconnect_btn, 3, 0, 1, 4)
        
        layout.addWidget(connection_group)

        # 2. 设备控制区域
        control_group = QGroupBox("设备控制")
        control_layout = QVBoxLayout(control_group)  # 改为垂直布局以更好地适应滑块设计

        # 创建一个水平容器来放置两个控制组
        controls_container = QWidget()
        controls_container_layout = QHBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(0, 0, 0, 0)

        # 保存为实例变量供其他方法使用
        self._controls_container_layout = controls_container_layout
        self._control_layout = control_layout
        self._hand_connection_layout = layout
        
        # 瑞尔曼控制
        self.arm_group = QGroupBox("瑞尔曼机械臂")
        arm_layout = QVBoxLayout(self.arm_group)

        # 控制模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("控制模式:"))
        self.arm_control_mode = QComboBox()
        self.arm_control_mode.addItems([
            "笛卡尔直线",  # Cartesian Linear
            "关节角度"     # Joint Angles
        ])
        self.arm_control_mode.currentTextChanged.connect(self.on_arm_control_mode_changed)
        mode_layout.addWidget(self.arm_control_mode)
        mode_layout.addStretch()
        arm_layout.addLayout(mode_layout)
        
        # 创建笛卡尔控件容器
        self.cartesian_controls_widget = QWidget()
        cartesian_layout = QVBoxLayout(self.cartesian_controls_widget)
        cartesian_layout.setContentsMargins(0, 0, 0, 0)
        cartesian_layout.setSpacing(5)

        # 创建机械臂参数配置
        arm_params = [
            {"name": "X", "color": "#ff7f00", "min": -1000, "max": 1000, "default": 400.0, "suffix": " mm"},
            {"name": "Y", "color": "#ff5555", "min": -1000, "max": 1000, "default": 0.0, "suffix": " mm"},
            {"name": "Z", "color": "#50fa7b", "min": -1000, "max": 1000, "default": 300.0, "suffix": " mm"},
            {"name": "Roll", "color": "#8be9fd", "min": -180, "max": 180, "default": 180.0, "suffix": "°"},
            {"name": "Pitch", "color": "#bd93f9", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "Yaw", "color": "#ffb86c", "min": -180, "max": 180, "default": 0.0, "suffix": "°"}
        ]

        # 存储控件引用
        self.arm_sliders = []
        self.arm_spinboxes = []

        for i, param in enumerate(arm_params):
            # 创建每个参数的容器
            param_widget = QWidget()
            param_layout = QHBoxLayout(param_widget)
            param_layout.setContentsMargins(5, 2, 5, 2)
            
            # 创建带颜色的滑块
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(param["min"] * 10), int(param["max"] * 10))  # 乘以10支持小数
            slider.setValue(int(param["default"] * 10))
            slider.setMinimumWidth(200)
            
            # 设置滑块样式
            slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    border: 1px solid #999999;
                    height: 8px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #B0B0B0, stop:1 {param["color"]});
                    margin: 2px 0;
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {param["color"]};
                    border: 2px solid #ffffff;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {param["color"]};
                    border: 2px solid {param["color"]};
                }}
            """)
            
            # 创建数值输入框
            spinbox = QDoubleSpinBox()
            spinbox.setRange(param["min"], param["max"])
            spinbox.setValue(param["default"])
            spinbox.setDecimals(1)
            spinbox.setSingleStep(1.0)
            spinbox.setSuffix(param["suffix"])
            spinbox.setKeyboardTracking(False)
            spinbox.setMinimumWidth(80)
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 移除上下箭头

            # 连接信号
            slider.valueChanged.connect(lambda v, sb=spinbox: sb.setValue(v / 10.0))
            spinbox.valueChanged.connect(lambda v, sl=slider: sl.setValue(int(v * 10)))
            
            # 添加到布局
            param_layout.addWidget(QLabel(f"{param['name']}:"), 0)
            param_layout.addWidget(slider, 1)
            param_layout.addWidget(spinbox, 0)

            cartesian_layout.addWidget(param_widget)

            # 保存引用
            self.arm_sliders.append(slider)
            self.arm_spinboxes.append(spinbox)
        
        # 为了保持兼容性，创建属性别名
        self.arm_x = self.arm_spinboxes[0]
        self.arm_y = self.arm_spinboxes[1] 
        self.arm_z = self.arm_spinboxes[2]
        self.arm_roll = self.arm_spinboxes[3]
        self.arm_pitch = self.arm_spinboxes[4]
        self.arm_yaw = self.arm_spinboxes[5]
        
        # 机械臂控制按钮
        arm_buttons_layout = QHBoxLayout()

        self.move_arm_btn = QPushButton("移动机械臂")
        self.move_arm_btn.clicked.connect(self.move_arm)
        arm_buttons_layout.addWidget(self.move_arm_btn)

        # 获取当前姿态按钮
        self.get_current_pose_btn = QPushButton("获取当前姿态")
        self.get_current_pose_btn.setStyleSheet("""
            QPushButton {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5af78e;
            }
        """)
        self.get_current_pose_btn.clicked.connect(self.get_current_pose)
        arm_buttons_layout.addWidget(self.get_current_pose_btn)

        cartesian_layout.addLayout(arm_buttons_layout)

        # 将笛卡尔控件容器添加到主布局
        arm_layout.addWidget(self.cartesian_controls_widget)

        self._controls_container_layout.addWidget(self.arm_group)

        # 初始化控制模式 - 预先创建所有控件
        self._create_all_control_widgets()
        self.on_arm_control_mode_changed(self.arm_control_mode.currentText())

        # 添加控制容器到主控制组
        control_layout.addWidget(controls_container)

        layout.addWidget(control_group)

        # 设置状态显示区域
        self.setup_status_group(layout)

    def _create_all_control_widgets(self):
        """预先创建所有控制模式的控件"""
        arm_layout = self.arm_group.layout()

        # 创建关节角度控制控件
        self.joint_controls_widget = QWidget()
        joint_layout = QVBoxLayout(self.joint_controls_widget)

        # 关节角度参数 (6自由度机械臂)
        joint_params = [
            {"name": "关节1", "color": "#ff5555", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "关节2", "color": "#50fa7b", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "关节3", "color": "#8be9fd", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "关节4", "color": "#bd93f9", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "关节5", "color": "#ffb86c", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "关节6", "color": "#ff79c6", "min": -180, "max": 180, "default": 0.0, "suffix": "°"}
        ]

        self.joint_spinboxes = []
        self.joint_sliders = []

        for param in joint_params:
            # 创建每个参数的容器
            param_widget = QWidget()
            param_layout = QHBoxLayout(param_widget)
            param_layout.setContentsMargins(5, 2, 5, 2)

            # 创建带颜色的滑块
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(param["min"] * 10), int(param["max"] * 10))  # 乘以10支持小数
            slider.setValue(int(param["default"] * 10))
            slider.setMinimumWidth(200)

            # 设置滑块样式
            slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    border: 1px solid #999999;
                    height: 8px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #B0B0B0, stop:1 {param["color"]});
                    margin: 2px 0;
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {param["color"]};
                    border: 2px solid #ffffff;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {param["color"]};
                    border: 2px solid {param["color"]};
                }}
            """)

            # 创建数值输入框
            spinbox = QDoubleSpinBox()
            spinbox.setRange(param["min"], param["max"])
            spinbox.setValue(param["default"])
            spinbox.setDecimals(1)
            spinbox.setSingleStep(1.0)
            spinbox.setSuffix(param["suffix"])
            spinbox.setKeyboardTracking(False)
            spinbox.setMinimumWidth(80)
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 移除上下箭头

            # 连接信号
            slider.valueChanged.connect(lambda v, sb=spinbox: sb.setValue(v / 10.0))
            spinbox.valueChanged.connect(lambda v, sl=slider: sl.setValue(int(v * 10)))

            # 添加到布局
            param_layout.addWidget(QLabel(f"{param['name']}:"), 0)
            param_layout.addWidget(slider, 1)
            param_layout.addWidget(spinbox, 0)

            joint_layout.addWidget(param_widget)

            # 保存引用
            self.joint_sliders.append(slider)
            self.joint_spinboxes.append(spinbox)

        # 控制按钮
        joint_buttons_layout = QHBoxLayout()
        self.get_current_joints_btn = QPushButton("获取当前关节角度")
        self.get_current_joints_btn.clicked.connect(self.get_current_joint_angles)
        joint_buttons_layout.addWidget(self.get_current_joints_btn)

        self.move_joints_btn = QPushButton("移动到关节角度")
        self.move_joints_btn.clicked.connect(self.move_to_joint_angles)
        joint_buttons_layout.addWidget(self.move_joints_btn)

        joint_layout.addLayout(joint_buttons_layout)
        self.joint_controls_widget.setVisible(False)
        arm_layout.addWidget(self.joint_controls_widget)

        # 创建笛卡尔偏移控制控件
        self.offset_controls_widget = QWidget()
        offset_layout = QVBoxLayout(self.offset_controls_widget)

        # 偏移参数
        offset_params = [
            {"name": "ΔX", "min": -500, "max": 500, "default": 0.0, "suffix": " mm"},
            {"name": "ΔY", "min": -500, "max": 500, "default": 0.0, "suffix": " mm"},
            {"name": "ΔZ", "min": -500, "max": 500, "default": 0.0, "suffix": " mm"},
            {"name": "ΔRoll", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "ΔPitch", "min": -180, "max": 180, "default": 0.0, "suffix": "°"},
            {"name": "ΔYaw", "min": -180, "max": 180, "default": 0.0, "suffix": "°"}
        ]

        self.offset_spinboxes = []
        for param in offset_params:
            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(f"{param['name']}:"))

            spinbox = QDoubleSpinBox()
            spinbox.setRange(param["min"], param["max"])
            spinbox.setValue(param["default"])
            spinbox.setDecimals(1)
            spinbox.setSingleStep(1.0)
            spinbox.setSuffix(param["suffix"])
            spinbox.setKeyboardTracking(False)
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 移除上下箭头
            param_layout.addWidget(spinbox)
            self.offset_spinboxes.append(spinbox)

            offset_layout.addLayout(param_layout)

        # 坐标系选择
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("坐标系:"))
        self.offset_frame_type = QComboBox()
        self.offset_frame_type.addItems(["工作坐标系", "工具坐标系"])
        frame_layout.addWidget(self.offset_frame_type)
        frame_layout.addStretch()
        offset_layout.addLayout(frame_layout)

        # 控制按钮
        offset_buttons_layout = QHBoxLayout()
        self.move_offset_btn = QPushButton("执行偏移运动")
        self.move_offset_btn.clicked.connect(self.move_cartesian_offset)
        offset_buttons_layout.addWidget(self.move_offset_btn)

        offset_layout.addLayout(offset_buttons_layout)
        self.offset_controls_widget.setVisible(False)
        arm_layout.addWidget(self.offset_controls_widget)

        # 创建速度控制控件
        self.velocity_controls_widget = QWidget()
        velocity_layout = QVBoxLayout(self.velocity_controls_widget)

        # 速度参数
        velocity_params = [
            {"name": "线速度X", "min": -1.0, "max": 1.0, "default": 0.0, "suffix": " m/s"},
            {"name": "线速度Y", "min": -1.0, "max": 1.0, "default": 0.0, "suffix": " m/s"},
            {"name": "线速度Z", "min": -1.0, "max": 1.0, "default": 0.0, "suffix": " m/s"},
            {"name": "角速度Roll", "min": -3.14, "max": 3.14, "default": 0.0, "suffix": " rad/s"},
            {"name": "角速度Pitch", "min": -3.14, "max": 3.14, "default": 0.0, "suffix": " rad/s"},
            {"name": "角速度Yaw", "min": -3.14, "max": 3.14, "default": 0.0, "suffix": " rad/s"}
        ]

        self.velocity_spinboxes = []
        for param in velocity_params:
            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(f"{param['name']}:"))

            spinbox = QDoubleSpinBox()
            spinbox.setRange(param["min"], param["max"])
            spinbox.setValue(param["default"])
            spinbox.setDecimals(3)
            spinbox.setSingleStep(0.01)
            spinbox.setSuffix(param["suffix"])
            spinbox.setKeyboardTracking(False)
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 移除上下箭头
            param_layout.addWidget(spinbox)
            self.velocity_spinboxes.append(spinbox)

            velocity_layout.addLayout(param_layout)

        # 控制按钮
        velocity_buttons_layout = QHBoxLayout()
        self.start_velocity_btn = QPushButton("开始速度控制")
        self.start_velocity_btn.clicked.connect(self.start_velocity_control)
        velocity_buttons_layout.addWidget(self.start_velocity_btn)

        self.stop_velocity_btn = QPushButton("停止速度控制")
        self.stop_velocity_btn.clicked.connect(self.stop_velocity_control)
        self.stop_velocity_btn.setEnabled(False)
        velocity_buttons_layout.addWidget(self.stop_velocity_btn)

        velocity_layout.addLayout(velocity_buttons_layout)
        self.velocity_controls_widget.setVisible(False)
        arm_layout.addWidget(self.velocity_controls_widget)

        # Inspire控制
        hand_group = QGroupBox("Inspire机械手")
        hand_layout = QVBoxLayout(hand_group)
        
        # 创建机械手参数配置
        finger_params = [
            {"name": "小指", "color": "#ff5555", "min": -1, "max": 1000, "default": 500},
            {"name": "无名指", "color": "#50fa7b", "min": -1, "max": 1000, "default": 500},
            {"name": "中指", "color": "#8be9fd", "min": -1, "max": 1000, "default": 500},
            {"name": "食指", "color": "#bd93f9", "min": -1, "max": 1000, "default": 500},
            {"name": "拇指", "color": "#ffb86c", "min": -1, "max": 1000, "default": 500},
            {"name": "拇指翻转", "color": "#f1fa8c", "min": -1, "max": 1000, "default": 500}
        ]
        
        # 存储控件引用
        self.hand_sliders = []
        self.hand_spinboxes = []
        self.hand_angles = []  # 保持兼容性
        
        for i, param in enumerate(finger_params):
            # 创建每个手指的容器
            finger_widget = QWidget()
            finger_layout = QHBoxLayout(finger_widget)
            finger_layout.setContentsMargins(5, 2, 5, 2)
            
            # 创建带颜色的滑块
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(param["min"], param["max"])
            slider.setValue(param["default"])
            slider.setMinimumWidth(200)
            
            # 设置滑块样式
            slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    border: 1px solid #999999;
                    height: 8px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #B0B0B0, stop:1 {param["color"]});
                    margin: 2px 0;
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {param["color"]};
                    border: 2px solid #ffffff;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }}
                QSlider::handle:horizontal:hover {{
                    background: {param["color"]};
                    border: 2px solid {param["color"]};
                }}
            """)
            
            # 创建数值输入框
            spinbox = QSpinBox()
            spinbox.setRange(param["min"], param["max"])
            spinbox.setValue(param["default"])
            spinbox.setMinimumWidth(80)
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # 移除上下箭头

            # 连接信号
            slider.valueChanged.connect(lambda v, sb=spinbox: sb.setValue(v))
            spinbox.valueChanged.connect(lambda v, sl=slider: sl.setValue(v))
            
            # 添加到布局
            finger_layout.addWidget(QLabel(f"{param['name']}:"), 0)
            finger_layout.addWidget(slider, 1)
            finger_layout.addWidget(spinbox, 0)
            
            hand_layout.addWidget(finger_widget)
            
            # 保存引用
            self.hand_sliders.append(slider)
            self.hand_spinboxes.append(spinbox)
            self.hand_angles.append(spinbox)  # 保持兼容性
        
        # 机械手控制按钮
        hand_buttons_layout = QVBoxLayout()
        
        # 第一行按钮
        hand_buttons_row1 = QHBoxLayout()
        
        self.set_hand_btn = QPushButton("设置手指角度")
        self.set_hand_btn.clicked.connect(self.set_hand_angles)
        hand_buttons_row1.addWidget(self.set_hand_btn)
        
        self.open_hand_btn = QPushButton("张开手爪")
        self.open_hand_btn.clicked.connect(self.open_hand)
        hand_buttons_row1.addWidget(self.open_hand_btn)
        
        self.close_hand_btn = QPushButton("闭合手爪")
        self.close_hand_btn.clicked.connect(self.close_hand)
        hand_buttons_row1.addWidget(self.close_hand_btn)
        
        hand_buttons_layout.addLayout(hand_buttons_row1)
        
        # 第二行按钮
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
        hand_buttons_layout.addWidget(self.save_action_btn)
        
        hand_layout.addLayout(hand_buttons_layout)

        self._controls_container_layout.addWidget(hand_group)

    def setup_status_group(self, layout):
        """设置状态显示区域"""
        # 3. 设备状态区域
        status_group = QGroupBox("设备状态")
        status_layout = QVBoxLayout(status_group)
        
        # 连接状态
        status_row_layout = QHBoxLayout()
        self.arm_status_label = QLabel("瑞尔曼: 未连接")
        self.hand_status_label = QLabel("Inspire: 未连接")
        status_row_layout.addWidget(self.arm_status_label)
        status_row_layout.addWidget(self.hand_status_label)
        status_layout.addLayout(status_row_layout)
        
        # 实时位置显示
        self.position_label = QLabel("机械臂位置: [0, 0, 0, 0, 0, 0]")
        self.angles_label = QLabel("手指角度: [0, 0, 0, 0, 0, 0]")
        status_layout.addWidget(self.position_label)
        status_layout.addWidget(self.angles_label)
        
        # 日志显示
        status_layout.addWidget(QLabel("操作日志:"))
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        status_layout.addWidget(self.log_text)
        
        layout.addWidget(status_group)

    def connect_signals(self):
        """连接信号"""
        if self.action_manager:
            # 动作相关信号
            self.action_manager.action_added.connect(self.on_action_added)
            self.action_manager.action_removed.connect(self.on_action_removed)
            self.action_manager.action_updated.connect(self.on_action_updated)

            # 序列相关信号
            self.action_manager.sequence_added.connect(self.on_sequence_added)
            self.action_manager.sequence_removed.connect(self.on_sequence_removed)
            self.action_manager.sequence_updated.connect(self.on_sequence_updated)

            # 执行相关信号
            self.action_manager.execution_started.connect(self.on_execution_started)
            self.action_manager.execution_completed.connect(self.on_execution_completed)
            self.action_manager.execution_progress.connect(self.on_execution_progress)
            self.action_manager.execution_error.connect(self.on_execution_error)

        # 序列列表选择变化
        self.sequences_list.itemSelectionChanged.connect(self.on_sequence_selection_changed)

    def on_arm_control_mode_changed(self, mode: str):
        """处理机械臂控制模式变化"""
        # 确保arm_group已经初始化
        if not hasattr(self, 'arm_group'):
            return

        # 根据选择的模式调整UI显示
        if mode == "关节角度":
            # 显示关节角度控制界面
            self._show_joint_angle_controls()
        elif mode == "笛卡尔直线":
            # 显示笛卡尔直线控制界面
            self._show_cartesian_linear_controls()

        # 强制更新布局
        self.arm_group.update()

    def _show_joint_angle_controls(self):
        """显示关节角度控制界面"""
        # 显示关节角度控件，隐藏笛卡尔控件
        if hasattr(self, 'joint_controls_widget'):
            self.joint_controls_widget.show()
        if hasattr(self, 'cartesian_controls_widget'):
            self.cartesian_controls_widget.hide()
        if hasattr(self, 'offset_controls_widget'):
            self.offset_controls_widget.hide()
        if hasattr(self, 'velocity_controls_widget'):
            self.velocity_controls_widget.hide()

    def _show_cartesian_linear_controls(self):
        """显示笛卡尔直线控制界面"""
        # 显示笛卡尔控件，隐藏关节角度控件
        if hasattr(self, 'joint_controls_widget'):
            self.joint_controls_widget.hide()
        if hasattr(self, 'cartesian_controls_widget'):
            self.cartesian_controls_widget.show()
        if hasattr(self, 'offset_controls_widget'):
            self.offset_controls_widget.hide()
        if hasattr(self, 'velocity_controls_widget'):
            self.velocity_controls_widget.hide()

    def _show_cartesian_offset_controls(self):
        """显示笛卡尔偏移控制界面"""
        # 显示偏移控件，隐藏其他控件
        if hasattr(self, 'offset_controls_widget'):
            self.offset_controls_widget.show()
        if hasattr(self, 'joint_controls_widget'):
            self.joint_controls_widget.hide()
        if hasattr(self, 'velocity_controls_widget'):
            self.velocity_controls_widget.hide()

    def _show_velocity_controls(self):
        """显示速度控制界面"""
        # 显示速度控件，隐藏其他控件
        if hasattr(self, 'velocity_controls_widget'):
            self.velocity_controls_widget.show()
        if hasattr(self, 'joint_controls_widget'):
            self.joint_controls_widget.hide()
        if hasattr(self, 'offset_controls_widget'):
            self.offset_controls_widget.hide()


    def get_current_joint_angles(self):
        """获取当前关节角度"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        angles = self.integrated_controller.get_arm_angles()
        if angles:
            for i, angle in enumerate(angles[:len(self.joint_spinboxes)]):
                self.joint_spinboxes[i].setValue(angle)
            self.log_message(f"获取当前关节角度: {angles}")
        else:
            QMessageBox.warning(self, "错误", "获取关节角度失败")

    def move_to_joint_angles(self):
        """移动到指定关节角度"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        angles = [spinbox.value() for spinbox in self.joint_spinboxes]
        if self.integrated_controller.set_arm_angles(angles):
            self.log_message(f"关节角度移动成功: {angles}")
        else:
            QMessageBox.warning(self, "错误", "关节角度移动失败")

    def move_cartesian_offset(self):
        """执行笛卡尔偏移运动"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        # 将mm转换为m，度转换为弧度
        offset = [
            self.offset_spinboxes[0].value() / 1000.0,  # mm -> m
            self.offset_spinboxes[1].value() / 1000.0,
            self.offset_spinboxes[2].value() / 1000.0,
            self.offset_spinboxes[3].value() * 3.14159 / 180.0,  # deg -> rad
            self.offset_spinboxes[4].value() * 3.14159 / 180.0,
            self.offset_spinboxes[5].value() * 3.14159 / 180.0
        ]

        frame_type = 0 if self.offset_frame_type.currentText() == "工作坐标系" else 1

        if self.integrated_controller.move_arm_cartesian_offset(offset, frame_type=frame_type):
            self.log_message(f"笛卡尔偏移运动成功: {offset}")
        else:
            QMessageBox.warning(self, "错误", "笛卡尔偏移运动失败")

    def start_velocity_control(self):
        """开始速度控制"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        velocity = [spinbox.value() for spinbox in self.velocity_spinboxes]
        if self.integrated_controller.move_arm_velocity(velocity):
            self.log_message(f"速度控制开始: {velocity}")
            self.start_velocity_btn.setEnabled(False)
            self.stop_velocity_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "错误", "速度控制启动失败")

    def stop_velocity_control(self):
        """停止速度控制"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            QMessageBox.warning(self, "错误", "控制器未初始化")
            return

        # 发送零速度来停止运动
        zero_velocity = [0.0] * 6
        if self.integrated_controller.move_arm_velocity(zero_velocity):
            self.log_message("速度控制已停止")
            self.start_velocity_btn.setEnabled(True)
            self.stop_velocity_btn.setEnabled(False)
        else:
            QMessageBox.warning(self, "错误", "停止速度控制失败")
        
        # 添加集成控制器信号连接
        if hasattr(self.integrated_controller, 'connected_signal'):
            self.integrated_controller.connected_signal.connect(self.on_integrated_connected)
        if hasattr(self.integrated_controller, 'error_signal'):
            self.integrated_controller.error_signal.connect(self.on_integrated_error)
        
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_integrated_status)
        self.status_timer.start(3000)  # 每3秒更新一次，减少性能压力
        
        # 连接手指角度变化信号以更新抓取控制显示
        if hasattr(self, 'hand_angles') and self.hand_angles:
            for i, spinbox in enumerate(self.hand_angles):
                if i == 3 or i == 4:  # 只监听食指(3)和拇指(4)
                    spinbox.valueChanged.connect(self.update_finger_display)
        
        # 连接传感器数据更新信号
        if self.sensor_data_manager:
            self.sensor_data_manager.data_updated_signal.connect(self.on_sensor_data_updated)

    def refresh_actions_list(self):
        """刷新动作列表"""
        self.actions_list.setRowCount(0)

        if not self.action_manager:
            return

        for action_name in self.action_manager.get_all_actions():
            action = self.action_manager.get_action(action_name)
            if not action:
                continue

            row = self.actions_list.rowCount()
            self.actions_list.insertRow(row)

            # 动作名称
            self.actions_list.setItem(row, 0, QTableWidgetItem(action.name))

            # 创建时间
            creation_time = datetime.fromtimestamp(action.creation_time).strftime('%Y-%m-%d %H:%M:%S')
            self.actions_list.setItem(row, 1, QTableWidgetItem(creation_time))

            # 最后修改时间
            modified_time = datetime.fromtimestamp(action.last_modified).strftime('%Y-%m-%d %H:%M:%S')
            self.actions_list.setItem(row, 2, QTableWidgetItem(modified_time))

            # 参数简要信息
            params = f"角度: [J1:{action.arm_position[0]:.1f}°, J2:{action.arm_position[1]:.1f}°, J3:{action.arm_position[2]:.1f}°]  手爪: {len(action.hand_angles)}"
            self.actions_list.setItem(row, 3, QTableWidgetItem(params))

    def refresh_sequences_list(self):
        """刷新序列列表"""
        self.sequences_list.setRowCount(0)

        if not self.action_manager:
            return

        for sequence_name in self.action_manager.get_all_sequences():
            sequence = self.action_manager.get_sequence(sequence_name)
            if not sequence:
                continue

            row = self.sequences_list.rowCount()
            self.sequences_list.insertRow(row)

            # 序列名称
            self.sequences_list.setItem(row, 0, QTableWidgetItem(sequence.name))

            # 创建时间
            creation_time = datetime.fromtimestamp(sequence.creation_time).strftime('%Y-%m-%d %H:%M:%S')
            self.sequences_list.setItem(row, 1, QTableWidgetItem(creation_time))

            # 最后修改时间
            modified_time = datetime.fromtimestamp(sequence.last_modified).strftime('%Y-%m-%d %H:%M:%S')
            self.sequences_list.setItem(row, 2, QTableWidgetItem(modified_time))

            # 动作数量
            self.sequences_list.setItem(row, 3, QTableWidgetItem(str(len(sequence.actions))))

    def create_action(self):
        """创建新动作"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        dialog = ActionDialog(self, None, self.action_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action_data = dialog.get_action_data()

            # 检查名称是否为空
            if not action_data["name"]:
                QMessageBox.warning(self, "错误", "动作名称不能为空")
                return

            # 检查名称是否已存在
            if action_data["name"] in self.action_manager.get_all_actions():
                QMessageBox.warning(self, "错误", f"动作名称 '{action_data['name']}' 已存在")
                return

            # 保存动作
            success = self.action_manager.save_action(
                name=action_data["name"],
                arm_position=action_data["arm_positions"],
                hand_angles=action_data["hand_angles"],
                arm_velocity=action_data["arm_velocity"],
                hand_velocity=action_data["hand_velocity"]
            )

            if success:
                self.status_label.setText(f"动作 '{action_data['name']}' 创建成功")
                # 刷新动作列表（由信号触发）
            else:
                QMessageBox.warning(self, "错误", f"创建动作 '{action_data['name']}' 失败")

    def save_current_position(self):
        """保存当前机械臂位置为动作"""
        QMessageBox.information(self, "提示", "请使用集成控制选项卡中的'保存当前姿态为动作'功能来保存当前位置")
        return
        
        # 原有功能已迁移到集成控制界面
        # if not self.action_manager:
        #     QMessageBox.warning(self, "错误", "动作管理器未初始化")
        #     return

        # if not self.action_manager.arm_controller:
        #     QMessageBox.warning(self, "错误", "机械臂控制器未初始化")
        #     return

        # if not self.action_manager.arm_controller.is_connected:
        #     QMessageBox.warning(self, "错误", "机械臂未连接")
        #     return
        # ... 其余代码已注释

    def execute_selected_action(self):
        """执行选中的动作"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.actions_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要执行的动作")
            return

        # 获取选中的动作名称
        row = selected_rows[0].row()
        action_name = self.actions_list.item(row, 0).text()

        # 执行动作
        success = self.action_manager.execute_action(action_name)

        if success:
            self.status_label.setText(f"动作 '{action_name}' 执行成功")
        else:
            QMessageBox.warning(self, "错误", f"执行动作 '{action_name}' 失败")

    def edit_selected_action(self):
        """编辑选中的动作"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.actions_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的动作")
            return

        # 获取选中的动作名称
        row = selected_rows[0].row()
        action_name = self.actions_list.item(row, 0).text()

        # 防止编辑自适应抓取动作
        if action_name == "自适应抓取":
            QMessageBox.information(self, "提示", "自适应抓取动作是系统保留动作，不可编辑")
            return

        # 获取动作对象
        action = self.action_manager.get_action(action_name)
        if not action:
            QMessageBox.warning(self, "错误", f"动作 '{action_name}' 不存在")
            return

        # 打开编辑对话框
        dialog = ActionDialog(self, action, self.action_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action_data = dialog.get_action_data()

            # 保存动作
            success = self.action_manager.save_action(
                name=action_data["name"],
                arm_position=action_data["arm_positions"],
                hand_angles=action_data["hand_angles"],
                arm_velocity=action_data["arm_velocity"],
                hand_velocity=action_data["hand_velocity"]
            )

            if success:
                self.status_label.setText(f"动作 '{action_data['name']}' 更新成功")
                # 刷新动作列表（由信号触发）
            else:
                QMessageBox.warning(self, "错误", f"更新动作 '{action_data['name']}' 失败")

    def delete_selected_action(self):
        """删除选中的动作"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.actions_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的动作")
            return

        # 获取选中的动作名称
        row = selected_rows[0].row()
        action_name = self.actions_list.item(row, 0).text()

        # 防止删除自适应抓取动作
        if action_name == "自适应抓取":
            QMessageBox.information(self, "提示", "自适应抓取动作是系统保留动作，不可删除")
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除动作 '{action_name}' 吗?\n注意: 所有使用此动作的序列也会受到影响。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除动作
        success = self.action_manager.delete_action(action_name)

        if success:
            self.status_label.setText(f"动作 '{action_name}' 已删除")
            # 刷新动作列表（由信号触发）
        else:
            QMessageBox.warning(self, "错误", f"删除动作 '{action_name}' 失败")

    def show_actions_context_menu(self, position):
        """显示动作列表上下文菜单"""
        menu = QMenu(self)

        # 添加菜单项
        execute_action = menu.addAction("执行动作")
        edit_action = menu.addAction("编辑动作")
        delete_action = menu.addAction("删除动作")
        menu.addSeparator()
        add_to_sequence = menu.addAction("添加到序列...")

        # 检查是否有选中项
        if not self.actions_list.selectionModel().selectedRows():
            execute_action.setEnabled(False)
            edit_action.setEnabled(False)
            delete_action.setEnabled(False)
            add_to_sequence.setEnabled(False)

        # 显示菜单并获取选择的动作
        action = menu.exec(self.actions_list.mapToGlobal(position))

        # 处理菜单选择
        if action == execute_action:
            self.execute_selected_action()
        elif action == edit_action:
            self.edit_selected_action()
        elif action == delete_action:
            self.delete_selected_action()
        elif action == add_to_sequence:
            self.add_action_to_sequence()

    def add_action_to_sequence(self):
        """将选中的动作添加到序列"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.actions_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要添加的动作")
            return

        # 获取选中的动作名称
        row = selected_rows[0].row()
        action_name = self.actions_list.item(row, 0).text()

        # 获取所有序列
        sequences = self.action_manager.get_all_sequences()
        if not sequences:
            reply = QMessageBox.question(
                self, "创建序列",
                "没有可用的序列，是否创建新序列?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.create_sequence()
            return

        # 选择序列
        sequence_name, ok = QInputDialog.getItem(
            self, "选择序列",
            "请选择要添加到的序列:",
            sequences, 0, False
        )

        if not ok or not sequence_name:
            return

        # 添加到序列
        delay, ok = QInputDialog.getDouble(
            self, "设置延迟",
            "请设置执行后的延迟时间(秒):",
            1.0, 0.0, 10.0, 1
        )

        if not ok:
            delay = 1.0

        success = self.action_manager.add_action_to_sequence(sequence_name, action_name, delay)

        if success:
            self.status_label.setText(f"动作 '{action_name}' 已添加到序列 '{sequence_name}'")
            # 刷新序列列表和详情（由信号触发）
        else:
            QMessageBox.warning(self, "错误", f"添加动作到序列失败")

    def create_sequence(self):
        """创建新序列"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        # 获取序列名称
        name, ok = QInputDialog.getText(self, "创建序列", "请输入序列名称:")
        if not ok or not name:
            return

        # 检查名称是否已存在
        if name in self.action_manager.get_all_sequences():
            QMessageBox.warning(self, "错误", f"序列名称 '{name}' 已存在")
            return

        # 获取序列描述
        description, ok = QInputDialog.getText(self, "序列描述", "请输入序列描述(可选):")
        if not ok:
            description = ""

        # 创建序列
        success = self.action_manager.create_sequence(name, description)

        if success:
            self.status_label.setText(f"序列 '{name}' 创建成功")
            # 刷新序列列表（由信号触发）

            # 自动切换到序列管理选项卡
            self.tab_widget.setCurrentIndex(1)

            # 询问是否立即编辑
            reply = QMessageBox.question(
                self, "编辑序列",
                f"序列 '{name}' 创建成功，是否立即编辑?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 编辑序列
                sequence = self.action_manager.get_sequence(name)
                if sequence:
                    dialog = SequenceDialog(self, sequence, self.action_manager)
                    dialog.exec()
        else:
            QMessageBox.warning(self, "错误", f"创建序列 '{name}' 失败")

    def execute_selected_sequence(self):
        """执行选中的序列"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        if self.action_manager.is_executing:
            QMessageBox.warning(self, "警告", "已有序列正在执行")
            return

        selected_rows = self.sequences_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要执行的序列")
            return

        # 获取选中的序列名称
        row = selected_rows[0].row()
        sequence_name = self.sequences_list.item(row, 0).text()

        # 确认执行
        reply = QMessageBox.question(
            self, "确认执行",
            f"确定要执行序列 '{sequence_name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 执行序列（非阻塞模式）
        success = self.action_manager.execute_sequence(sequence_name, blocking=False)

        if success:
            self.status_label.setText(f"序列 '{sequence_name}' 开始执行")
            self.execution_status.setText(f"正在执行: {sequence_name}")
            self.execution_progress.setValue(0)
            self.stop_execution_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "错误", f"执行序列 '{sequence_name}' 失败")

    def edit_selected_sequence(self):
        """编辑选中的序列"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.sequences_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的序列")
            return

        # 获取选中的序列名称
        row = selected_rows[0].row()
        sequence_name = self.sequences_list.item(row, 0).text()

        # 获取序列对象
        sequence = self.action_manager.get_sequence(sequence_name)
        if not sequence:
            QMessageBox.warning(self, "错误", f"序列 '{sequence_name}' 不存在")
            return

        # 打开编辑对话框
        dialog = SequenceDialog(self, sequence, self.action_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sequence_data = dialog.get_sequence_data()

            # 更新序列
            # 清空原序列动作
            old_sequence = self.action_manager.get_sequence(sequence_name)
            if old_sequence:
                while len(old_sequence.actions) > 0:
                    old_sequence.remove_action(0)

                # 设置描述
                old_sequence.description = sequence_data["description"]

                # 添加新动作
                for i, action_name in enumerate(sequence_data["actions"]):
                    delay = sequence_data["delays"][i]
                    self.action_manager.add_action_to_sequence(sequence_name, action_name, delay)

                self.status_label.setText(f"序列 '{sequence_name}' 更新成功")
                # 刷新序列列表和详情（由信号触发）
            else:
                QMessageBox.warning(self, "错误", f"更新序列 '{sequence_name}' 失败")

    def delete_selected_sequence(self):
        """删除选中的序列"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        selected_rows = self.sequences_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的序列")
            return

        # 获取选中的序列名称
        row = selected_rows[0].row()
        sequence_name = self.sequences_list.item(row, 0).text()

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除序列 '{sequence_name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除序列
        success = self.action_manager.delete_sequence(sequence_name)

        if success:
            self.status_label.setText(f"序列 '{sequence_name}' 已删除")
            # 清空序列详情
            self.sequence_description.setText("选择一个序列查看详情")
            self.sequence_actions_table.setRowCount(0)
            # 刷新序列列表（由信号触发）
        else:
            QMessageBox.warning(self, "错误", f"删除序列 '{sequence_name}' 失败")

    def show_sequences_context_menu(self, position):
        """显示序列列表上下文菜单"""
        menu = QMenu(self)

        # 添加菜单项
        execute_sequence = menu.addAction("执行序列")
        edit_sequence = menu.addAction("编辑序列")
        delete_sequence = menu.addAction("删除序列")

        # 检查是否有选中项
        if not self.sequences_list.selectionModel().selectedRows():
            execute_sequence.setEnabled(False)
            edit_sequence.setEnabled(False)
            delete_sequence.setEnabled(False)

        # 显示菜单并获取选择的动作
        action = menu.exec(self.sequences_list.mapToGlobal(position))

        # 处理菜单选择
        if action == execute_sequence:
            self.execute_selected_sequence()
        elif action == edit_sequence:
            self.edit_selected_sequence()
        elif action == delete_sequence:
            self.delete_selected_sequence()

    def on_sequence_selection_changed(self):
        """处理序列选择变化"""
        selected_rows = self.sequences_list.selectionModel().selectedRows()
        if not selected_rows:
            # 清空序列详情
            self.sequence_description.setText("选择一个序列查看详情")
            self.sequence_actions_table.setRowCount(0)
            return

        # 获取选中的序列名称
        row = selected_rows[0].row()
        sequence_name = self.sequences_list.item(row, 0).text()

        # 获取序列对象
        sequence = self.action_manager.get_sequence(sequence_name)
        if not sequence:
            return

        # 更新序列描述
        self.sequence_description.setText(f"序列: {sequence_name}\n描述: {sequence.description}\n执行次数: {sequence.repeat_count}")

        # 更新序列动作表格
        self.sequence_actions_table.setRowCount(0)

        for i, action_name in enumerate(sequence.actions):
            row = self.sequence_actions_table.rowCount()
            self.sequence_actions_table.insertRow(row)

            # 序号
            self.sequence_actions_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))

            # 动作名称
            self.sequence_actions_table.setItem(row, 1, QTableWidgetItem(action_name))

            # 延迟时间
            self.sequence_actions_table.setItem(row, 2, QTableWidgetItem(str(sequence.delays[i])))

    def stop_execution(self):
        """停止当前执行的序列"""
        if not self.action_manager:
            return

        if not self.action_manager.is_executing:
            return

        # 停止执行
        success = self.action_manager.stop_execution()

        if success:
            self.status_label.setText("序列执行已停止")
            self.execution_status.setText("已停止")
            self.stop_execution_btn.setEnabled(False)

        # 信号处理函数

    def on_action_added(self, action_name):
        """处理动作添加信号"""
        self.refresh_actions_list()
        self.status_label.setText(f"动作 '{action_name}' 已添加")

    def on_action_removed(self, action_name):
        """处理动作删除信号"""
        self.refresh_actions_list()
        self.status_label.setText(f"动作 '{action_name}' 已删除")

    def on_action_updated(self, action_name):
        """处理动作更新信号"""
        self.refresh_actions_list()
        self.status_label.setText(f"动作 '{action_name}' 已更新")

    def on_sequence_added(self, sequence_name):
        """处理序列添加信号"""
        self.refresh_sequences_list()
        self.status_label.setText(f"序列 '{sequence_name}' 已添加")

    def on_sequence_removed(self, sequence_name):
        """处理序列删除信号"""
        self.refresh_sequences_list()
        self.status_label.setText(f"序列 '{sequence_name}' 已删除")

    def on_sequence_updated(self, sequence_name):
        """处理序列更新信号"""
        self.refresh_sequences_list()

        # 如果当前选中的是更新的序列，刷新详情
        selected_rows = self.sequences_list.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if self.sequences_list.item(row, 0).text() == sequence_name:
                self.on_sequence_selection_changed()

        self.status_label.setText(f"序列 '{sequence_name}' 已更新")

    def on_execution_started(self, sequence_name):
        """处理序列执行开始信号"""
        self.execution_status.setText(f"正在执行: {sequence_name}")
        self.execution_progress.setValue(0)
        self.stop_execution_btn.setEnabled(True)
        self.status_label.setText(f"序列 '{sequence_name}' 开始执行")

    def on_execution_completed(self, sequence_name):
        """处理序列执行完成信号"""
        self.execution_status.setText(f"执行完成: {sequence_name}")
        self.execution_progress.setValue(100)
        self.stop_execution_btn.setEnabled(False)
        self.status_label.setText(f"序列 '{sequence_name}' 执行完成")

    def on_execution_progress(self, sequence_name, current_index, total_count):
        """处理序列执行进度信号"""
        if total_count > 0:
            # 获取序列对象
            sequence = self.action_manager.get_sequence(sequence_name)
            if not sequence:
                return
                
            progress = int((current_index / total_count) * 100)
            self.execution_progress.setValue(progress)
            
            # 计算当前循环次数和当前循环中的动作索引
            actions_per_cycle = len(sequence.actions)
            if actions_per_cycle > 0:
                current_cycle = current_index // actions_per_cycle + 1
                current_action_in_cycle = current_index % actions_per_cycle + 1
                
                # 显示包含循环信息的状态
                if sequence.repeat_count > 1:
                    self.execution_status.setText(
                        f"正在执行: {sequence_name} [循环 {current_cycle}/{sequence.repeat_count}] "
                        f"(动作 {current_action_in_cycle}/{actions_per_cycle})"
                    )
                else:
                    self.execution_status.setText(
                        f"正在执行: {sequence_name} (动作 {current_index + 1}/{total_count})"
                    )
            else:
                self.execution_status.setText(f"正在执行: {sequence_name} ({current_index + 1}/{total_count})")

    def on_execution_error(self, sequence_name, error_message):
        """处理序列执行错误信号"""
        self.execution_status.setText(f"执行错误: {sequence_name}")
        self.stop_execution_btn.setEnabled(False)
        self.status_label.setText(f"序列 '{sequence_name}' 执行出错: {error_message}")
        QMessageBox.warning(self, "执行错误", f"序列 '{sequence_name}' 执行出错: {error_message}")

    def toggle_hand_connection(self):
        """切换机械手连接状态"""
        if not self.action_manager:
            QMessageBox.warning(self, "错误", "动作管理器未初始化")
            return

        if not self.action_manager.arm_controller:
            QMessageBox.warning(self, "错误", "机械臂控制器未初始化")
            return

        if self.action_manager.arm_controller.is_connected:
            # 断开连接
            if self.action_manager.arm_controller.disconnect():
                self.hand_status_label.setText("已断开连接")
                self.hand_connection_status.setText("未连接")
                self.hand_connection_status.setStyleSheet("color: #ff5555;")
                self.hand_connect_btn.setText("连接")
                self.hand_connect_btn.setStyleSheet("""
                       QPushButton {
                           background-color: #50fa7b;
                           color: #282a36;
                           border-radius: 4px;
                           padding: 5px 15px;
                           font-weight: bold;
                       }
                       QPushButton:hover {
                           background-color: #5af78e;
                       }
                       QPushButton:pressed {
                           background-color: #46e070;
                       }
                   """)
                self.update_hand_ui_state(False)
            else:
                self.hand_status_label.setText("断开连接失败")
        else:
            # 建立连接
            ip = self.hand_ip_input.text()
            port = self.hand_port_input.value()

            if self.action_manager.arm_controller.connect(ip, port):
                self.hand_status_label.setText(f"已连接到 {ip}:{port}")
                self.hand_connection_status.setText("已连接")
                self.hand_connection_status.setStyleSheet("color: #50fa7b;")
                self.hand_connect_btn.setText("断开")
                self.hand_connect_btn.setStyleSheet("""
                       QPushButton {
                           background-color: #ff5555;
                           color: #f8f8f2;
                           border-radius: 4px;
                           padding: 5px 15px;
                           font-weight: bold;
                       }
                       QPushButton:hover {
                           background-color: #ff6e6e;
                       }
                       QPushButton:pressed {
                           background-color: #e64747;
                       }
                   """)
                self.update_hand_ui_state(True)
                self.get_hand_angles()
            else:
                self.hand_status_label.setText(f"连接到 {ip}:{port} 失败")

    def update_hand_ui_state(self, is_connected):
        """更新手爪UI控件状态"""
        # 手爪控制按钮
        self.apply_hand_btn.setEnabled(is_connected)
        self.get_hand_angles_btn.setEnabled(is_connected)
        self.hand_reset_btn.setEnabled(is_connected)
        self.save_hand_btn.setEnabled(is_connected)

        # 机械臂控制按钮
        self.apply_arm_btn.setEnabled(is_connected)
        self.get_arm_angles_btn.setEnabled(is_connected)
        self.save_arm_btn.setEnabled(is_connected)

        # 手爪滑块
        for slider in self.hand_sliders:
            slider.setEnabled(is_connected)

        # 机械臂滑块
        for slider in self.arm_sliders:
            slider.setEnabled(is_connected)

        # 预设按钮
        for button in self.hand_connection_tab.findChildren(QPushButton):
            if button != self.hand_connect_btn and button.parent().objectName() in ["presetsFrame"]:
                button.setEnabled(is_connected)

    def update_hand_value(self, index, value):
        """更新手爪值显示"""
        self.hand_values[index].setText(f"{value} μs")

    def get_hand_angles(self):
        """获取当前手爪角度"""
        if not self.action_manager or not self.action_manager.arm_controller:
            self.hand_status_label.setText("机械臂控制器未初始化")
            return
            
        if not self.action_manager.arm_controller.is_connected:
            self.hand_status_label.setText("请先连接机械臂")
            return
            
        try:
            # 获取当前手爪角度 - 修复：添加错误检查
            hand_angles = self.action_manager.arm_controller.getHandAngles()
            if not isinstance(hand_angles, (list, tuple)) or len(hand_angles) < 6:
                QMessageBox.warning(self, "错误", f"获取手爪角度失败: {hand_angles}")
                return
                
            # 更新滑块值
            for i, angle in enumerate(hand_angles):
                if i < len(self.hand_controls):
                    self.hand_controls[i].setValue(int(angle))
                    
            self.hand_status_label.setText(f"已获取当前手爪角度: {hand_angles} (共{len(hand_angles)}个关节)")
        except Exception as e:
            self.hand_status_label.setText(f"获取手爪角度出错: {str(e)}")

    def apply_hand_control(self):
        """应用手爪控制"""
        if not self.action_manager or not self.action_manager.arm_controller:
            self.hand_status_label.setText("机械臂控制器未初始化")
            return

        if not self.action_manager.arm_controller.is_connected:
            self.hand_status_label.setText("请先连接机械臂")
            return

        # 获取所有手爪值
        angles = [slider.value() for slider in self.hand_sliders]
        velocity = self.hand_speed.value()

        # 执行手爪控制 - 修复：使用正确的方法名
        self.action_manager.arm_controller.set_hand_angles(angles)
        self.hand_status_label.setText(f"已设置手爪角度: {angles}")

    def reset_hand(self):
        """将手爪重置为默认位置"""
        if not self.action_manager or not self.action_manager.arm_controller:
            QMessageBox.warning(self, "警告", "机械臂控制器未连接")
            return
            
        try:
            # 获取默认手爪角度
            default_angles = [500, 500, 500, 500, 500, 500]
            
            # 执行重置 - 修复：使用正确的方法名
            self.action_manager.arm_controller.set_hand_angles(default_angles)
            
            # 更新UI
            for i, spin_box in enumerate(self.hand_controls):
                spin_box.setValue(default_angles[i])
                
            self.log_message(f"手爪已重置为默认位置: {default_angles}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重置手爪失败: {str(e)}")
            self.log_message(f"重置手爪失败: {e}")

    def set_hand_preset(self, preset_angles):
        """设置预设手爪角度"""
        if not self.action_manager or not self.action_manager.arm_controller:
            QMessageBox.warning(self, "警告", "机械臂控制器未连接")
            return
            
        try:
            # 执行预设 - 修复：使用正确的方法名
            self.action_manager.arm_controller.set_hand_angles(preset_angles)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置预设手爪角度失败: {str(e)}")

    def update_arm_value(self, index, value):
        """更新机械臂值显示"""
        self.arm_values[index].setText(f"{value} °")

    def get_arm_angles(self):
        """获取当前机械臂角度"""
        if not self.action_manager or not self.action_manager.arm_controller:
            self.hand_status_label.setText("机械臂控制器未初始化")
            return

        if not self.action_manager.arm_controller.is_connected:
            self.hand_status_label.setText("请先连接机械臂")
            return

        # 获取当前机械臂角度 - 修复：添加错误检查
        try:
            arm_angles = self.action_manager.arm_controller.getArmAngles()
            if not isinstance(arm_angles, (list, tuple)) or len(arm_angles) < 6:
                QMessageBox.warning(self, "错误", f"获取机械臂角度失败: {arm_angles}")
                return
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取机械臂角度失败: {str(e)}")
            return

        self.hand_status_label.setText(f"当前机械臂角度: {arm_angles}")

        # 更新滑块值
        for i, angle in enumerate(arm_angles):
            if i < len(self.arm_sliders):
                self.arm_sliders[i].setValue(int(angle))
                self.update_arm_value(i, int(angle))

    def apply_arm_control(self):
        """应用机械臂控制"""
        QMessageBox.information(self, "提示", "此功能已被集成控制界面替代，请使用集成控制选项卡")
        return
        
        # 原有的控制代码已注释，请使用集成控制界面
        # if not self.action_manager or not self.action_manager.arm_controller:
        #     self.hand_status_label.setText("机械臂控制器未初始化")
        #     return

        # if not self.action_manager.arm_controller.is_connected:
        #     self.hand_status_label.setText("请先连接机械臂")
        #     return

        # # 获取所有机械臂关节值
        # angles = [slider.value() for slider in self.arm_sliders]
        # velocity = self.arm_speed.value()

        # # 执行机械臂控制 - 修复：使用正确的方法名
        # self.action_manager.arm_controller.set_arm_angles(angles, velocity)
        # self.hand_status_label.setText(f"已设置机械臂角度: {angles}")

    def save_arm_action(self):
        """将当前机械臂姿态保存为动作"""
        QMessageBox.information(self, "提示", "请使用集成控制选项卡中的'保存当前姿态为动作'功能")
        return
        
        # 原有功能已迁移到集成控制界面，请使用集成控制选项卡
        # if not self.action_manager:
        #     QMessageBox.warning(self, "错误", "动作管理器未初始化")
        #     return

        # if not self.action_manager.arm_controller or not self.action_manager.arm_controller.is_connected:
        #     QMessageBox.warning(self, "错误", "请先连接机械臂")
        #     return
        # ... 其余代码已注释

    def save_hand_action(self):
        """将当前手爪姿态保存为动作"""
        QMessageBox.information(self, "提示", "请使用集成控制选项卡中的'保存当前姿态为动作'功能")
        return
        
        # 原有功能已迁移到集成控制界面，请使用集成控制选项卡
        # if not self.action_manager:
        #     QMessageBox.warning(self, "错误", "动作管理器未初始化")
        #     return
        # ... 其余代码已注释

    # 集成控制相关方法 - 使用ArmController的原始方法
    def refresh_serial_ports(self):
        """刷新可用串口列表"""
        import serial.tools.list_ports
        import os
        
        # 保存当前选择
        current_port = self.hand_port_input.currentText() if hasattr(self, 'hand_port_input') else ""
        
        # 清空列表
        if hasattr(self, 'hand_port_input'):
            self.hand_port_input.clear()
        
        available_ports = []
        
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
            # 安全记录错误
            error_msg = f"扫描串口失败: {str(e)}"
            self.log_message(error_msg)
        
        # 如果没有找到串口，添加常见的默认选项
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
            self.log_message(scan_msg)
        
        return available_ports

    def get_selected_serial_port(self):
        """获取当前选择的串口名称"""
        if hasattr(self, 'hand_port_input'):
            # 获取选中项的实际端口名（data），而不是显示文本
            current_data = self.hand_port_input.currentData()
            if current_data:
                return current_data
            else:
                # 如果没有data，则返回当前文本
                return self.hand_port_input.currentText()
        return ""

    def connect_arm(self):
        """连接瑞尔曼机械臂 - 使用ArmController"""
        ip = self.arm_ip_input.currentText()
        self.arm_connect_btn.setEnabled(False)
        self.log_message(f"正在连接瑞尔曼: {ip}...")
        
        import threading
        def connect_thread():
            try:
                if self.integrated_controller.connect_arm(ip):
                    self.log_message(f"瑞尔曼连接成功: {ip}")
                    self.arm_status_label.setText(f"瑞尔曼: 已连接 ({ip})")
                    # 更新按钮状态
                    self.arm_connect_btn.setText("断开瑞尔曼")
                    self.arm_connect_btn.clicked.disconnect()
                    self.arm_connect_btn.clicked.connect(self.disconnect_arm)
                else:
                    self.log_message(f"瑞尔曼连接失败: {ip}")
                    self.arm_status_label.setText("瑞尔曼: 连接失败")
            except Exception as e:
                self.log_message(f"瑞尔曼连接异常: {str(e)}")
                self.arm_status_label.setText("瑞尔曼: 连接异常")
            finally:
                self.arm_connect_btn.setEnabled(True)
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def disconnect_arm(self):
        """断开瑞尔曼连接"""
        try:
            if self.integrated_controller.disconnect_arm():
                self.log_message("瑞尔曼已断开连接")
                self.arm_status_label.setText("瑞尔曼: 未连接")
                self.arm_connect_btn.setText("连接瑞尔曼")
                self.arm_connect_btn.clicked.disconnect()
                self.arm_connect_btn.clicked.connect(self.connect_arm)
            else:
                self.log_message("瑞尔曼断开连接失败")
        except Exception as e:
            self.log_message(f"瑞尔曼断开连接异常: {str(e)}")

    def connect_hand(self):
        """连接Inspire机械手 - 使用ArmController"""
        port = self.get_selected_serial_port()
        if not port:
            self.log_message("请先选择一个串口")
            return
            
        self.hand_connect_btn.setEnabled(False)
        self.log_message(f"正在连接Inspire: {port}...")
        
        import threading
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
                
                if self.integrated_controller.connect_hand(port):
                    self.log_message(f"Inspire连接成功: {port}")
                    self.hand_status_label.setText(f"Inspire: 已连接 ({port})")
                    self.hand_connect_btn.setText("断开Inspire")
                    self.hand_connect_btn.clicked.disconnect()
                    self.hand_connect_btn.clicked.connect(self.disconnect_hand)
                else:
                    self.log_message(f"Inspire连接失败: {port}")
                    self.hand_status_label.setText("Inspire: 连接失败")
                    self.log_message("提示：请检查串口号、波特率设置和设备连接")
                    
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"Inspire连接异常: {error_msg}")
                self.hand_status_label.setText("Inspire: 连接异常")
                
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
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def disconnect_hand(self):
        """断开Inspire连接"""
        try:
            if self.integrated_controller.disconnect_hand():
                self.log_message("Inspire已断开连接")
                self.hand_status_label.setText("Inspire: 未连接")
                self.hand_connect_btn.setText("连接Inspire")
                self.hand_connect_btn.clicked.disconnect()
                self.hand_connect_btn.clicked.connect(self.connect_hand)
            else:
                self.log_message("Inspire断开连接失败")
        except Exception as e:
            self.log_message(f"Inspire断开连接异常: {str(e)}")

    def connect_all(self):
        """连接所有设备 - 使用ArmController"""
        ip = self.arm_ip_input.currentText()
        port = self.get_selected_serial_port()
        self.connect_all_btn.setEnabled(False)
        self.log_message("正在连接所有设备...")
        
        import threading
        def connect_thread():
            try:
                if self.integrated_controller.connect_all(ip, port):
                    self.log_message("设备连接完成")
                    # 更新状态标签
                    self.arm_status_label.setText(f"瑞尔曼: 已连接 ({ip})")
                    self.hand_status_label.setText(f"Inspire: 已连接 ({port})")
                else:
                    self.log_message("设备连接失败")
            except Exception as e:
                self.log_message(f"设备连接异常: {str(e)}")
            finally:
                self.connect_all_btn.setEnabled(True)
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def disconnect_all(self):
        """断开所有设备连接 - 使用ArmController"""
        self.disconnect_btn.setEnabled(False)
        self.log_message("正在断开所有连接...")
        
        import threading
        def disconnect_thread():
            try:
                if self.integrated_controller.disconnect_all():
                    self.log_message("所有设备已断开连接")
                    # 更新状态标签
                    self.arm_status_label.setText("瑞尔曼: 未连接")
                    self.hand_status_label.setText("Inspire: 未连接")
                else:
                    self.log_message("断开连接时出现错误")
            except Exception as e:
                self.log_message(f"断开连接异常: {str(e)}")
            finally:
                self.disconnect_btn.setEnabled(True)
        
        thread = threading.Thread(target=disconnect_thread, daemon=True)
        thread.start()

    def move_arm(self):
        """移动机械臂 - 根据控制模式调用相应方法"""
        if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
            self.log_message("控制器未初始化")
            return

        current_mode = self.arm_control_mode.currentText()

        if current_mode == "笛卡尔直线":
            # 笛卡尔直线运动
            position = [
                self.arm_x.value() / 1000.0,  # mm -> m
                self.arm_y.value() / 1000.0,
                self.arm_z.value() / 1000.0,
                self.arm_roll.value() * 3.14159 / 180.0,  # deg -> rad
                self.arm_pitch.value() * 3.14159 / 180.0,
                self.arm_yaw.value() * 3.14159 / 180.0
            ]

            if self.integrated_controller.move_arm_cartesian_linear(position):
                self.log_message(f"笛卡尔直线运动成功: {position}")
            else:
                self.log_message("笛卡尔直线运动失败")

        elif current_mode == "关节角度":
            # 关节角度运动 - 这个应该在move_to_joint_angles方法中处理
            self.move_to_joint_angles()

        elif current_mode == "笛卡尔偏移":
            # 笛卡尔偏移运动 - 这个应该在move_cartesian_offset方法中处理
            self.move_cartesian_offset()

        elif current_mode == "速度控制":
            # 速度控制 - 这个应该在start_velocity_control方法中处理
            self.start_velocity_control()

    def set_hand_angles(self):
        """设置手指角度 - 使用ArmController"""
        angles = [spin.value() for spin in self.hand_angles]
        if self.integrated_controller.set_hand_angles(angles):
            self.log_message(f"手指角度设置为: {angles}")
        else:
            self.log_message("手指角度设置失败")

    def open_hand(self):
        """张开手爪 - 使用ArmController"""
        if self.integrated_controller.open_hand():
            self.log_message("手爪已张开")
            # 更新UI显示
            open_angles = [1000, 1000, 1000, 1000, 1000, 200]
            for i, angle in enumerate(open_angles):
                if i < len(self.hand_angles):
                    self.hand_angles[i].setValue(angle)
        else:
            self.log_message("张开手爪失败")

    def close_hand(self):
        """闭合手爪 - 使用ArmController"""
        if self.integrated_controller.close_hand():
            self.log_message("手爪已闭合")
            # 更新UI显示
            close_angles = [400, 400, 400, 400, 700, 200]
            for i, angle in enumerate(close_angles):
                if i < len(self.hand_angles):
                    self.hand_angles[i].setValue(angle)
        else:
            self.log_message("闭合手爪失败")

    def save_current_action(self):
        """保存当前UI设置的姿态为动作（不获取硬件状态）"""
        self.log_message("开始保存当前动作（使用UI设置值）...")
        
        # 检查连接状态（仅基础检查，不获取硬件数据）
        if not hasattr(self.integrated_controller, 'arm_connected') or not self.integrated_controller.arm_connected:
            self.log_message("警告: 机械臂未连接")
            QMessageBox.warning(self, "警告", "请先连接机械臂")
            return

        self.log_message("机械臂连接状态检查通过")

        # 获取动作名称
        name, ok = QInputDialog.getText(self, "保存动作", "请输入动作名称:")
        if not ok or not name.strip():
            self.log_message("用户取消了动作名称输入")
            return

        name = name.strip()
        self.log_message(f"用户输入动作名称: {name}")

        # 检查名称是否已存在（如果有动作管理器的话）
        if self.action_manager and name in self.action_manager.get_all_actions():
            self.log_message(f"动作名称 '{name}' 已存在，询问是否覆盖")
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"动作名称 '{name}' 已存在，是否覆盖?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.log_message("用户选择不覆盖，取消保存")
                return

        try:
            self.log_message("使用关节角度保存动作...")

            # 获取当前关节角度（如果在关节模式）或从硬件获取
            arm_angles = None
            if hasattr(self, 'joint_spinboxes') and self.joint_spinboxes:
                # 从关节角度UI控件获取
                arm_angles = [spinbox.value() for spinbox in self.joint_spinboxes]
                self.log_message(f"从UI获取关节角度: {arm_angles}")
            else:
                # 从硬件获取当前关节角度
                arm_angles = self.integrated_controller.get_arm_angles()
                if arm_angles:
                    self.log_message(f"从硬件获取关节角度: {arm_angles}")
                else:
                    self.log_message("无法获取关节角度")
                    QMessageBox.warning(self, "错误", "无法获取机械臂关节角度")
                    return

            # 直接使用UI中设置的手指角度值
            ui_hand_angles = [spin.value() for spin in self.hand_angles]

            self.log_message(f"保存的关节角度: {arm_angles}")
            self.log_message(f"保存的手指角度: {ui_hand_angles}")

            # 如果有动作管理器，保存到动作管理器
            if self.action_manager:
                self.log_message("使用动作管理器保存动作（关节角度模式）")

                success = self.action_manager.save_current_pose_as_action(
                    name=name,
                    use_ui_values=True,
                    ui_arm_angles=arm_angles,  # 改为关节角度
                    ui_hand_angles=ui_hand_angles
                )

                if success:
                    self.log_message(f"动作 '{name}' 已保存到动作管理器（数据来源：UI设置值）")
                    self.refresh_actions_list()

                    # 询问是否切换到动作管理选项卡
                    reply = QMessageBox.question(
                        self, "查看动作",
                        f"动作 '{name}' 已保存（使用UI设置值），是否切换到动作管理选项卡查看?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.tab_widget.setCurrentIndex(1)  # 切换到动作管理选项卡
                else:
                    self.log_message(f"保存动作 '{name}' 到动作管理器失败")
                    QMessageBox.warning(self, "错误", f"保存动作 '{name}' 到动作管理器失败")
            else:
                self.log_message("没有动作管理器，保存到JSON文件")
                # 如果没有动作管理器，保存到JSON文件
                import json
                import os
                import time
                
                # 构建动作数据（使用关节角度）
                action_data = {
                    "name": name,
                    "arm_angles": arm_angles,  # 改为关节角度
                    "hand_angles": ui_hand_angles,
                    "timestamp": time.time(),
                    "source": "关节角度控制"
                }
                
                actions_dir = "saved_actions"
                if not os.path.exists(actions_dir):
                    os.makedirs(actions_dir)
                    
                file_path = os.path.join(actions_dir, f"{name}.json")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(action_data, f, indent=2, ensure_ascii=False)
                
                self.log_message(f"动作 '{name}' 已保存到 {file_path}（数据来源：UI设置值）")
                QMessageBox.information(self, "成功", f"动作 '{name}' 保存成功！\n数据来源：UI设置值")
            
        except Exception as e:
            error_msg = f"保存动作失败: {str(e)}"
            self.log_message(error_msg)
            self.log_message(f"错误详情: {repr(e)}")
            QMessageBox.critical(self, "错误", error_msg)

    def log_message(self, message):
        """记录日志消息"""
        if hasattr(self, 'log_text') and self.log_text is not None:
            import time
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
            # 自动滚动到底部 - 修复PyQt6语法
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
        else:
            print(f"Log: {message}")
    
    # 集成控制器信号处理方法
    @pyqtSlot(bool)
    def on_integrated_connected(self, connected):
        """处理集成控制器连接状态变化"""
        status = "已连接" if connected else "已断开"
        self.log_message(f"设备连接状态: {status}")

    @pyqtSlot(str)
    def on_integrated_error(self, error_msg):
        """处理集成控制器错误信息"""
        self.log_message(f"设备错误: {error_msg}")
        QMessageBox.warning(self, "设备错误", error_msg)
    
    def update_integrated_status(self):
        """更新XArm-Inspire集成状态（优化版，停止频繁角度查询）"""
        try:
            # 防止并发执行状态更新
            if hasattr(self, '_updating_status') and self._updating_status:
                return
            
            self._updating_status = True
            
            try:
                # 只在需要时更新状态
                current_time = time.time()
                
                # 控制更新频率，避免过于频繁的查询
                if not hasattr(self, '_last_status_update'):
                    self._last_status_update = 0
                
                # 如果距离上次更新时间过短，跳过此次更新
                if current_time - self._last_status_update < 2.0:  # 增加间隔到2秒
                    return
                
                self._last_status_update = current_time
                
                # 获取状态信息（添加超时保护）
                try:
                    # 使用非阻塞方式获取状态
                    status = self.integrated_controller.get_status()
                    
                    # 更新连接状态显示
                    if status.get("arm_connected", False):
                        self.arm_status_label.setText("瑞尔曼: 已连接")
                    else:
                        self.arm_status_label.setText("瑞尔曼: 未连接")
                    
                    if status.get("hand_connected", False):
                        self.hand_status_label.setText("Inspire: 已连接")
                    else:
                        self.hand_status_label.setText("Inspire: 未连接")
                    
                    # 注释掉频繁的角度查询，只在用户明确操作时才获取
                    # 这样可以避免持续的角度异常问题
                    
                except Exception as e:
                    # 静默处理状态获取错误，不影响UI响应
                    print(f"获取状态时出错: {e}")
                    
            except Exception as e:
                # 静默处理更新错误
                print(f"更新状态时出错: {e}")
        finally:
            self._updating_status = False

    def get_current_pose(self):
        """获取当前机械臂和机械手的姿态并更新UI显示"""
        self.log_message("开始获取当前设备姿态...")

        # 检查连接状态
        if not hasattr(self.integrated_controller, 'arm_connected') or not self.integrated_controller.arm_connected:
            self.log_message("警告: 机械臂未连接")
            QMessageBox.warning(self, "警告", "请先连接机械臂")
            return

        try:
            # 获取当前运动模式
            current_mode = self.arm_control_mode.currentText()
            self.log_message(f"当前运动模式: {current_mode}")

            # 根据运动模式获取相应的姿态信息
            if current_mode == "关节角度":
                # 获取关节角度
                self.log_message("正在获取机械臂关节角度...")
                arm_angles = self.integrated_controller.get_arm_angles()

                if arm_angles is None:
                    self.log_message("获取机械臂关节角度失败")
                    QMessageBox.warning(self, "错误", "无法获取当前机械臂关节角度")
                    return

                self.log_message(f"机械臂当前关节角度: {arm_angles}")

                # 更新关节角度UI显示
                if len(arm_angles) >= len(self.joint_spinboxes):
                    for i, angle in enumerate(arm_angles[:len(self.joint_spinboxes)]):
                        self.joint_spinboxes[i].setValue(angle)
                    self.log_message("机械臂关节角度UI已更新")

            else:
                # 笛卡尔模式（包括"笛卡尔直线"、"笛卡尔偏移"、"速度控制"）
                # 获取当前机械臂位置
                self.log_message("正在获取机械臂笛卡尔位置...")
                arm_position = self.integrated_controller.get_arm_position()

                if arm_position is None:
                    self.log_message("获取机械臂位置失败")
                    QMessageBox.warning(self, "错误", "无法获取当前机械臂位置")
                    return

                self.log_message(f"机械臂当前位置: {arm_position}")

                # 更新机械臂笛卡尔坐标UI显示
                # 单位转换：SDK返回的是米和弧度，UI需要毫米和度
                if len(arm_position) >= 6:
                    self.arm_x.setValue(arm_position[0] * 1000.0)      # m -> mm
                    self.arm_y.setValue(arm_position[1] * 1000.0)      # m -> mm
                    self.arm_z.setValue(arm_position[2] * 1000.0)      # m -> mm
                    self.arm_roll.setValue(arm_position[3] * 180.0 / math.pi)   # rad -> deg
                    self.arm_pitch.setValue(arm_position[4] * 180.0 / math.pi)  # rad -> deg
                    self.arm_yaw.setValue(arm_position[5] * 180.0 / math.pi)    # rad -> deg
                    self.log_message("机械臂笛卡尔位置UI已更新（已转换单位：m->mm, rad->deg）")
            
            # 获取当前机械手角度
            if hasattr(self.integrated_controller, 'hand_connected') and self.integrated_controller.hand_connected:
                self.log_message("正在获取机械手角度...")
                hand_angles = self.integrated_controller.get_hand_angles()
                
                if hand_angles is None:
                    self.log_message("获取机械手角度失败")
                else:
                    self.log_message(f"机械手当前角度: {hand_angles}")
                    
                    # 更新机械手UI显示
                    if len(hand_angles) >= len(self.hand_angles):
                        for i, angle in enumerate(hand_angles[:len(self.hand_angles)]):
                            self.hand_angles[i].setValue(int(angle))
                        self.log_message("机械手UI角度已更新")
            else:
                self.log_message("机械手未连接，跳过获取手指角度")
            
            # 更新状态显示
            if hasattr(self, 'position_label'):
                self.position_label.setText(f"机械臂位置: {arm_position}")
            
            if hasattr(self, 'angles_label') and 'hand_angles' in locals():
                self.angles_label.setText(f"手指角度: {hand_angles}")
            
            self.log_message("姿态获取完成")
            QMessageBox.information(self, "成功", "当前设备姿态已获取并更新到UI")
            
        except Exception as e:
            error_msg = f"获取当前姿态失败: {str(e)}"
            self.log_message(error_msg)
            self.log_message(f"错误详情: {repr(e)}")
            QMessageBox.critical(self, "错误", error_msg)

    def setup_grasp_control_tab(self):
        """设置抓取控制选项卡"""
        layout = QVBoxLayout(self.grasp_control_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel("手部抓取控制")
        title_label.setObjectName("sectionTitle")
        title_label.setStyleSheet("""
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: bold;
                color: #50fa7b;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)

        # 创建主要控制区域
        main_control_widget = QWidget()
        main_control_layout = QHBoxLayout(main_control_widget)
        main_control_layout.setContentsMargins(0, 0, 0, 0)
        main_control_layout.setSpacing(30)

        # 左侧控制按钮区域
        left_control_group = QGroupBox("控制按钮")
        left_control_layout = QVBoxLayout(left_control_group)
        left_control_layout.setSpacing(15)

        # 创建按钮容器，用于并列显示闭合和释放按钮
        grasp_button_container = QWidget()
        grasp_button_layout = QHBoxLayout(grasp_button_container)
        grasp_button_layout.setContentsMargins(0, 0, 0, 0)
        grasp_button_layout.setSpacing(10)
        
        # 红色闭合按钮
        self.close_grasp_btn = QPushButton("闭合")
        self.close_grasp_btn.setMinimumSize(110, 60)
        self.close_grasp_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5555;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #ff6e6e;
            }
            QPushButton:pressed {
                background-color: #e64747;
            }
        """)
        self.close_grasp_btn.clicked.connect(self.execute_close_grasp)
        grasp_button_layout.addWidget(self.close_grasp_btn)
        
        # 蓝色释放按钮
        self.release_grasp_btn = QPushButton("释放")
        self.release_grasp_btn.setMinimumSize(110, 60)
        self.release_grasp_btn.setStyleSheet("""
            QPushButton {
                background-color: #6272a4;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #7289bc;
            }
            QPushButton:pressed {
                background-color: #525b84;
            }
        """)
        self.release_grasp_btn.clicked.connect(self.execute_release_grasp)
        grasp_button_layout.addWidget(self.release_grasp_btn)
        
        left_control_layout.addWidget(grasp_button_container)

        # 保存数据按钮
        self.save_data_btn = QPushButton("保存数据")
        self.save_data_btn.setMinimumSize(120, 50)
        self.save_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #50fa7b;
                color: #282a36;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5af78e;
            }
            QPushButton:pressed {
                background-color: #46e070;
            }
        """)
        self.save_data_btn.clicked.connect(self.save_grasp_data)
        left_control_layout.addWidget(self.save_data_btn)

        # 切换文件按钮
        self.change_file_btn = QPushButton("切换文件")
        self.change_file_btn.setMinimumSize(120, 40)
        self.change_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #8be9fd;
                color: #282a36;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #9cf0ff;
            }
            QPushButton:pressed {
                background-color: #7dd3e8;
            }
        """)
        self.change_file_btn.clicked.connect(self.change_csv_file)
        left_control_layout.addWidget(self.change_file_btn)

        # 添加备注输入区域
        notes_label = QLabel("数据备注:")
        notes_label.setStyleSheet("font-weight: bold; color: #f8f8f2; margin-top: 15px;")
        left_control_layout.addWidget(notes_label)
        
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText("在此输入本次保存数据的备注信息...")
        self.notes_text.setStyleSheet("""
            QTextEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border: 2px solid #6272a4;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #bd93f9;
            }
        """)
        left_control_layout.addWidget(self.notes_text)

        # 添加一些间距
        left_control_layout.addStretch()

        # 右侧参数显示区域
        right_display_group = QGroupBox("手指参数")
        right_display_layout = QVBoxLayout(right_display_group)
        right_display_layout.setSpacing(15)

        # 食指参数显示
        index_finger_widget = QWidget()
        index_finger_layout = QHBoxLayout(index_finger_widget)
        index_finger_layout.setContentsMargins(10, 5, 10, 5)

        index_finger_label = QLabel("食指:")
        index_finger_label.setStyleSheet("font-weight: bold; color: #bd93f9;")
        index_finger_layout.addWidget(index_finger_label)

        self.index_finger_value = QLabel("500")
        self.index_finger_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #bd93f9;
                border: 2px solid #bd93f9;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
        """)
        index_finger_layout.addWidget(self.index_finger_value)
        index_finger_layout.addStretch()

        right_display_layout.addWidget(index_finger_widget)

        # 拇指参数显示
        thumb_widget = QWidget()
        thumb_layout = QHBoxLayout(thumb_widget)
        thumb_layout.setContentsMargins(10, 5, 10, 5)

        thumb_label = QLabel("拇指:")
        thumb_label.setStyleSheet("font-weight: bold; color: #ffb86c;")
        thumb_layout.addWidget(thumb_label)

        self.thumb_value = QLabel("500")
        self.thumb_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #ffb86c;
                border: 2px solid #ffb86c;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
        """)
        thumb_layout.addWidget(self.thumb_value)
        thumb_layout.addStretch()

        right_display_layout.addWidget(thumb_widget)

        # 添加间距
        right_display_layout.addStretch()

        # 将左右区域添加到主布局
        main_control_layout.addWidget(left_control_group)
        main_control_layout.addWidget(right_display_group)

        layout.addWidget(main_control_widget)

        # 添加状态信息区域
        status_group = QGroupBox("操作状态")
        status_layout = QVBoxLayout(status_group)

        self.grasp_status_label = QLabel("就绪")
        self.grasp_status_label.setStyleSheet("""
            QLabel {
                color: #50fa7b;
                font-size: 14px;
                padding: 10px;
                background-color: #282a36;
                border: 1px solid #50fa7b;
                border-radius: 5px;
            }
        """)
        status_layout.addWidget(self.grasp_status_label)

        layout.addWidget(status_group)

        # 添加传感器数据显示区域
        sensor_group = QGroupBox("传感器数据")
        sensor_layout = QVBoxLayout(sensor_group)
        sensor_layout.setSpacing(10)

        # 传感器选择区域
        sensor_select_widget = QWidget()
        sensor_select_layout = QHBoxLayout(sensor_select_widget)
        sensor_select_layout.setContentsMargins(5, 5, 5, 5)

        sensor_select_label = QLabel("选择传感器:")
        sensor_select_label.setStyleSheet("font-weight: bold; color: #8be9fd;")
        sensor_select_layout.addWidget(sensor_select_label)

        self.sensor_combo = QComboBox()
        self.sensor_combo.setMinimumWidth(120)
        self.sensor_combo.setStyleSheet("""
            QComboBox {
                background-color: #282a36;
                color: #f8f8f2;
                border: 2px solid #8be9fd;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                border: none;
                width: 12px;
                height: 12px;
            }
        """)
        self.sensor_combo.currentTextChanged.connect(self.on_sensor_selection_changed)
        sensor_select_layout.addWidget(self.sensor_combo)

        # 刷新传感器按钮
        self.refresh_sensor_btn = QPushButton("刷新")
        self.refresh_sensor_btn.setStyleSheet("""
            QPushButton {
                background-color: #8be9fd;
                color: #282a36;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9cf0ff;
            }
        """)
        self.refresh_sensor_btn.clicked.connect(self.refresh_sensor_list)
        sensor_select_layout.addWidget(self.refresh_sensor_btn)

        sensor_select_layout.addStretch()
        sensor_layout.addWidget(sensor_select_widget)

        # 传感器数值显示区域
        sensor_values_widget = QWidget()
        sensor_values_layout = QGridLayout(sensor_values_widget)
        sensor_values_layout.setContentsMargins(10, 5, 10, 5)
        sensor_values_layout.setSpacing(10)

        # X轴数值
        x_label = QLabel("X轴:")
        x_label.setStyleSheet("font-weight: bold; color: #ff5555;")
        sensor_values_layout.addWidget(x_label, 0, 0)

        self.sensor_x_value = QLabel("0.00")
        self.sensor_x_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #ff5555;
                border: 2px solid #ff5555;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)
        sensor_values_layout.addWidget(self.sensor_x_value, 0, 1)

        # Y轴数值
        y_label = QLabel("Y轴:")
        y_label.setStyleSheet("font-weight: bold; color: #50fa7b;")
        sensor_values_layout.addWidget(y_label, 0, 2)

        self.sensor_y_value = QLabel("0.00")
        self.sensor_y_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #50fa7b;
                border: 2px solid #50fa7b;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)
        sensor_values_layout.addWidget(self.sensor_y_value, 0, 3)

        # Z轴数值
        z_label = QLabel("Z轴:")
        z_label.setStyleSheet("font-weight: bold; color: #8be9fd;")
        sensor_values_layout.addWidget(z_label, 1, 0)

        self.sensor_z_value = QLabel("0.00")
        self.sensor_z_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #8be9fd;
                border: 2px solid #8be9fd;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)
        sensor_values_layout.addWidget(self.sensor_z_value, 1, 1)

        # 传感器状态
        sensor_status_label = QLabel("状态:")
        sensor_status_label.setStyleSheet("font-weight: bold; color: #f1fa8c;")
        sensor_values_layout.addWidget(sensor_status_label, 1, 2)

        self.sensor_status_value = QLabel("未连接")
        self.sensor_status_value.setStyleSheet("""
            QLabel {
                background-color: #282a36;
                color: #f1fa8c;
                border: 2px solid #f1fa8c;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)
        sensor_values_layout.addWidget(self.sensor_status_value, 1, 3)

        sensor_layout.addWidget(sensor_values_widget)

        layout.addWidget(sensor_group)

        # 添加底部间距
        layout.addStretch()

        # 初始化参数显示
        self.update_finger_display()
        
        # 初始化传感器相关变量
        self.selected_sensor_id = None
        self.current_csv_file = None  # 当前CSV文件路径
        self.refresh_sensor_list()

    def execute_close_grasp(self):
        """执行闭合抓取动作（食指和拇指参数-5）"""
        try:
            self.grasp_status_label.setText("正在执行闭合动作...")
            self.log_message("开始执行闭合抓取动作")

            # 检查集成控制器连接状态
            if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
                self.grasp_status_label.setText("错误：集成控制器未初始化")
                self.log_message("错误：集成控制器未初始化")
                QMessageBox.warning(self, "错误", "集成控制器未初始化")
                return

            # 检查机械手连接状态
            if not hasattr(self.integrated_controller, 'hand_connected') or not self.integrated_controller.hand_connected:
                self.grasp_status_label.setText("错误：机械手未连接")
                self.log_message("错误：机械手未连接，请先连接Inspire机械手")
                QMessageBox.warning(self, "警告", "请先在集成控制选项卡中连接Inspire机械手")
                return

            # 获取当前手指角度
            current_angles = []
            if hasattr(self, 'hand_angles') and self.hand_angles:
                # 从UI获取当前设置的角度
                current_angles = [spin.value() for spin in self.hand_angles]
            else:
                # 使用默认值
                current_angles = [500, 500, 500, 500, 500, 500]

            self.log_message(f"当前手指角度: {current_angles}")

            # 计算新的角度：食指(索引3)和拇指(索引4)参数-5
            new_angles = current_angles.copy()
            new_angles[3] = max(0, new_angles[3] - 5)  # 食指，确保不小于0
            new_angles[4] = max(0, new_angles[4] - 5)  # 拇指，确保不小于0

            self.log_message(f"新的手指角度: {new_angles}")

            # 执行闭合动作
            if self.integrated_controller.set_hand_angles(new_angles):
                self.log_message("闭合动作执行成功")
                self.grasp_status_label.setText("闭合动作执行成功")
                
                # 更新UI显示的角度值
                if hasattr(self, 'hand_angles') and self.hand_angles:
                    for i, angle in enumerate(new_angles):
                        if i < len(self.hand_angles):
                            self.hand_angles[i].setValue(angle)
                
                # 更新参数显示
                self.update_finger_display()
                
                # 短暂延迟后恢复状态
                QTimer.singleShot(2000, lambda: self.grasp_status_label.setText("就绪"))
                
            else:
                self.log_message("闭合动作执行失败")
                self.grasp_status_label.setText("闭合动作执行失败")
                QMessageBox.warning(self, "错误", "闭合动作执行失败，请检查设备连接")

        except Exception as e:
            error_msg = f"执行闭合动作时出错: {str(e)}"
            self.log_message(error_msg)
            self.grasp_status_label.setText("执行出错")
            QMessageBox.critical(self, "错误", error_msg)

    def execute_release_grasp(self):
        """执行释放抓取动作（食指和拇指参数+5）"""
        try:
            self.grasp_status_label.setText("正在执行释放动作...")
            self.log_message("开始执行释放抓取动作")

            # 检查集成控制器连接状态
            if not hasattr(self, 'integrated_controller') or not self.integrated_controller:
                self.grasp_status_label.setText("错误：集成控制器未初始化")
                self.log_message("错误：集成控制器未初始化")
                QMessageBox.warning(self, "错误", "集成控制器未初始化")
                return

            # 检查机械手连接状态
            if not hasattr(self.integrated_controller, 'hand_connected') or not self.integrated_controller.hand_connected:
                self.grasp_status_label.setText("错误：机械手未连接")
                self.log_message("错误：机械手未连接，请先连接Inspire机械手")
                QMessageBox.warning(self, "警告", "请先在集成控制选项卡中连接Inspire机械手")
                return

            # 获取当前手指角度
            current_angles = []
            if hasattr(self, 'hand_angles') and self.hand_angles:
                # 从UI获取当前设置的角度
                current_angles = [spin.value() for spin in self.hand_angles]
            else:
                # 使用默认值
                current_angles = [500, 500, 500, 500, 500, 500]

            self.log_message(f"当前手指角度: {current_angles}")

            # 计算新的角度：食指(索引3)和拇指(索引4)参数+5
            new_angles = current_angles.copy()
            new_angles[3] = min(1000, new_angles[3] + 5)  # 食指，确保不大于1000
            new_angles[4] = min(1000, new_angles[4] + 5)  # 拇指，确保不大于1000

            self.log_message(f"新的手指角度: {new_angles}")

            # 执行释放动作
            if self.integrated_controller.set_hand_angles(new_angles):
                self.log_message("释放动作执行成功")
                self.grasp_status_label.setText("释放动作执行成功")
                
                # 更新UI显示的角度值
                if hasattr(self, 'hand_angles') and self.hand_angles:
                    for i, angle in enumerate(new_angles):
                        if i < len(self.hand_angles):
                            self.hand_angles[i].setValue(angle)
                
                # 更新参数显示
                self.update_finger_display()
                
                # 短暂延迟后恢复状态
                QTimer.singleShot(2000, lambda: self.grasp_status_label.setText("就绪"))
                
            else:
                self.log_message("释放动作执行失败")
                self.grasp_status_label.setText("释放动作执行失败")
                QMessageBox.warning(self, "错误", "释放动作执行失败，请检查设备连接")

        except Exception as e:
            error_msg = f"执行释放动作时出错: {str(e)}"
            self.log_message(error_msg)
            self.grasp_status_label.setText("执行出错")
            QMessageBox.critical(self, "错误", error_msg)

    def update_finger_display(self):
        """更新食指和拇指参数显示"""
        try:
            # 获取当前手指角度值
            if hasattr(self, 'hand_angles') and self.hand_angles and len(self.hand_angles) >= 5:
                # 食指是索引3，拇指是索引4
                index_finger_angle = self.hand_angles[3].value()
                thumb_angle = self.hand_angles[4].value()
            else:
                # 使用默认值
                index_finger_angle = 500
                thumb_angle = 500

            # 更新显示
            self.index_finger_value.setText(str(index_finger_angle))
            self.thumb_value.setText(str(thumb_angle))

        except Exception as e:
            self.log_message(f"更新手指参数显示时出错: {str(e)}")
            # 使用默认值
            self.index_finger_value.setText("500")
            self.thumb_value.setText("500")

    def refresh_sensor_list(self):
        """刷新传感器列表"""
        try:
            # 保存当前选择
            current_selection = self.sensor_combo.currentText()
            
            # 清空下拉框
            self.sensor_combo.clear()
            self.sensor_combo.addItem("请选择传感器")
            
            if not self.sensor_data_manager:
                self.sensor_status_value.setText("数据管理器未初始化")
                self.log_message("传感器数据管理器未初始化")
                return
            
            # 获取可用传感器列表
            available_sensors = self.sensor_data_manager.get_all_sensors()
            
            if not available_sensors:
                self.sensor_status_value.setText("未检测到传感器")
                self.log_message("未检测到任何传感器")
                return
            
            # 添加传感器到下拉框
            for sensor_id in sorted(available_sensors):
                self.sensor_combo.addItem(f"传感器 {sensor_id}")
            
            # 尝试恢复之前的选择
            if current_selection and current_selection != "请选择传感器":
                index = self.sensor_combo.findText(current_selection)
                if index >= 0:
                    self.sensor_combo.setCurrentIndex(index)
            
            self.log_message(f"已检测到 {len(available_sensors)} 个传感器: {available_sensors}")
            
        except Exception as e:
            self.log_message(f"刷新传感器列表时出错: {str(e)}")
            self.sensor_status_value.setText("刷新失败")

    def on_sensor_selection_changed(self, text):
        """传感器选择变化处理"""
        try:
            if text == "请选择传感器" or not text:
                self.selected_sensor_id = None
                self.sensor_status_value.setText("未选择")
                self.reset_sensor_display()
                return
            
            # 从文本中提取传感器ID
            import re
            match = re.search(r'传感器 (\d+)', text)
            if match:
                self.selected_sensor_id = int(match.group(1))
                self.sensor_status_value.setText("已连接")
                self.log_message(f"选择了传感器 {self.selected_sensor_id}")
                # 立即更新显示
                self.update_sensor_display()
            else:
                self.selected_sensor_id = None
                self.sensor_status_value.setText("选择错误")
                self.reset_sensor_display()
                
        except Exception as e:
            self.log_message(f"处理传感器选择变化时出错: {str(e)}")
            self.selected_sensor_id = None
            self.sensor_status_value.setText("选择错误")

    def on_sensor_data_updated(self, sensor_id, values):
        """传感器数据更新时的回调"""
        try:
            # 只更新当前选中的传感器数据
            if self.selected_sensor_id == sensor_id:
                self.update_sensor_display()
                
        except Exception as e:
            self.log_message(f"更新传感器数据显示时出错: {str(e)}")

    def update_sensor_display(self):
        """更新传感器数值显示"""
        try:
            if not self.selected_sensor_id or not self.sensor_data_manager:
                self.reset_sensor_display()
                return
            
            # 获取传感器数据
            sensor_data = self.sensor_data_manager.get_sensor_data(self.selected_sensor_id)
            if not sensor_data:
                self.reset_sensor_display()
                self.sensor_status_value.setText("无数据")
                return
            
            # 获取最新数值
            latest_values = sensor_data.get_latest_values()
            if not latest_values or len(latest_values) < 3:
                self.reset_sensor_display()
                self.sensor_status_value.setText("数据不完整")
                return
            
            # 更新显示
            self.sensor_x_value.setText(f"{latest_values[0]:.2f}")
            self.sensor_y_value.setText(f"{latest_values[1]:.2f}")
            self.sensor_z_value.setText(f"{latest_values[2]:.2f}")
            self.sensor_status_value.setText("实时更新")
            
        except Exception as e:
            self.log_message(f"更新传感器显示时出错: {str(e)}")
            self.reset_sensor_display()

    def reset_sensor_display(self):
        """重置传感器数值显示"""
        try:
            self.sensor_x_value.setText("0.00")
            self.sensor_y_value.setText("0.00")
            self.sensor_z_value.setText("0.00")
            
        except Exception as e:
            self.log_message(f"重置传感器显示时出错: {str(e)}")

    def save_grasp_data(self):
        """保存当前抓取数据（传感器数据和手指参数）到CSV文件"""
        try:
            self.log_message("开始保存抓取数据...")
            
            # 收集当前数据
            data = self.collect_current_data()
            if not data:
                QMessageBox.warning(self, "警告", "没有可保存的数据")
                return
            
            # 检查是否已选择CSV文件
            if not hasattr(self, 'current_csv_file') or not self.current_csv_file:
                # 第一次保存，需要选择文件
                self.log_message("首次保存，选择CSV文件...")
                csv_file_path = self.select_csv_file_for_first_save()
                if not csv_file_path:
                    return  # 用户取消了保存
                self.current_csv_file = csv_file_path
            else:
                # 使用已选择的文件
                csv_file_path = self.current_csv_file
                self.log_message(f"使用现有CSV文件: {csv_file_path}")
            
            # 保存数据到CSV
            success = self.append_data_to_csv(csv_file_path, data)
            
            if success:
                self.log_message(f"数据已成功追加到: {csv_file_path}")
                self.grasp_status_label.setText("数据追加成功")
                
                # 显示简短的成功提示，不显示完整路径
                filename = os.path.basename(csv_file_path)
                QMessageBox.information(self, "成功", f"数据已追加到文件: {filename}")
                
                # 2秒后恢复状态
                QTimer.singleShot(2000, lambda: self.grasp_status_label.setText("就绪"))
            else:
                self.log_message("数据保存失败")
                self.grasp_status_label.setText("数据保存失败")
                QMessageBox.warning(self, "错误", "数据保存失败，请检查文件权限")
                
        except Exception as e:
            error_msg = f"保存抓取数据时出错: {str(e)}"
            self.log_message(error_msg)
            self.grasp_status_label.setText("保存出错")
            QMessageBox.critical(self, "错误", error_msg)

    def collect_current_data(self):
        """收集当前的传感器数据和手指参数
        
        传感器状态码说明：
        - VALID_DATA: 有效数据
        - INVALID_DATA: 数据无效
        - NO_DATA: 传感器无数据
        - NO_SENSOR: 未选择传感器
        - NO_SELECTION: 未选择传感器（默认状态）
        """
        try:
            # 获取备注文本
            notes = ""
            if hasattr(self, 'notes_text') and self.notes_text:
                notes = self.notes_text.toPlainText().strip()
            
            data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # 精确到毫秒
                'sensor_id': None,
                'sensor_x': 0.0,
                'sensor_y': 0.0,
                'sensor_z': 0.0,
                'index_finger': 500,
                'thumb': 500,
                'sensor_status': 'NO_SELECTION',  # 使用英文状态码避免编码问题
                'notes': notes  # 添加备注字段
            }
            
            # 获取传感器数据
            if self.selected_sensor_id and self.sensor_data_manager:
                sensor_data = self.sensor_data_manager.get_sensor_data(self.selected_sensor_id)
                if sensor_data:
                    latest_values = sensor_data.get_latest_values()
                    if latest_values and len(latest_values) >= 3:
                        data['sensor_id'] = self.selected_sensor_id
                        data['sensor_x'] = round(latest_values[0], 3)
                        data['sensor_y'] = round(latest_values[1], 3)
                        data['sensor_z'] = round(latest_values[2], 3)
                        data['sensor_status'] = 'VALID_DATA'  # 有效数据
                        self.log_message(f"收集传感器{self.selected_sensor_id}数据: X={data['sensor_x']}, Y={data['sensor_y']}, Z={data['sensor_z']}")
                    else:
                        data['sensor_status'] = 'INVALID_DATA'  # 数据无效
                        self.log_message("传感器数据无效")
                else:
                    data['sensor_status'] = 'NO_DATA'  # 传感器无数据
                    self.log_message("传感器无数据")
            else:
                data['sensor_status'] = 'NO_SENSOR'  # 未选择传感器
                self.log_message("未选择传感器")
            
            # 获取手指参数
            if hasattr(self, 'hand_angles') and self.hand_angles and len(self.hand_angles) >= 5:
                data['index_finger'] = self.hand_angles[3].value()  # 食指
                data['thumb'] = self.hand_angles[4].value()  # 拇指
                self.log_message(f"收集手指参数: 食指={data['index_finger']}, 拇指={data['thumb']}")
            else:
                self.log_message("使用默认手指参数值")
            
            return data
            
        except Exception as e:
            self.log_message(f"收集数据时出错: {str(e)}")
            return None

    def select_csv_file_for_first_save(self):
        """第一次保存时选择CSV文件"""
        try:
            # 创建数据目录
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 默认文件名
            default_filename = "grasp_data.csv"
            default_path = os.path.join(data_dir, default_filename)
            
            # 显示文件选择对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择保存抓取数据的CSV文件",
                default_path,
                "CSV文件 (*.csv);;所有文件 (*.*)"
            )
            
            if file_path:
                self.log_message(f"首次选择CSV文件: {file_path}")
                return file_path
            else:
                self.log_message("用户取消了文件选择")
                return None
            
        except Exception as e:
            self.log_message(f"选择文件时出错: {str(e)}")
            return None

    def append_data_to_csv(self, file_path, data):
        """将数据追加到CSV文件"""
        try:
            # 定义CSV列标题
            fieldnames = [
                'timestamp', 'sensor_id', 'sensor_x', 'sensor_y', 'sensor_z',
                'index_finger', 'thumb', 'sensor_status', 'notes'
            ]
            
            # 检查文件是否存在
            file_exists = os.path.exists(file_path)
            
            # 以追加模式打开文件，使用UTF-8 BOM编码确保兼容性
            with open(file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 如果文件不存在或为空，写入标题行
                if not file_exists or os.path.getsize(file_path) == 0:
                    writer.writeheader()
                    self.log_message("写入CSV文件标题行（UTF-8 BOM编码）")
                
                # 写入数据行
                writer.writerow(data)
                self.log_message("数据行已追加到CSV文件")
            
            return True
            
        except Exception as e:
            self.log_message(f"写入CSV文件时出错: {str(e)}")
            return False

    def change_csv_file(self):
        """切换到新的CSV文件"""
        try:
            # 创建数据目录
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 生成新的默认文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"grasp_data_{timestamp}.csv"
            default_path = os.path.join(data_dir, default_filename)
            
            # 显示确认对话框
            current_file = getattr(self, 'current_csv_file', None)
            if current_file:
                current_filename = os.path.basename(current_file)
                reply = QMessageBox.question(
                    self, "确认切换文件",
                    f"当前正在使用文件: {current_filename}\n\n是否要切换到新的CSV文件？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 显示文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择新的CSV文件保存路径",
                default_path,
                "CSV文件 (*.csv);;所有文件 (*.*)"
            )
            
            if file_path:
                old_file = getattr(self, 'current_csv_file', None)
                self.current_csv_file = file_path
                
                old_filename = os.path.basename(old_file) if old_file else "无"
                new_filename = os.path.basename(file_path)
                self.log_message(f"切换CSV文件: {old_filename} -> {new_filename}")
                
                # 更新状态显示
                self.grasp_status_label.setText("已切换文件")
                QMessageBox.information(self, "成功", f"已切换到新文件: {new_filename}\n\n后续保存将追加到此文件")
                
                # 2秒后恢复状态
                QTimer.singleShot(2000, lambda: self.grasp_status_label.setText("就绪"))
            else:
                self.log_message("用户取消了文件切换")
                
        except Exception as e:
            error_msg = f"切换CSV文件时出错: {str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)