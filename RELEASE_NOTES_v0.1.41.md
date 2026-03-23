# rwif-builder v0.1.41

Feature release adding canonical VRWIF object state.

## What Changed

- formalizes `objects[].state` as a compact canonical VRWIF enum with `idle`, `active`, and `transitioning`
- carries object state through VRWIF validation stats, inspect scene summaries, diff scene-change reporting, and batch diff analysis
- keeps normalization compatible with canonical object state by lowercasing and trimming loose source values before validation
- extends the VRWIF test suite with state validation, normalization, inspect, diff, and batch-analysis coverage
- updates the README, CLI contract, VRWIF draft spec, and shipped VRWIF example to document the canonical state surface

## Scope

This release strengthens the first VRWIF review surface by making object state a stable reasoning primitive. Scene revisions can now distinguish idle, active, and transitioning objects without relying on free-form labels.