# rwif-builder v0.1.54

Feature release adding VRWIF object-trajectory displacement summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_trajectory_displacement_total` and derived `object_trajectory_displacement_range`
- extends VRWIF diff scene-change reporting with `object_trajectory_displacement_total_delta` and `object_trajectory_displacement_range_changed`
- extends VRWIF batch diff analysis with aggregate object-trajectory displacement drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-trajectory displacement review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object trajectory keyframes now expose compact net-movement summaries and drift signals, making direct start-to-end motion revisions easier to review across pairs and batches.