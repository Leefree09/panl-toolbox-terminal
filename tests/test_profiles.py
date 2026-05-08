"""Profile name + internal id mapping."""

import pytest

from panl_toolbox_terminal import profiles


def test_default_profile_is_recommended():
    assert profiles.DEFAULT_PROFILE == "recommended"


def test_all_public_names_resolve():
    expected = {"recommended", "fast", "compact", "archival", "original"}
    assert set(profiles.ALL_PROFILES) == expected
    for name in expected:
        spec = profiles.resolve(name)
        assert spec.name == name
        assert spec.internal_id


def test_recommended_maps_to_locked_internal_id():
    spec = profiles.resolve("recommended")
    assert spec.internal_id == "reader-balanced-tiled-smart"


def test_fast_maps_to_a_fast_internal_id():
    spec = profiles.resolve("fast")
    # Either of these is acceptable as the engineering target.
    assert spec.internal_id in {
        "reader-fast-convert-tiled-smart",
        "reader-fast-tiled-smart",
    }


def test_archival_internal_id_is_a_deep_or_smallest_profile():
    spec = profiles.resolve("archival")
    assert spec.internal_id in {
        "reader-balanced-tiled-smart-deep",
        "reader-archive-tiled-smart",
        "archive-smallest",
        "reader-audit-tiled-smart",
    }


def test_original_maps_to_preserve_original():
    spec = profiles.resolve("original")
    assert spec.internal_id == "preserve-original"


def test_internal_aliases_resolve():
    # Internal ids are accepted but resolve to one of the public specs.
    spec = profiles.resolve("reader-balanced-tiled-smart")
    assert spec.name == "recommended"
    spec = profiles.resolve("preserve-original")
    assert spec.name == "original"
    spec = profiles.resolve("reader-fast-convert-tiled-smart")
    assert spec.name == "fast"


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        profiles.resolve("totally-fake-profile")


def test_public_name_for_internal_id_round_trip():
    for name, spec in profiles.ALL_PROFILES.items():
        assert profiles.public_name_for_internal_id(spec.internal_id) == name


def test_public_name_for_internal_id_unknown_returns_none():
    assert profiles.public_name_for_internal_id("not-a-real-profile") is None
    assert profiles.public_name_for_internal_id("") is None
    assert profiles.public_name_for_internal_id(None) is None


def test_help_table_lists_every_public_profile():
    text = profiles.help_table()
    for name in profiles.ALL_PROFILES:
        assert name in text
