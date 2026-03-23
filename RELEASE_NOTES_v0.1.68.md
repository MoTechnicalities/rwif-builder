# rwif-builder v0.1.68

Feature release adding VRWIF object-trajectory peak-speed summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_peak_speed_total` and derived `object_trajectory_peak_speed_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_peak_speed_total_delta` and `object_trajectory_peak_speed_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory peak-speed drift counts
- defines peak speed as the largest non-skipped adjacent-segment speed within each trajectory, skipping non-positive segment durations for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory peak-speed review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact burst-intensity summaries and drift signals, making average-versus-spike motion revisions easier to review across pairs and batches.