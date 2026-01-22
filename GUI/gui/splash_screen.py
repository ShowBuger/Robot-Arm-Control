#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QColor, QPainter, QPixmap, QScreen
from PyQt6.QtWidgets import QSplashScreen, QApplication, QLabel, QVBoxLayout, QProgressBar, QFrame

class SplashScreen(QSplashScreen):
    """程序启动界面"""
    
    def __init__(self):
        # 创建基础像素图用于QSplashScreen
        try:
            # 1. 先尝试创建透明像素图
            pixmap = QPixmap(400, 400)
            if pixmap.isNull():
                raise Exception("无法创建透明像素图")
                
            # 2. 填充透明背景
            pixmap.fill(Qt.GlobalColor.transparent)
        except Exception as e:
            print(f"创建透明启动界面失败: {e}")
            try:
                # 3. 如果透明失败，尝试创建实心背景
                pixmap = QPixmap(400, 400)
                if pixmap.isNull():
                    raise Exception("无法创建像素图")
                pixmap.fill(QColor("#2D2D2D"))
            except Exception as e:
                print(f"创建启动界面像素图时严重错误: {e}")
                # 4. 最后的尝试 - 创建最小的有效像素图
                pixmap = QPixmap(1, 1)
                pixmap.fill(QColor("#000000"))
            
        # 初始化父类
        super().__init__(pixmap)
        
        # 设置窗口属性
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 避免时机问题，先创建必要的成员变量
        self._progress_value = 0
        self.progress_value_requested = 0
        self.fade_counter = 0
        self.opacity = 1.0
        self.timer = QTimer(self)
        self.progress_bar = None
        self.description_label = None
        self.app_name_label = None
        self.version_label = None
        self.main_frame = None
        
        # 创建自定义UI
        self.setup_ui()
        
        # 设置计时器更新进度
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)
        
        # 窗口居中显示
        self.center_on_screen()
        
        # 确保窗口更新
        self.update()
        
    def setup_ui(self):
        """设置UI"""
        try:
            # 创建主框架
            self.main_frame = QFrame(self)
            self.main_frame.setObjectName("SplashFrame")
            self.main_frame.setStyleSheet("""
                #SplashFrame {
                    background-color: #2D2D2D;
                    border-radius: 15px;
                }
            """)
            
            # 设置尺寸和位置
            size = 400
            self.resize(size, size)
            self.main_frame.setGeometry(0, 0, size, size)  # 将主框架设置为与窗口大小相同
            
            # 创建垂直布局
            layout = QVBoxLayout(self.main_frame)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(0)
            
            # 尝试加载应用图标 - 简化处理以减少错误
            logo_loaded = False
            try:
                # 尝试从多个可能的位置获取路径
                try:
                    # 1. 尝试从全局变量
                    from builtins import APP_ROOT_PATH
                    app_path = APP_ROOT_PATH
                except (ImportError, AttributeError):
                    try:
                        # 2. 尝试内置变量
                        if 'APP_ROOT_PATH' in globals():
                            app_path = APP_ROOT_PATH
                        else:
                            # 3. 使用相对路径
                            app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    except:
                        app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # 简单尝试几个固定路径
                potential_paths = [
                    os.path.join(app_path, "resources", "images", "logo.png"),
                    os.path.join(app_path, "resources", "images", "icon.png"),
                ]
                
                for path in potential_paths:
                    if os.path.exists(path):
                        pixmap = QPixmap(path)
                        if not pixmap.isNull():
                            logo_label = QLabel()
                            logo_label.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, 
                                                            Qt.TransformationMode.SmoothTransformation))
                            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            layout.addWidget(logo_label)
                            logo_loaded = True
                            break
            except Exception as e:
                print(f"加载图标时出错: {e}")
            
            # 如果未能加载图标，使用文字替代
            if not logo_loaded:
                title_label = QLabel("传感器数据分析系统")
                title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                title_label.setStyleSheet("font-size: 24px; color: white; font-weight: bold;")
                layout.addWidget(title_label)
                layout.addSpacing(40)
            
            # 添加空间
            layout.addStretch()
            
            # 添加应用名称标签
            self.app_name_label = QLabel("传感器数据分析系统")
            self.app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.app_name_label.setStyleSheet("font-size: 24px; color: white; font-weight: bold;")
            layout.addWidget(self.app_name_label)
            
            # 添加描述标签
            self.description_label = QLabel("正在加载系统组件...")
            self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.description_label.setStyleSheet("font-size: 14px; color: #AAA; margin-top: 10px;")
            layout.addWidget(self.description_label)
            
            # 添加进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #404040;
                    border-radius: 5px;
                    height: 10px;
                    margin-top: 15px;
                }
                QProgressBar::chunk {
                    background-color: #0078D7;
                    border-radius: 5px;
                }
            """)
            layout.addWidget(self.progress_bar)
            
            # 添加底部版本信息
            self.version_label = QLabel("V1.0")
            self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            self.version_label.setStyleSheet("font-size: 12px; color: #777; margin-top: 10px;")
            layout.addWidget(self.version_label)
        except Exception as e:
            print(f"创建界面时出错: {e}")
            # 创建备用界面
            try:
                self.main_frame = QFrame(self)
                layout = QVBoxLayout(self.main_frame)
                self.app_name_label = QLabel("系统启动中")
                self.description_label = QLabel("请稍候...")
                self.progress_bar = QProgressBar()
                layout.addWidget(self.app_name_label)
                layout.addWidget(self.description_label)
                layout.addWidget(self.progress_bar)
                self.main_frame.setGeometry(0, 0, 400, 400)
            except:
                print("无法创建备用界面")
    
    def center_on_screen(self):
        """将窗口居中显示在屏幕上"""
        # 获取当前屏幕
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
    
    def update_progress(self):
        """更新进度"""
        loading_texts = [
            "正在初始化系统...",
            "加载传感器组件...",
            "连接外部设备...",
            "准备数据分析模块...",
            "初始化图形界面...",
            "系统启动完成！"
        ]
        
        # 处理外部设置的目标进度值
        if self.progress_value_requested > self._progress_value:
            # 每次最多增加2个单位，使得进度条更新更平滑
            self._progress_value = min(self._progress_value + 2, self.progress_value_requested)
            self.progress_bar.setValue(self._progress_value)
            
            # 更新加载文本
            index = min(len(loading_texts) - 1, self._progress_value // 20)
            self.description_label.setText(loading_texts[index])
            return
        
        # 默认自动增长行为(当没有外部设置值时)
        if self._progress_value < 100:
            # 默认情况下更平缓地增加值
            self._progress_value += 1
            self.progress_bar.setValue(self._progress_value)
            
            # 更新加载文本
            index = min(len(loading_texts) - 1, self._progress_value // 20)
            self.description_label.setText(loading_texts[index])
            
        else:
            # 完成加载后停止计时器
            self.timer.stop()
    
    def paintEvent(self, event):
        """
        重写paintEvent方法，用最简单的方式绘制背景
        """
        # 如果不透明度为0，不绘制任何内容
        if self.opacity <= 0.01:
            return
            
        # 创建绘制器
        painter = QPainter(self)
        
        # 设置不透明度
        painter.setOpacity(self.opacity)
        
        # 简单绘制背景
        if self.main_frame:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2D2D2D"))
            painter.drawRoundedRect(self.main_frame.geometry(), 15, 15)
        
        # 结束绘制器
        painter.end()
    
    def showEvent(self, event):
        """
        重写showEvent，确保窗口正确显示
        """
        try:
            super().showEvent(event)
            # 确保窗口是顶层且获得焦点
            self.raise_()
            self.activateWindow()
        except Exception as e:
            print(f"显示启动界面时出错: {e}")
    
    # 添加setter属性用于从外部设置进度值
    @property
    def progress_value(self):
        return self._progress_value
        
    @progress_value.setter
    def progress_value(self, value):
        # 将请求值设为目标值，实际UI更新在update_progress中处理
        self.progress_value_requested = value
    
    def fade_out(self, new_window_or_callback):
        """
        渐变消失效果
        
        Args:
            new_window_or_callback: 可以是要显示的窗口对象，也可以是完成后调用的回调函数
        """
        try:
            # 确保进度条完成
            self.progress_value = 100
            
            # 确保已经初始化完毕
            self.progress_bar.setValue(100)
            self.description_label.setText("系统启动完成！")
            
            # 停止自动更新进度的计时器
            if self.timer.isActive():
                self.timer.stop()
                
            # 使用计时器逐渐降低透明度
            self.fade_timer = QTimer(self)
            self.fade_timer.timeout.connect(self._update_fade)
            self.fade_steps = 10  # 减少步数，加快渐变过程
            self.current_fade_step = 0
            self.fade_callback = new_window_or_callback
            self.fade_timer.start(30)  # 更短的间隔使渐变更快
        except Exception as e:
            print(f"启动渐变效果时出错: {e}")
            # 出错时直接隐藏启动界面并显示主窗口
            self.hide()
            self._safe_call_callback(new_window_or_callback)
    
    def _update_fade(self):
        """更新渐变效果"""
        try:
            self.current_fade_step += 1
            # 计算当前不透明度
            self.opacity = max(0, 1.0 - (self.current_fade_step / self.fade_steps))
            
            # 使用更简单的更新方式
            self.repaint()
            
            # 检查是否完成渐变
            if self.current_fade_step >= self.fade_steps:
                self.fade_timer.stop()
                self.finish_splash(self.fade_callback)
        except Exception as e:
            print(f"更新渐变效果时出错: {e}")
            # 出现错误时，直接结束启动画面
            self.fade_timer.stop()
            self.hide()
            self._safe_call_callback(self.fade_callback)
    
    def _safe_call_callback(self, callback):
        """安全地调用回调函数或显示窗口"""
        try:
            if callable(callback):
                callback()
            elif hasattr(callback, 'show'):
                callback.show()
        except Exception as e:
            print(f"调用回调时出错: {e}")
    
    def finish_splash(self, new_window_or_callback):
        """
        结束启动界面，显示主窗口或执行回调
        
        Args:
            new_window_or_callback: 可以是要显示的窗口对象，也可以是完成后调用的回调函数
        """
        try:
            # 首先隐藏启动画面
            self.hide()
            
            # 确保所有挂起的绘制操作完成
            QApplication.processEvents()
            
            # 使用安全的方法调用回调
            self._safe_call_callback(new_window_or_callback)
        except Exception as e:
            print(f"结束启动界面时出错: {e}")
            # 确保错误不会阻止主窗口显示
            self._safe_call_callback(new_window_or_callback) 