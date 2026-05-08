"""Tiny formatting helpers shared by the inspection commands."""

from __future__ import annotations

import os
from typing import Iterable, List, Sequence


def fmt_size(n_bytes: float) -> str:
    """Format a byte count like ``11.13 MB``."""
    if n_bytes is None:
        return "?"
    n = float(n_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} TB"


def fmt_seconds(s: float) -> str:
    if s is None:
        return "?"
    if s < 1.0:
        return f"{s * 1000:.0f}ms"
    return f"{s:.1f}s"


def fmt_pct(p: float, sign: bool = False) -> str:
    if p is None:
        return "?"
    if sign:
        return f"{p:+.1f}%"
    return f"{p:.1f}%"


def file_size(path: str) -> int:
    return os.path.getsize(path)


def print_kv(label: str, value: str, *, indent: int = 0) -> None:
    pad = "  " * indent
    print(f"{pad}{label}: {value}")


def print_section(title: str) -> None:
    print(title)


def print_table(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> None:
    """Plain text table — used for small, fixed-shape data."""
    cols: List[List[str]] = [[h] + [str(r[i]) for r in rows] for i, h in enumerate(headers)]
    widths = [max(len(c) for c in col) for col in cols]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def warn(msg: str) -> None:
    import sys
    print(f"warning: {msg}", file=sys.stderr)


def error(msg: str) -> None:
    import sys
    print(f"error: {msg}", file=sys.stderr)
