# rwif-builder v0.1.38

Feature release formalizing ARWIF Level 3 listening-zone intents.

## What Changed

- formalizes `room.listening_zones[].intent` with compact canonical enums: `focused`, `balanced`, `diffuse`, and `casual`, so listening-zone metadata now carries a stable review vocabulary instead of free-form strings
- validates listening-zone intents during strict ARWIF spec and artifact checks and exposes derived `listening_zone_intents` summaries in validation stats for both source-spec and built-artifact review flows
- extends `rwif arwif-inspect` and `rwif arwif-diff` so compact spatial summaries now include listening-zone-intent sets and a dedicated `listening_zone_intents_changed` signal alongside existing listening-zone count and identifier review fields
- extends `rwif arwif-batch-diff-analyze` and `rwif arwif-batch-review` so recurring listening-zone-intent drift is aggregated through `listening_zone_intents_changed_pairs`
- updates regression coverage and public docs so listening-zone intent review is part of the tested ARWIF Level 3 batch-review contract

## Scope

This release keeps Level 3 room-aware ARWIF compact and interpretable. Canonical listening-zone intents do not try to model detailed psychoacoustic seating analysis or renderer-specific optimization; they add a small semantic layer so authoring and review workflows can distinguish tighter focal listening from balanced, diffuse, or casual listening areas while preserving the same validate, inspect, diff, export, and batch-review workflow established by earlier room-aware slices.