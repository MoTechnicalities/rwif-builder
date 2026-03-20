# rwif-builder v0.1.4

Release aligning the published package version with the current public tag series and shipping the complete ARWIF authoring path.

## What Changed

- adds published ARWIF example artifacts and a source YAML spec for the strict CEG example
- adds `rwif arwif-build` for YAML or JSON driven ARWIF authoring
- validates generated ARWIF artifacts immediately after build
- extends the ARWIF integration coverage to exercise build, validate, and render together
- updates the CLI and ARWIF docs to document the end-to-end authoring workflow
- aligns the package-reported version with the public release tag lineage

## Scope

This release makes ARWIF usable as a small complete toolchain inside rwif-builder: source spec, authoring command, validation, rendering, and published examples. It also fixes the stale package version so command-line and package metadata match the public release number.