# rwif-builder v0.1.12

Feature release adding ARWIF batch normalization.

## What Changed

- adds `rwif arwif-batch-normalize` to run the existing ARWIF normalization workflow across multiple artifacts in one command
- writes normalized strict source specs into a target `--spec-dir` and can optionally collect rebuilt strict artifacts, normalization reports, and assumptions manifests into sibling output directories
- reuses the same single-artifact normalization logic so injected defaults, preserved metadata, validation behavior, and assumptions-manifest contents stay consistent between single and batch workflows
- returns an aggregated machine-readable payload with per-artifact results plus collection-level counts for processed artifacts, successful normalizations, failures, and total assumption entries
- extends the ARWIF integration suite to verify end-to-end batch normalization output generation and aggregate payload behavior
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch normalization as the next automation step after assumptions manifests

## Scope

This release moves ARWIF normalization from single-file migration into collection-scale operations. Teams can now normalize multiple prototype artifacts in one pass while keeping strict specs, rebuilt artifacts, reports, and assumptions manifests organized into predictable directories for CI and review workflows.