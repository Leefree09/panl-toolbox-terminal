"""Public-facing PANL naming helpers."""

import pytest

from panl_toolbox_terminal import naming


def test_default_output_path_replaces_extension():
    assert naming.default_output_path("foo.cbz") == "foo.panl"
    assert naming.default_output_path("dir/Hawkeye 001.cbz") == "dir/Hawkeye 001.panl"
    assert naming.default_output_path("noext") == "noext.panl"


def test_default_output_path_respects_explicit_argument():
    assert naming.default_output_path("foo.cbz", "bar.panl") == "bar.panl"
    # Explicit output is returned unchanged even with an unusual ext.
    assert naming.default_output_path("foo.cbz", "out.kpow") == "out.kpow"


def test_legacy_and_panl_extension_predicates():
    assert naming.is_legacy_extension("foo.kpow")
    assert naming.is_legacy_extension("FOO.KPOW")
    assert not naming.is_legacy_extension("foo.panl")

    assert naming.is_panl_extension("foo.panl")
    assert naming.is_panl_extension("FOO.PANL")
    assert not naming.is_panl_extension("foo.kpow")


def test_file_label_distinguishes_panl_and_legacy_kpow():
    assert naming.file_label("Hawkeye.panl") == "PANL"
    assert naming.file_label("Hawkeye.kpow") == "legacy KPOW"
    assert naming.file_label("Hawkeye.cbz") == "container"


def test_translate_engine_text_swaps_kpow_tokens():
    assert naming.translate_engine_text("KPOW v1 file") == "PANL v1 file"
    assert naming.translate_engine_text("Validating .kpow file at /tmp") == \
        "Validating .panl file at /tmp"
    assert naming.translate_engine_text("Kpow conversion done") == \
        "Panl conversion done"


def test_translate_engine_text_leaves_extension_namespace_keys_alone():
    # The extension namespace `org.kpow.metadata` is a structural
    # token that the migrate command handles separately. The text
    # translator must NOT munge it, otherwise migration warnings
    # in the engine's output get garbled.
    src = 'extension org.kpow.metadata schemaVersion=1.0'
    assert "org.kpow.metadata" in naming.translate_engine_text(src)


def test_translate_engine_text_leaves_user_paths_alone():
    src = "Reading /tmp/Hawkeye 001.kpow ..."
    # The path itself stays; only the user-facing label is rewritten.
    out = naming.translate_engine_text(src)
    assert "Hawkeye 001.kpow" in out


def test_panl_to_kpow_path():
    assert naming.panl_to_kpow_path("foo.panl") == "foo.kpow"
    assert naming.panl_to_kpow_path("dir/foo.panl") == "dir/foo.kpow"
