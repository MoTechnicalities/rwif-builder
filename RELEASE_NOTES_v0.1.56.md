# rwif-builder v0.1.56

Feature release adding VRWIF object-trajectory straightness summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_straightness_total` and derived `object_trajectory_straightness_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_straightness_total_delta` and `object_trajectory_straightness_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory straightness drift counts
- defines straightness as displacement divided by path length, with zero-length trajectories treated as maximally straight for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory straightness review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact path-directness summaries and drift signals, making detoured-versus-direct motion revisions easier to review across pairs and batches.