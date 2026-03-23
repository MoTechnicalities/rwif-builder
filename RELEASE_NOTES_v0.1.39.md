# rwif-builder v0.1.39

Feature release adding canonical VRWIF camera framing intent.

## What Changed

- formalizes `camera.framing_intent` as a compact canonical VRWIF enum with `establishing`, `centered-medium`, `subject-focused`, and `detail-close`
- carries camera framing intent through VRWIF validation stats, inspect scene summaries, diff scene-change reporting, and batch diff analysis
- keeps normalization compatible with canonical framing intent by lowercasing and trimming loose source values before validation
- extends the VRWIF test suite with framing-intent validation, normalization, inspect, diff, and batch-analysis coverage
- updates the README, CLI contract, VRWIF draft spec, and shipped VRWIF example to document the canonical framing-intent surface

## Scope

This release strengthens the first VRWIF review surface without widening the realm into rendering or asset-packaging concerns. Camera framing is now a compact reasoning primitive that can be validated and compared explicitly across scene revisions.