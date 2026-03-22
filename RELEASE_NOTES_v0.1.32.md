# rwif-builder v0.1.32

Feature release extending the ARWIF Level 3 room-aware slice with renderer adaptation hints.

## What Changed

- adds structured `room.renderer_adaptation_hints` support to strict ARWIF specs and artifacts using compact `target_playback`, `spatial_priority`, and `downmix_policy` fields for playback-target intent
- validates renderer adaptation hints during spec and artifact checks and exposes the derived room adaptation summary in validation stats so review tooling can reason about how a scene should translate across playback situations
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface renderer-adaptation summaries and change signals alongside room dimensions, surface profile, reflection policy, listening zones, and speakers
- extends `rwif arwif-batch-diff-analyze` so recurring renderer-adaptation changes are aggregated across reviewed artifact pairs, including target-playback, spatial-priority, and downmix-policy drift
- expands the ARWIF integration suite and public docs so room-aware round trips, invalid room validation, and batch room review now cover renderer adaptation hints as part of the public Level 3 contract

## Scope

This release keeps Level 3 room-aware ARWIF interpretable and non-renderer-specific. Renderer adaptation hints capture target playback assumptions and translation priorities without hardcoding a specific engine or output device model. The room layer can now express not only what the scene is and how reflective it feels, but also how that intent should survive across headphones, stereo speakers, multichannel rooms, or smaller playback targets.
