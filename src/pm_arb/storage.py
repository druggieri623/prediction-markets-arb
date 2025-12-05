"""Simple file-based storage helpers for the project.

Provides atomic JSON save/load helpers used by small utilities and demos.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_json(path: Path | str, obj: Any, *, indent: int = 2) -> None:
    """Atomically save `obj` as JSON to `path`.

    The write is performed to a temporary file in the same directory and
    then renamed into place to avoid partial writes.
    """
    p = Path(path)
    _ensure_parent(p)

    dirpath = str(p.parent)
    fd, tmp = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def load_json(path: Path | str, default: Optional[Any] = None) -> Any:
    """Load JSON from `path`. Return `default` if file does not exist."""
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def exists(path: Path | str) -> bool:
    return Path(path).exists()


def remove(path: Path | str) -> None:
    p = Path(path)
    try:
        p.unlink()
    except FileNotFoundError:
        pass
