#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSpacerItem, QSizePolicy
)


class HomePage(QWidget):
    """主页，显示欢迎信息和帮助说明"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window

        # 设置UI
        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建欢迎标题
        self.title_label = QLabel("欢迎使用 ForceVisual XARM 版本")
        self.title_label.setObjectName("pageTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # 创建内容区域
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)

        # 尝试添加图标
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 尝试加载图标
        try:
            from builtins import APP_ROOT_PATH
            icon_path = os.path.join(APP_ROOT_PATH, "resources", "images", "logo.png")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path).scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(pixmap)
            else:
                # 如果图标不存在，使用文本替代
                self.logo_label.setText("ForceVisual XARM")
                self.logo_label.setStyleSheet("""
                    font-size: 36px;
                    font-weight: bold;
                    color: #bd93f9;
                """)
        except:
            # 如果无法导入APP_ROOT_PATH，使用文本替代
            self.logo_label.setText("ForceVisual XARM")
            self.logo_label.setStyleSheet("""
                font-size: 36px;
                font-weight: bold;
                color: #bd93f9;
            """)

        self.content_layout.addWidget(self.logo_label)

        # 添加欢迎信息
        self.welcome_label = QLabel(
            "ForceVisual XARM 是一个功能强大的三轴力传感器上位机系统，"
            "集成机械臂控制、机械手操作和实时数据可视化。"
        )
        self.welcome_label.setWordWrap(True)
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.welcome_label)

        # 添加功能说明
        self.features_title = QLabel("主要功能:")
        self.features_title.setObjectName("sectionTitle")
        self.content_layout.addWidget(self.features_title)

        # 创建功能列表
        features = [
            "实时传感器监测 - 多传感器数据同步采集和可视化",
            "串口通信 - 灵活的串口配置和数据传输",
            "机械臂控制 - 集成xArm机械臂SDK，支持精确位置和速度控制",
            "机械手操作 - 集成Inspire灵巧手，支持多自由度手指控制",
            "动作管理 - 动作序列录制、编辑和回放",
            "数据记录 - 完整的数据记录和导出功能",
            "3D可视化 - 实时力场可视化和曲线绘制"
        ]

        for feature in features:
            feature_label = QLabel(f"• {feature}")
            feature_label.setWordWrap(True)
            self.content_layout.addWidget(feature_label)

        # 添加技术栈信息
        self.tech_title = QLabel("技术栈:")
        self.tech_title.setObjectName("sectionTitle")
        self.content_layout.addWidget(self.tech_title)

        tech_info = QLabel(
            "基于 PyQt6 + xArm SDK + Inspire Controller + Matplotlib + pyqtgraph"
        )
        tech_info.setWordWrap(True)
        self.content_layout.addWidget(tech_info)

        # 添加版本信息
        self.version_label = QLabel("版本: 2.0.0")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.version_label.setObjectName("versionLabel")
        self.content_layout.addWidget(self.version_label)

        # 添加内容框架到主布局
        self.main_layout.addWidget(self.content_frame)

        # 添加一个弹性空间
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
