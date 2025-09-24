from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_STATE_FILE = "recu_state.json"
_lock = threading.Lock()


def _state_path(custom_path: Optional[str] = None) -> Path:
    return Path(custom_path or _STATE_FILE).resolve()


def load(path: Optional[str] = None) -> Dict[str, Any]:
    p = _state_path(path)
    if not p.exists():
        return {"entries": []}
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"entries": []}


def save(data: Dict[str, Any], path: Optional[str] = None) -> None:
    p = _state_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


def record(
    source_url: str,
    filename: str,
    status: str,
    last_index: Optional[int] = None,
    json_loc: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
) -> None:
    """Append or update a progress entry without touching config.json.

    status: "COMPLETE" | "FAILED" | "ABORTED" | custom
    last_index: segment index where it stopped (if applicable)
    json_loc: index within the urls list in config, for reference
    extra: any additional metadata
    """
    state = load(path)
    ts = int(time.time())
    entry = {
        "timestamp": ts,
        "url": source_url,
        "filename": filename,
        "status": status,
        "last_index": last_index,
        "json_loc": json_loc,
    }
    if extra:
        entry.update(extra)

    # Append immutable log; no destructive updates
    state.setdefault("entries", []).append(entry)
    save(state, path)
