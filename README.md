# wodilist

[![PyPI Version](https://img.shields.io/pypi/v/wodilist?color=blue)](https://pypi.org/project/wodilist/)
[![Python](https://img.shields.io/pypi/pyversions/wodilist?logo=python&logoColor=white)](https://pypi.org/project/wodilist/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`wodilist` is a command-line directory lister designed as a smarter replacement for `ls` with relevance sorting and git awareness. Answers *what matters right now*, not just *what exists* on the disk.

```
$ wodilist
src/          dir        -    2h ago
main.py       file     4.2K   47m ago
Makefile      exec     1.1K    3d ago
README.md     file     8.9K    3d ago
node_modules/ dir        -   12d ago   ← collapsed, de-emphasized
.git/         dir        -   12d ago   ← collapsed, de-emphasized
```

Inside a git repo:
```
$ wodilist
M  auth.py      file     6.1K   12m ago   ← modified: floats up
?  experiment/  dir        -    5m ago    ← untracked
   main.py      file     4.2K    3d ago
   src/         dir        -    3d ago
```

---

## Install

```sh
pip install wodilist
```

`wodilist` is now on your PATH. It does not shadow Python's builtin `list`, that lives in the interpreter, not the shell.

---

## Usage

```
wodilist [subcommand] [directory] [flags]
```

### Default

```sh
wodilist               # current directory
wodilist ~/projects    # explicit directory
```

Groups by kind (dirs → executables → files → links), sorts each group by relevance.

### Subcommands

| Command        | Behavior                                      |
|----------------|-----------------------------------------------|
| `wodilist recent`  | Sort by mtime descending                      |
| `wodilist large`   | Files only, sort by size descending           |
| `wodilist dirty`   | Git-modified and untracked files only         |
| `wodilist entry`   | Entry point files only (main.py, Makefile…)  |

### Flags

| Flag          | Effect                                           |
|---------------|--------------------------------------------------|
| `-a` / `--all`| Show hidden files                               |
| `--json`      | JSON output (stable schema)                     |
| `--raw`       | Tab-separated, no color (pipe-safe)             |
| `--no-git`    | Skip git status (faster in very large repos)    |
| `--branch`    | Show current git branch in header               |

---

## Machine output

### `--raw`

Tab-separated. Five fields per line:

```
git_status  name  kind  size_bytes  mtime_unix
M	auth.py	file	6243	1714000123.456
-	main.py	file	4312	1713900000.000
```

`git_status` is `-` when clean or not in a git repo.

### `--json`

```json
{
  "entries": [
    {
      "name": "auth.py",
      "path": "/home/user/project/auth.py",
      "kind": "file",
      "size": 6243,
      "mtime": 1714000123.456,
      "ext": ".py",
      "git_status": "M",
      "relevance": 135.0,
      "is_hidden": false,
      "is_entry": false
    }
  ],
  "branch": "main"
}
```

Schema is stable. New fields may be added; existing fields will not be renamed or removed without a major version bump.

---

## Failure behavior

- If git is unavailable or slow, list falls back to non-git mode automatically.
- If permissions prevent stat, entries are shown with size `-`.
- Errors never abort the listing unless the directory itself is unreadable.

## Design

**Relevance scoring**

| Signal                    | Score delta |
|---------------------------|-------------|
| Git conflict              | +110        |
| Git modified              | +100        |
| Git added                 | +90         |
| Git untracked             | +75         |
| Git deleted               | +60         |
| Modified < 1 hour ago     | +50         |
| Modified < 1 day ago      | +35         |
| Modified < 1 week ago     | +20         |
| Entry point file          | +30         |
| Executable                | +15         |
| Directory (non-noise)     | +5          |
| Hidden file               | −30         |
| Collapsed (noise) dir     | −50         |

**Git is always one call.** `git status --porcelain=v1 -z` runs once. Status chars map to top-level directory entries automatically (files inside `src/` mark `src/` as modified).

**Performance target:** full pipeline (scan + score + format) < 50ms on a 200-file directory.

---

## Architecture

```
wodilist/
├── scanner.py    # filesystem scanning only
├── detect.py     # TTY, CI, git-root detection
├── git.py        # single-call git status
├── formatter.py  # output only; no scanning
└── cli.py        # argument parsing and dispatch
```

Rules:
- Scanner never formats
- Formatter never scans
- CLI never contains logic
- Git logic isolated to git.py
- Each module testable in isolation

---

## Development

```sh
git clone https://github.com/calchiwo/wodilist.git
cd wodilist
pip install -e ".[dev]"
pytest
python benchmarks/bench.py
```

---

## Compatibility

- Python 3.10+
- Linux, macOS, Windows
- Works in CI (non-TTY: no color, no ANSI)
- Works in pipes (`wodilist --raw | awk ...`)
- Respects `NO_COLOR` env var
- Zero runtime dependencies

---

## Non-goals

- Recursive listing (use `find` or `fd`)
- Interactive UI
- Icons or emoji
- Per-file git calls
- Replacing `find`, `tree`, or `du`

## License
MIT

## Author

Caleb Wodi
