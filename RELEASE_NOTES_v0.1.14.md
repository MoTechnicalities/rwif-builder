# rwif-builder v0.1.14

Feature release adding ARWIF batch render.

## What Changed

- adds `rwif arwif-batch-render` to render multiple ARWIF artifacts into `.wav` outputs in one command
- writes rendered audio into a target `--output-dir` while reusing the same reference synthesis path as single-artifact `arwif-render`
- returns an aggregated machine-readable payload with per-artifact render results plus collection-level counts for processed artifacts, successful renders, failures, and total rendered duration
- extends the ARWIF integration suite to verify end-to-end batch render output generation and aggregate payload behavior
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch render as the next batch export step after batch build

## Scope

This release extends ARWIF batch workflows from authoring and migration into playback export. Teams can now render multiple validated `.arwif` artifacts into WAV outputs in one pass and capture both per-artifact render metadata and collection-level totals for automation, QA, and release packaging.
