# rwif-builder v0.1.61

Feature release adding VRWIF camera-trajectory peak-turn-angle summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_peak_turn_angle_degrees`
- extends VRWIF diff scene-change reporting with `camera_trajectory_peak_turn_angle_degrees_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory peak-turn-angle drift counts
- defines peak turn angle as the largest inter-segment direction change in degrees within each trajectory, skipping zero-length adjacent segments for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory peak-turn-angle review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera sharpest-corner summary and drift signal, making gradual-versus-sharp shot revisions easier to review across pairs and batches.