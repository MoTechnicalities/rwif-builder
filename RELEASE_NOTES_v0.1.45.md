# rwif-builder v0.1.45

Feature release adding VRWIF light-intensity summaries.

## What Changed

- extends VRWIF inspect scene summaries with `light_intensity_total` and derived `light_intensity_range`
- extends VRWIF diff scene-change reporting with `light_intensity_total_delta` and `light_intensity_range_changed`
- extends VRWIF batch diff analysis with aggregate light-intensity drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new light-intensity review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry numeric light intensity values now expose compact energy summaries and drift signals, making lighting-balance revisions easier to review across pairs and batches.