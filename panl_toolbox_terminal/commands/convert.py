"""``panl convert`` — convert a CBZ/CBR/folder source into a ``.panl`` file."""

from __future__ import annotations

import os
import sys
import time
from typing import List

from .. import naming
from .. import profiles
from .. import output as out
from .. import runner


HELP = "convert a comic source (.cbz / .cbr / folder) into a .panl file"

CONVERT_EPILOG = f"""\
Profiles:
{profiles.help_table()}

Examples:
  panl convert input.cbz                       # input.panl, recommended profile
  panl convert input.cbz output.panl           # explicit output path
  panl convert input.cbz --profile original    # preserve source bytes
  panl convert input.cbz --validate            # validate the result

Use `panl convert --help-advanced` (or `panl experimental --help`)
for fine-grained encoder, audit, and AVIF tuning flags.
"""


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "convert",
        help=HELP,
        description=HELP,
        epilog=CONVERT_EPILOG,
        formatter_class=__import__("argparse").RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="source file (.cbz / .cbr / folder)")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help=f"output {naming.PANL_EXTENSION} path (default: alongside input)",
    )
    p.add_argument(
        "--profile",
        default=profiles.DEFAULT_PROFILE,
        choices=list(profiles.ALL_PROFILES) + [
            # Internal aliases — tolerated but not advertised.
            *profiles._INTERNAL_TO_PUBLIC.keys(),
        ],
        metavar="PROFILE",
        help=(
            f"conversion profile (default: {profiles.DEFAULT_PROFILE}). "
            f"One of: {', '.join(profiles.ALL_PROFILES)}."
        ),
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite the output file if it already exists.",
    )
    p.add_argument(
        "--validate",
        action="store_true",
        help="re-open and validate the output after conversion.",
    )
    p.add_argument(
        "--quiet", "-q", action="store_true",
        help="suppress per-page progress.",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true",
        help="print per-page details from the underlying engine.",
    )
    # Friendly CPU controls.
    p.add_argument(
        "--cpu-mode",
        choices=("low", "balanced", "max"),
        default=None,
        help="parallelism preset. low keeps the system responsive; "
             "balanced is the safe default; max saturates the box.",
    )
    p.add_argument(
        "--jobs", "-j", default=None, metavar="N",
        help="explicit worker count (or one of: auto, balanced, max, low).",
    )
    p.add_argument(
        "--no-thumbnails",
        action="store_true",
        help="skip thumbnail generation.",
    )
    p.set_defaults(func=run)


def _prepare_engine_args(args) -> List[str]:
    profile_spec = profiles.resolve(args.profile)
    output_path = naming.default_output_path(args.input, args.output)

    engine_args: List[str] = [
        "convert",
        args.input,
        output_path,
        "--profile",
        profile_spec.internal_id,
    ]
    if args.overwrite:
        engine_args.append("--overwrite")
    if args.validate:
        engine_args.append("--validate")
    if args.verbose:
        engine_args.append("--verbose")
    if args.no_thumbnails:
        engine_args.extend(["--thumbnails", "none"])
    if args.cpu_mode:
        engine_args.extend(["--cpu-mode", args.cpu_mode])
    if args.jobs:
        engine_args.extend(["--jobs", str(args.jobs)])
    return engine_args, profile_spec, output_path


def _print_summary(args, profile_spec, output_path: str, elapsed: float) -> None:
    """Print the public conversion summary in PANL house style."""
    if not os.path.exists(output_path):
        # Engine failed to produce the output but didn't raise; the
        # underlying CLI already printed an error.
        return

    in_size  = out.file_size(args.input) if os.path.exists(args.input) else None
    out_size = out.file_size(output_path)
    saved_pct = None
    if in_size and out_size and in_size > 0:
        saved_pct = (in_size - out_size) * 100.0 / in_size

    pages_read = tiles_read = audit_status = audit_repairs = None
    validation_status = "ok" if args.validate else "skipped"

    # Best-effort post-mortem read of the file via the engine to
    # surface page count / tile count / audit state.
    try:
        engine = runner.import_engine()
        with engine.KpowReader(output_path) as r:
            try:
                pind = r.read_page_index()
                pages_read = len(pind.get("pages", []))
                tiles_read = sum(
                    len(p.get("tiles") or []) for p in pind.get("pages", [])
                )
            except Exception:
                pass
            try:
                # Audit info lives under the EDIT debug extension or
                # legacy provenance; pick whichever is present.
                if hasattr(r, "read_edit_overlay"):
                    overlay = r.read_edit_overlay() or {}
                    debug = (overlay.get("extensions") or {}).get(
                        "org.kpow.debug"
                    ) or (overlay.get("extensions") or {}).get(
                        "org.panl.debug"
                    ) or {}
                    for entry in reversed(debug.get("entries", []) or []):
                        if entry.get("category") in ("visual-audit", "audit"):
                            audit_status = entry.get("level") or "info"
                            audit_repairs = (entry.get("data") or {}).get(
                                "repairs"
                            )
                            break
            except Exception:
                pass
    except runner.EngineUnavailable:
        pass
    except Exception:
        pass

    print()
    print(f"{naming.PANL_NAME} conversion complete")
    if in_size is not None:
        out.print_kv("Input ", f"{args.input} {out.fmt_size(in_size)}")
    else:
        out.print_kv("Input ", args.input)
    out.print_kv("Output", f"{output_path} {out.fmt_size(out_size)}")
    if saved_pct is not None:
        out.print_kv("Saved ", out.fmt_pct(saved_pct))
    if pages_read is not None:
        out.print_kv("Pages ", str(pages_read))
    if tiles_read:
        out.print_kv("Tiles ", str(tiles_read))
    out.print_kv("Time  ", out.fmt_seconds(elapsed))
    out.print_kv("Profile", profile_spec.name)
    if audit_status is not None:
        repair_note = (
            f", {audit_repairs} repair{'s' if (audit_repairs or 0) != 1 else ''}"
            if audit_repairs is not None else ""
        )
        out.print_kv("Audit ", f"{audit_status}{repair_note}")
    out.print_kv("Validation", validation_status)


def run(args) -> int:
    profile_spec = profiles.resolve(args.profile)

    if naming.is_legacy_extension(args.input):
        out.warn(
            f"input has the legacy {naming.LEGACY_EXTENSION} extension; "
            f"that's typically a converted file, not a source. To "
            f"re-encode a {naming.LEGACY_NAME} file as {naming.PANL_NAME}, "
            f"use `panl migrate` instead."
        )

    engine_args, profile_spec, output_path = _prepare_engine_args(args)

    if profile_spec.audit_note and not args.quiet:
        print(profile_spec.audit_note)

    started = time.monotonic()
    try:
        rc, _stdout, _stderr = runner.run_engine_cli(engine_args)
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2
    elapsed = time.monotonic() - started

    if rc != 0:
        return rc

    _print_summary(args, profile_spec, output_path, elapsed)
    return 0
