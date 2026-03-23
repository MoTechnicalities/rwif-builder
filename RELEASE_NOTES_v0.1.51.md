# rwif-builder v0.1.51

Feature release adding VRWIF camera-trajectory path-length summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_path_length`
- extends VRWIF diff scene-change reporting with `camera_trajectory_path_length_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory path-length drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory path-length review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose compact camera motion-distance summaries and drift signals, making shot-movement revisions easier to review across pairs and batches.