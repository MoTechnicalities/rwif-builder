# rwif-builder v0.1.66

Feature release adding VRWIF object-trajectory turn-angle standard-deviation summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_turn_angle_standard_deviation_total_degrees` and derived `object_trajectory_turn_angle_standard_deviation_range_degrees`
- extends VRWIF diff scene-change reporting with `object_trajectory_turn_angle_standard_deviation_total_degrees_delta` and `object_trajectory_turn_angle_standard_deviation_range_degrees_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory turn-angle standard-deviation drift counts
- defines turn-angle standard deviation as the population standard deviation of non-skipped inter-segment direction changes in degrees within each trajectory, returning `0.0` when a trajectory has fewer than two valid turns
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory turn-angle standard-deviation review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact bend-consistency summaries and drift signals, making even-versus-irregular turning revisions easier to review across pairs and batches.