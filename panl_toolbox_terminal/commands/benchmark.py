"""``panl benchmark`` — measure open / read / decode times against a .panl file."""

from __future__ import annotations

import os

from .. import naming
from .. import output as out
from .. import runner


HELP = "time open/read/decode operations against a .panl file"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "benchmark",
        help=HELP,
        description=HELP,
    )
    p.add_argument("file", help="path to a .panl (or legacy .kpow) file")
    p.add_argument(
        "--pages",
        default=None,
        help="comma-separated page indices (default: cover/middle/last + sample).",
    )
    p.add_argument(
        "--sample", type=int, default=5,
        help="number of random sample pages when --pages is not given.",
    )
    p.add_argument(
        "--no-decode-images",
        action="store_true",
        help="skip codec-level decode benchmarks (container/read only).",
    )
    p.add_argument(
        "--regions",
        action="store_true",
        help="benchmark a centered 30%% region decode for each tiled sample page.",
    )
    p.add_argument(
        "--simulate-range",
        action="store_true",
        dest="simulate_range",
        help="estimate range-read behaviour for streamable files.",
    )
    p.add_argument(
        "--json", default=None, dest="json_out",
        help="write the report as JSON to this path (suppresses text output).",
    )
    p.set_defaults(func=run)


def run(args) -> int:
    path = args.file
    if not os.path.exists(path):
        out.error(f"file not found: {path}")
        return 2

    if not args.json_out:
        print(f"{naming.PANL_NAME} benchmark  ({naming.file_label(path)})")
        out.print_kv("Path", path)

    engine_args = ["benchmark", path, "--sample", str(args.sample)]
    if args.pages:
        engine_args.extend(["--pages", args.pages])
    if args.no_decode_images:
        engine_args.append("--no-decode-images")
    if args.regions:
        engine_args.append("--regions")
    if args.simulate_range:
        engine_args.append("--simulate-range")
    if args.json_out:
        engine_args.extend(["--json", args.json_out])

    try:
        rc, _stdout, _stderr = runner.run_engine_cli(engine_args)
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    return rc
