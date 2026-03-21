# ARWIF Examples

This directory contains two small ARWIF example artifacts built around the same C major triad.

## Files

- `CEG_legacy.arwif`: the original prototype artifact generated before the ARWIF v0.1 metadata contract existed
- `CEG_legacy.md`: sidecar notes for the legacy prototype
- `CEG_v0_1.yaml`: source spec consumable by `rwif arwif-build`
- `CEG_v0_1.arwif`: a compliant ARWIF v0.1 example using the strict metadata fields
- `CEG_v0_1.md`: sidecar notes for the strict example

## Validate

Build the strict example from source spec:

```bash
rwif arwif-validate-spec examples/arwif/CEG_v0_1.yaml --json
rwif arwif-build --spec examples/arwif/CEG_v0_1.yaml --output dist/CEG_v0_1.arwif --json
rwif arwif-batch-build first.yaml second.yaml --output-dir dist/built_arwif --json
rwif arwif-batch-import first.yaml second.yaml --output-dir dist/imported_arwif --json
```

Export it back to a source spec:

```bash
rwif arwif-export dist/CEG_v0_1.arwif dist/CEG_v0_1.export.yaml --json
```

Normalize the legacy prototype into a strict source spec and rebuilt artifact:

```bash
rwif arwif-normalize examples/arwif/CEG_legacy.arwif --spec dist/CEG_legacy.normalized.yaml --output dist/CEG_legacy.normalized.arwif --report dist/CEG_legacy.normalized.report.json --assumptions dist/CEG_legacy.normalized.assumptions.json --json
```

The optional normalization report captures the legacy-validation result, injected strict defaults, preserved library and state metadata, normalized-spec validation, normalized content counts, and rebuilt-artifact validation.

The optional assumptions manifest captures the narrower migration contract: which defaults were injected, which library and state metadata fields were preserved, and which warnings still surfaced from the source artifact, normalized spec, or rebuilt artifact.

To run the same migration flow across multiple artifacts, use the batch command and collect outputs into directories:

```bash
rwif arwif-batch-normalize old-a.arwif old-b.arwif --spec-dir dist/normalized_specs --output-dir dist/normalized_artifacts --report-dir dist/normalization_reports --assumptions-dir dist/assumptions --json
```

To diff multiple ARWIF baseline and candidate pairs in one pass:

```bash
rwif arwif-batch-diff --left dist/a.baseline.arwif dist/b.baseline.arwif --right dist/a.candidate.arwif dist/b.candidate.arwif --output dist/batch-diff-report.json --json
```

To export multiple ARWIF artifacts into strict source specs in one pass:

```bash
rwif arwif-batch-export dist/a.arwif dist/b.arwif --output-dir dist/exported_specs --format yaml --json
```

To validate multiple strict ARWIF source specs in one pass:

```bash
rwif arwif-batch-validate-spec first.yaml second.yaml --json
```

To render multiple ARWIF artifacts into WAV outputs in one pass:

```bash
rwif arwif-batch-render dist/a.arwif dist/b.arwif --output-dir dist/rendered_wav --json
```

To validate multiple ARWIF artifacts in one pass:

```bash
rwif arwif-batch-validate dist/a.arwif dist/b.arwif --json
```

To inspect multiple ARWIF artifacts in one pass:

```bash
rwif arwif-batch-inspect dist/a.arwif dist/b.arwif --json
```

Import the exported spec again:

```bash
rwif arwif-validate-spec dist/CEG_v0_1.export.yaml --json
rwif arwif-import --spec dist/CEG_v0_1.export.yaml --output dist/CEG_v0_1.roundtrip.arwif --json
```

Inspect it semantically:

```bash
rwif arwif-inspect dist/CEG_v0_1.arwif --json
```

Compare two ARWIF variants:

```bash
rwif arwif-diff old.arwif new.arwif --json
```

Then validate it:

Strict validation of the v0.1 example:

```bash
rwif arwif-validate examples/arwif/CEG_v0_1.arwif --json
```

Legacy-compatible validation of the prototype:

```bash
rwif arwif-validate examples/arwif/CEG_legacy.arwif --legacy --json
```

## Render

```bash
rwif arwif-render examples/arwif/CEG_v0_1.arwif examples/arwif/CEG_v0_1.wav --json
```

The renderer writes 16-bit PCM WAV output using the ARWIF reference synthesis path, staying mono when no channel layout is declared and emitting multichannel output for supported layouts.