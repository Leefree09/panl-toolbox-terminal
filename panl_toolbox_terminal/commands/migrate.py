"""``panl migrate`` — read a legacy .kpow file and write a .panl with
``org.kpow.*`` extensions migrated to ``org.panl.*``.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from typing import Dict

from .. import naming
from .. import output as out
from .. import runner


HELP = "read a legacy .kpow file and write a .panl with extensions migrated to org.panl.*"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "migrate",
        help=HELP,
        description=HELP,
    )
    p.add_argument(
        "input",
        help="legacy .kpow file (or any container the engine can read).",
    )
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help=f"output .panl path (default: alongside the input).",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite the output file if it already exists.",
    )
    p.add_argument(
        "--keep-legacy-namespaces",
        action="store_true",
        dest="keep_legacy",
        help=(
            "leave org.kpow.* extensions in place and only ADD "
            "org.panl.* aliases (default: rewrite the legacy keys "
            "to org.panl.* and drop the legacy duplicates)."
        ),
    )
    p.set_defaults(func=run)


# Mapping defined by panl-format/spec/COMPATIBILITY.md.
LEGACY_TO_PANL = {
    "org.kpow.metadata":          "org.panl.metadata",
    "org.kpow.presentation":      "org.panl.presentation",
    "org.kpow.preferences":       "org.panl.preferences",
    "org.kpow.panels":            "org.panl.panels",
    "org.kpow.page-roles":        "org.panl.page-roles",
    "org.kpow.debug":             "org.panl.debug",
    # panel-detections folds into the debug extension; we mark the
    # original entries with category="panel-detection" when migrating.
}


def _migrate_extensions(extensions: Dict[str, dict], keep_legacy: bool) -> Dict[str, dict]:
    """Apply the legacy → PANL extension mapping. Preserves unknowns."""
    new: Dict[str, dict] = {}
    legacy_to_drop = set()

    for ns, payload in extensions.items():
        if ns in LEGACY_TO_PANL:
            target = LEGACY_TO_PANL[ns]
            if target in extensions:
                # Both shapes present already; keep PANL, leave the
                # legacy alone. The user can re-run with
                # --keep-legacy-namespaces=false to drop it.
                new[ns] = payload
                continue
            new[target] = payload
            if not keep_legacy:
                legacy_to_drop.add(ns)
            else:
                new[ns] = payload
        elif ns == "org.kpow.panel-detections":
            # Fold into org.panl.debug as panel-detection entries.
            debug = new.setdefault("org.panl.debug", {
                "schemaVersion": "1.0",
                "entries": [],
            })
            debug.setdefault("entries", [])
            now_ms = int(time.time() * 1000)
            debug["entries"].append({
                "id": f"dbg-{now_ms}-panel-det-migrated",
                "createdAtMs": now_ms,
                "source": naming.TOOL_ID,
                "category": "panel-detection",
                "level": "info",
                "summary": "Migrated from org.kpow.panel-detections.",
                "data": payload,
            })
            if keep_legacy:
                new[ns] = payload
            else:
                legacy_to_drop.add(ns)
        else:
            # Unknown extension — preserved verbatim. This is the
            # most important rule in the extension model.
            new[ns] = payload

    for ns in legacy_to_drop:
        new.pop(ns, None)
    return new


def _record_migration(overlay: dict, summary: str) -> None:
    """Append a `compat-migration` debug entry."""
    extensions = overlay.setdefault("extensions", {})
    debug = extensions.setdefault("org.panl.debug", {
        "schemaVersion": "1.0",
        "entries": [],
    })
    debug.setdefault("entries", [])
    now_ms = int(time.time() * 1000)
    debug["entries"].append({
        "id": f"dbg-{now_ms}-migration",
        "createdAtMs": now_ms,
        "source": naming.TOOL_ID,
        "category": "compat-migration",
        "level": "info",
        "summary": summary,
        "data": {
            "tool": naming.TOOL_NAME,
            "fromExtension": naming.LEGACY_EXTENSION,
            "toExtension": naming.PANL_EXTENSION,
            "namespaceMapping": LEGACY_TO_PANL,
        },
    })


def run(args) -> int:
    src = args.input
    if not os.path.exists(src):
        out.error(f"file not found: {src}")
        return 2

    dst = args.output or naming.default_output_path(src, None)
    if os.path.abspath(src) == os.path.abspath(dst):
        out.error(
            f"input and output paths are the same ({src}). "
            f"Pick a different output path."
        )
        return 1
    if os.path.exists(dst) and not args.overwrite:
        out.error(
            f"{dst} already exists. Pass --overwrite to replace it."
        )
        return 1

    try:
        engine = runner.import_engine()
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2

    src_label = naming.file_label(src)
    print(f"{naming.PANL_NAME} migrate  ({src_label} -> {naming.PANL_NAME})")
    out.print_kv("Input ", f"{src} {out.fmt_size(out.file_size(src))}")
    out.print_kv("Output", dst)

    # Step 1: copy the bytes verbatim. We don't re-encode anything —
    # the on-disk format is the same in v1, only the namespaces and
    # extension labels differ.
    shutil.copyfile(src, dst)

    # Step 2: read the EDIT overlay, migrate namespaces, write back.
    try:
        overlay_before = None
        if hasattr(engine, "_editor"):
            overlay_before = engine._editor.read_edit_overlay(dst)
        else:
            with engine.KpowReader(dst) as r:
                overlay_before = (
                    r.read_edit_overlay()
                    if hasattr(r, "read_edit_overlay")
                    else None
                )
    except Exception as exc:
        out.warn(f"could not read EDIT overlay from {dst}: {exc}")
        overlay_before = None

    if not overlay_before:
        print("No EDIT overlay present; no extension migration required.")
        return 0

    extensions_before = overlay_before.get("extensions") or {}
    if not extensions_before:
        # Legacy flat-shape overlay; we can't migrate that here
        # without rewriting the EDIT JSON shape itself. Punt to the
        # engine's migrate-edit which knows the flat shape.
        print(
            "Legacy flat-shape EDIT overlay detected; running "
            "engine migrate-edit to upgrade in place."
        )
        rc, _stdout, _stderr = runner.run_engine_cli(["migrate-edit", dst])
        return rc

    extensions_after = _migrate_extensions(
        extensions_before, keep_legacy=args.keep_legacy
    )

    overlay_after = dict(overlay_before)
    overlay_after["extensions"] = extensions_after
    overlay_after["updatedAtMs"] = int(time.time() * 1000)

    summary_parts = []
    for legacy_ns, panl_ns in LEGACY_TO_PANL.items():
        if legacy_ns in extensions_before and panl_ns in extensions_after:
            summary_parts.append(f"{legacy_ns}->{panl_ns}")
    if "org.kpow.panel-detections" in extensions_before:
        summary_parts.append(
            "org.kpow.panel-detections->org.panl.debug(panel-detection)"
        )

    if summary_parts:
        _record_migration(
            overlay_after,
            summary=(
                f"Migrated by {naming.TOOL_NAME}: "
                + ", ".join(summary_parts)
            ),
        )

    try:
        if hasattr(engine, "_editor"):
            engine._editor.update_edit_overlay(dst, overlay_after)
        else:
            # Fallback: invoke the engine's set-edit subcommand with
            # a temp file holding the new overlay.
            import tempfile
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".json", delete=False
            ) as tf:
                json.dump(overlay_after, tf)
                tmp_path = tf.name
            try:
                rc, _stdout, _stderr = runner.run_engine_cli(
                    ["set-edit", dst, tmp_path]
                )
                if rc != 0:
                    out.error(
                        "engine set-edit failed; the output file's "
                        "EDIT overlay may be partially migrated."
                    )
                    return rc
            finally:
                os.unlink(tmp_path)
    except Exception as exc:
        out.error(f"could not write migrated EDIT overlay: {exc}")
        return 2

    migrated_keys = sorted(set(extensions_before) - set(extensions_after))
    new_keys = sorted(set(extensions_after) - set(extensions_before))
    if migrated_keys or new_keys:
        print()
        if migrated_keys:
            print(f"Removed legacy extensions: {', '.join(migrated_keys)}")
        if new_keys:
            print(f"Added official extensions: {', '.join(new_keys)}")
    print(f"Migration recorded in org.panl.debug (category compat-migration).")
    print(f"{naming.PANL_NAME} migration complete: {dst}")
    return 0
