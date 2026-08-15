"""Settings storage (persistent configuration)."""
import json
from pathlib import Path
from typing import Any

from .database import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"


def _load_settings() -> dict:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(settings: dict) -> None:
    """Save settings to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    settings = _load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Set a setting value."""
    settings = _load_settings()
    settings[key] = value
    _save_settings(settings)
