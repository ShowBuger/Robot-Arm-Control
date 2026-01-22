import yaml
from pathlib import Path

cfg_path = Path(__file__).parent / "inspire_cfg.yml"
with open(cfg_path, "r") as f:
    inspire_cfg = yaml.safe_load(f)
