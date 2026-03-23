# rwif-builder v0.1.46

Feature release adding VRWIF camera-distance summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_distance_from_origin`
- extends VRWIF diff scene-change reporting with `camera_distance_from_origin_delta`
- extends VRWIF batch diff analysis with aggregate camera-distance drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-distance review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera position vectors now expose a compact distance summary and drift signal, making camera-placement revisions easier to review across pairs and batches.