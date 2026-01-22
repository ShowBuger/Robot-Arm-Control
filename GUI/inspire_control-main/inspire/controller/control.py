import serial
import time
from typing import Union, List
import numpy as np
import threading
from inspire.config import inspire_cfg
from inspire.utils.convert import as_binary_angle

class InspireController:
    HAND_DOF = inspire_cfg['hand_dof']

    def __init__(self, port: str, baudrate: int, connect: bool = False) -> None:
        self.hand_id = 1
        self.lock = threading.Lock()
        self.ser = serial.Serial(
            port = port if port else inspire_cfg['port'],
            baudrate = baudrate if baudrate else inspire_cfg['baudrate']
        )
        self.initial_angle = inspire_cfg['initial_angle']
        self.binary_open = inspire_cfg['binary_open']
        self.binary_close = inspire_cfg['binary_close']
        self.radian_to_cylinder_ratio = inspire_cfg['radian_to_cylinder_ratio']
        self.radian_to_cylinder_offset = inspire_cfg['radian_to_cylinder_offset']

        if connect:
            self.connect()

    # def __enter__(self):
    #     print('enter')
    #     return self

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     self.disconnect()

    def connect(self):
        with self.lock:
            if not self.ser.is_open:
                self.ser.open()

    def disconnect(self):
        with self.lock:
            if not self.ser.closed:
                self.ser.close()

    @property
    def connected(self):
        with self.lock:
            return self.ser.is_open

    @property
    def exceed_force_limit(self):
        force = np.array(self.get_force())
        force_limit = np.array(self.get_force_limit())
        return bool(np.any(force > force_limit))

    @property
    def last_angle(self):
        return self.get_angle(actual=True)[-1]

    def reset(self):
        self.set_angle(self.initial_angle)

    def _calculate_checksum(self, data: list, start: int, end: int) -> int:
        """计算校验和"""
        return sum(data[start:end]) & 0xff

    def _split_to_bytes(self, value: int, little_endian: bool = True) -> tuple:
        """
        将整数拆分为高位和低位字节。

        参数:
            value (int): 要拆分的整数，范围为 -1 或 0 ~ 65535。
            little_endian (bool): 字节顺序，'True'（低位在前，高位在后，默认）或 'big'（高位在前，低位在后）。

        返回:
            tuple: (高位字节, 低位字节) 或 (低位字节, 高位字节)，取决于 endian 参数。

        示例:
            >>> controller._split_to_bytes(1000, 'little')
            (232, 3)  # 0x03E8 -> (低位 0xE8, 高位 0x03)
            >>> controller._split_to_bytes(1000, 'big')
            (3, 232)  # 0x03E8 -> (高位 0x03, 低位 0xE8)
        """
        if value == -1:
            return 0xff, 0xff
        if little_endian:
            return value & 0xff, (value >> 8) & 0xff
        else:
            return (value >> 8) & 0xff, value & 0xff

    def _bytes_to_int(self, high: int, low: int) -> int:
        """工具函数：从字节数组合并为整数"""
        if high == 0xff and low == 0xff:
            return -1
        return (high << 8) + low

    def _build_packet(self, data_len: int, cmd: int, addr: int, data: List[int] = None) -> bytearray:
        """工具函数：构建数据包"""
        packet = [0xEB, 0x90, self.hand_id, data_len, cmd]  # 包头 + ID + 数据长度 + 命令
        packet.extend(self._split_to_bytes(addr))  # 地址高低字节
        if data:
            for value in data:
                packet.extend(self._split_to_bytes(value))  # 数据低字节在前，高字节在后
        packet.append(self._calculate_checksum(packet, 2, len(packet)))
        return bytearray(packet)

    def _send_and_receive(self, packet: bytearray, response_len: int) -> bytes:
        """工具函数：发送数据并接收响应"""
        with self.lock:
            self.ser.write(packet)
            return self.ser.read(response_len)

    def _parse_multi_dof_response(self, response: bytes, offset: int = 7) -> List[int]:
        """工具函数: 解析多DOF响应数据"""
        result = []
        for i in range(self.HAND_DOF):
            low, high = response[offset + i * 2], response[offset + i * 2 + 1]
            value = self._bytes_to_int(high, low)
            result.append(value)
        return result

    def set_angle(self, angle: Union[int, List[int]]):
        if isinstance(angle, int):
            angle = [angle] * self.HAND_DOF
        if len(angle) != self.HAND_DOF or any(a < -1 or a > 1000 for a in angle):
            raise ValueError('角度数据必须为6个, 且范围在 -1 ~ 1000')
        packet = self._build_packet(0x0F, 0x12, 0x05CE, angle)
        self._send_and_receive(packet, 9)

    def set_i_angle(self, i: int, angle: int):
        """设置第i个关节的角度"""
        assert i in range(self.HAND_DOF), f"Invalid index i: {i}"
        o = self.get_angle()
        o[i] = angle
        self.set_angle(o)
    
    def get_angle(self, actual: bool = False):
        addr = 0x060A if actual else 0x05CE
        packet = self._build_packet(0x05, 0x11, addr, [0x0C])
        response = self._send_and_receive(packet, 20)
        return self._parse_multi_dof_response(response)

    # def get_pos(self, actual: bool = False):
    #     addr = 0x05FE if actual else 0x05C2
    #     packet = self._build_packet(0x05, 0x11, addr, [0x0C])
    #     response = self._send_and_receive(packet, 20)
    #     return self._parse_multi_dof_response(response)

    def set_speed(self, speed: Union[int, List[int]]):
        if isinstance(speed, int):
            speed = [speed] * self.HAND_DOF
        if len(speed) != self.HAND_DOF or any(s < 0 or s > 1000 for s in speed):
            raise ValueError('速度数据必须为6个, 且范围在 0 ~ 1000')
        packet = self._build_packet(0x0F, 0x12, 0x05F2, speed)
        self._send_and_receive(packet, 9)

    def set_i_speed(self, i: int, speed: int):
        """设置第i个关节的速度"""
        assert i in range(self.HAND_DOF), f"Invalid index i: {i}"
        o = self.get_speed()
        o[i] = speed
        self.set_speed(o)

    def get_speed(self):
        packet = self._build_packet(0x05, 0x11, 0x05F2, [0x0C])
        response = self._send_and_receive(packet, 20)
        return self._parse_multi_dof_response(response)

    def get_force(self):
        packet = self._build_packet(0x05, 0x11, 0x062E, [0x0C])
        response = self._send_and_receive(packet, 20)
        force = self._parse_multi_dof_response(response)
        # 处理有符号数据
        return [f - 65536 if f > 32767 else f for f in force]

    def set_force_limit(self, force_limit: Union[int, List[int]]):
        if isinstance(force_limit, int):
            force_limit = [force_limit] * self.HAND_DOF
        if len(force_limit) != self.HAND_DOF or any(f < 0 or f > 1000 for f in force_limit):
            raise ValueError('力限制数据必须为6个，且范围在 0 ~ 1000')
        packet = self._build_packet(0x0F, 0x12, 0x05DA, force_limit)
        self._send_and_receive(packet, 9)

    def set_i_force_limit(self, i: int, force_limit: int):
        """设置第i个关节的力阈值"""
        assert i in range(self.HAND_DOF), f"Invalid index i: {i}"
        o = self.get_force_limit()
        o[i] = force_limit
        self.set_force_limit(o)

    def get_force_limit(self):
        packet = self._build_packet(0x05, 0x11, 0x05DA, [0x0C])
        response = self._send_and_receive(packet, 20)
        return self._parse_multi_dof_response(response)

    def gesture_force_clb(self):
        """力阈值校准, 该方法执行15秒"""
        packet = self._build_packet(0x05, 0x12, 0x03F1, [0x01])
        self._send_and_receive(packet, 18)

    def get_error(self):
        packet = self._build_packet(0x05, 0x11, 0x0646, [0x06])
        response = self._send_and_receive(packet, 14)
        return list(response[7:13])

    def get_status(self):
        packet = self._build_packet(0x05, 0x11, 0x064C, [0x06])
        response = self._send_and_receive(packet, 14)
        return list(response[7:13])

    def clear_error(self):
        packet = self._build_packet(0x05, 0x12, 0x03EC, [0x01])
        self._send_and_receive(packet, 9)

    def set_last_angle(self, angle: int, sleep: bool = True):
        """大拇指翻转角度, 0~1000"""
        if not (-1 <= angle and angle <= 1000):
            raise ValueError('角度必须在 -1 ~ 1000')
        self.set_angle([1000] * self.HAND_DOF)
        if sleep:
            time.sleep(3)
        cur_angle = self.get_angle(actual=True)
        cur_angle[-1] = angle
        self.set_angle(cur_angle)

    def set_bin_angle(self, bin_angle: float):
        """输入的浮点数表示将手当作夹爪, 0-close 1-open"""
        if not (0.0 <= bin_angle and bin_angle <= 1.0):
            raise ValueError('二指夹爪角度必须 [0.0, 1.0]')
        # bin_angle = 1 - bin_angle
        angle = [
            int(np.interp(
                bin_angle,
                [0, 1],
                [close_angle, open_angle]
            ))
            for close_angle, open_angle in zip(
                self.binary_close,
                self.binary_open
            )
        ]
        angle[-1] = self.get_angle(actual=False)[-1]
        self.set_angle(angle)

    def get_bin_angle(self) -> float:
        """计算将手当作夹爪的binary角度, 0-close 1-open"""
        angle = self.get_angle(actual=True)
        return as_binary_angle(angle)
    
    def emergency_release(self, four_finger: bool, thumb: bool, thumb_flip: bool):
        """紧急情况调用，释放*四指|大拇指|大拇指翻转*中的一个"""
        assert sum([four_finger, thumb, thumb_flip]) == 1, "一次调用只能在[四指|大拇指|大拇指翻转]中选一个"
        if four_finger:
            self.set_angle([1000, 1000, 1000, 1000, -1, -1])
        if thumb:
            self.set_angle([-1, -1, -1, -1, 1000, -1])
        if thumb_flip:
            self.set_angle([-1, -1, -1, -1, -1, 1000])