from __future__ import annotations

import subprocess
import os

_PRIORITY = {"C": 0, "M": 1, "A": 2, "D": 3, "?": 4}


def _collapse_xy(x: str, y: str) -> str | None:
    if x not in (" ", "?") and y not in (" ", "?") and not (x == "?" and y == "?"):
        if x != y:
            return "C"

    if x == "?" and y == "?":
        return "?"
    if x == "D" or y == "D":
        return "D"
    if x == "A":
        return "A"
    if x == "M" or y == "M":
        return "M"
    if x == "R" or y == "R":
        return "M"
    if x not in (" ", ".", "!") or y not in (" ", ".", "!"):
        return "M"
    return None


def batch_status(directory: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--no-renames",
            ],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}

    if result.returncode not in (0, 128):
        return {}

    raw: str = result.stdout.decode("utf-8", errors="replace")
    if not raw:
        return {}

    status_map: dict[str, str] = {}
    parts = raw.split("\x00")
    for part in parts:
        if len(part) < 4:
            continue
        x = part[0]
        y = part[1]
        path = part[3:]

        if not path:
            continue

        top = path.split("/")[0].split(os.sep)[0]
        if not top:
            continue

        char = _collapse_xy(x, y)
        if char is None:
            continue

        existing = status_map.get(top)
        if existing is None or _PRIORITY.get(char, 99) < _PRIORITY.get(existing, 99):
            status_map[top] = char

    return status_map


def current_branch(directory: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    return result.stdout.decode("utf-8", errors="replace").strip() or None
