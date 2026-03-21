# rwif-builder v0.1.20

Feature release adding initial ARWIF object-spatial metadata.

## What Changed

- adds an initial Level 2 object-metadata slice to strict ARWIF authoring via top-level `listener_anchor` and per-state `position`, `orientation`, `spread`, and `distance_model`
- validates those new spatial object fields in both source-spec and built-artifact flows, including finite coordinate checks, non-negative spread, and bounded `distance_model` values
- preserves the new object-spatial metadata through `arwif-build`, `arwif-import`, `arwif-export`, and round-trip diff flows without changing the existing Level 1 channel-aware rendering path
- extends `rwif arwif-inspect` and `rwif arwif-diff` with object-spatial summaries covering listener anchors, positioned-state counts, orientation/spread usage, and distance-model changes
- extends ARWIF batch diff analysis so recurring review payloads also summarize listener-anchor changes, object-position deltas, orientation deltas, spread usage deltas, and distance-model changes across artifact pairs
- expands the ARWIF integration suite and updates the README plus ARWIF mini-spec so the new object-spatial metadata is documented as a validated reviewable authoring surface rather than a rendered spatial mix engine

## Scope

This release opens the first object-based ARWIF slice without overreaching on rendering claims. Teams can now author, validate, diff, inspect, export, import, and batch-review structured spatial object intent in a stable machine-readable form while the reference renderer remains intentionally limited to the existing Level 1 channel-aware path.