# rwif-builder v0.1.63

Feature release adding VRWIF camera-trajectory turn-count summaries.

## What Changed

- extends VRWIF inspect scene summaries with derived `camera_trajectory_turn_count`
- extends VRWIF diff scene-change reporting with `camera_trajectory_turn_count_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory turn-count drift counts
- defines turn count as the number of non-zero inter-segment direction changes within each trajectory, skipping zero-length adjacent segments for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory turn-count review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose a compact camera repeated-bending summary and drift signal, making one-turn-versus-many-turn shot revisions easier to review across pairs and batches.