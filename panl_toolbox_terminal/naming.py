"""Public-facing PANL naming.

The underlying engine still uses ``KPOW`` / ``.kpow`` / ``org.kpow.*``
in many user-visible strings (its CLI output, its provenance
records, its log lines). This wrapper presents PANL throughout, so
this module owns the small amount of logic that translates those
labels in passing.

We deliberately do NOT touch byte-level identifiers (file magic,
chunk type codes); those are part of the on-disk format and the
PANL spec keeps them as opaque v1 magic for compatibility. See
panl-format/spec/COMPATIBILITY.md.
"""

import os
import re
from typing import Optional

PANL_NAME = "PANL"
PANL_EXTENSION = ".panl"
LEGACY_NAME = "KPOW"
LEGACY_EXTENSION = ".kpow"

TOOL_NAME = "PANL Toolbox Terminal"
TOOL_ID = "panl-toolbox-terminal"


# Word-boundary patterns that swap KPOW → PANL in human-readable
# tool output without touching legitimate references like
# ``Hawkeye.kpow`` paths the user typed in or chunk-id strings
# inside JSON dumps. The CLI applies these only to free-form text
# emitted by the underlying engine; structured commands
# (``info``, ``validate``, etc.) print their own clean output.

_TOKEN_PATTERNS = [
    # "KPOW v1" -> "PANL v1"
    (re.compile(r"\bKPOW\b"), "PANL"),
    # ".kpow file" / ".kpow conversion" — informational sentences
    (re.compile(r"\.kpow file\b"),       ".panl file"),
    (re.compile(r"\.kpow files\b"),      ".panl files"),
    (re.compile(r"\.kpow conversion"),   ".panl conversion"),
    (re.compile(r"\bKpow\b"),            "Panl"),
    (re.compile(r"\bkpow CLI\b"),        "panl CLI"),
]


def translate_engine_text(text: str) -> str:
    """Swap KPOW/Kpow tokens for PANL in human-readable engine output.

    Leaves structural tokens (URLs, JSON keys like ``org.kpow.*``,
    paths the user typed in) alone unless they're part of the
    tokenised patterns above. Used to clean up stdout/stderr from
    delegated subprocess calls.
    """
    if not text:
        return text
    out = text
    for pat, repl in _TOKEN_PATTERNS:
        out = pat.sub(repl, out)
    return out


def is_legacy_extension(path: str) -> bool:
    """``True`` if the path ends in ``.kpow`` (case-insensitive)."""
    return path.lower().endswith(LEGACY_EXTENSION)


def is_panl_extension(path: str) -> bool:
    """``True`` if the path ends in ``.panl`` (case-insensitive)."""
    return path.lower().endswith(PANL_EXTENSION)


def file_label(path: str) -> str:
    """Short user-facing description of a file path's container kind.

    Used in messages like ``Reading legacy KPOW file foo.kpow`` so
    the user always knows which side of the rename their file is
    on.
    """
    if is_legacy_extension(path):
        return "legacy KPOW"
    if is_panl_extension(path):
        return PANL_NAME
    return "container"


def default_output_path(input_path: str, output_path: Optional[str] = None) -> str:
    """Derive the ``.panl`` output path for a conversion.

    - If ``output_path`` is provided, return it unchanged.
    - Otherwise replace the input's extension with ``.panl``,
      placing the result next to the input.
    """
    if output_path:
        return output_path
    base, _ = os.path.splitext(input_path)
    return base + PANL_EXTENSION


def panl_to_kpow_path(panl_path: str) -> str:
    """Sibling helper: a ``.panl`` path mapped to the same base with
    ``.kpow`` extension. Used internally when the underlying engine
    insists on a ``.kpow`` filename for a transient operation."""
    base, _ = os.path.splitext(panl_path)
    return base + LEGACY_EXTENSION
