from __future__ import annotations

import os
import stat
import sys
import time
from dataclasses import dataclass, field
from pathlib import PurePath

NOISE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        ".eggs",
        "target",
        ".gradle",
        ".idea",
        ".vscode",
    }
)

ENTRY_POINTS: frozenset[str] = frozenset(
    {
        "main.py",
        "app.py",
        "server.py",
        "index.py",
        "main.go",
        "main.rs",
        "main.c",
        "main.cpp",
        "index.js",
        "index.ts",
        "app.js",
        "app.ts",
        "server.js",
        "main.java",
        "App.java",
        "Makefile",
        "makefile",
        "GNUmakefile",
        "CMakeLists.txt",
        "Cargo.toml",
        "go.mod",
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "README.md",
        "README.rst",
        "README.txt",
    }
)

KIND_DIR = "dir"
KIND_FILE = "file"
KIND_EXEC = "exec"
KIND_LINK = "link"

_IS_WINDOWS = sys.platform == "win32"
_WIN_EXEC_EXTS = frozenset({".exe", ".bat", ".cmd", ".ps1", ".com"})


@dataclass(slots=True)
class FileEntry:
    name: str
    path: str
    size: int
    mtime: float
    kind: str
    ext: str
    is_hidden: bool
    is_collapsed: bool
    is_entry: bool
    git_status: str | None = field(default=None)
    relevance: float = field(default=0.0)


def scan(directory: str, show_hidden: bool = False) -> list[FileEntry]:
    entries: list[FileEntry] = []
    now = time.time()

    try:
        it = os.scandir(directory)
    except PermissionError:
        return entries
    except OSError:
        return entries

    with it:
        for de in it:
            name: str = de.name
            is_hidden = name[0] == "." if name else False

            if is_hidden and not show_hidden:
                continue

            try:
                st = de.stat(follow_symlinks=False)
            except OSError:
                continue

            mode = st.st_mode
            is_link = stat.S_ISLNK(mode)

            if is_link:
                try:
                    target_st = de.stat(follow_symlinks=True)
                    is_dir = stat.S_ISDIR(target_st.st_mode)
                except OSError:
                    is_dir = False
                kind = KIND_LINK
            elif stat.S_ISDIR(mode):
                is_dir = True
                kind = KIND_DIR
            else:
                is_dir = False
                if _IS_WINDOWS:
                    ext_check = PurePath(name).suffix.lower()
                    kind = KIND_EXEC if ext_check in _WIN_EXEC_EXTS else KIND_FILE
                else:
                    kind = KIND_EXEC if (mode & 0o111) else KIND_FILE

            size = 0 if is_dir else st.st_size
            mtime = st.st_mtime
            ext = "" if is_dir else PurePath(name).suffix.lower()
            is_collapsed = is_dir and name in NOISE_DIRS
            is_entry = name in ENTRY_POINTS

            entries.append(
                FileEntry(
                    name=name,
                    path=os.path.join(directory, name),
                    size=size,
                    mtime=mtime,
                    kind=kind,
                    ext=ext,
                    is_hidden=is_hidden,
                    is_collapsed=is_collapsed,
                    is_entry=is_entry,
                )
            )

    return entries


def score(entry: FileEntry, now: float) -> float:
    s = 0.0

    if entry.git_status == "M":
        s += 100.0
    elif entry.git_status == "A":
        s += 90.0
    elif entry.git_status == "?":
        s += 75.0
    elif entry.git_status == "D":
        s += 60.0
    elif entry.git_status == "C":
        s += 110.0

    age = now - entry.mtime
    if age < 3_600:
        s += 50.0
    elif age < 86_400:
        s += 35.0
    elif age < 604_800:
        s += 20.0
    elif age < 2_592_000:
        s += 8.0

    if entry.is_entry:
        s += 30.0

    if entry.kind == KIND_EXEC:
        s += 15.0

    if entry.kind == KIND_DIR and not entry.is_collapsed:
        s += 5.0

    if entry.is_collapsed:
        s -= 50.0
    if entry.is_hidden:
        s -= 30.0

    return s


def apply_scores(entries: list[FileEntry], now: float) -> None:
    for e in entries:
        e.relevance = score(e, now)
