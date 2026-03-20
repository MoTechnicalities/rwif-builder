# rwif-builder v0.1.10

Feature release adding ARWIF normalization reports.

## What Changed

- extends `rwif arwif-normalize` with `--report <output.{json|yaml|yml}>` to emit a machine-readable normalization report artifact
- records source-artifact validation, including whether the input required legacy-compatible interpretation
- captures injected strict defaults and preserved library/state metadata so normalization assumptions are auditable
- records normalized-spec validation and normalized content counts alongside the written strict source spec
- includes rebuilt-artifact validation details in the report when `--output` is supplied for a strict `.arwif` rebuild
- extends the ARWIF integration suite to verify report-file generation and report contents end to end
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document normalization reports

## Scope

This release makes ARWIF normalization auditable as a first-class artifact. Teams migrating legacy prototype files can now keep the strict normalized spec, the rebuilt strict artifact, and a separate report describing exactly what was preserved, what defaults were injected, and how both the normalized spec and rebuilt artifact validated.
