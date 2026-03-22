# rwif-builder v0.1.37

Feature release formalizing ARWIF Level 3 speaker roles.

## What Changed

- formalizes the existing `room.speakers[].role` field with compact canonical enums: `main`, `surround`, `height`, and `fill`, so speaker-placement metadata now carries a stable review vocabulary instead of free-form strings
- validates speaker roles during strict ARWIF spec and artifact checks and exposes derived `speaker_roles` summaries in validation stats for both source-spec and built-artifact review flows
- extends `rwif arwif-inspect` and `rwif arwif-diff` so compact spatial summaries now include speaker-role sets and a dedicated `speaker_roles_changed` signal alongside existing speaker-channel and speaker-coverage review fields
- extends `rwif arwif-batch-diff-analyze` and `rwif arwif-batch-review` so recurring speaker-role drift is aggregated through `speaker_roles_changed_pairs`
- updates the shipped Level 3 room-review example pair, regression coverage, and public docs so speaker-role review is part of the tested ARWIF batch-review contract

## Scope

This release keeps Level 3 room-aware ARWIF disciplined and interpretable. Canonical speaker roles do not try to encode detailed routing logic or renderer-specific topology rules; they add a compact semantic layer so review tooling can distinguish main deployment from surround, height, or fill usage while preserving the same validate, inspect, diff, export, and batch-review workflow established by earlier room-aware slices.