# rwif-builder v0.1.69

Feature release adding VRWIF camera-trajectory peak-speed summaries.

## What Changed

- extends VRWIF inspect scene summaries with `camera_trajectory_peak_speed`
- extends VRWIF diff scene-change reporting with `camera_trajectory_peak_speed_delta`
- extends VRWIF batch diff analysis with aggregate camera-trajectory peak-speed drift counts
- defines peak speed as the largest non-skipped adjacent-segment speed within the camera trajectory, skipping non-positive segment durations for stable review output
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new camera-trajectory peak-speed review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release completes the first peak-speed motion-intensity pair for VRWIF without adding new schema fields. Scenes that already carry camera trajectory keyframes now expose motion-spike summaries and drift signals, making camera movement bursts reviewable alongside average-speed changes across pairs and batches.