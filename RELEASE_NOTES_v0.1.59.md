# rwif-builder v0.1.59

Feature release adding VRWIF camera-trajectory turn-angle summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_turn_angle_degrees`
- extends VRWIF diff scene-change reporting with `camera_trajectory_turn_angle_degrees_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory turn-angle drift counts
- defines cumulative turn angle as the sum of inter-segment direction changes in degrees across each trajectory, skipping zero-length adjacent segments for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory turn-angle review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera path-bending summary and drift signal, making straight-versus-turning shot revisions easier to review across pairs and batches.