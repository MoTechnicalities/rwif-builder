# rwif-builder v0.1.67

Feature release adding VRWIF camera-trajectory turn-angle standard-deviation summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_turn_angle_standard_deviation_degrees`
- extends VRWIF diff scene-change reporting with `camera_trajectory_turn_angle_standard_deviation_degrees_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory turn-angle standard-deviation drift counts
- defines turn-angle standard deviation as the population standard deviation of non-skipped inter-segment direction changes in degrees within each trajectory, returning `0.0` when a trajectory has fewer than two valid turns
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory turn-angle standard-deviation review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose compact camera bend-consistency summaries and drift signals, making even-versus-irregular turning revisions easier to review across pairs and batches.