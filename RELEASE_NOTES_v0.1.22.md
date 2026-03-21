# rwif-builder v0.1.22

Feature release expanding the VRWIF source-spec authoring and review surface.

## What Changed

- adds `rwif vrwif-normalize` so loosely authored VRWIF YAML or JSON scene specs can be rewritten into a canonical strict source form before inspection or diff
- adds `rwif vrwif-batch-normalize` so multiple VRWIF specs can be normalized in one pass and collected into a reusable aggregate report
- canonicalizes key VRWIF authoring details during normalization, including `class` to `appearance_class`, reference-frame casing, stable object-group ordering, sorted trajectories, and stable object and light ordering for cleaner diff baselines
- adds `rwif vrwif-batch-diff-analyze` to summarize recurring metadata, object, camera, trajectory, and lighting changes from a saved VRWIF batch diff report
- adds `rwif vrwif-batch-review` as a one-shot workflow that runs VRWIF batch diff and recurring-change analysis together in a single persisted payload
- fixes VRWIF batch diff change detection so scene-only revisions such as camera-only or lighting-only changes are no longer misclassified as unchanged when object counts stay flat
- expands the VRWIF integration suite and updates the README plus realm docs so the shipped VRWIF surface is documented as validation, normalization, inspection, diff, and batch review rather than prose-only design intent

## Scope

This release deepens VRWIF as a source-spec realm without claiming any artifact or render semantics. Teams can now canonicalize loose scene specs into a stable authoring baseline, review collections of scene diffs for recurring patterns, and run a higher-level VRWIF batch review workflow in one step. The scope remains intentionally narrow and review-oriented: VRWIF is now better for structured visual authoring and comparison, not yet for build or render pipelines.