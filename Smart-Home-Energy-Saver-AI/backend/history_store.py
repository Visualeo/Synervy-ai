"""
backend/history_store.py
--------------------------
In-memory + JSON-backed store for optimization history log.
Records: timestamp, agent, action summary, approval status.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

HISTORY_FILE = Path(__file__).parent / "history.json"
_lock = Lock()
_history: list[dict] = []


def _load():
    global _history
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                _history = json.load(f)
        except Exception:
            _history = []


def _save():
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(_history[-500:], f, indent=2, default=str)  # keep last 500
    except Exception:
        pass


# Load on import
_load()


def add_entry(
    agent: str,
    action: str,
    risk_level: str = "LOW",
    approval_status: str = "pending",
    details: dict | None = None
) -> dict:
    """Add a new history entry and persist it."""
    entry = {
        "id": f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "risk_level": risk_level,
        "approval_status": approval_status,
        "details": details or {}
    }
    with _lock:
        _history.append(entry)
        _save()
    return entry


def get_history(limit: int = 50) -> list[dict]:
    """Return the most recent history entries."""
    with _lock:
        return list(reversed(_history[-limit:]))


def update_approval(entry_id: str, status: str) -> bool:
    """Update approval status of an entry."""
    with _lock:
        for entry in _history:
            if entry["id"] == entry_id:
                entry["approval_status"] = status
                _save()
                return True
    return False


def clear_history():
    global _history
    with _lock:
        _history = []
        _save()
