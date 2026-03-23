# rwif-builder v0.1.42

Feature release adding canonical VRWIF lighting color.

## What Changed

- formalizes `lighting[].color` as a compact canonical VRWIF enum with `warm`, `neutral`, `cool`, and `accent`
- carries lighting color through VRWIF validation stats, inspect scene summaries, diff scene-change reporting, and batch diff analysis
- keeps normalization compatible with canonical lighting color by lowercasing and trimming loose source values before validation
- extends the VRWIF test suite with lighting-color validation, normalization, inspect, diff, and batch-analysis coverage
- updates the README, CLI contract, VRWIF draft spec, and shipped VRWIF example to document the canonical lighting-color surface

## Scope

This release strengthens the first VRWIF review surface by making lighting color a stable reasoning primitive. Scene revisions can now track warm, neutral, cool, and accent lighting drift without relying on free-form labels.