# rwif-builder v0.1.44

Feature release adding VRWIF light-temperature summaries.

## What Changed

- extends VRWIF inspect scene summaries with `lights_with_temperature` and derived `light_temperature_range_kelvin`
- extends VRWIF diff scene-change reporting with `lights_with_temperature_delta` and `light_temperature_range_changed`
- extends VRWIF batch diff analysis with aggregate light-temperature coverage and range drift counts
- extends the VRWIF test suite with inspect, diff, and batch-analysis coverage for the new light-temperature review surface
- updates the README, CLI contract, and VRWIF draft spec to document the new summary surface

## Scope

This release strengthens the first VRWIF review surface without adding new schema fields. Scenes that already carry numeric `temperature_kelvin` values now expose compact warmth-range summaries and drift signals, making lighting-temperature revisions easier to review across pairs and batches.