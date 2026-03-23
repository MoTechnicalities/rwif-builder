# rwif-builder v0.1.65

Feature release adding VRWIF camera-trajectory average-turn-angle summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_average_turn_angle_degrees`
- extends VRWIF diff scene-change reporting with `camera_trajectory_average_turn_angle_degrees_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory average-turn-angle drift counts
- defines average turn angle as the mean non-skipped inter-segment direction change in degrees within each trajectory, returning `0.0` when a trajectory has positions but no valid turns
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory average-turn-angle review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose compact camera typical-bend summaries and drift signals, making subtle-versus-severe average turning revisions easier to review across pairs and batches.