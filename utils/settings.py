import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).parent.parent / "user_settings.json"


def load_settings():
    try:
        if _SETTINGS_PATH.exists():
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_settings(data: dict):
    try:
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_setting(key, default=None):
    s = load_settings()
    return s.get(key, default)


def set_setting(key, value):
    s = load_settings()
    s[key] = value
    save_settings(s)
