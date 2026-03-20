# rwif-builder v0.1.13

Feature release adding ARWIF batch build.

## What Changed

- adds `rwif arwif-batch-build` to build multiple strict ARWIF source specs into `.arwif` artifacts in one command
- writes built artifacts into a target `--output-dir` while reusing the same strict validation and build path as single-spec `arwif-build`
- returns an aggregated machine-readable payload with per-spec build results plus collection-level counts for processed specs, successful builds, failures, and total oscillator entries
- extends the ARWIF integration suite to verify end-to-end batch build output generation and aggregate payload behavior
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document batch build as the next batch authoring step after batch normalization

## Scope

This release extends ARWIF batch authoring from migration workflows into direct strict-spec production. Teams can now build multiple validated `.arwif` artifacts from source specs in one pass and capture the full per-spec build results in a single machine-readable payload for CI and release pipelines.