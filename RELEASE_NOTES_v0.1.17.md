# rwif-builder v0.1.17

Feature release adding ARWIF batch export.

## What Changed

- adds `rwif arwif-batch-export` to export multiple ARWIF artifacts into strict YAML or JSON source specs in one command
- writes exported specs into a target `--output-dir` using predictable `.export.yaml` or `.export.json` filenames and defaults to YAML unless `--format json` is requested
- reuses the same strict-spec-compatible export path as single-artifact `arwif-export` and returns aggregated machine-readable totals for exported files, states, and oscillator entries
- extends the ARWIF integration suite with end-to-end batch export coverage across multiple artifacts
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch export as the next collection-scale authoring companion to batch build, diff, and render

## Scope

This release extends ARWIF batch workflows into source-spec emission. Teams can now export multiple validated `.arwif` artifacts into reusable strict source documents in one pass and capture collection-level metadata for CI, migration review, and round-trip authoring flows.
