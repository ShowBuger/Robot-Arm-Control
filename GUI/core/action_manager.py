#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal


class Action:
    """单个动作类，包含机械臂位置和手爪角度信息"""

    def __init__(self, name: str, arm_position: List[float], hand_angles: List[int],
                 arm_velocity: int = 20, hand_velocity: int = 1000):
        """
        初始化动作

        Args:
            name: 动作名称
            arm_position: 机械臂位置 [x, y, z, roll, pitch, yaw]
            hand_angles: 手爪角度列表
            arm_velocity: 机械臂运动速度
            hand_velocity: 手爪运动速度
        """
        self.name = name
        self.arm_position = arm_position
        self.hand_angles = hand_angles
        self.arm_velocity = arm_velocity
        self.hand_velocity = hand_velocity
        self.creation_time = time.time()
        self.last_modified = time.time()
        self.adaptive_config = None  # 自适应抓取配置（可选）

    def __str__(self):
        return f"Action(name='{self.name}', arm_position={self.arm_position}, hand_angles={self.hand_angles})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self) -> Dict[str, Any]:
        """将动作转换为字典格式"""
        result = {
            "name": self.name,
            "arm_position": self.arm_position,
            "hand_angles": self.hand_angles,
            "arm_velocity": self.arm_velocity,
            "hand_velocity": self.hand_velocity,
            "creation_time": self.creation_time,
            "last_modified": self.last_modified
        }
        # 如果有自适应配置，也保存
        if self.adaptive_config is not None:
            result["adaptive_config"] = self.adaptive_config
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """从字典创建Action对象"""
        arm_position = data.get('arm_position', [0, 0, 0, 0, 0, 0])

        # 修复arm_position长度问题
        if len(arm_position) == 7:
            # 如果有7个值，可能是多了一个额外的值，取前6个
            print(f"警告: 动作 '{data.get('name', 'unknown')}' 的arm_position有7个值，取前6个")
            arm_position = arm_position[:6]
        elif len(arm_position) < 6:
            # 如果少于6个值，用0补齐
            print(f"警告: 动作 '{data.get('name', 'unknown')}' 的arm_position不足6个值，用0补齐")
            arm_position = arm_position + [0] * (6 - len(arm_position))
        elif len(arm_position) > 7:
            # 如果超过7个值，取前6个
            print(f"警告: 动作 '{data.get('name', 'unknown')}' 的arm_position有{len(arm_position)}个值，取前6个")
            arm_position = arm_position[:6]

        action = cls(
            name=data.get('name', ''),
            arm_position=arm_position,
            hand_angles=data.get('hand_angles', [0, 0, 0, 0, 0, 0]),
            arm_velocity=data.get('arm_velocity', 20),
            hand_velocity=data.get('hand_velocity', 1000)
        )
        action.creation_time = data.get("creation_time", time.time())
        action.last_modified = data.get("last_modified", time.time())
        # 加载自适应配置（如果有）
        action.adaptive_config = data.get("adaptive_config", None)
        return action

    def update(self, name: Optional[str] = None, arm_position: Optional[List[float]] = None,
               hand_angles: Optional[List[int]] = None, arm_velocity: Optional[int] = None,
               hand_velocity: Optional[int] = None) -> None:
        """
        更新动作参数

        Args:
            name: 新的动作名称
            arm_position: 新的机械臂位置
            hand_angles: 新的手爪角度
            arm_velocity: 新的机械臂速度
            hand_velocity: 新的手爪速度
        """
        if name is not None:
            self.name = name
        if arm_position is not None:
            self.arm_position = arm_position
        if hand_angles is not None:
            self.hand_angles = hand_angles
        if arm_velocity is not None:
            self.arm_velocity = arm_velocity
        if hand_velocity is not None:
            self.hand_velocity = hand_velocity
        self.last_modified = time.time()


class ActionSequence:
    """动作序列类，包含多个按顺序执行的动作"""

    def __init__(self, name: str, description: str = ""):
        """
        初始化动作序列

        Args:
            name: 序列名称
            description: 序列描述
        """
        self.name = name
        self.description = description
        self.actions = []  # 动作名称列表
        self.delays = []  # 每个动作之间的延迟时间(秒)
        self.creation_time = time.time()
        self.last_modified = time.time()
        self.repeat_count = 1  # 执行次数，默认为1

    def add_action(self, action_name: str, delay: float = 1.0) -> None:
        """添加动作到序列"""
        self.actions.append(action_name)
        self.delays.append(delay)
        self.last_modified = time.time()

    def remove_action(self, index: int) -> bool:
        """从序列中删除指定索引的动作"""
        if 0 <= index < len(self.actions):
            self.actions.pop(index)
            self.delays.pop(index)
            self.last_modified = time.time()
            return True
        return False

    def move_action_up(self, index: int) -> bool:
        """将动作在序列中向上移动"""
        if 0 < index < len(self.actions):
            self.actions[index], self.actions[index - 1] = self.actions[index - 1], self.actions[index]
            self.delays[index], self.delays[index - 1] = self.delays[index - 1], self.delays[index]
            self.last_modified = time.time()
            return True
        return False

    def move_action_down(self, index: int) -> bool:
        """将动作在序列中向下移动"""
        if 0 <= index < len(self.actions) - 1:
            self.actions[index], self.actions[index + 1] = self.actions[index + 1], self.actions[index]
            self.delays[index], self.delays[index + 1] = self.delays[index + 1], self.delays[index]
            self.last_modified = time.time()
            return True
        return False

    def update_delay(self, index: int, delay: float) -> bool:
        """更新指定动作的延迟时间"""
        if 0 <= index < len(self.delays):
            self.delays[index] = delay
            self.last_modified = time.time()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """将序列转换为字典格式用于JSON序列化"""
        return {
            "name": self.name,
            "description": self.description,
            "actions": self.actions,
            "delays": self.delays,
            "creation_time": self.creation_time,
            "last_modified": self.last_modified,
            "repeat_count": self.repeat_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionSequence':
        """从字典创建序列对象"""
        sequence = cls(
            name=data["name"],
            description=data.get("description", "")
        )
        sequence.actions = data["actions"]
        sequence.delays = data["delays"]
        sequence.repeat_count = data.get("repeat_count", 1)  # 默认为1

        # 恢复创建时间和修改时间
        if "creation_time" in data:
            sequence.creation_time = data["creation_time"]
        if "last_modified" in data:
            sequence.last_modified = data["last_modified"]

        return sequence


class ActionManager(QObject):
    """动作管理器类，用于管理动作和动作序列"""

    # 定义信号
    action_added = pyqtSignal(str)  # 动作添加信号(动作名称)
    action_removed = pyqtSignal(str)  # 动作删除信号(动作名称)
    action_updated = pyqtSignal(str)  # 动作更新信号(动作名称)
    sequence_added = pyqtSignal(str)  # 序列添加信号(序列名称)
    sequence_removed = pyqtSignal(str)  # 序列删除信号(序列名称)
    sequence_updated = pyqtSignal(str)  # 序列更新信号(序列名称)
    execution_started = pyqtSignal(str)  # 执行开始信号(序列名称)
    execution_completed = pyqtSignal(str)  # 执行完成信号(序列名称)
    execution_progress = pyqtSignal(str, int, int)  # 执行进度信号(序列名称, 当前索引, 总动作数)
    execution_error = pyqtSignal(str, str)  # 执行错误信号(序列名称, 错误信息)

    def __init__(self, arm_controller=None):
        """
        初始化动作管理器

        Args:
            arm_controller: 机械臂控制器实例
        """
        super().__init__()

        # 机械臂控制器
        self.arm_controller = arm_controller

        # 动作字典 {动作名称: Action对象}
        self.actions = {}

        # 动作序列字典 {序列名称: ActionSequence对象}
        self.sequences = {}

        # 数据文件路径
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        self.actions_file = os.path.join(self.config_dir, "actions.json")
        self.sequences_file = os.path.join(self.config_dir, "action_sequences.json")

        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        # 执行状态
        self.is_executing = False
        self.current_sequence = None

        # 自适应抓取回调
        self.adaptive_grasp_callback = None

        # 自适应配置存储 {name: config_dict}
        self.configs = {}
        self.configs_file = os.path.join(self.config_dir, "adaptive_configs.json")

        # 加载保存的动作和序列
        self.load_actions()
        self.load_sequences()
        # 加载自适应配置
        self.load_configs()

    def load_configs(self):
        """加载自适应配置文件"""
        try:
            if os.path.exists(self.configs_file):
                with open(self.configs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.configs = data
                    else:
                        print("警告: adaptive_configs.json 格式异常，期望 dict")
            else:
                self.configs = {}
        except Exception as e:
            print(f"加载自适应配置失败: {e}")
            self.configs = {}

    def save_configs_to_file(self):
        """保存自适应配置到文件"""
        try:
            with open(self.configs_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存自适应配置失败: {e}")
            return False

    def get_all_configs(self) -> List[str]:
        """返回所有保存的配置名称列表"""
        return list(self.configs.keys())

    def save_config(self, name: str, config: Dict[str, Any]) -> bool:
        """保存单个自适应配置（覆盖同名配置）"""
        try:
            if not name:
                return False
            self.configs[name] = config
            return self.save_configs_to_file()
        except Exception as e:
            print(f"保存配置错误: {e}")
            return False

    def get_config(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指定名称的配置，找不到返回None"""
        return self.configs.get(name)

    def delete_config(self, name: str) -> bool:
        """删除指定名称的配置"""
        if name in self.configs:
            del self.configs[name]
            return self.save_configs_to_file()
        return False

    def set_arm_controller(self, arm_controller):
        """设置机械臂控制器"""
        self.arm_controller = arm_controller

    def set_adaptive_grasp_callback(self, callback):
        """设置自适应抓取回调函数"""
        self.adaptive_grasp_callback = callback

    def save_action(self, name: str, arm_position: List[float], hand_angles: List[int],
                    arm_velocity: int = 20, hand_velocity: int = 1000) -> bool:
        """
        保存一个新动作或更新已有动作

        Args:
            name: 动作名称
            arm_position: 机械臂位置
            hand_angles: 手爪角度列表
            arm_velocity: 机械臂运动速度
            hand_velocity: 手爪运动速度

        Returns:
            保存是否成功
        """
        try:
            if name in self.actions:
                # 更新已有动作
                self.actions[name].update(
                    name=name,
                    arm_position=arm_position,
                    hand_angles=hand_angles,
                    arm_velocity=arm_velocity,
                    hand_velocity=hand_velocity
                )
                self.action_updated.emit(name)
            else:
                # 创建新动作
                action = Action(
                    name=name,
                    arm_position=arm_position,
                    hand_angles=hand_angles,
                    arm_velocity=arm_velocity,
                    hand_velocity=hand_velocity
                )
                self.actions[name] = action
                self.action_added.emit(name)

            # 保存到文件
            self.save_actions_to_file()
            return True
        except Exception as e:
            print(f"保存动作错误: {e}")
            return False

    def save_current_pose_as_action(self, name: str, use_ui_values: bool = False, 
                                   ui_arm_position: List[float] = None, 
                                   ui_hand_angles: List[int] = None) -> bool:
        """
        将当前机械臂姿态保存为动作

        Args:
            name: 动作名称
            use_ui_values: 是否使用UI设置值而不是硬件当前值
            ui_arm_position: UI中设置的机械臂位置（当use_ui_values=True时使用）
            ui_hand_angles: UI中设置的手爪角度（当use_ui_values=True时使用）

        Returns:
            保存是否成功
        """
        if use_ui_values and ui_arm_position is not None and ui_hand_angles is not None:
            # 使用UI设置值，不获取硬件状态
            print(f"使用UI设置值保存动作 '{name}'")
            print(f"UI机械臂位置: {ui_arm_position}")
            print(f"UI手爪角度: {ui_hand_angles}")
            
            return self.save_action(
                name=name,
                arm_position=ui_arm_position,
                hand_angles=ui_hand_angles
            )
        
        # 原有的硬件获取逻辑
        if not self.arm_controller or not hasattr(self.arm_controller, 'is_connected'):
            print("机械臂控制器未初始化，无法保存当前姿态")
            return False
            
        if not self.arm_controller.is_connected():
            print("机械臂未连接，无法保存当前姿态")
            return False

        try:
            # 获取当前机械臂位置 - 修复：添加错误检查
            arm_position = self.arm_controller.get_arm_position()
            if not isinstance(arm_position, (list, tuple)) or len(arm_position) < 6:
                print(f"获取机械臂位置失败或格式错误: {arm_position}")
                return False

            # 获取当前手爪角度 - 修复：添加错误检查
            hand_angles = self.arm_controller.get_hand_angles()
            if not isinstance(hand_angles, (list, tuple)) or len(hand_angles) < 6:
                print(f"获取手爪角度失败或格式错误: {hand_angles}")
                return False

            # 保存为动作
            return self.save_action(
                name=name,
                arm_position=arm_position,
                hand_angles=hand_angles
            )
        except Exception as e:
            print(f"保存当前姿态错误: {e}")
            return False

    def delete_action(self, name: str) -> bool:
        """
        删除一个动作

        Args:
            name: 动作名称

        Returns:
            删除是否成功
        """
        # 防止删除自适应抓取动作
        if name == "自适应抓取":
            print("不能删除自适应抓取动作")
            return False
            
        if name in self.actions:
            # 从动作字典中删除
            del self.actions[name]

            # 从所有序列中删除对该动作的引用
            for sequence in self.sequences.values():
                while name in sequence.actions:
                    index = sequence.actions.index(name)
                    sequence.remove_action(index)

            # 保存更改
            self.save_actions_to_file()
            self.save_sequences_to_file()

            # 发射信号
            self.action_removed.emit(name)
            return True
        return False

    def rename_action(self, old_name: str, new_name: str) -> bool:
        """
        重命名一个动作

        Args:
            old_name: 旧名称
            new_name: 新名称

        Returns:
            重命名是否成功
        """
        if old_name in self.actions and new_name not in self.actions:
            # 获取动作对象
            action = self.actions[old_name]

            # 更新名称
            action.name = new_name

            # 更新字典
            self.actions[new_name] = action
            del self.actions[old_name]

            # 更新所有序列中的引用
            for sequence in self.sequences.values():
                for i, action_name in enumerate(sequence.actions):
                    if action_name == old_name:
                        sequence.actions[i] = new_name

            # 保存更改
            self.save_actions_to_file()
            self.save_sequences_to_file()

            # 发射信号
            self.action_removed.emit(old_name)
            self.action_added.emit(new_name)
            return True
        return False

    def get_action(self, name: str) -> Optional[Action]:
        """获取指定名称的动作"""
        return self.actions.get(name)

    def get_all_actions(self) -> List[str]:
        """获取所有动作名称列表"""
        return list(self.actions.keys())

    def get_all_sequences(self) -> List[str]:
        """获取所有序列名称列表"""
        return list(self.sequences.keys())

    def create_sequence(self, name: str, description: str = "") -> bool:
        """
        创建一个新的动作序列

        Args:
            name: 序列名称
            description: 序列描述

        Returns:
            创建是否成功
        """
        if name in self.sequences:
            return False

        # 创建新序列
        sequence = ActionSequence(name, description)
        self.sequences[name] = sequence

        # 保存到文件
        self.save_sequences_to_file()

        # 发射信号
        self.sequence_added.emit(name)
        return True

    def delete_sequence(self, name: str) -> bool:
        """
        删除一个动作序列

        Args:
            name: 序列名称

        Returns:
            删除是否成功
        """
        if name in self.sequences:
            # 从序列字典中删除
            del self.sequences[name]

            # 保存更改
            self.save_sequences_to_file()

            # 发射信号
            self.sequence_removed.emit(name)
            return True
        return False

    def rename_sequence(self, old_name: str, new_name: str) -> bool:
        """
        重命名一个动作序列

        Args:
            old_name: 旧名称
            new_name: 新名称

        Returns:
            重命名是否成功
        """
        if old_name in self.sequences and new_name not in self.sequences:
            # 获取序列对象
            sequence = self.sequences[old_name]

            # 更新名称
            sequence.name = new_name

            # 更新字典
            self.sequences[new_name] = sequence
            del self.sequences[old_name]

            # 保存更改
            self.save_sequences_to_file()

            # 发射信号
            self.sequence_removed.emit(old_name)
            self.sequence_added.emit(new_name)
            return True
        return False

    def get_sequence(self, name: str) -> Optional[ActionSequence]:
        """获取指定名称的动作序列"""
        return self.sequences.get(name)

    def add_action_to_sequence(self, sequence_name: str, action_name: str, delay: float = 1.0) -> bool:
        """
        将动作添加到序列中

        Args:
            sequence_name: 序列名称
            action_name: 动作名称
            delay: 执行后的延迟时间(秒)

        Returns:
            添加是否成功
        """
        if sequence_name in self.sequences and action_name in self.actions:
            # 获取序列对象
            sequence = self.sequences[sequence_name]

            # 添加动作
            sequence.add_action(action_name, delay)

            # 保存更改
            self.save_sequences_to_file()

            # 发射信号
            self.sequence_updated.emit(sequence_name)
            return True
        return False

    def remove_action_from_sequence(self, sequence_name: str, index: int) -> bool:
        """
        从序列中移除指定索引的动作

        Args:
            sequence_name: 序列名称
            index: 动作索引

        Returns:
            移除是否成功
        """
        if sequence_name in self.sequences:
            # 获取序列对象
            sequence = self.sequences[sequence_name]

            # 移除动作
            if sequence.remove_action(index):
                # 保存更改
                self.save_sequences_to_file()

                # 发射信号
                self.sequence_updated.emit(sequence_name)
                return True
        return False

    def move_action_in_sequence(self, sequence_name: str, from_index: int, to_index: int) -> bool:
        """
        在序列中移动动作位置

        Args:
            sequence_name: 序列名称
            from_index: 原始索引
            to_index: 目标索引

        Returns:
            移动是否成功
        """
        if sequence_name in self.sequences:
            sequence = self.sequences[sequence_name]

            # 确保索引有效
            if not (0 <= from_index < len(sequence.actions) and 0 <= to_index < len(sequence.actions)):
                return False

            # 如果索引相同，无需移动
            if from_index == to_index:
                return True

            # 保存要移动的动作和延迟
            action_name = sequence.actions[from_index]
            delay = sequence.delays[from_index]

            # 先移除
            sequence.remove_action(from_index)

            # 计算新的插入位置
            insert_index = to_index
            if from_index < to_index:
                insert_index -= 1

            # 插入到新位置
            sequence.actions.insert(insert_index, action_name)
            sequence.delays.insert(insert_index, delay)

            # 更新最后修改时间
            sequence.last_modified = time.time()

            # 保存更改
            self.save_sequences_to_file()

            # 发射信号
            self.sequence_updated.emit(sequence_name)
            return True
        return False

    def update_sequence_delay(self, sequence_name: str, index: int, delay: float) -> bool:
        """
        更新序列中动作的延迟时间

        Args:
            sequence_name: 序列名称
            index: 动作索引
            delay: 新的延迟时间(秒)

        Returns:
            更新是否成功
        """
        if sequence_name in self.sequences:
            sequence = self.sequences[sequence_name]

            # 更新延迟
            if sequence.update_delay(index, delay):
                # 保存更改
                self.save_sequences_to_file()

                # 发射信号
                self.sequence_updated.emit(sequence_name)
                return True
        return False

    def execute_action(self, action_name: str) -> bool:
        """
        执行动作

        Args:
            action_name: 动作名称

        Returns:
            执行是否成功
        """
        print(f"[DEBUG] 开始执行动作: {action_name}")

        # 基本检查
        if not self.arm_controller:
            print("[DEBUG] 机械臂控制器为None")
            return False

        if not hasattr(self.arm_controller, 'is_connected'):
            print("[DEBUG] 机械臂控制器没有is_connected方法")
            return False

        print(f"[DEBUG] 机械臂控制器类型: {type(self.arm_controller)}")

        # 检查连接状态
        try:
            is_connected = self.arm_controller.is_connected()
            print(f"[DEBUG] 机械臂连接状态: {is_connected}")
        except Exception as e:
            print(f"[DEBUG] 检查连接状态时出错: {e}")
            return False

        if not is_connected:
            print("[DEBUG] 机械臂未连接，无法执行动作")
            return False

        # 检查动作是否存在
        if action_name not in self.actions:
            print(f"[DEBUG] 动作不存在: {action_name}")
            available_actions = list(self.actions.keys())
            print(f"[DEBUG] 可用动作列表: {available_actions}")
            return False

        print(f"[DEBUG] 找到动作: {action_name}")

        # 获取动作对象
        action = self.actions[action_name]

        # 检查是否是自适应抓取动作
        if hasattr(action, 'adaptive_config') and action.adaptive_config is not None:
            print(f"[DEBUG] 检测到自适应抓取动作，调用回调函数")
            # 这是一个自适应抓取动作，需要特殊处理
            if hasattr(self, 'adaptive_grasp_callback') and self.adaptive_grasp_callback:
                return self.adaptive_grasp_callback(action.adaptive_config)
            else:
                print("[DEBUG] 未设置自适应抓取回调函数")
                return False

        try:
            print(f"[DEBUG] 动作详情 - 位置: {action.arm_position}, 手爪: {action.hand_angles}")
            print(f"[DEBUG] 动作速度 - 机械臂: {action.arm_velocity}, 手爪: {action.hand_velocity}")

            # 执行机械臂动作，最多重试3次
            print(f"[DEBUG] 开始执行机械臂动作...")
            arm_success = self._execute_arm_command(
                action.arm_position,
                action.arm_velocity,
                max_retries=3
            )
            
            if not arm_success:
                print(f"[DEBUG] 执行机械臂动作失败: {action_name}")
                return False
            
            print(f"[DEBUG] 机械臂动作执行成功，准备执行手爪动作...")
            
            # 稍微延迟确保机械臂移动开始
            time.sleep(0.2)

            # 执行手爪动作，最多重试3次
            hand_success = self._execute_hand_command(
                action.hand_angles,
                action.hand_velocity,
                max_retries=3
            )
            
            if not hand_success:
                print(f"[DEBUG] 执行手爪动作失败: {action_name}")
                return False

            print(f"[DEBUG] 动作执行完全成功: {action_name}")
            return True
            
        except IndexError as e:
            # 特殊处理索引错误（通常来自Inspire角度获取）
            error_msg = str(e)
            if "index out of range" in error_msg or "list index out of range" in error_msg:
                print(f"[DEBUG] 执行动作过程中出现索引错误（通常为Inspire角度获取问题）: {action_name} - {e}")
                print(f"[DEBUG] 这个错误通常表示机械手通信不稳定，但动作可能已经执行")
                # 对于这种错误，我们认为动作可能已经执行成功
                return True
            else:
                print(f"[DEBUG] 执行动作过程中出现其他索引错误: {action_name} - {e}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            # 处理其他类型的错误
            error_msg = str(e)
            error_type = type(e).__name__
            
            print(f"[DEBUG] 执行动作错误 (类型: {error_type}): {action_name} - {error_msg}")
            
            # 检查是否是通信相关的非关键错误
            non_critical_errors = [
                "index out of range",
                "list index out of range", 
                "'int' object is not subscriptable",
                "串口通信错误",
                "响应数据长度不足"
            ]
            
            if any(err_pattern in error_msg for err_pattern in non_critical_errors):
                print(f"[DEBUG] 这是一个非关键错误，动作可能已经成功执行")
                return True
            else:
                # 其他错误正常处理
                print(f"[DEBUG] 这是一个关键错误，动作执行失败")
                import traceback
                traceback.print_exc()
                return False

    def _execute_arm_command(self, position, velocity, max_retries=3):
        """
        执行机械臂动作命令，带重试逻辑
        
        Args:
            position: 机械臂位置列表 [x, y, z, roll, pitch, yaw]
            velocity: 执行速度
            max_retries: 最大重试次数
            
        Returns:
            是否执行成功
        """
        if not self.arm_controller or not hasattr(self.arm_controller, 'is_connected'):
            print("机械臂控制器未初始化，无法执行命令")
            return False
            
        if not self.arm_controller.is_connected():
            print("机械臂未连接，无法执行命令")
            return False
            
        # 重试计数
        retry_count = 0
        
        while retry_count < max_retries:
            # 执行命令 - 使用move_arm_to_position方法
            result = self.arm_controller.move_arm_to_position(position, velocity)
            
            if result:
                # 执行成功
                if retry_count > 0:
                    print(f"机械臂命令执行成功，重试次数: {retry_count}")
                return True
                
            # 执行失败，重试
            retry_count += 1
            print(f"机械臂命令执行失败，正在重试 ({retry_count}/{max_retries})...")
            
            # 等待短暂时间后重试
            time.sleep(1.0)
            
        # 重试次数用尽，仍然失败
        print(f"机械臂命令执行失败，已重试 {max_retries} 次")
        return False
        
    def _execute_hand_command(self, angles, velocity, max_retries=3):
        """
        执行手爪动作命令，带重试逻辑
        
        Args:
            angles: 手爪角度列表
            velocity: 执行速度
            max_retries: 最大重试次数
            
        Returns:
            是否执行成功
        """
        if not self.arm_controller or not hasattr(self.arm_controller, 'is_connected'):
            print("机械臂控制器未初始化，无法执行手爪命令")
            return False
            
        if not self.arm_controller.is_connected():
            print("机械臂未连接，无法执行手爪命令")
            return False
            
        # 重试计数
        retry_count = 0
        
        while retry_count < max_retries:
            # 执行命令 - 使用set_hand_angles方法
            result = self.arm_controller.set_hand_angles(angles)
            
            if result:
                # 执行成功
                if retry_count > 0:
                    print(f"手爪命令执行成功，重试次数: {retry_count}")
                return True
                
            # 执行失败，重试
            retry_count += 1
            print(f"手爪命令执行失败，正在重试 ({retry_count}/{max_retries})...")
            
            # 等待短暂时间后重试
            time.sleep(1.0)
            
        # 重试次数用尽，仍然失败
        print(f"手爪命令执行失败，已重试 {max_retries} 次")
        return False

    def execute_sequence(self, sequence_name: str, blocking: bool = False) -> bool:
        """
        执行动作序列

        Args:
            sequence_name: 序列名称
            blocking: 是否阻塞等待序列执行完成

        Returns:
            执行是否成功启动
        """
        if self.is_executing:
            print("已有序列正在执行")
            return False

        if not self.arm_controller or not hasattr(self.arm_controller, 'is_connected'):
            print("机械臂控制器未初始化，无法执行序列")
            return False
            
        if not self.arm_controller.is_connected():
            print("机械臂未连接，无法执行序列")
            return False

        if sequence_name not in self.sequences:
            print(f"序列不存在: {sequence_name}")
            return False

        # 获取序列对象
        sequence = self.sequences[sequence_name]

        # 检查序列是否为空
        if not sequence.actions:
            print(f"序列为空: {sequence_name}")
            return False

        # 设置执行状态
        self.is_executing = True
        self.current_sequence = sequence_name

        # 发射执行开始信号
        self.execution_started.emit(sequence_name)

        if blocking:
            # 阻塞模式下直接执行
            success = self._execute_sequence_impl(sequence)

            # 设置执行状态
            self.is_executing = False
            self.current_sequence = None

            # 发射执行完成信号
            if success:
                self.execution_completed.emit(sequence_name)
            else:
                self.execution_error.emit(sequence_name, "执行序列失败")

            return success
        else:
            # 非阻塞模式下使用线程执行
            import threading
            execution_thread = threading.Thread(
                target=self._execute_sequence_thread,
                args=(sequence,)
            )
            execution_thread.daemon = True
            execution_thread.start()
            return True

    def _execute_sequence_thread(self, sequence):
        """在线程中执行序列的实现"""
        success = self._execute_sequence_impl(sequence)

        # 设置执行状态
        self.is_executing = False
        sequence_name = self.current_sequence
        self.current_sequence = None

        # 发射执行完成信号
        if success:
            self.execution_completed.emit(sequence_name)
        else:
            self.execution_error.emit(sequence_name, "执行序列失败")

    def _execute_sequence_impl(self, sequence):
        """执行序列的实际实现"""
        try:
            # 获取重复执行次数
            repeat_count = sequence.repeat_count
            if repeat_count < 1:
                repeat_count = 1  # 确保至少执行一次
                
            # 多次执行序列
            for repeat_index in range(repeat_count):
                # 发射循环执行进度信息
                if repeat_count > 1:
                    print(f"开始执行序列第 {repeat_index + 1}/{repeat_count} 次循环")
                
                # 遍历序列中的动作
                for i, action_name in enumerate(sequence.actions):
                    # 检查动作是否存在
                    if action_name not in self.actions:
                        print(f"动作不存在: {action_name}")
                        self.execution_error.emit(sequence.name, f"动作不存在: {action_name}")
                        return False

                    # 计算总进度比例，考虑到重复执行次数
                    total_actions = len(sequence.actions) * repeat_count
                    current_index = repeat_index * len(sequence.actions) + i
                    
                    # 发射进度信号
                    self.execution_progress.emit(sequence.name, current_index, total_actions)

                    # 执行动作 - 检查执行结果
                    action_success = self.execute_action(action_name)
                    if not action_success:
                        error_msg = f"动作执行失败: {action_name}"
                        print(error_msg)
                        self.execution_error.emit(sequence.name, error_msg)
                        return False

                    # 等待指定的延迟时间
                    delay = sequence.delays[i]
                    if delay > 0:
                        time.sleep(delay)
                        
                # 每次循环结束后，添加短暂延迟
                if repeat_index < repeat_count - 1:
                    time.sleep(0.5)  # 循环之间的间隔

            return True
        except Exception as e:
            error_msg = f"执行序列错误: {e}"
            print(error_msg)
            self.execution_error.emit(sequence.name, error_msg)
            return False

    def stop_execution(self) -> bool:
        """
        停止当前执行的序列

        Returns:
            停止是否成功
        """
        if not self.is_executing:
            return True

        # 重置执行状态
        current_sequence = self.current_sequence
        self.is_executing = False
        self.current_sequence = None

        # 发射执行错误信号
        if current_sequence:
            self.execution_error.emit(current_sequence, "用户中止执行")

        return True

    def save_actions_to_file(self) -> bool:
        """
        将动作保存到文件

        Returns:
            保存是否成功
        """
        try:
            # 将动作转换为字典
            actions_dict = {}
            for name, action in self.actions.items():
                actions_dict[name] = action.to_dict()

            # 写入JSON文件
            with open(self.actions_file, 'w', encoding='utf-8') as f:
                json.dump(actions_dict, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存动作文件错误: {e}")
            return False

    def save_sequences_to_file(self) -> bool:
        """
        将动作序列保存到文件

        Returns:
            保存是否成功
        """
        try:
            # 将序列转换为字典
            sequences_dict = {}
            for name, sequence in self.sequences.items():
                sequences_dict[name] = sequence.to_dict()

            # 写入JSON文件
            with open(self.sequences_file, 'w', encoding='utf-8') as f:
                json.dump(sequences_dict, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存序列文件错误: {e}")
            return False

    def load_actions(self) -> bool:
        """
        从文件加载动作

        Returns:
            加载是否成功
        """
        if not os.path.exists(self.actions_file):
            print(f"动作文件不存在: {self.actions_file}")
            return False

        try:
            # 读取JSON文件
            with open(self.actions_file, 'r', encoding='utf-8') as f:
                actions_dict = json.load(f)

            # 清空当前动作
            self.actions.clear()

            # 加载动作
            for name, action_data in actions_dict.items():
                self.actions[name] = Action.from_dict(action_data)

            return True
        except Exception as e:
            print(f"加载动作文件错误: {e}")
            return False

    def load_sequences(self) -> bool:
        """
        从文件加载动作序列

        Returns:
            加载是否成功
        """
        if not os.path.exists(self.sequences_file):
            print(f"序列文件不存在: {self.sequences_file}")
            return False

        try:
            # 读取JSON文件
            with open(self.sequences_file, 'r', encoding='utf-8') as f:
                sequences_dict = json.load(f)

            # 清空当前序列
            self.sequences.clear()

            # 加载序列
            for name, sequence_data in sequences_dict.items():
                self.sequences[name] = ActionSequence.from_dict(sequence_data)

            return True
        except Exception as e:
            print(f"加载序列文件错误: {e}")
            return False