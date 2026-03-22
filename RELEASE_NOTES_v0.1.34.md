# rwif-builder v0.1.34

Feature release extending the ARWIF Level 3 room-aware slice with explicit surface treatment summaries.

## What Changed

- adds structured `room.surface_treatment` support to strict ARWIF specs and artifacts using compact `absorption` and `diffusion` enums so room surfaces can be reviewed more explicitly than the existing coarse `surface_profile`
- validates surface-treatment fields during spec and artifact checks and exposes the derived surface-treatment summary in validation stats so review tooling can reason about absorption and diffusion intent separately
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface surface-treatment summaries and change signals alongside room dimensions, surface profile, reflection policy, renderer adaptation hints, listening zones, and speakers
- extends `rwif arwif-batch-diff-analyze` and `rwif arwif-batch-review` so recurring surface-treatment changes are aggregated across reviewed artifact pairs, including explicit absorption and diffusion drift counters
- updates the shipped Level 3 room-review example pair, integration coverage, and public docs so surface-treatment review is part of the tested ARWIF batch-review contract

## Scope

This release keeps Level 3 room-aware ARWIF interpretable and compact. Surface treatment does not attempt to model dense physical material parameters; it adds a small semantic layer that lets authoring and review workflows distinguish whether a room tends to absorb energy, scatter reflections, or stay more focused without requiring renderer-specific acoustic simulation.