# rwif-builder v0.1.71

Feature release adding VRWIF camera-trajectory speed-standard-deviation summaries.

## What Changed

- extends VRWIF inspect scene summaries with `camera_trajectory_speed_standard_deviation`
- extends VRWIF diff scene-change reporting with `camera_trajectory_speed_standard_deviation_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory speed-standard-deviation drift counts
- defines speed standard deviation as the population standard deviation across non-skipped adjacent-segment speeds within the camera trajectory, skipping non-positive segment durations for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory speed-consistency review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release completes the first speed-variability motion-intensity pair for VRWIF without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose compact camera speed-consistency summaries and drift signals, making smooth-versus-bursty shot revisions easier to review across pairs and batches.