"""``panl info`` — high-level summary of a .panl (or legacy .kpow) file."""

from __future__ import annotations

import os

from .. import naming
from .. import profiles
from .. import output as out
from .. import runner


HELP = "show a high-level summary of a .panl file"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "info",
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

    try:
        engine = runner.import_engine()
    except runner.EngineUnavailable as exc:
        out.error(str(exc))
        return 2

    label = naming.file_label(path)
    file_size = out.file_size(path)

    try:
        with engine.KpowReader(path) as r:
            try:
                manifest = r.read_manifest() or {}
            except Exception:
                manifest = {}
            try:
                pind = r.read_page_index() or {}
            except Exception:
                pind = {}

            print(f"{naming.PANL_NAME} info  ({label})")
            out.print_kv("Path", path)
            out.print_kv("Size", out.fmt_size(file_size))

            ver = manifest.get("version") or {}
            ver_label = (
                f"{ver.get('major', '?')}.{ver.get('minor', '?')}"
                if ver else "?"
            )
            out.print_kv("Format version", ver_label)

            declared = manifest.get("format")
            if declared and declared.upper() == "KPOW":
                out.print_kv("Declared format", f"{declared} (legacy KPOW)")
            elif declared:
                out.print_kv("Declared format", declared)

            try:
                streamable = bool(getattr(r, "is_streamable", False))
            except Exception:
                streamable = False
            out.print_kv("Layout", "streamable" if streamable else "classic")
            try:
                if getattr(r, "recovered_from_footer", False):
                    out.warn(
                        "header was clobbered; reader recovered via the footer."
                    )
            except Exception:
                pass

            page_count = manifest.get("pageCount") or len(pind.get("pages", []))
            out.print_kv("Pages", str(page_count or "?"))

            tiles = sum(
                len(p.get("tiles") or []) for p in pind.get("pages", [])
            )
            if tiles:
                out.print_kv("Tiles", str(tiles))

            cover = manifest.get("coverPage")
            if cover is not None:
                out.print_kv("Cover page", str(cover))
            rd = manifest.get("defaultReadingDirection")
            if rd:
                out.print_kv("Reading direction", rd)

            features = manifest.get("features") or {}
            if features:
                enabled = [k for k, v in features.items() if v]
                if enabled:
                    out.print_kv("Features", ", ".join(sorted(enabled)))

            # Profile / provenance — pulled from EDIT debug if present,
            # legacy PROV chunk otherwise. Always rendered with the
            # public profile name.
            profile_id = _provenance_profile(r)
            if profile_id:
                public = profiles.public_name_for_internal_id(profile_id)
                if public:
                    out.print_kv("Profile", f"{public} (internal: {profile_id})")
                else:
                    out.print_kv("Profile", profile_id)

            # EDIT extensions summary.
            ext_summary = _extension_summary(r)
            if ext_summary:
                out.print_section("EDIT extensions:")
                for label, count in ext_summary:
                    out.print_kv(label, str(count), indent=1)

            # Audit summary if recorded.
            audit = _audit_summary(r)
            if audit:
                out.print_kv("Audit", audit)

            print()
            print(
                "Run `panl validate` for a deeper structural check, "
                "or `panl extensions` for the full extension table."
            )
    except Exception as exc:
        out.error(f"could not open {path}: {exc}")
        return 2

    return 0


def _provenance_profile(reader) -> str:
    """Best-effort pull of the conversion profile id from a file."""
    try:
        if hasattr(reader, "read_edit_overlay"):
            overlay = reader.read_edit_overlay() or {}
            for ns in ("org.panl.debug", "org.kpow.debug"):
                ext = (overlay.get("extensions") or {}).get(ns) or {}
                for entry in reversed(ext.get("entries", []) or []):
                    if entry.get("category") == "conversion":
                        data = entry.get("data") or {}
                        return (
                            data.get("internalProfileId")
                            or data.get("profileId")
                            or data.get("profile")
                        )
    except Exception:
        pass
    try:
        prov = reader.read_provenance() or {}
        conv = (prov.get("conversion") or {})
        return conv.get("profile")
    except Exception:
        return None


def _extension_summary(reader):
    """Return ``[(label, count_summary), ...]`` for the EDIT extensions."""
    try:
        overlay = reader.read_edit_overlay() if hasattr(reader, "read_edit_overlay") else None
    except Exception:
        return []
    if not overlay:
        return []
    exts = overlay.get("extensions") or {}
    if not exts:
        return []
    rows = []
    for ns, payload in sorted(exts.items()):
        if ns.startswith("org.panl."):
            kind = "official"
        elif ns.startswith("org.kpow."):
            kind = "legacy KPOW"
        elif "." in ns:
            kind = "private"
        else:
            kind = "non-namespaced"
        size = len(__import__("json").dumps(payload, separators=(",", ":")))
        rows.append((f"  {ns:<28} {kind:<14}", out.fmt_size(size)))
    return [(label, value) for label, value in rows]


def _audit_summary(reader) -> str:
    try:
        if hasattr(reader, "read_edit_overlay"):
            overlay = reader.read_edit_overlay() or {}
            for ns in ("org.panl.debug", "org.kpow.debug"):
                ext = (overlay.get("extensions") or {}).get(ns) or {}
                for entry in reversed(ext.get("entries", []) or []):
                    if entry.get("category") in ("visual-audit", "audit"):
                        return entry.get("summary") or entry.get("level") or "present"
    except Exception:
        pass
    return ""
