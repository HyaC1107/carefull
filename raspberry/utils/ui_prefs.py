import json
import os

_PREFS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "db", "ui_prefs.json")
)

_SCALES = {"normal": 1.0, "large": 1.18, "xlarge": 1.35}


def _load() -> dict:
    try:
        with open(_PREFS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_font_size_key() -> str:
    return _load().get("font_size", "normal")


def set_font_size(key: str) -> None:
    data = _load()
    data["font_size"] = key
    os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
    with open(_PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


_prefs = _load()
FONT_SCALE: float = _SCALES.get(_prefs.get("font_size", "normal"), 1.0)
