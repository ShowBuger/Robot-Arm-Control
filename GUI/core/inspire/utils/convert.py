import numpy as np
from typing import List
from core.inspire.config import inspire_cfg

# 外部接口
def as_cylinder_angle(angle: List[float], radian: bool = False) -> List[int]:
    """将角度转为0~1000, 如果输入的angle为弧度, radian=True"""
    offset, ratio = np.array(inspire_cfg['radian_to_cylinder_offset']), np.array(inspire_cfg['radian_to_cylinder_ratio'])
    angle = np.rad2deg(angle) if radian else angle
    return list(map(int, (np.array(angle) - offset) / ratio))

def as_degree_angle(angle: List[int], radian: bool = False) -> List[float]:
    """将0~1000转为角度, 输入的angle为0~1000, 如果要输出的angle为弧度, radian=True"""
    offset, ratio = np.array(inspire_cfg['radian_to_cylinder_offset']), np.array(inspire_cfg['radian_to_cylinder_ratio'])
    degree_angle = list(map(float, np.array(angle) * ratio + offset))
    return degree_angle if not radian else np.deg2rad(degree_angle)

def as_binary_angle(angle: List[int]) -> float:
    """转为0-close 1-open, 输入的angle为0~1000"""
    index_finger_bin = float(np.interp(angle[3], [inspire_cfg['binary_close'][3], inspire_cfg['binary_open'][3]], [0, 1]))
    thumb_finger_bin = float(np.interp(angle[4], [inspire_cfg['binary_close'][4], inspire_cfg['binary_open'][4]], [0, 1]))
    return (index_finger_bin + thumb_finger_bin) / 2
