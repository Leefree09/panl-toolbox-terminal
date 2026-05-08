"""Migration logic — exercised against in-memory dicts so the test
doesn't need the underlying engine."""

from panl_toolbox_terminal.commands import migrate


def test_legacy_to_panl_mapping_covers_official_namespaces():
    expected_legacy = {
        "org.kpow.metadata",
        "org.kpow.presentation",
        "org.kpow.preferences",
        "org.kpow.panels",
        "org.kpow.page-roles",
        "org.kpow.debug",
    }
    assert expected_legacy.issubset(set(migrate.LEGACY_TO_PANL))
    for legacy, panl in migrate.LEGACY_TO_PANL.items():
        assert panl.startswith("org.panl.")
        assert legacy.replace("org.kpow.", "org.panl.") == panl


def test_migrate_extensions_swaps_namespaces():
    extensions = {
        "org.kpow.metadata":     {"schemaVersion": "1.0", "title": "Hawkeye"},
        "org.kpow.preferences":  {"schemaVersion": "1.0", "readingDirection": "ltr"},
        "com.panel-flip":        {"schemaVersion": "1.0", "matchScore": 0.9},
    }
    out = migrate._migrate_extensions(extensions, keep_legacy=False)
    assert "org.panl.metadata" in out
    assert "org.panl.preferences" in out
    assert out["org.panl.metadata"]["title"] == "Hawkeye"
    # Legacy keys dropped by default.
    assert "org.kpow.metadata" not in out
    assert "org.kpow.preferences" not in out
    # Unknown / private extensions preserved verbatim.
    assert out["com.panel-flip"] == extensions["com.panel-flip"]


def test_migrate_extensions_keep_legacy_keeps_both():
    extensions = {
        "org.kpow.metadata": {"schemaVersion": "1.0", "title": "Hawkeye"},
    }
    out = migrate._migrate_extensions(extensions, keep_legacy=True)
    assert out["org.panl.metadata"] == extensions["org.kpow.metadata"]
    assert out["org.kpow.metadata"] == extensions["org.kpow.metadata"]


def test_migrate_extensions_panel_detections_folds_into_debug():
    extensions = {
        "org.kpow.panel-detections": {"detector": "opencv_v1", "pages": []},
    }
    out = migrate._migrate_extensions(extensions, keep_legacy=False)
    assert "org.panl.debug" in out
    debug = out["org.panl.debug"]
    assert debug["schemaVersion"] == "1.0"
    entries = debug.get("entries") or []
    assert any(e.get("category") == "panel-detection" for e in entries)
    # Fold means the original key is gone (since keep_legacy=False).
    assert "org.kpow.panel-detections" not in out


def test_migrate_extensions_does_not_overwrite_existing_panl_namespace():
    """When both org.kpow.x and org.panl.x are present (an edge case
    seen in partly-migrated files), keep org.panl.x as authoritative."""
    extensions = {
        "org.kpow.metadata": {"schemaVersion": "1.0", "title": "stale"},
        "org.panl.metadata": {"schemaVersion": "1.0", "title": "fresh"},
    }
    out = migrate._migrate_extensions(extensions, keep_legacy=False)
    assert out["org.panl.metadata"]["title"] == "fresh"


def test_migrate_extensions_preserves_unknowns_unchanged():
    """The most important rule of the extension model — unknowns
    round-trip exactly."""
    extensions = {
        "com.example.weird":  {"random": "data", "nested": {"x": 1}},
        "io.acme.viewer":     {"schemaVersion": "2.5", "deeply": {"nested": [1, 2]}},
    }
    out = migrate._migrate_extensions(extensions, keep_legacy=False)
    assert out["com.example.weird"] == extensions["com.example.weird"]
    assert out["io.acme.viewer"] == extensions["io.acme.viewer"]


def test_record_migration_appends_compat_migration_entry():
    overlay = {
        "schemaVersion": "1.0",
        "extensions": {},
    }
    migrate._record_migration(overlay, summary="Test migration")
    debug = overlay["extensions"]["org.panl.debug"]
    assert debug["entries"]
    entry = debug["entries"][-1]
    assert entry["category"] == "compat-migration"
    assert entry["summary"] == "Test migration"
    assert entry["data"]["fromExtension"] == ".kpow"
    assert entry["data"]["toExtension"] == ".panl"
