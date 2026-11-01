from __future__ import annotations

import json
import os
import re
import threading
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_THEME: dict[str, str] = {
    "accent": "#4c6fff",
    "card_top": "#172a57",
    "card_bottom": "#0b1330",
    "border": "#314880",
    "bar_track": "#1c2c50",
    "bar_fill": "#e8efff",
}

DEFAULTS: dict[str, Any] = {
    "welcome_channel_id": None,
    "goal": 300,
    "brand_line": "brand_line",
    "title": "title",
    "tagline": "tagline",
    "card_title": "card title",
    "card_footer": "card footer",
    "flags": "🇲🇲 | 🇲🇲",
    "verify_role_id": None,
    "tos_channel_id": None,
    "verify_label": "",
    "read_label": "",
    "theme": dict(DEFAULT_THEME),
}

_HEX = re.compile(r"^[0-9a-fA-F]{6}$")
_LOCK = threading.Lock()


class SettingsError(ValueError):
    """Raised when a value coming from a slash command is invalid."""


def parse_color(value: str) -> str:
    """Normalise `#1e3a8a`, `1e3a8a` or `0x1e3a8a` to `#1e3a8a`."""
    raw = value.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    raw = raw.lstrip("#")
    if not _HEX.match(raw):
        raise SettingsError(f"`{value}` is not a hex color — try `#1e3a8a`")
    return f"#{raw}"


def color_int(value: str) -> int:
    return int(parse_color(value)[1:], 16)


def color_rgb(value: str) -> tuple[int, int, int]:
    raw = parse_color(value)[1:]
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _merge_defaults(data: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULTS))  # deep copy
    for key, value in data.items():
        if key == "theme" and isinstance(value, dict):
            merged["theme"].update({k: v for k, v in value.items() if k in DEFAULT_THEME})
        elif key in DEFAULTS:
            merged[key] = value
    return merged


def load() -> dict[str, Any]:
    """Current settings, falling back to defaults for anything missing."""
    if not os.path.exists(SETTINGS_PATH):
        return _merge_defaults({})
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            return _merge_defaults(json.load(fh))
    except (OSError, ValueError):
        return _merge_defaults({})


def save(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = SETTINGS_PATH + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_merge_defaults(data), fh, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_PATH)


def update(**changes: Any) -> dict[str, Any]:
    """Merge non-`None` changes into the stored settings and return the result."""
    data = load()
    theme_changes = changes.pop("theme", None)
    if theme_changes:
        data["theme"].update(
            {k: parse_color(v) for k, v in theme_changes.items() if k in DEFAULT_THEME and v}
        )
    data.update({k: v for k, v in changes.items() if v is not None})
    save(data)
    return data


def reset() -> dict[str, Any]:
    data = _merge_defaults({})
    save(data)
    return data


def clear(*keys: str) -> dict[str, Any]:
    """Set the given keys back to `None` (used by /links clear)."""
    data = load()
    for key in keys:
        data[key] = None
    save(data)
    return data
