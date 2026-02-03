#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPixmap, QScreen
from PyQt6.QtWidgets import QWidget, QApplication, QLabel

class SplashScreen(QWidget):
    """程序启动界面 - 只显示logo"""

    def __init__(self, duration=3000):
        super().__init__()

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                          Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 设置窗口大小
        self.setFixedSize(300, 200)

        # 创建logo标签
        self.logo_label = QLabel(self)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 获取资源路径
        try:
            from builtins import APP_ROOT_PATH
            app_path = APP_ROOT_PATH
        except (ImportError, AttributeError):
            app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 在打包环境中，资源文件位于临时目录中
        if getattr(sys, 'frozen', False):
            # PyInstaller打包环境
            if hasattr(sys, '_MEIPASS'):
                app_path = sys._MEIPASS
            else:
                # 备用方案：可执行文件所在目录
                app_path = os.path.dirname(sys.executable)

        # 尝试加载logo图片
        logo_path = os.path.join(app_path, "resources", "images", "logo.png")
        icon_path = os.path.join(app_path, "resources", "images", "icon.png")

        if os.path.exists(logo_path):
            self.original_pixmap = QPixmap(logo_path)
            # 缩放图片
            scaled_pixmap = self.original_pixmap.scaled(250, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                                      Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            self.logo_label.setGeometry(25, 20, 250, 160)

            # 设置窗口图标
            if os.path.exists(icon_path):
                from PyQt6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
        else:
            # 如果找不到logo，使用文本替代
            self.logo_label.setText("机械臂控制系统")
            self.logo_label.setGeometry(25, 75, 250, 50)
            self.logo_label.setStyleSheet("font-size: 24px; color: white; font-weight: bold;")

        # 设置初始透明样式
        self.logo_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: rgba(255, 255, 255, 0);
            }
        """)

        # 初始化动画属性
        self._opacity = 0.0

        # 创建淡入动画
        self.fade_in_animation = QPropertyAnimation(self, b"opacity")
        self.fade_in_animation.setDuration(1000)  # 1秒淡入
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # 创建淡出动画
        self.fade_out_animation = QPropertyAnimation(self, b"opacity")
        self.fade_out_animation.setDuration(800)  # 0.8秒淡出
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_out_animation.finished.connect(self.close)

        # 设置定时器
        self.duration = duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.start_fade_out)
        self.timer.setSingleShot(True)

        # 窗口居中显示
        self.center_on_screen()
        
    @pyqtProperty(float)
    def opacity(self):
        """获取透明度"""
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        """设置透明度"""
        self._opacity = value
        # 直接设置logo标签的透明度
        if hasattr(self, 'logo_label'):
            # 创建半透明效果的样式
            opacity_value = int(self._opacity * 255)
            if opacity_value < 0:
                opacity_value = 0
            elif opacity_value > 255:
                opacity_value = 255

            # 设置标签的透明度样式
            self.logo_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: rgba(255, 255, 255, {opacity_value});
                }}
            """)
            self.logo_label.update()
    
    def paintEvent(self, event):
        """自定义绘制事件 - 完全透明背景"""
        # 不绘制任何背景，让logo自己处理透明度
        pass

    def showEvent(self, event):
        """显示事件，开始淡入动画"""
        super().showEvent(event)
        self.fade_in_animation.start()
        self.timer.start(self.duration)

    def start_fade_out(self):
        """开始淡出动画"""
        self.fade_out_animation.start()

    def close_immediately(self):
        """立即关闭启动画面"""
        self.timer.stop()
        self.fade_in_animation.stop()
        self.fade_out_animation.stop()
        self.close()

    def center_on_screen(self):
        """将窗口居中显示在屏幕上"""
        screen = QApplication.primaryScreen()
        if not screen:
            return

        # 获取屏幕几何信息
        screen_geometry = screen.availableGeometry()

        # 计算窗口位置使其居中
        window_size = self.size()
        x = (screen_geometry.width() - window_size.width()) // 2
        y = (screen_geometry.height() - window_size.height()) // 2

        # 设置窗口位置
        self.move(x, y) 