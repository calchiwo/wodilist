from __future__ import annotations

import os
import sys

_CI_VARS = (
    "CI",
    "CONTINUOUS_INTEGRATION",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "JENKINS_URL",
    "CIRCLECI",
    "TRAVIS",
    "BUILDKITE",
    "TEAMCITY_VERSION",
)


def is_tty() -> bool:
    return sys.stdout.isatty()


def is_ci() -> bool:
    return any(os.environ.get(v) for v in _CI_VARS)


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return is_tty() and not is_ci()


def terminal_width() -> int:
    if not is_tty():
        return 0
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def find_git_root(start: str) -> str | None:
    current = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def cwd() -> str:
    return os.getcwd()
