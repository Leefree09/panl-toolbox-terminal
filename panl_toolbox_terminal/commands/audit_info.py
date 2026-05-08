"""``panl audit-info`` — show visual-audit provenance for a .panl file."""

from __future__ import annotations

import os

from .. import naming
from .. import output as out
from .. import runner


HELP = "show visual-audit provenance for a .panl file"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "audit-info",
        help=HELP,
        description=HELP,
    )
    p.add_argument("file", help="path to a .panl (or legacy .kpow) file")
    p.set_defaults(func=run)


def run(args) -> int:
    path = args.file
    if not os.path.exists(path):
        out.error(f"file not found: {path}")
        return 2

    label = naming.file_label(path)

    # The engine already knows how to format audit info. Run it,
    # filter the output through the naming translator, and print
    # an opening header noting the file kind.
    print(f"{naming.PANL_NAME} audit info  ({label})")
    out.print_kv("Path", path)

    try:
        rc, _stdout, _stderr = runner.run_engine_cli(["audit-info", path])
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    return rc
