# rwif-builder v0.1.40

Feature release adding canonical VRWIF object visibility.

## What Changed

- formalizes `objects[].visibility` as a compact canonical VRWIF enum with `visible`, `occluded`, and `hidden`
- carries object visibility through VRWIF validation stats, inspect scene summaries, diff scene-change reporting, and batch diff analysis
- keeps normalization compatible with canonical object visibility by lowercasing and trimming loose source values before validation
- extends the VRWIF test suite with visibility validation, normalization, inspect, diff, and batch-analysis coverage
- updates the README, CLI contract, VRWIF draft spec, and shipped VRWIF example to document the canonical visibility surface

## Scope

This release strengthens the first VRWIF review surface by making object visibility a stable reasoning primitive. Scene revisions can now express whether objects remain visible, become occluded, or disappear from view without relying on free-form labels.