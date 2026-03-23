# rwif-builder v0.1.64

Feature release adding VRWIF object-trajectory average-turn-angle summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_average_turn_angle_total_degrees` and derived `object_trajectory_average_turn_angle_range_degrees`
- extends VRWIF diff scene-change reporting with `object_trajectory_average_turn_angle_total_degrees_delta` and `object_trajectory_average_turn_angle_range_degrees_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory average-turn-angle drift counts
- defines average turn angle as the mean non-skipped inter-segment direction change in degrees within each trajectory, returning `0.0` when a trajectory has positions but no valid turns
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory average-turn-angle review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact typical-bend summaries and drift signals, making subtle-versus-severe average turning revisions easier to review across pairs and batches.