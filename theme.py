"""
ui/theme.py — Iridium multi-theme system.

Settings are cached in memory after first read. Writes still go to disk via
set_setting(), and the cache is updated in the same call. Single-user
desktop app, so no cross-process invalidation needed.
"""

import datetime
import json
import os

_PALETTES = {
    "Red": {
        "BG_BASE":       "#0a0606",
        "BG_PANEL":      "#140b0b",
        "BG_TITLEBAR":   "#0d0808",
        "BG_INPUT":      "#1a0f0f",
        "FG_TEXT":       "#f2ecec",
        "FG_MUTED":      "#a89a9a",
        "FG_DIM":        "#6b5c5c",
        "ACCENT":        "#e63b3b",
        "ACCENT_HOVER":  "#ff5555",
        "ACCENT_PRESS":  "#b82a2a",
        "ACCENT_GLOW":   "#7a1f1f",
        "CLOSE_HOVER":   "#e81123",
        "MIN_HOVER":     "#221414",
    },
    "Pink": {
        "BG_BASE":       "#0a0709",
        "BG_PANEL":      "#150d12",
        "BG_TITLEBAR":   "#0e080c",
        "BG_INPUT":      "#1b1018",
        "FG_TEXT":       "#f3ecf1",
        "FG_MUTED":      "#a5969f",
        "FG_DIM":        "#6b5a64",
        "ACCENT":        "#ff5fa8",
        "ACCENT_HOVER":  "#ff7fbc",
        "ACCENT_PRESS":  "#e04589",
        "ACCENT_GLOW":   "#8a2f5c",
        "CLOSE_HOVER":   "#e81123",
        "MIN_HOVER":     "#231520",
    },
    "Purple": {
        "BG_BASE":       "#08060c",
        "BG_PANEL":      "#120d1a",
        "BG_TITLEBAR":   "#0b0812",
        "BG_INPUT":      "#170f22",
        "FG_TEXT":       "#efecf4",
        "FG_MUTED":      "#a094af",
        "FG_DIM":        "#615874",
        "ACCENT":        "#a36bff",
        "ACCENT_HOVER":  "#b98cff",
        "ACCENT_PRESS":  "#8852e0",
        "ACCENT_GLOW":   "#4f2f8a",
        "CLOSE_HOVER":   "#e81123",
        "MIN_HOVER":     "#1d1428",
    },
    "Halloween": {
        "BG_BASE":       "#07080a",
        "BG_PANEL":      "#10130d",
        "BG_TITLEBAR":   "#0a0c08",
        "BG_INPUT":      "#141810",
        "FG_TEXT":       "#f1efe2",
        "FG_MUTED":      "#a7a390",
        "FG_DIM":        "#6a6754",
        "ACCENT":        "#ff8c1a",
        "ACCENT_HOVER":  "#ffab4a",
        "ACCENT_PRESS":  "#d96f0d",
        "ACCENT_GLOW":   "#7a3b0a",
        "CLOSE_HOVER":   "#e81123",
        "MIN_HOVER":     "#1a1d12",
        "SECONDARY":     "#a8c93a",
    },
    "Christmas": {
        "BG_BASE":       "#06090a",
        "BG_PANEL":      "#0d1414",
        "BG_TITLEBAR":   "#080e0e",
        "BG_INPUT":      "#121a1a",
        "FG_TEXT":       "#f0f3f0",
        "FG_MUTED":      "#9aa8a3",
        "FG_DIM":        "#5c6b66",
        "ACCENT":        "#c8202a",
        "ACCENT_HOVER":  "#e6323c",
        "ACCENT_PRESS":  "#a01720",
        "ACCENT_GLOW":   "#6d0f14",
        "CLOSE_HOVER":   "#e81123",
        "MIN_HOVER":     "#101a18",
        "SECONDARY":     "#1f6b3a",
    },
}

_BASE_THEMES = ["Red", "Pink", "Purple"]
_SEASONAL = {
    "Halloween":  (10, 31),
    "Christmas":  (12, 25),
}

WINDOW_W        = 800
WINDOW_H        = 500
TITLEBAR_HEIGHT = 36
VERSION         = "1.0.0"

FONT_TITLE   = ("Segoe UI", 13, "bold")
FONT_HERO    = ("Segoe UI", 16, "italic")
FONT_INPUT   = ("Segoe UI", 13)
FONT_BUTTON  = ("Segoe UI", 13, "bold")
FONT_ICON    = ("Segoe UI", 12, "bold")
FONT_SMALL   = ("Segoe UI", 11)

_active_theme_name = "Purple"
_active_palette = _PALETTES["Purple"]

BG_BASE = FG_TEXT = ACCENT = ACCENT_HOVER = ACCENT_PRESS = ACCENT_GLOW = ""
BG_PANEL = BG_TITLEBAR = BG_INPUT = FG_MUTED = FG_DIM = ""
CLOSE_HOVER = MIN_HOVER = SECONDARY = ""


def _apply_palette(palette):
    global _active_palette
    _active_palette = palette
    for key, value in palette.items():
        globals()[key] = value


_apply_palette(_PALETTES["Purple"])


def _today():
    d = datetime.date.today()
    return (d.month, d.day)


def is_theme_unlocked(name: str) -> bool:
    if name in _BASE_THEMES:
        return True
    if name in _SEASONAL:
        return _today() == _SEASONAL[name]
    return False


def available_themes():
    return [n for n in _PALETTES if is_theme_unlocked(n)]


def all_themes():
    return list(_PALETTES.keys())


# ---- settings with in-memory cache ----

_SETTINGS_DIR  = os.path.join(os.path.expanduser("~"), ".iridium")
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "settings.json")
_settings_cache = None


def _load_settings():
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            _settings_cache = json.load(f)
    except Exception:
        _settings_cache = {}
    return _settings_cache


def _write_settings(data):
    try:
        os.makedirs(_SETTINGS_DIR, exist_ok=True)
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_setting(key, default=None):
    return _load_settings().get(key, default)


def set_setting(key, value):
    data = _load_settings()
    data[key] = value
    _write_settings(data)


def apply_theme(name: str) -> bool:
    global _active_theme_name
    if name not in _PALETTES:
        return False
    if not is_theme_unlocked(name):
        return False
    _active_theme_name = name
    _apply_palette(_PALETTES[name])
    set_setting("theme", name)
    return True


def load_active_theme():
    saved = get_setting("theme", "Purple")
    if not apply_theme(saved):
        apply_theme("Purple")


def active_theme_name() -> str:
    return _active_theme_name


def palette() -> dict:
    return dict(_active_palette)