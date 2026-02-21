from __future__ import annotations

import json as _json
import os
import time
from typing import Sequence

from .scanner import FileEntry, KIND_DIR, KIND_EXEC, KIND_LINK

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_BLUE = "\033[34m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_WHITE = "\033[37m"

_BOLD_BLUE = "\033[1;34m"
_BOLD_GREEN = "\033[1;32m"
_BOLD_YELLOW = "\033[1;33m"
_BOLD_RED = "\033[1;31m"


def _ansi(text: str, *codes: str) -> str:
    return "".join(codes) + text + _RESET


def _human_size(n: int) -> str:
    if n < 0:
        return "     -"
    for unit, divisor in (("G", 1 << 30), ("M", 1 << 20), ("K", 1 << 10)):
        if n >= divisor:
            val = n / divisor
            s = f"{val:.1f}{unit}" if val < 100 else f"{int(val)}{unit}"
            return s.rjust(6)
    return f"{n}B".rjust(6)


def _human_age(mtime: float, now: float) -> str:
    age = now - mtime
    if age < 0:
        age = 0
    if age < 60:
        s = "now"
    elif age < 3600:
        s = f"{int(age // 60)}m ago"
    elif age < 86400:
        s = f"{int(age // 3600)}h ago"
    elif age < 7 * 86400:
        s = f"{int(age // 86400)}d ago"
    elif age < 30 * 86400:
        s = f"{int(age // 7 // 86400)}wk ago"
    elif age < 365 * 86400:
        s = f"{int(age // 30 // 86400)}mo ago"
    else:
        s = f"{int(age // 365 // 86400)}yr ago"
    return s.rjust(7)


def _git_char(status: str | None) -> str:
    if status is None:
        return " "
    return status[0]


def _render_name(entry: FileEntry, color: bool, max_width: int) -> str:
    name = entry.name
    if len(name) > max_width:
        name = name[: max_width - 1] + "…"

    if not color:
        suffix = "/" if entry.kind == KIND_DIR else ""
        return name + suffix

    if entry.is_collapsed:
        return _ansi(name + "/", _DIM)
    if entry.kind == KIND_DIR:
        return _ansi(name + "/", _BOLD_BLUE)
    if entry.kind == KIND_LINK:
        return _ansi(name, _CYAN)
    if entry.kind == KIND_EXEC:
        return _ansi(name, _BOLD_GREEN)

    if entry.git_status == "M":
        return _ansi(name, _BOLD_YELLOW)
    if entry.git_status == "?":
        return _ansi(name, _RED)
    if entry.git_status == "A":
        return _ansi(name, _GREEN)
    if entry.git_status == "D":
        return _ansi(name, _DIM)
    if entry.git_status == "C":
        return _ansi(name, _BOLD_RED)

    if entry.is_entry:
        return _ansi(name, _BOLD)

    return name


def _render_git(status: str | None, color: bool) -> str:
    char = _git_char(status)
    if not color or char == " ":
        return char
    mapping = {
        "M": _BOLD_YELLOW,
        "A": _GREEN,
        "?": _RED,
        "D": _DIM,
        "C": _BOLD_RED,
    }
    code = mapping.get(char, _WHITE)
    return _ansi(char, code)


def _render_kind(kind: str) -> str:
    return {
        KIND_DIR: "dir ",
        KIND_EXEC: "exec",
        KIND_LINK: "link",
    }.get(kind, "file")


_KIND_ORDER = {KIND_DIR: 0, KIND_EXEC: 1, "file": 2, KIND_LINK: 3}


def sort_entries(
    entries: list[FileEntry],
    group: bool = True,
) -> list[FileEntry]:

    if group:
        return sorted(
            entries,
            key=lambda e: (_KIND_ORDER.get(e.kind, 99), -e.relevance, e.name.lower()),
        )
    return sorted(entries, key=lambda e: -e.relevance)


def render_table(
    entries: Sequence[FileEntry],
    color: bool,
    width: int,
    now: float,
    branch: str | None = None,
    git_enabled: bool = False,
):

    import sys

    write = sys.stdout.write
    flush = sys.stdout.flush

    if not entries:
        return

    GIT_W = 2
    KIND_W = 5
    SIZE_W = 7
    AGE_W = 8
    overhead = GIT_W + KIND_W + SIZE_W + AGE_W + 3
    name_w = max(20, (width or 100) - overhead) if width else 60

    if branch and git_enabled and color:
        write(_ansi(f" on {branch}", _DIM) + "\n")
    elif branch and git_enabled:
        write(f" on {branch}\n")

    for entry in entries:
        git_col = (_render_git(entry.git_status, color) + " ") if git_enabled else ""
        name_col = _render_name(entry, color, name_w)
        kind_col = _render_kind(entry.kind)
        size_col = " " + (_human_size(entry.size) if entry.kind != KIND_DIR else "     -")
        age_col = " " + _human_age(entry.mtime, now)

        raw_name = entry.name
        if entry.kind in (KIND_DIR, KIND_LINK):
            raw_name += "/"
        padding = " " * max(0, name_w - len(raw_name))

        line = f"{git_col}{name_col}{padding}  {kind_col}{size_col}{age_col}\n"
        write(line)

    flush()


def render_raw(
    entries: Sequence[FileEntry],
    now: float,
    git_enabled: bool = False,
) -> None:

    import sys

    write = sys.stdout.write
    for entry in entries:
        git = entry.git_status or "-"
        write(f"{git}\t{entry.name}\t{entry.kind}\t{entry.size}\t{entry.mtime:.3f}\n")
    sys.stdout.flush()


def render_json(
    entries: Sequence[FileEntry],
    now: float,
    branch: str | None = None,
) -> None:

    import sys

    records = []
    for e in entries:
        records.append(
            {
                "name": e.name,
                "path": e.path,
                "kind": e.kind,
                "size": e.size,
                "mtime": e.mtime,
                "ext": e.ext,
                "git_status": e.git_status,
                "relevance": round(e.relevance, 2),
                "is_hidden": e.is_hidden,
                "is_entry": e.is_entry,
            }
        )

    out: dict = {"entries": records}
    if branch is not None:
        out["branch"] = branch

    sys.stdout.write(_json.dumps(out, separators=(",", ":")) + "\n")
    sys.stdout.flush()
