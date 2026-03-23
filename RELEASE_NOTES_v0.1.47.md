# rwif-builder v0.1.47

Feature release adding VRWIF object-distance summaries.

## What Changed

- extends VRWIF inspect scene summaries with `object_distance_from_origin_total` and derived `object_distance_from_origin_range`
- extends VRWIF diff scene-change reporting with `object_distance_from_origin_total_delta` and `object_distance_from_origin_range_changed`
- extends VRWIF batch diff analysis with aggregate object-distance drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new object-distance review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry object position vectors now expose compact layout-distance summaries and drift signals, making object-placement revisions easier to review across pairs and batches.