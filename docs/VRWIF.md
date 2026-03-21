# VRWIF Draft

## Purpose

`VRWIF` stands for Visual Resonant Wave Information Format.

Its role is to preserve structured visual causality rather than only final frames.

Where a conventional video format stores rendered images over time, `VRWIF` should store how a scene is composed, how it changes, and what visual forces shape its perception.

## Scope

`VRWIF` should describe:

- scene state
- object layout
- motion
- camera framing and movement
- lighting behavior
- visual attention cues
- renderable visual intent

It should not try to replace every production asset format.
Its purpose is to be a reasoning-friendly representation of visual structure.

## Core Questions

`VRWIF` should help answer:

- What is in the scene?
- How is it changing?
- Why does the scene feel sparse, tense, intimate, or monumental?
- What changed visually between two versions?

## Core Entities

### Scene State

Represents the current structured state of a visual environment.

This can include:

- participating objects
- spatial arrangement
- environmental context
- active lighting profile

### Visual Object

Represents a renderable or semantically meaningful element in the scene.

This can include:

- identity
- position and transform
- appearance class
- motion role
- group membership

### Camera Intent

Represents how the scene is meant to be observed.

This can include:

- framing
- perspective
- movement path
- focal priority
- cut or transition intent

### Lighting Intent

Represents the visual shaping force of the scene.

This can include:

- source locations
- color and temperature
- intensity behavior
- contrast goals
- atmospheric emphasis

## Draft Shape

A practical `VRWIF` draft would likely need:

- scene identifiers
- object records
- transform and motion fields
- camera records
- lighting records
- transition metadata
- render policy or target metadata

## Smallest Viable v0.1 Surface

The healthiest first `VRWIF` slice should stay narrow and align with the identity bridge now present in `ARWIF`.

Top-level scene fields:

- `vrwif_version`
- `scene_id`
- `reference_frame` as one of `scene` or `world`
- `title`
- `description`
- `objects`
- `camera`
- `lighting`
- `metadata`

Minimum object fields:

- `object_id` as a stable non-empty identifier
- `object_groups` as a list of non-empty grouping labels
- `class` or `appearance_class`
- `position`
- `orientation` or `transform`
- optional `trajectory`
- optional `state` or `visibility`

Minimum camera fields:

- `camera_id`
- `position`
- `orientation`
- optional `trajectory`
- optional `framing_intent`

Minimum lighting fields:

- one or more light records with stable ids
- position or directional intent
- intensity
- color or temperature

This keeps `VRWIF` inspectable and diffable without trying to encode full render-engine behavior.

## Current Repo Surface

This repo now implements an initial `VRWIF` source-spec validation, inspection, and diff path.

Supported commands:

- `rwif vrwif-validate-spec <spec> --json`
- `rwif vrwif-normalize <spec> --output <normalized.{yaml|json}> --json`
- `rwif vrwif-inspect <spec> --json`
- `rwif vrwif-diff <left> <right> --json`
- `rwif vrwif-batch-diff-analyze <report.{json|yaml}> --output <analysis.json|yaml> --json`
- `rwif vrwif-batch-normalize <spec...> --output-dir <dir> --output <report.json|yaml> --json`
- `rwif vrwif-batch-inspect <spec...> --output <report.json|yaml> --json`
- `rwif vrwif-batch-diff --left <spec...> --right <spec...> --output <report.json|yaml> --json`
- `rwif vrwif-batch-review --left <spec...> --right <spec...> --output <review.json|yaml> --json`
- `rwif vrwif-batch-validate-spec <spec...> --output <report.json|yaml> --json`

The current validator checks:

- top-level `scene_id`
- top-level `reference_frame`
- object identity via `object_id`
- object grouping via `object_groups`
- object placement via `position`
- optional object `orientation` and `trajectory`
- camera identity and placement
- lighting identity plus directional or positional intent

The current normalization path also:

- inserts the strict `vrwif_version`
- canonicalizes `class` into `appearance_class`
- normalizes reference-frame casing
- sorts object groups for stable review output
- sorts trajectories by `offset_seconds`
- reorders objects and lights by stable ids for cleaner diff baselines

The current inspection path reports compact scene summaries including object ids, object groups, appearance classes, positioned-object counts, trajectory counts, camera presence, and lighting presence.

The current diff path reports top-level metadata changes, added or removed objects, changed objects, object field deltas, and scene-level changes such as reference-frame drift, group changes, camera changes, and lighting id changes.

The current batch normalization, batch inspection, and batch diff paths scale those same source-authoring and review surfaces across collections of VRWIF scene specs, returning aggregated counts plus the full per-spec or per-pair payloads.

The current batch diff analysis path builds on a saved `vrwif-batch-diff` report, aggregates recurring metadata and object changes across all compared pairs, and summarizes scene-level drift such as reference-frame changes, camera changes, trajectory deltas, and lighting identity churn.

The current batch review path collapses those two review steps into one command by running pairwise VRWIF batch diff and the recurring-change analysis together in a single payload.

It does not yet build artifacts or render them.

## ARWIF Alignment

The current `ARWIF` bridge work suggests a clean cross-realm contract:

- `ARWIF.source_id` should map naturally to `VRWIF.object_id` when a sound source belongs to a visible scene object
- `ARWIF.source_groups` should map naturally to `VRWIF.object_groups` for coarse scene membership
- `ARWIF.reference_frame` and `VRWIF.reference_frame` should use compatible semantics so audio and visual coordinates can be compared without ad hoc reinterpretation

That does not mean `VRWIF` extends `ARWIF`.
It means both realms can share a stable identity and coordinate contract while remaining separate reasoning surfaces.

## Design Principles

1. Preserve visual causality, not only visual output.
2. Keep the model inspectable and diffable.
3. Distinguish scene intent from final render strategy.
4. Represent salience and emphasis explicitly when possible.
5. Keep the schema narrow enough for reasoning systems to use reliably.

## Relationship To This Repo

This repo now implements a narrow `VRWIF` source-spec surface.

It appears in the wider format-family vision because structured vision is the natural companion to `ARWIF` structured sound and `RWIF` semantic memory, but the shipped implementation remains intentionally limited to validation, normalization, inspection, diff, and batch review.