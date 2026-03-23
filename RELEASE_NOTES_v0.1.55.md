# rwif-builder v0.1.55

Feature release adding VRWIF camera-trajectory displacement summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_displacement`
- extends VRWIF diff scene-change reporting with `camera_trajectory_displacement_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory displacement drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory displacement review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera net-movement summary and drift signal, making shot start-to-end movement revisions easier to review across pairs and batches.