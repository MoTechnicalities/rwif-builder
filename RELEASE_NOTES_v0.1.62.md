# rwif-builder v0.1.62

Feature release adding VRWIF object-trajectory turn-count summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_turn_count_total` and derived `object_trajectory_turn_count_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_turn_count_total_delta` and `object_trajectory_turn_count_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory turn-count drift counts
- defines turn count as the number of non-zero inter-segment direction changes within each trajectory, skipping zero-length adjacent segments for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory turn-count review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact repeated-bending summaries and drift signals, making one-turn-versus-many-turn motion revisions easier to review across pairs and batches.