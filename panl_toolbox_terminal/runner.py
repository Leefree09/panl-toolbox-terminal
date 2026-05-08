"""Adapters around the underlying engine.

Two layers:

* ``import_engine()`` — try to import the in-process ``kpow`` package
  for direct API calls (preferred for inspection commands so we can
  format output cleanly).
* ``run_engine_cli()`` — subprocess fallback for commands where the
  engine's CLI does too much for us to reasonably re-implement
  (encode pipelines, AVIF tuning, etc.). Output is filtered through
  the PANL naming translator before being printed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Iterable, List, Optional, Tuple

from . import naming


class EngineUnavailable(RuntimeError):
    """Raised when the underlying ``kpow`` engine can't be located."""


def import_engine():
    """Import the in-process engine module. Cached by Python."""
    try:
        import kpow  # noqa: F401  (imported for side effects)
        return __import__("kpow")
    except ImportError as exc:
        raise EngineUnavailable(
            "the underlying PANL engine package ('kpow') is not "
            "installed. Install it from the panl-format reference "
            "implementation to use PANL Toolbox Terminal."
        ) from exc


def run_engine_cli(
    args: Iterable[str],
    *,
    capture: bool = False,
    cwd: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Invoke ``python -m kpow`` with ``args`` and return
    ``(returncode, stdout, stderr)``.

    When ``capture`` is False (default), stdout / stderr stream live
    through naming-translation filters so PANL labels appear in
    real-time during long encodes. The returned strings are the
    captured text in either case.
    """
    full = [sys.executable, "-m", "kpow", *args]
    env = os.environ.copy()
    # Force UTF-8 output so the naming filter can run without
    # encode-decode surprises on Windows code pages.
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Ensure the engine's stdout/stderr are unbuffered, otherwise
    # per-page progress lines pile up in 4KB buffers and only
    # surface when the encode finishes.
    env.setdefault("PYTHONUNBUFFERED", "1")

    if capture:
        proc = subprocess.run(
            full,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            env=env,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    # Streaming: read line-by-line so the user sees progress, and
    # apply the naming filter on each line as it arrives.
    #
    # The engine's `kpow convert` writes per-page progress to
    # stderr and reserves stdout for the final summary block.
    # Reading the two pipes sequentially (stdout then stderr)
    # would hold every progress line back until the convert ends.
    # We merge stderr into stdout via subprocess.STDOUT so lines
    # arrive interleaved in real time. The downstream caller sees
    # everything on its stdout channel, which is what `panl info`,
    # `panl convert`, and the GUI all want.
    proc = subprocess.Popen(
        full,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
        bufsize=1,
    )
    out_buf: List[str] = []

    if proc.stdout is not None:
        for line in proc.stdout:
            translated = naming.translate_engine_text(line)
            sys.stdout.write(translated)
            sys.stdout.flush()
            out_buf.append(translated)

    rc = proc.wait()
    return rc, "".join(out_buf), ""
