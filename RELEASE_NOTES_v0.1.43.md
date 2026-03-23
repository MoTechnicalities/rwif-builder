# rwif-builder v0.1.43

Feature release adding VRWIF light-placement summaries.

## What Changed

- extends VRWIF inspect scene summaries with explicit counts for positioned lights and directional lights
- extends VRWIF diff scene-change reporting with `positioned_lights_delta` and `directional_lights_delta`
- extends VRWIF batch diff analysis with aggregate light-placement drift counts so directional-versus-positioned lighting changes are visible across review sets
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new light-placement summaries
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Lighting layout changes are now easier to reason about because inspect and diff summaries distinguish positioned-light drift from directional-light drift.