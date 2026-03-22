# rwif-builder v0.1.30

Feature release extending the initial ARWIF Level 3 room-aware slice with speaker placement.

## What Changed

- adds structured `room.speakers` support to strict ARWIF specs and artifacts using `{ speaker_id, anchor, channel?, role? }` entries for explicit room speaker placement
- validates room speaker entries during spec and artifact checks, including finite anchor coordinates, non-empty identifiers, and channel bindings that must match the declared `channel_layout` when present
- extends `rwif arwif-inspect` and `rwif arwif-diff` to surface room speaker summaries and change signals alongside the earlier room dimensions, surface profile, and listening-zone fields
- extends `rwif arwif-batch-diff-analyze` so recurring room speaker changes are aggregated across reviewed artifact pairs with speaker-change, speaker-channel-change, and speaker-count-delta summaries
- expands the ARWIF integration suite and public docs so room-aware round trips, invalid room validation, and batch room review now cover speaker placement as part of the public Level 3 contract

## Scope

This release keeps Level 3 room-aware ARWIF interpretable. Speaker placement is modeled as explicit scene context rather than renderer-specific acoustics, which makes room review stronger without pretending ARWIF already performs full room-adaptive playback synthesis. The room model now covers where the space is, how reflective it is, where listeners are expected to be, and where the playback endpoints live.
