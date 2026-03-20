# rwif-builder v0.1.8

Feature release adding explicit ARWIF source-spec validation.

## What Changed

- adds `rwif arwif-validate-spec` to validate ARWIF YAML or JSON specs before build or import
- reuses the same strict source-spec validation in `rwif arwif-build` and `rwif arwif-import`
- reports field-level spec validation errors and warnings instead of surfacing raw exceptions for malformed specs
- checks top-level metadata, state-level overrides, oscillator entries, and Nyquist bounds against `sample_rate_hz`
- extends the ARWIF integration suite with explicit spec-validation and structured build-failure coverage
- updates the README, CLI reference, ARWIF spec, and examples guide to document the new validation step

## Scope

This release hardens the ARWIF authoring path. ARWIF specs can now be validated directly before artifact generation, and the builder/importer reject malformed source documents with structured diagnostics before writing output files.