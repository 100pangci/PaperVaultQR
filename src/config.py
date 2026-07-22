import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".papervaultqr")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "appearance_mode": "System",
    "language": "",
    "chunk_size": 500,
    "qr_error": "M",
    "qr_width_cm": 4.0,
    "font_size_label": 10,
    "cols_per_page": 4,
    "page_margin": 1.0,
    "rs_strength": 0,
}


def load_config():
    try:
        if not os.path.exists(CONFIG_PATH):
            return dict(DEFAULT_CONFIG)
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        merged["rs_strength"] = int(merged.get("rs_strength", 0))
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
