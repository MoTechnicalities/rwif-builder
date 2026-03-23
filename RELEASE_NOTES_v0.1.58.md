# rwif-builder v0.1.58

Feature release adding VRWIF object-trajectory turn-angle summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_turn_angle_total_degrees` and derived `object_trajectory_turn_angle_range_degrees`
- extends VRWIF diff scene-change reporting with `object_trajectory_turn_angle_total_degrees_delta` and `object_trajectory_turn_angle_range_degrees_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory turn-angle drift counts
- defines cumulative turn angle as the sum of inter-segment direction changes in degrees across each trajectory, skipping zero-length adjacent segments for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory turn-angle review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact path-bending summaries and drift signals, making straight-versus-turning motion revisions easier to review across pairs and batches.