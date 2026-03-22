# rwif-builder v0.1.36

Feature release extending the ARWIF Level 3 room-aware slice with speaker coverage intent.

## What Changed

- adds structured `room.speakers[].coverage_intent` support to strict ARWIF specs and artifacts using compact `focused`, `balanced`, `wide`, and `ambient` enums so room speaker placement can express coarse coverage semantics without turning into renderer-specific panning logic
- validates speaker coverage intent during spec and artifact checks and exposes the derived speaker-coverage summary in validation stats so review tooling can distinguish tighter mains from wider fills or more ambient coverage assumptions
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface speaker-coverage summaries and change signals alongside room geometry, surface treatment, reflection policy, renderer adaptation hints, listening zones, and speaker placement
- extends `rwif arwif-batch-diff-analyze` and `rwif arwif-batch-review` so recurring speaker-coverage changes are aggregated across reviewed artifact pairs through a dedicated `speaker_coverage_intents_changed_pairs` counter
- updates the shipped Level 3 room-review example pair, integration coverage, and public docs so speaker-coverage review is part of the tested ARWIF batch-review contract

## Scope

This release keeps Level 3 room-aware ARWIF compact and interpretable. Speaker coverage intent does not attempt to define detailed directivity patterns, crossover design, or renderer-specific beam shaping; it adds a small semantic layer that lets authoring and review workflows describe whether a speaker is meant to cover a tighter focus region, a balanced listening area, a wider spread, or a more ambient support role.