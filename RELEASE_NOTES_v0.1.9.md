# rwif-builder v0.1.9

Feature release adding ARWIF legacy normalization.

## What Changed

- adds `rwif arwif-normalize` to upgrade legacy or loosely specified ARWIF artifacts into a strict ARWIF `v0.1` source spec
- optionally rebuilds a strict `.arwif` artifact from the normalized source spec in the same command
- injects strict playback metadata defaults for legacy artifacts that omit required ARWIF `v0.1` fields
- preserves non-reserved library metadata and state metadata while moving artifacts onto the strict authoring path
- validates the generated normalized spec before writing it and validates rebuilt artifacts through the existing import path
- extends the ARWIF integration suite with end-to-end normalization coverage and verifies the shipped legacy CEG example can be upgraded successfully
- updates the README, CLI reference, ARWIF spec, and examples guide to document normalization as the next step after source validation

## Scope

This release creates a practical migration path from pre-spec ARWIF prototypes to strict ARWIF `v0.1`. Legacy artifacts can now be normalized into a strict source document, validated, rebuilt, inspected, diffed, and rendered through the main CLI surface.