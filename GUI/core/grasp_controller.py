#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from core.sensor_data_manager import SensorDataManager


class GraspController(QObject):
    """抓取控制器，负责控制机械手抓取物体并判定抓取状态"""

    # 定义信号
    grasp_status_changed = pyqtSignal(bool)  # 抓取状态变化信号
    force_threshold_changed = pyqtSignal(float)  # 力阈值变化信号

    def __init__(self, sensor_data_manager: SensorDataManager):
        super().__init__()
        
        self.sensor_data_manager = sensor_data_manager
        
        # 抓取参数
        self.force_threshold = 2.0  # 抓取力阈值（N）
        self.stable_time = 0.5  # 稳定时间（s）
        self.sample_rate = 100  # 采样率（Hz）
        
        # 抓取状态
        self.is_grasping = False
        self.grasp_start_time = 0
        self.stable_samples = 0
        self.required_stable_samples = int(self.stable_time * self.sample_rate)
        
        # 数据缓冲区
        self.force_buffer = []
        self.buffer_size = 10  # 缓冲区大小
        
        # 连接信号
        self.sensor_data_manager.data_updated_signal.connect(self.on_sensor_data_updated)

    def set_force_threshold(self, threshold: float):
        """设置抓取力阈值"""
        self.force_threshold = threshold
        self.force_threshold_changed.emit(threshold)

    def set_stable_time(self, time: float):
        """设置稳定时间"""
        self.stable_time = time
        self.required_stable_samples = int(time * self.sample_rate)

    def on_sensor_data_updated(self, sensor_id: int, values: list):
        """处理传感器数据更新"""
        if not self.is_grasping:
            return
            
        # 计算合力大小
        force = np.sqrt(sum(x**2 for x in values))
        
        # 更新缓冲区
        self.force_buffer.append(force)
        if len(self.force_buffer) > self.buffer_size:
            self.force_buffer.pop(0)
            
        # 计算平均力
        avg_force = np.mean(self.force_buffer)
        
        # 判定抓取状态
        if avg_force >= self.force_threshold:
            self.stable_samples += 1
            if self.stable_samples >= self.required_stable_samples:
                self.grasp_status_changed.emit(True)  # 抓取成功
        else:
            self.stable_samples = 0
            self.grasp_status_changed.emit(False)  # 抓取失败

    def start_grasp(self):
        """开始抓取"""
        self.is_grasping = True
        self.stable_samples = 0
        self.force_buffer.clear()
        self.grasp_status_changed.emit(False)

    def stop_grasp(self):
        """停止抓取"""
        self.is_grasping = False
        self.stable_samples = 0
        self.force_buffer.clear()
        self.grasp_status_changed.emit(False)

    def get_grasp_status(self) -> bool:
        """获取当前抓取状态"""
        return self.is_grasping and self.stable_samples >= self.required_stable_samples

    def get_current_force(self) -> float:
        """获取当前力值"""
        if not self.force_buffer:
            return 0.0
        return np.mean(self.force_buffer) 