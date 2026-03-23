# rwif-builder v0.1.53

Feature release adding VRWIF camera-trajectory average-speed summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_average_speed`
- extends VRWIF diff scene-change reporting with `camera_trajectory_average_speed_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory average-speed drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory average-speed review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera motion-speed summary and drift signal, making shot-intensity revisions easier to review across pairs and batches.