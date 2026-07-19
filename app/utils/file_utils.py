from __future__ import annotations
import re
from pathlib import Path

FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")

def sanitize_filename(filename: str) -> str:
    base = Path(filename).name
    safe = FILENAME_SAFE.sub("_", base)
    return safe.strip("_.-") or "file"
