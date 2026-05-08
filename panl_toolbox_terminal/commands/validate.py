"""``panl validate`` — structural validation of a .panl (or .kpow) file."""

from __future__ import annotations

import os

from .. import naming
from .. import output as out
from .. import runner


HELP = "validate the structure of a .panl file"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "validate",
        help=HELP,
        description=HELP,
    )
    p.add_argument("file", help="path to a .panl (or legacy .kpow) file")
    p.add_argument(
        "--strict",
        action="store_true",
        help=(
            "warn on unknown chunk types, unknown codecs, and "
            "non-namespaced extension keys."
        ),
    )
    p.add_argument(
        "--decode-images",
        action="store_true",
        dest="decode_images",
        help=(
            "decode every page and thumbnail in its declared codec "
            "(needs Pillow + pillow_avif for AVIF)."
        ),
    )
    p.add_argument(
        "--source",
        default=None,
        help=(
            "original source archive (.cbz / .cbr / folder). When "
            "given, also runs visual audit against the source."
        ),
    )
    p.add_argument(
        "--visual-audit",
        choices=("none", "quick", "risky-only", "balanced", "strict", "auto"),
        default=None,
        help="visual-audit mode when --source is given.",
    )
    p.set_defaults(func=run)


def run(args) -> int:
    path = args.file
    if not os.path.exists(path):
        out.error(f"file not found: {path}")
        return 2

    label = naming.file_label(path)
    if label == "legacy KPOW":
        print(f"Validating legacy {naming.LEGACY_NAME} file ({path}).")

    if args.source:
        # Re-run validation against the source via the engine's
        # audit-quality command, which accepts the same audit flags.
        engine_args = [
            "audit-quality",
            path,
            args.source,
        ]
        if args.visual_audit:
            engine_args.extend(["--visual-audit", args.visual_audit])
        try:
            rc, _stdout, _stderr = runner.run_engine_cli(engine_args)
        except runner.EngineUnavailable as exc:
            out.error(str(exc))
            return 2
        return rc

    engine_args = ["validate", path]
    if args.strict:
        engine_args.append("--strict")
    if args.decode_images:
        engine_args.append("--decode-images")

    try:
        rc, _stdout, _stderr = runner.run_engine_cli(engine_args)
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    return rc
