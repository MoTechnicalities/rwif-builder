# rwif-builder v0.1.49

Feature release adding VRWIF camera-trajectory duration summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_duration`
- extends VRWIF diff scene-change reporting with `camera_trajectory_duration_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory duration drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory duration review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose compact camera motion-duration summaries and drift signals, making shot-timing revisions easier to review across pairs and batches.