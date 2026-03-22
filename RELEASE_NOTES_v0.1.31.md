# rwif-builder v0.1.31

Feature release extending the ARWIF Level 3 room-aware slice with reflection policy.

## What Changed

- adds structured `room.reflection_policy` support to strict ARWIF specs and artifacts using interpretable `style`, `early_reflections`, and `late_reverb` fields instead of renderer-specific acoustics
- validates reflection-policy values during spec and artifact checks and exposes the derived room reflection summary in validation stats so review tooling can reason about direct versus reverberant intent
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface reflection-policy summaries and change signals alongside room dimensions, surface profile, listening zones, and speakers
- extends `rwif arwif-batch-diff-analyze` so recurring reflection-policy changes are aggregated across reviewed artifact pairs, including style, early-reflection, and late-reverb drift
- expands the ARWIF integration suite and public docs so room-aware round trips, invalid room validation, and batch room review now cover reflection policy as part of the public Level 3 contract

## Scope

This release keeps Level 3 room-aware ARWIF interpretable. Reflection policy is modeled as compact scene intent rather than physical acoustics, which makes room-aware review stronger without pretending the format already encodes a full simulation model. The room surface now captures not just the space, listeners, and speakers, but also whether a scene should feel direct, balanced, or enveloping and how strongly reflections should read.
