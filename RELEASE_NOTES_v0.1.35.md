# rwif-builder v0.1.35

Feature release extending the ARWIF Level 3 room-aware slice with explicit geometry references.

## What Changed

- adds structured `room.geometry_reference` support to strict ARWIF specs and artifacts using a stable `geometry_id` plus an interpretable `geometry_class` enum so room archetypes can be reviewed without embedding dense geometric models
- validates geometry-reference fields during spec and artifact checks and exposes the derived geometry summary in validation stats so review tooling can reason about whether a room stays corridor-like, arena-like, shoebox-like, or irregular across revisions
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface geometry-reference summaries and change signals alongside room dimensions, surface treatment, reflection policy, renderer adaptation hints, listening zones, and speakers
- extends `rwif arwif-batch-diff-analyze` and `rwif arwif-batch-review` so recurring geometry-reference changes are aggregated across reviewed artifact pairs, including explicit geometry-id and geometry-class drift counters
- updates the shipped Level 3 room-review example pair, integration coverage, and public docs so geometry-reference review is part of the tested ARWIF batch-review contract

## Scope

This release keeps Level 3 room-aware ARWIF compact and interpretable. Geometry reference does not attempt to encode full CAD-style room meshes or dense boundary topology; it adds a small semantic bridge that lets authoring and review workflows refer to stable room archetypes and named venue models while preserving the existing abstraction boundary.