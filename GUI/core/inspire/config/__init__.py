import yaml
from pathlib import Path
import sys
import os

# Try to find the config file in different locations
cfg_path = None

# First try the current directory relative to this file
current_path = Path(__file__).parent / "inspire_cfg.yml"
if current_path.exists():
    cfg_path = current_path
else:
    # If running as packaged app, try relative to the executable
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        app_dir = Path(sys.executable).parent
        packaged_path = app_dir / "core" / "inspire" / "config" / "inspire_cfg.yml"
        if packaged_path.exists():
            cfg_path = packaged_path
        else:
            # Try relative to the _MEIPASS directory (PyInstaller temp dir)
            if hasattr(sys, '_MEIPASS'):
                meipass_path = Path(sys._MEIPASS) / "core" / "inspire" / "config" / "inspire_cfg.yml"
                if meipass_path.exists():
                    cfg_path = meipass_path

# If we still can't find the file, use default configuration
if cfg_path is None or not cfg_path.exists():
    print(f"Warning: Could not find inspire_cfg.yml, using default configuration")
    inspire_cfg = {
        'hand_dof': 6,
        'port': '/dev/ttyUSB0',
        'baudrate': 115200,
        'initial_angle': [0, 0, 0, 0, 500, 1000],
        'binary_open': [1000, 1000, 1000, 1000, 1000, -1],
        'binary_close': [400, 400, 400, 400, 700, -1],
        'radian_to_cylinder_ratio': [0.08, 0.08, 0.08, 0.08, -0.04, 0.08],
        'radian_to_cylinder_offset': [90, 90, 90, 90, 170, 85]
    }
else:
    try:
        with open(cfg_path, "r", encoding='utf-8') as f:
            inspire_cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Failed to load config file {cfg_path}: {e}, using default configuration")
        inspire_cfg = {
            'hand_dof': 6,
            'port': '/dev/ttyUSB0',
            'baudrate': 115200,
            'initial_angle': [0, 0, 0, 0, 500, 1000],
            'binary_open': [1000, 1000, 1000, 1000, 1000, -1],
            'binary_close': [400, 400, 400, 400, 700, -1],
            'radian_to_cylinder_ratio': [0.08, 0.08, 0.08, 0.08, -0.04, 0.08],
            'radian_to_cylinder_offset': [90, 90, 90, 90, 170, 85]
        }
