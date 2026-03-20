# rwif-builder v0.1.16

Feature release tightening ARWIF batch diff with optional file output.

## What Changed

- adds an optional `--output` path to `rwif arwif-batch-diff` so aggregated pairwise diff reports can be persisted to disk
- infers report format from the destination suffix and writes `.json`, `.yaml`, or `.yml` using the same machine-readable artifact convention already used by ARWIF normalization and export flows
- returns `report_output` and `report_format` fields in the batch diff payload when a persisted report is requested
- extends the ARWIF integration suite to verify the batch diff payload and persisted report document stay aligned
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch diff report output for CI and review pipelines

## Scope

This release tightens the existing ARWIF batch diff workflow rather than broadening it. Teams can now keep the same explicit pairwise comparison contract from `v0.1.15` while optionally saving the aggregated diff report as a reusable machine-readable artifact for review, automation, and release signoff.
