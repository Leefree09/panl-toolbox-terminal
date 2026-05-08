"""``panl estimate`` — preflight size / time / savings estimate."""

from __future__ import annotations

from .. import naming
from .. import profiles
from .. import output as out
from .. import runner


HELP = "preflight estimate for a comic source: predict output size, savings, time, and recommendation"

DESCRIPTION = (
    "Preflight estimate for a comic source: predict output size, "
    "savings %, conversion time, and emit a recommendation. The "
    "estimator runs the smart-tile selector on a sample of pages "
    "and extrapolates; it does not write a .panl file."
)


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "estimate",
        help=HELP,
        description=DESCRIPTION,
    )
    p.add_argument("input", help="source file (.cbz / .cbr / folder)")
    p.add_argument(
        "--profile",
        default=profiles.DEFAULT_PROFILE,
        choices=list(profiles.ALL_PROFILES) + list(profiles._INTERNAL_TO_PUBLIC.keys()),
        metavar="PROFILE",
        help=(
            f"profile to estimate against (default: {profiles.DEFAULT_PROFILE}). "
            f"One of: {', '.join(profiles.ALL_PROFILES)}."
        ),
    )
    p.add_argument(
        "--sample-pages", type=int, default=None,
        help="number of pages to sample (default: 20).",
    )
    p.add_argument(
        "--json", default=None, dest="json_out",
        help="write the estimate as JSON to this path.",
    )
    p.add_argument(
        "--quiet", action="store_true",
        help="suppress the human-readable report. Useful with --json.",
    )
    p.set_defaults(func=run)


def run(args) -> int:
    profile_spec = profiles.resolve(args.profile)
    engine_args = [
        "estimate",
        args.input,
        "--profile",
        profile_spec.internal_id,
    ]
    if args.sample_pages is not None:
        engine_args.extend(["--sample-pages", str(args.sample_pages)])
    if args.json_out:
        engine_args.extend(["--json", args.json_out])
    if args.quiet:
        engine_args.append("--quiet")

    if not args.quiet:
        print(f"{naming.PANL_NAME} estimate")
        out.print_kv("Profile", profile_spec.name)

    try:
        rc, _stdout, _stderr = runner.run_engine_cli(engine_args)
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    return rc
