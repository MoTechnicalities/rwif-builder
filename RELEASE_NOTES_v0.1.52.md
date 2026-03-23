# rwif-builder v0.1.52

Feature release adding VRWIF object-trajectory average-speed summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_average_speed_total` and derived `object_trajectory_average_speed_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_average_speed_total_delta` and `object_trajectory_average_speed_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory average-speed drift counts
- fixes pair-change inference so fractional float deltas still mark a pair as changed during batch review
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory average-speed review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact motion-speed summaries and drift signals, making movement-intensity revisions easier to review across pairs and batches.