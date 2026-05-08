# PANL Toolbox Terminal

The public command-line tool for the **PANL** open comic container
format. Convert, inspect, validate, and migrate `.panl` files (and
existing `.kpow` files) from the terminal.

PANL is the public name for what shipped during early development
under the internal codename **KPOW**. The on-disk format is the same;
the public surface (commands, profile names, output text) is now
PANL throughout. See [panl-format/spec/COMPATIBILITY.md](../panl-format/spec/COMPATIBILITY.md)
for the full rename guide.

## Install

PANL Toolbox Terminal is a Python 3.9+ package. It delegates the
on-disk encode/decode to the reference engine that currently ships
under the `kpow` distribution.

```bash
pip install panl-toolbox-terminal
```

Both entry points are installed:

- `panl` — the standard command name.
- `panl-toolbox` — alias if `panl` collides with another binary.

## Quick start

```bash
# Convert a CBZ to .panl using the Recommended profile (default):
panl convert input.cbz

# Explicit output path:
panl convert input.cbz output.panl

# Estimate before committing the encode:
panl estimate input.cbz

# Inspect / validate a .panl (or legacy .kpow) file:
panl info book.panl
panl validate book.panl
panl validate book.panl --strict
panl validate book.panl --source original.cbz --visual-audit strict

# List every EDIT extension:
panl extensions book.panl

# Visual-audit provenance:
panl audit-info book.panl

# Open + read + decode timings:
panl benchmark book.panl

# Migrate a legacy .kpow to .panl with org.kpow.* -> org.panl.*:
panl migrate legacy.kpow output.panl
```

## Profiles

PANL Toolbox Terminal exposes five user-facing profiles. Pick by
what you care about; the converter handles the rest.

| Profile       | What it's for                                                  |
|---------------|----------------------------------------------------------------|
| `recommended` | **Default.** 512 tiled pages, AVIF speed=6 cq=20 chroma 4:2:0 with autotiling, decode-only candidate gate, adaptive risky-tile audit + targeted repair, streamable layout, EDIT/extensions enabled. |
| `fast`        | Quicker conversion, lower assurance. Lighter audit; good for previews and bulk imports. |
| `compact`     | More aggressive visually-lossless settings (palette + WebP-lossless on top of AVIF). Smaller output, slower than Recommended. |
| `archival`    | Strictest audit, slowest, maximum confidence. For long-term storage or suspicious sources. |
| `original`    | Preserve original image bytes inside the PANL container. Useful for sources with little compression headroom or bloat risk. |

The internal engineering profile names (`reader-balanced-tiled-smart`,
`reader-fast-convert-tiled-smart`, etc.) are still accepted as
aliases for benchmark traceability, but normal users should use the
public names.

## Default conversion

`panl convert input.cbz` (no other flags) does:

- Output goes to `input.panl` next to the source.
- Profile: `recommended`.
- Layout: streamable (BOOT chunk).
- Audit: adaptive risky-tile audit with targeted repair.
- Validation: skipped unless `--validate` is passed; pass it for a
  deep structural pass over the result.
- Provenance: PANL Toolbox Terminal records the conversion under
  `extensions["org.panl.debug"]` (category `conversion`) with the
  public profile name, internal profile id, AVIF settings, audit
  settings, and worker / thread counts.

A successful run prints a concise summary:

```
PANL conversion complete
Input : Hawkeye 001.cbz 26.61 MB
Output: Hawkeye 001.panl 11.13 MB
Saved : 58.2%
Pages : 23
Tiles : 552
Time  : 20.3s
Profile: recommended
Audit : pass, 0 repairs
Validation: ok
```

## Estimate

`panl estimate input.cbz` runs the smart-tile selector on a sample
of pages (cover + last + 25/50/75% pages plus random fill) and
reports a low/high size band, expected savings %, and a
recommendation for whether converting is worth it.

```
PANL estimate
Input: 51.56 MB
Estimated output: 50-54 MB
Estimated savings: -3% to +3%
Recommendation: original or convert for features only
Reason: source appears already heavily compressed; tiled overhead
        may erase AVIF savings.
```

## Validate

`panl validate book.panl` runs the structural validator: header /
footer / directory CRCs, chunk integrity, manifest / page-index
sanity, EDIT-overlay container shape, official-extension schemas
where available. Strict mode upgrades selected warnings to errors.

```bash
panl validate book.panl
panl validate book.panl --strict
panl validate book.panl --decode-images
panl validate book.panl --source original.cbz --visual-audit strict
```

When the input has the legacy `.kpow` extension, `panl validate`
prints a header noting it's validating a "legacy KPOW file" so the
operator knows which side of the rename their file is on.

## Migrate

`panl migrate legacy.kpow output.panl` reads a legacy `.kpow` file
and writes a `.panl` with the same on-disk shape, but with
`org.kpow.*` extensions migrated to `org.panl.*` (and any
`org.kpow.panel-detections` entries folded into `org.panl.debug`
with `category="panel-detection"`).

Migration is **lossless**: unknown extensions and any data the
migrator doesn't recognise are preserved exactly. The migration is
recorded in `extensions["org.panl.debug"]` with
`category="compat-migration"` so the audit trail survives.

Pass `--keep-legacy-namespaces` to leave the `org.kpow.*` keys in
place alongside the new `org.panl.*` aliases (rather than dropping
the legacy duplicates).

## Legacy KPOW compatibility

PANL Toolbox Terminal reads existing `.kpow` files transparently.
- File identity is the on-disk magic, not the file extension. A
  `.kpow` file opens the same as a `.panl` file.
- Reads of files with `manifest.format = "KPOW"` are surfaced as
  "legacy KPOW" in `info` / `validate` output.
- New files always declare `manifest.format = "PANL"` and use the
  `org.panl.*` extension namespaces.
- The on-disk magic byte sequence is unchanged for v1 (kept opaque
  to avoid breaking existing readers — see
  [panl-format/spec/COMPATIBILITY.md](../panl-format/spec/COMPATIBILITY.md)).
- Files produced by PANL Toolbox Terminal continue to open in
  third-party readers like Kpow Flip without changes.

## Experimental flags

The flagship default is locked. Engineering knobs (mixed-codec
candidates, JXL, delta compression, strict candidate-time metrics,
archive-smallest, deep / exhaustive ladders, AVIF backend / speed
sweeps) are accessible through:

```bash
panl experimental <engine-subcommand> ...
panl convert --help-advanced
```

These are not part of the stable public CLI surface and may change.

## Running tests

```bash
python -m pytest panl-toolbox-terminal/tests/
```

The tests cover the bits that don't require a working engine:
profile mapping, naming translation, default-output-path logic, and
CLI help formatting.

## License

Apache-2.0. See [LICENSE](LICENSE).

The PANL format spec, JSON Schemas, conformance vectors, and
documentation live in [panl-format/](../panl-format/) under
CC BY 4.0.
