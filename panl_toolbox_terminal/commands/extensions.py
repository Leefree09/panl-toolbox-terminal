"""``panl extensions`` — list every extension in a file's EDIT overlay."""

from __future__ import annotations

import json
import os

from .. import naming
from .. import output as out
from .. import runner


HELP = "list every EDIT extension in a .panl file"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "extensions",
        help=HELP,
        description=HELP,
    )
    p.add_argument("file", help="path to a .panl (or legacy .kpow) file")
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="emit raw JSON {namespace: payload} instead of the table.",
    )
    p.set_defaults(func=run)


def _classify(namespace: str) -> str:
    """Return ``official``/``legacy KPOW``/``private``/``unknown``."""
    if namespace.startswith("org.panl."):
        return "official"
    if namespace.startswith("org.kpow."):
        return "legacy KPOW"
    if "." in namespace:
        return "private"
    return "unknown"


def run(args) -> int:
    path = args.file
    if not os.path.exists(path):
        out.error(f"file not found: {path}")
        return 2

    try:
        engine = runner.import_engine()
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2

    try:
        with engine.KpowReader(path) as r:
            overlay = r.read_edit_overlay() if hasattr(r, "read_edit_overlay") else None
    except Exception as exc:
        out.error(f"could not open {path}: {exc}")
        return 2

    if not overlay:
        if args.json_out:
            print("{}")
            return 0
        print("No EDIT overlay (or empty).")
        return 0

    extensions = overlay.get("extensions") or {}
    if args.json_out:
        print(json.dumps(extensions, indent=2, sort_keys=True))
        return 0

    if not extensions:
        # Legacy flat shape — no extensions key.
        legacy_keys = sorted(k for k in overlay if k != "schemaVersion")
        if legacy_keys:
            print(f"Legacy flat-shape EDIT overlay (pre-extension; {naming.LEGACY_NAME}).")
            print("Run `panl migrate` to upgrade to the extension shape.")
            for k in legacy_keys:
                size = len(json.dumps(overlay[k], separators=(",", ":")))
                print(f"  {k:<30} flat-field            {out.fmt_size(size)}")
        else:
            print("No EDIT extensions present.")
        return 0

    rows = []
    warnings = []
    for ns in sorted(extensions):
        payload = extensions[ns] or {}
        kind = _classify(ns)
        sv = payload.get("schemaVersion") if isinstance(payload, dict) else None
        size = len(json.dumps(payload, separators=(",", ":")))
        rows.append((ns, kind, sv or "-", out.fmt_size(size)))
        if isinstance(payload, dict) and "schemaVersion" not in payload:
            warnings.append(f"{ns}: missing schemaVersion")
        if kind == "unknown":
            warnings.append(f"{ns}: extension key is not namespaced")
        if kind == "legacy KPOW":
            warnings.append(
                f"{ns}: legacy KPOW namespace; run `panl migrate` to "
                f"rewrite as org.panl.*."
            )

    out.print_table(
        rows,
        headers=("namespace", "kind", "schemaVersion", "size"),
    )
    if warnings:
        print()
        for w in warnings:
            out.warn(w)
    return 0
