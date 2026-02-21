from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path


def _make_synthetic_dir(n_files: int = 200) -> str:
    d = tempfile.mkdtemp(prefix="wodilist_bench_")
    exts = [".py", ".txt", ".md", ".json", ".yaml", ".sh", ".toml", ""]
    for i in range(n_files):
        ext = exts[i % len(exts)]
        Path(d, f"file_{i:04d}{ext}").write_text("x" * (i % 512))

    for noise in ("node_modules", ".venv", "__pycache__"):
        Path(d, noise).mkdir()

    for s in ("src", "tests", "docs"):
        Path(d, s).mkdir()
    return d


def bench_import(n: int = 5) -> float:
    import importlib
    import wodilist.scanner as mod
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        importlib.reload(mod)
        times.append(time.perf_counter() - t0)
    return min(times)


def bench_scan(directory: str, n: int = 20) -> float:
    from wodilist.scanner import scan
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        scan(directory)
        times.append(time.perf_counter() - t0)
    return min(times)


def bench_full_pipeline(directory: str, n: int = 20) -> float:
    from wodilist.scanner import scan, apply_scores
    from wodilist.formatter import sort_entries, render_raw
    import io

    times = []
    now = time.time()
    for _ in range(n):
        t0 = time.perf_counter()
        entries = scan(directory)
        apply_scores(entries, now)
        sorted_ = sort_entries(entries)

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            render_raw(sorted_, now)
        finally:
            sys.stdout = old_stdout

        times.append(time.perf_counter() - t0)
    return min(times)


def main() -> None:
    print("Building synthetic directory...")
    d = _make_synthetic_dir(200)
    print(f"  dir: {d}")
    print(f"  files: {len(os.listdir(d))}")
    print()

    import_ms = bench_import() * 1000
    scan_ms   = bench_scan(d) * 1000
    full_ms   = bench_full_pipeline(d) * 1000

    print(f"{'import (reload proxy)':<30} {import_ms:>8.2f} ms")
    print(f"{'scan() 200-file dir':<30} {scan_ms:>8.2f} ms")
    print(f"{'full pipeline':<30} {full_ms:>8.2f} ms")
    print()

    target_ms = 50.0
    status = "PASS ✓" if full_ms < target_ms else f"FAIL ✗  (target: {target_ms}ms)"
    print(f"Full pipeline vs {target_ms}ms target: {status}")

    import shutil
    shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()