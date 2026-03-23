# rwif-builder v0.1.70

Feature release adding VRWIF object-trajectory speed-standard-deviation summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_speed_standard_deviation_total` and derived `object_trajectory_speed_standard_deviation_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_speed_standard_deviation_total_delta` and `object_trajectory_speed_standard_deviation_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory speed-standard-deviation drift counts
- defines speed standard deviation as the population standard deviation across non-skipped adjacent-segment speeds within each trajectory, skipping non-positive segment durations for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory speed-consistency review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release extends the VRWIF motion-intensity family without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact speed-variability summaries and drift signals, making smooth-versus-bursty object motion revisions easier to review across pairs and batches.