# rwif-builder v0.1.33

Documentation-and-example release for the ARWIF Level 3 room-aware review workflow.

## What Changed

- adds two shipped ARWIF example specs, `ROOM_REVIEW_baseline_v0_1.yaml` and `ROOM_REVIEW_candidate_v0_1.yaml`, that exercise the current Level 3 room-aware surface with dimensions, surface profile, reflection policy, renderer adaptation hints, listening zones, and speaker placement
- expands the examples guide and top-level ARWIF docs so the room-aware review flow now has a concrete validate, build, and `rwif arwif-batch-review` command sequence instead of only abstract command references
- adds integration coverage that validates both shipped room-review specs, builds both artifacts, and confirms the combined batch-review payload reports the expected room-aware drift counters
- keeps the release scoped to usability and regression safety for already-published Level 3 features without extending the ARWIF schema further

## Scope

This release does not change the ARWIF Level 3 data model. It makes the existing room-aware authoring and review surface easier to use, easier to validate, and harder to regress by shipping a realistic example pair and turning that workflow into a tested public contract.
