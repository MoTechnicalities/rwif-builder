# rwif-builder v0.1.29

Feature release adding the initial ARWIF Level 3 room-aware slice.

## What Changed

- adds a structured top-level `room` surface to strict ARWIF specs and artifacts with validated `dimensions`, constrained `surface_profile`, and optional `listening_zones`
- preserves room context through the full authoring loop so `rwif arwif-build`, `rwif arwif-export`, and `rwif arwif-inspect` now round-trip room metadata cleanly instead of treating it as opaque preserved data
- extends ARWIF validation and inspection stats with room-aware summaries including `room_present`, `room_dimensions`, `room_surface_profile`, `listening_zone_count`, and `listening_zone_ids`
- teaches `rwif arwif-diff` and `rwif arwif-batch-diff-analyze` to report room-level changes explicitly, including room presence, dimensions, surface profile, listening-zone changes, and aggregate listening-zone count deltas across reviewed pairs
- extends the ARWIF integration suite with room-aware round-trip, invalid-room validation, and batch-diff analysis coverage, and refreshes the README, CLI reference, ARWIF guide, and spatial roadmap to document the new Level 3 surface

## Scope

This release starts Level 3 ARWIF as disciplined acoustic-scene context rather than physical simulation. `ARWIF` now has a first-class room-aware layer for dimensions, surface character, and listening zones, but it still avoids renderer-specific acoustics or dense propagation models. The result is a stronger reasoning and review surface for audio scenes without blurring the format boundary into full environmental simulation.
