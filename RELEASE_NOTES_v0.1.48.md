# rwif-builder v0.1.48

Feature release adding VRWIF object-trajectory duration summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_duration_total` and derived `object_trajectory_duration_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_duration_total_delta` and `object_trajectory_duration_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory duration drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory duration review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact motion-duration summaries and drift signals, making motion-timing revisions easier to review across pairs and batches.