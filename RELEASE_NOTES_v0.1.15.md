# rwif-builder v0.1.15

Feature release adding ARWIF batch diff.

## What Changed

- adds `rwif arwif-batch-diff` to compare multiple ARWIF artifact pairs in one command
- accepts explicit pairwise `--left` and `--right` artifact collections so baseline and candidate comparisons stay aligned without inventing directory conventions
- reuses the same state-level and metadata diff flow as single-artifact `arwif-diff` and returns aggregated machine-readable totals for changed, unchanged, invalid, and incompatible pairs
- extends the ARWIF integration suite with end-to-end batch diff coverage for both changed and unchanged pairs
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch diff as the next collection-scale comparison step after batch render

## Scope

This release extends ARWIF batch workflows into pairwise comparison and review. Teams can now diff multiple baseline and candidate artifact pairs in one pass, capture the full per-pair ARWIF diff payloads, and summarize collection-level change totals for CI, QA, and release signoff.
