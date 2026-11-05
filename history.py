"""core/history.py — persistent download history."""

import datetime
import json
import os

_HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".iridium", "history.json")
_MAX_ENTRIES = 200


def load_history() -> list:
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def add_entry(title: str, url: str, kind: str = "video",
              path: str = "", date: str = None):
    entries = load_history()
    entry = {
        "title": (title or "Unknown").strip(),
        "url": url or "",
        "kind": kind or "video",
        "date": date or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "path": path or "",
    }
    entries.insert(0, entry)
    if len(entries) > _MAX_ENTRIES:
        entries = entries[:_MAX_ENTRIES]
    _save(entries)


def clear_history():
    _save([])


def _save(entries):
    try:
        os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass