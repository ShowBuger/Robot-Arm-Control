#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication
# 导入应用设置
from core.app_settings import Settings
import logging
import datetime
import time
from typing import List
from serial import Serial


# 确保可以找到资源文件
if getattr(sys, 'frozen', False):
    # 如果应用被打包
    APP_ROOT_PATH = os.path.dirname(sys.executable)
else:
    # 如果在开发环境中运行
    APP_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# 将APP_ROOT_PATH添加到全局作用域，以便其他模块可以导入
import builtins
builtins.APP_ROOT_PATH = APP_ROOT_PATH

# 创建日志目录
logs_dir = os.path.join(APP_ROOT_PATH, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 生成日志文件名
log_filename = os.path.join(logs_dir, f"debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 创建自定义日志过滤器，屏蔽特定错误
class ErrorFilter(logging.Filter):
    """自定义日志过滤器，用于屏蔽特定的非关键错误信息"""
    
    def filter(self, record):
        # 过滤掉包含'int' object is not subscriptable的错误信息
        if hasattr(record, 'msg') and record.msg:
            msg_str = str(record.msg)
            if "'int' object is not subscriptable" in msg_str:
                return False  # 不记录这类错误
        return True  # 记录其他所有信息

# 创建过滤器实例
error_filter = ErrorFilter()

# 配置日志系统
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

# 为所有日志处理器添加过滤器
for handler in logging.getLogger().handlers:
    handler.addFilter(error_filter)

# 创建根日志记录器
root_logger = logging.getLogger()
root_logger.info(f"应用程序启动，日志文件: {log_filename}")
print(f"日志文件路径: {log_filename}")

# 自定义异常钩子，过滤特定错误
def custom_excepthook(exc_type, exc_value, exc_traceback):
    """自定义异常钩子，用于过滤特定的错误信息"""
    error_message = str(exc_value)
    
    # 如果是我们要过滤的错误，就静默处理
    if "'int' object is not subscriptable" in error_message:
        # 只在调试模式下记录
        root_logger.debug(f"已过滤的非关键错误: {exc_type.__name__}: {error_message}")
        return
    
    # 其他错误正常处理
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# 设置自定义异常钩子
sys.excepthook = custom_excepthook

# 应用程序主入口
if __name__ == "__main__":
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性，确保QPainter正常工作
    # PyQt6 中属性名称可能与 PyQt5 不同
    try:
        # 尝试直接设置一些常见的高 DPI 相关属性
        common_attrs = [
            "AA_UseHighDpiPixmaps",
            "AA_EnableHighDpiScaling",
            "AA_DontCreateNativeWidgetSiblings"
        ]
        
        # 尝试直接设置这些常见属性
        for attr_name in common_attrs:
            try:
                if hasattr(Qt.ApplicationAttribute, attr_name):
                    attr = getattr(Qt.ApplicationAttribute, attr_name)
                    app.setAttribute(attr, True)
            except Exception as e:
                print(f"设置属性 {attr_name} 时出错: {e}")
        
        # 备份方法：动态查找其他高 DPI 相关属性
        try:
            # 使用反射获取所有应用程序属性
            aa_map = {name: getattr(Qt.ApplicationAttribute, name) 
                     for name in dir(Qt.ApplicationAttribute) 
                     if not name.startswith('_')}
            
            # 找出所有包含 HighDpi 字样的属性
            high_dpi_attrs = [attr for name, attr in aa_map.items() 
                             if ('HighDpi' in name or 'highdpi' in name.lower())
                             and name not in common_attrs]
            
            # 应用这些属性
            for attr in high_dpi_attrs:
                app.setAttribute(attr, True)
                print(f"动态启用属性: {attr}")
        except Exception as e:
            print(f"动态设置高 DPI 属性时出错: {e}")
    except Exception as e:
        print(f"设置应用程序属性时出错: {e}")
    
    # 在显示启动画面前先处理所有事件，确保Qt环境准备好
    app.processEvents()

    # 创建应用设置（轻量级，可以在主线程中初始化）
    settings = Settings()
    settings.load_settings()
    
    try:
        # 延迟导入启动画面和主窗口，确保APP_ROOT_PATH已设置
        from gui.splash_screen import SplashScreen
        from gui.main_window import MainWindow
        
        # 创建启动界面并立即显示
        splash = SplashScreen()
        splash.show()
        
        # 再次强制处理事件，确保启动界面立即显示
        app.processEvents()

        # 创建主窗口但不立即完全初始化和显示
        window = MainWindow(initialize_immediately=False)
        
        # 逐步初始化主窗口组件
        def init_step_1():
            try:
                # 初始化基础组件（UI相关）
                window.initialize_ui_components()
                # 继续下一步初始化
                QTimer.singleShot(100, init_step_2)
                splash.progress_value = 30
                app.processEvents()  # 确保更新界面
            except Exception as e:
                print(f"初始化UI组件时出错: {e}")
                continue_initialization()
        
        def init_step_2():
            try:
                # 初始化数据管理组件
                window.initialize_data_manager()
                # 继续下一步初始化
                QTimer.singleShot(100, init_step_3)
                splash.progress_value = 60
                app.processEvents()  # 确保更新界面
            except Exception as e:
                print(f"初始化数据管理组件时出错: {e}")
                continue_initialization()
        
        def init_step_3():
            try:
                # 初始化硬件控制组件（串口、机械臂等）
                window.initialize_hardware_components()
                # 完成初始化
                QTimer.singleShot(100, finish_init)
                splash.progress_value = 90
                app.processEvents()  # 确保更新界面
            except Exception as e:
                print(f"初始化硬件组件时出错: {e}")
                continue_initialization()
        
        def continue_initialization():
            """出错时跳过当前初始化步骤，继续后续步骤"""
            QTimer.singleShot(100, finish_init)
            
        def finish_init():
            try:
                # 完成所有初始化
                window.finalize_initialization()
                splash.progress_value = 100
                app.processEvents()  # 确保更新界面
                
                # 检查日志设置并启动记录
                try:
                    logging_settings = settings.get_setting("logging")
                    if logging_settings and logging_settings.get("enabled", False):
                        if hasattr(window, "data_logger"):
                            window.data_logger.start_logging()
                except Exception as log_error:
                    print(f"启动日志记录时出错: {log_error}")
                
                # 设置主窗口全屏并置顶显示
                def show_fullscreen_window():
                    try:
                        # 使用专门为此创建的maximize_and_raise方法
                        window.maximize_and_raise()
                    except Exception as e:
                        print(f"显示主窗口时出错: {e}")
                        # 出错时尝试使用基本的show方法
                        window.show()
                

                
                # 设置短延时后显示主窗口
                QTimer.singleShot(200, lambda: splash.fade_out(show_fullscreen_window))
                
            except Exception as e:
                print(f"完成初始化时出错: {e}")
                # 即使出错也要尝试显示主窗口
                try:
                    splash.progress_value = 100
                    app.processEvents()
                    
                    # 尝试直接显示主窗口
                    def show_window_fallback():
                        try:
                            window.show()
                            splash.hide()
                        except Exception as show_error:
                            print(f"fallback显示窗口时出错: {show_error}")
                            # 最后的保险：直接隐藏启动画面
                            try:
                                splash.hide()
                            except:
                                pass
                    
                    QTimer.singleShot(200, show_window_fallback)
                    
                except Exception as fallback_error:
                    print(f"fallback处理时出错: {fallback_error}")
                    # 最终保险：直接显示主窗口并隐藏启动画面
                    window.show()
                    try:
                        splash.hide()
                    except:
                        pass

        # 开始初始化过程，短延时确保启动画面已正确显示
        QTimer.singleShot(200, init_step_1)
    
    except Exception as e:
        print(f"启动程序时出错: {e}")
        # 出错时，跳过启动画面，直接启动主程序
        from gui.main_window import MainWindow
        window = MainWindow()
        window.show()
    
    # 执行应用程序
    sys.exit(app.exec())