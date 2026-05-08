"""Public PANL profile names and their internal mapping.

PANL Toolbox Terminal exposes five user-facing profiles. Each maps
to one of the locked engineering profile ids in the reference
encoder. Internal ids are kept for benchmark traceability and
recorded in provenance, but normal users never see them.
"""

from collections import OrderedDict
from typing import NamedTuple, Optional


class ProfileSpec(NamedTuple):
    """A user-facing profile and the underlying engineering id."""

    name: str                 # public name shown in help / output
    internal_id: str          # passed to the underlying engine as --profile
    summary: str              # one-line description for `panl convert --help`
    audit_note: Optional[str] # extra notice printed during conversion


# The flagship default. Frozen — see panl-format/spec/PROFILES.md.
PROFILE_RECOMMENDED = ProfileSpec(
    name="recommended",
    internal_id="reader-balanced-tiled-smart",
    summary=(
        "default. 512 tiled pages, AVIF speed=6 cq=20 chroma 4:2:0 "
        "with autotiling, decode-only candidate gate, adaptive "
        "risky-tile audit + targeted repair, streamable layout, "
        "EDIT/extensions enabled."
    ),
    audit_note=None,
)

PROFILE_FAST = ProfileSpec(
    name="fast",
    internal_id="reader-fast-convert-tiled-smart",
    summary=(
        "quicker conversion, lower assurance. Lighter audit; good "
        "for previews and bulk imports."
    ),
    audit_note=(
        "Note: Fast profile reduces audit coverage compared to "
        "Recommended."
    ),
)

# Compact maps to the smart-light profile, which adds palette /
# WebP-lossless candidates on top of the AVIF baseline. This is
# already shipping; the public name signals "smaller files" without
# exposing the smart-light/smart-deep distinction.
PROFILE_COMPACT = ProfileSpec(
    name="compact",
    internal_id="reader-balanced-tiled-smart-light",
    summary=(
        "more aggressive visually-lossless settings: palette + "
        "WebP-lossless candidates added on top of AVIF. Smaller "
        "output, slower than Recommended."
    ),
    audit_note=None,
)

# Archival is the deep / strict-audit profile.
PROFILE_ARCHIVAL = ProfileSpec(
    name="archival",
    internal_id="reader-balanced-tiled-smart-deep",
    summary=(
        "strictest audit, slowest, maximum confidence. For "
        "long-term storage or suspicious sources."
    ),
    audit_note="Note: Archival runs the strict audit ladder; expect 5-7x Recommended runtime.",
)

# Original preserves source bytes verbatim.
PROFILE_ORIGINAL = ProfileSpec(
    name="original",
    internal_id="preserve-original",
    summary=(
        "preserve original image bytes inside the PANL container. "
        "Useful for sources with little compression headroom or "
        "bloat risk. Metadata + EDIT extensions still written."
    ),
    audit_note=None,
)

# Order matters for help output.
ALL_PROFILES = OrderedDict([
    (PROFILE_RECOMMENDED.name, PROFILE_RECOMMENDED),
    (PROFILE_FAST.name,        PROFILE_FAST),
    (PROFILE_COMPACT.name,     PROFILE_COMPACT),
    (PROFILE_ARCHIVAL.name,    PROFILE_ARCHIVAL),
    (PROFILE_ORIGINAL.name,    PROFILE_ORIGINAL),
])

DEFAULT_PROFILE = PROFILE_RECOMMENDED.name


# Reverse map from internal id (or any known alias) back to a public
# profile spec, for telling the user what kind of file they're
# looking at when `info` / `audit-info` etc. report on something
# that was produced under an internal-only profile name.
_INTERNAL_TO_PUBLIC = {
    "reader-balanced-tiled-smart":        PROFILE_RECOMMENDED,
    "reader-balanced-tiled-smart-light":  PROFILE_COMPACT,
    "reader-balanced-tiled-smart-deep":   PROFILE_ARCHIVAL,
    "reader-balanced-tiled-smart-tune":   PROFILE_ARCHIVAL,
    "reader-fast-convert-tiled-smart":    PROFILE_FAST,
    "reader-balanced-collection-fast":    PROFILE_FAST,
    "reader-archive-tiled-smart":         PROFILE_ARCHIVAL,
    "reader-mixed-tiled-smart":           PROFILE_COMPACT,
    "reader-fast-tiled-smart":            PROFILE_FAST,
    "reader-audit-tiled-smart":           PROFILE_ARCHIVAL,
    "archive-smallest":                   PROFILE_ARCHIVAL,
    "preserve-original":                  PROFILE_ORIGINAL,
}


def resolve(name_or_id: str) -> ProfileSpec:
    """Resolve a user-supplied profile string.

    Accepts the public names (``recommended``/``fast``/``compact``/
    ``archival``/``original``) and the internal engineering ids /
    aliases. Raises ``ValueError`` for unknown values.
    """
    if name_or_id is None:
        raise ValueError("profile name is required")
    key = name_or_id.strip().lower()
    if key in ALL_PROFILES:
        return ALL_PROFILES[key]
    if key in _INTERNAL_TO_PUBLIC:
        return _INTERNAL_TO_PUBLIC[key]
    raise ValueError(
        f"unknown profile: {name_or_id!r}. "
        f"Valid: {', '.join(ALL_PROFILES)}"
    )


def public_name_for_internal_id(internal_id: str) -> Optional[str]:
    """Best-effort reverse mapping for telling a user which public
    profile produced a given file. Returns ``None`` for unknowns."""
    if not internal_id:
        return None
    spec = _INTERNAL_TO_PUBLIC.get(internal_id.strip().lower())
    return spec.name if spec else None


def help_table() -> str:
    """Pretty profile listing for ``panl convert --help`` and the README."""
    rows = []
    for spec in ALL_PROFILES.values():
        rows.append(f"  {spec.name:<13} {spec.summary}")
    return "\n".join(rows)
