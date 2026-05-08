"""``panl experimental`` — escape hatch to the underlying engine's CLI.

Lets advanced users reach the unstable / engineering-only knobs
(JXL candidates, delta compression, deep AVIF tuning, smart-mode
overrides, archive-smallest, ...) without bloating the main help.

Everything routed through here forwards to ``python -m kpow ...``
unchanged, so its arguments are whatever the underlying engine
currently accepts.
"""

from __future__ import annotations

from typing import List

from .. import naming
from .. import output as out
from .. import runner


HELP = (
    "advanced/experimental subcommands forwarded to the underlying "
    "engine. NOT recommended for normal use."
)


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "experimental",
        help=HELP,
        description=HELP,
        add_help=False,  # let the engine print its own help
    )
    p.add_argument(
        "passthrough",
        nargs=argparse_REMAINDER(),
        help="forwarded verbatim to the underlying engine.",
    )
    p.set_defaults(func=run)


def argparse_REMAINDER():
    """Local re-export so we don't import argparse at module top-level
    (keeps ``python -m panl_toolbox_terminal --help`` lean)."""
    import argparse
    return argparse.REMAINDER


def run(args) -> int:
    forwarded: List[str] = list(args.passthrough or [])
    if not forwarded:
        # No subcommand — print a friendly summary of what's
        # available behind the experimental gate.
        print(f"{naming.TOOL_NAME} - experimental commands")
        print()
        print(
            "These call into the underlying engine directly. They are\n"
            "not part of the stable PANL Toolbox Terminal CLI surface\n"
            "and may change between releases."
        )
        print()
        print(
            "Available passthrough subcommands include:\n"
            "  bootstrap       inspect the streamable BOOT chunk\n"
            "  dedup-info      inspect dedup map (DDUP)\n"
            "  compression-sample  estimate full-book smart-tile output size\n"
            "  list-chunks     list every chunk in the directory\n"
            "  pages           per-page table with codec / preset breakdown\n"
            "  tiles           tile grid for a single tiled page\n"
            "  panels          panel layout for one page\n"
            "  extract / extract-page / extract-thumb / extract-chunk / extract-tile\n"
            "  dump-json / dump-edit / set-edit\n"
            "  patch-metadata / patch-panels\n"
            "  set-extension / get-extension / remove-extension\n"
            "  edit-info / expand-edit / restream / migrate-edit\n"
            "  compare         source vs converted comparison\n"
            "  batch-benchmark / tune-speed / tune-avif-speed / tune-avif-effort\n"
            "  tune-avif-speed6\n"
            "\n"
            "Run `panl experimental <subcommand> --help` to see the\n"
            "engine's documentation for any of these. Output is\n"
            "translated through the PANL naming filter."
        )
        return 0

    try:
        rc, _stdout, _stderr = runner.run_engine_cli(forwarded)
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    return rc
