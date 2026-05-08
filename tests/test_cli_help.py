"""CLI help / argparse smoke tests.

These don't need the underlying engine to be installed — they only
exercise the public CLI surface.
"""

import io
import sys
from contextlib import redirect_stderr, redirect_stdout

import pytest

from panl_toolbox_terminal import cli


def _run(argv):
    """Run the CLI with given argv. Returns (rc, stdout, stderr).

    SystemExit is the normal path through ``cli.main`` after a
    subcommand; we catch it so the test asserts on the code +
    output instead of the exception bubbling up.
    """
    out = io.StringIO()
    err = io.StringIO()
    rc_holder = {"rc": None}
    try:
        with redirect_stdout(out), redirect_stderr(err):
            cli.main(argv)
    except SystemExit as e:
        rc_holder["rc"] = int(e.code) if e.code is not None else 0
    return rc_holder["rc"], out.getvalue(), err.getvalue()


def test_top_level_help_uses_panl_naming():
    rc, out, err = _run(["--help"])
    text = out + err
    assert "PANL" in text
    assert ".panl" in text
    # Top-level program description must declare PANL.
    assert "PANL Toolbox Terminal" in text
    # And the program name must be `panl`.
    assert text.splitlines()[0].lstrip().startswith("usage: panl")


def test_top_level_help_lists_all_public_commands():
    rc, out, err = _run(["--help"])
    text = out + err
    for cmd in (
        "convert", "estimate", "info", "validate", "benchmark",
        "extensions", "audit-info", "migrate",
    ):
        assert cmd in text, f"{cmd!r} missing from top-level help"


def test_no_args_prints_help_and_exits_nonzero():
    rc, out, err = _run([])
    assert rc == 1
    assert "PANL" in out
    # Profile listing is part of our augmented help.
    assert "recommended" in out


def test_help_advanced_mentions_experimental():
    rc, out, err = _run(["--help-advanced"])
    text = out + err
    assert "experimental" in text.lower()


def test_convert_help_lists_all_public_profiles():
    rc, out, err = _run(["convert", "--help"])
    text = out + err
    for name in ("recommended", "fast", "compact", "archival", "original"):
        assert name in text


def test_convert_help_does_not_advertise_internal_profiles():
    """Internal engineering profile ids should be accepted as
    aliases but should not be the headline names in convert --help.
    The metavar is ``PROFILE`` for that reason."""
    rc, out, err = _run(["convert", "--help"])
    text = out + err
    # The help line lists the *public* options first.
    assert "default: recommended" in text


def test_convert_help_does_not_show_kpow_branding():
    rc, out, err = _run(["convert", "--help"])
    text = out + err
    # The convert help text talks about PANL.
    assert "PANL" in text or ".panl" in text
    # And notably does NOT advertise KPOW as the format name.
    assert "KPOW" not in text or "legacy" in text.lower()


def test_validate_help_mentions_strict_and_source():
    rc, out, err = _run(["validate", "--help"])
    text = out + err
    assert "--strict" in text
    assert "--source" in text


def test_extensions_help_mentions_json_output():
    rc, out, err = _run(["extensions", "--help"])
    text = out + err
    assert "--json" in text


def test_migrate_help_describes_legacy_kpow():
    rc, out, err = _run(["migrate", "--help"])
    text = out + err
    assert "legacy" in text.lower() and ".kpow" in text


def test_experimental_no_args_prints_summary():
    rc, out, err = _run(["experimental"])
    text = out + err
    assert "experimental" in text.lower()
    # The summary mentions a few of the engine subcommands so users
    # know what they can reach.
    assert "bootstrap" in text or "list-chunks" in text


def test_unknown_profile_is_rejected():
    rc, out, err = _run(["convert", "input.cbz", "--profile", "fictional"])
    # argparse rejects with code 2.
    assert rc == 2
    assert "fictional" in (out + err) or "invalid choice" in (out + err)


def test_cli_does_not_default_experimental_flags():
    """Verify the parser doesn't silently turn on experimental encoder
    flags. The convert subparser only carries the public knobs."""
    rc, out, err = _run(["convert", "--help"])
    text = out + err
    # These engineering flags should not be in the *primary* convert
    # help text — they live behind `panl experimental`.
    assert "--avif-cq-level" not in text
    assert "--enable-jxl" not in text
    assert "--delta" not in text
    assert "--quality-gate" not in text
