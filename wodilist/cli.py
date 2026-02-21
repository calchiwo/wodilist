from __future__ import annotations

import argparse
import os
import sys
import time


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wodilist",
        description="A smarter replacement for ls with relevance sorting and git awareness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    p.add_argument(
        "subcommand_or_dir",
        nargs="?",
        default=None,
        metavar="[subcommand|directory]",
        help="Subcommand (recent|large|dirty|entry) or directory path.",
    )
    p.add_argument(
        "directory",
        nargs="?",
        default=None,
        metavar="directory",
        help="A smarter replacement for ls. Lists what matters right now.",
    )
    p.add_argument(
        "-a", "--all", dest="show_hidden", action="store_true", help="Show hidden files."
    )
    p.add_argument("--json", dest="output_json", action="store_true", help="Output JSON.")
    p.add_argument(
        "--raw",
        dest="output_raw",
        action="store_true",
        help="Tab-separated output, no color, stable schema.",
    )
    p.add_argument(
        "--no-git",
        dest="no_git",
        action="store_true",
        help="Skip git status (faster in large repos).",
    )
    p.add_argument(
        "--branch",
        dest="show_branch",
        action="store_true",
        help="Show current git branch in header.",
    )
    p.add_argument(
        "--collapsed",
        dest="show_collapsed",
        action="store_true",
        help="Show noise directories (they are dimmed).",
    )
    return p


_SUBCOMMANDS = frozenset({"recent", "large", "dirty", "entry"})


def _resolve_args(
    raw: argparse.Namespace,
) -> tuple[str | None, str]:
    first = raw.subcommand_or_dir
    second = raw.directory

    if first is None:
        return None, os.getcwd()

    if first in _SUBCOMMANDS:
        return first, second if second is not None else os.getcwd()

    if second is not None:
        print(
            f"wodilist: too many argument: '{second}' after directory",
            file=sys.stderr,
        )
        sys.exit(1)

    return None, first


def main(argv: list[str] | None = None) -> None:
    from . import detect, scanner, formatter

    parser = _build_parser()
    args = parser.parse_args(argv)

    subcommand, directory = _resolve_args(args)

    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"wodilist: '{directory}': not a directory", file=sys.stderr)
        sys.exit(2)

    output_raw = args.output_raw
    output_json = args.output_json
    if output_raw and output_json:
        print("wodilist: --raw and --json are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    color = detect.use_color() and not output_raw and not output_json
    width = detect.terminal_width() if color else 0
    now = time.time()

    entries = scanner.scan(directory, show_hidden=args.show_hidden)

    branch: str | None = None
    git_enabled = False

    if not args.no_git and not output_raw:
        git_root = detect.find_git_root(directory)
        if git_root is not None:
            from . import git as gitmod

            status_map = gitmod.batch_status(directory)
            for e in entries:
                e.git_status = status_map.get(e.name)
            if args.show_branch:
                branch = gitmod.current_branch(directory)
            git_enabled = True
    elif not args.no_git and output_raw:
        git_root = detect.find_git_root(directory)
        if git_root is not None:
            from . import git as gitmod

            status_map = gitmod.batch_status(directory)
            for e in entries:
                e.git_status = status_map.get(e.name)
            git_enabled = True

    scanner.apply_scores(entries, now)

    group = True

    if subcommand == "recent":
        group = False
        entries.sort(key=lambda e: -e.mtime)

    elif subcommand == "large":
        group = False
        entries = [e for e in entries if e.kind != "dir"]
        entries.sort(key=lambda e: -e.size)

    elif subcommand == "dirty":
        if not git_enabled:
            print("wodilist dirty: not in a git repository", file=sys.stderr)
            sys.exit(2)
        entries = [e for e in entries if e.git_status is not None]
        group = False
        entries.sort(key=lambda e: -e.relevance)

    elif subcommand == "entry":
        entries = [e for e in entries if e.is_entry]
        group = False
        entries.sort(key=lambda e: -e.relevance)

    else:
        if not args.show_collapsed:
            pass
        entries = formatter.sort_entries(entries, group=True)

    if output_json:
        formatter.render_json(entries, now, branch=branch)
    elif output_raw:
        formatter.render_raw(entries, now, git_enabled=git_enabled)
    else:
        formatter.render_table(
            entries,
            color=color,
            width=width,
            now=now,
            branch=branch,
            git_enabled=git_enabled,
        )


def entrypoint() -> None:
    main()
