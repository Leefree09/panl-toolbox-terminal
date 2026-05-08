"""``panl`` / ``panl-toolbox`` — public CLI entry point."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from . import naming
from . import profiles
from .commands import (
    audit_info as cmd_audit_info,
    benchmark as cmd_benchmark,
    convert as cmd_convert,
    estimate as cmd_estimate,
    experimental as cmd_experimental,
    extensions as cmd_extensions,
    info as cmd_info,
    migrate as cmd_migrate,
    validate as cmd_validate,
)


PROG_NAME = "panl"
DESCRIPTION = (
    f"{naming.TOOL_NAME} - convert, inspect, validate, and migrate "
    f"{naming.PANL_NAME} comic container files (.panl)."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{naming.TOOL_NAME} {__version__}",
    )
    parser.add_argument(
        "--help-advanced",
        action="store_true",
        help="show experimental flags and lower-level subcommands.",
    )

    sub = parser.add_subparsers(dest="cmd", metavar="<command>")
    cmd_convert.register(sub)
    cmd_estimate.register(sub)
    cmd_info.register(sub)
    cmd_validate.register(sub)
    cmd_benchmark.register(sub)
    cmd_extensions.register(sub)
    cmd_audit_info.register(sub)
    cmd_migrate.register(sub)
    cmd_experimental.register(sub)

    return parser


def _print_help(parser: argparse.ArgumentParser, advanced: bool = False) -> None:
    parser.print_help()
    print()
    print("Profiles:")
    print(profiles.help_table())
    if advanced:
        print()
        print(
            "Advanced flags and engineering subcommands are exposed via\n"
            "  panl experimental <subcommand>\n"
            "Run `panl experimental --help` for the full list."
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # No subcommand: print our augmented help and exit non-zero so
    # tooling can detect "no input."
    if args.help_advanced:
        _print_help(parser, advanced=True)
        sys.exit(0)
    if not args.cmd:
        _print_help(parser)
        sys.exit(1)

    rc = args.func(args)
    if rc is None:
        rc = 0
    sys.exit(int(rc))


if __name__ == "__main__":
    main()
