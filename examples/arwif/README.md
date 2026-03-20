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
rwif arwif-build --spec examples/arwif/CEG_v0_1.yaml --output dist/CEG_v0_1.arwif --json
```

Inspect it semantically:

```bash
rwif arwif-inspect dist/CEG_v0_1.arwif --json
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

The renderer writes mono 16-bit PCM WAV output using the ARWIF reference synthesis path.