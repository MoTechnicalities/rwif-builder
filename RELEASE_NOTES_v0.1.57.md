# rwif-builder v0.1.57

Feature release adding VRWIF camera-trajectory straightness summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_straightness`
- extends VRWIF diff scene-change reporting with `camera_trajectory_straightness_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory straightness drift counts
- defines straightness as displacement divided by path length, with zero-length trajectories treated as maximally straight for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory straightness review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera path-directness summary and drift signal, making detoured-versus-direct shot revisions easier to review across pairs and batches.