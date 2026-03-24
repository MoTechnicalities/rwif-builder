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
- stable identity growth or shrinkage across revisions
- state diversity growth or shrinkage across revisions
- visibility diversity growth or shrinkage across revisions
- position and transform
- appearance class
- appearance-class diversity growth or shrinkage across revisions
- motion role
- group membership
- group diversity growth or shrinkage across revisions

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
- light-color diversity growth or shrinkage across revisions
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
- optional `state` or `visibility`, where state can use `idle`, `active`, or `transitioning` and visibility can use `visible`, `occluded`, or `hidden`

Minimum camera fields:

- `camera_id`
- `position`
- `orientation`
- optional `trajectory`
- optional `framing_intent` using one of `establishing`, `centered-medium`, `subject-focused`, or `detail-close`

Minimum lighting fields:

- one or more light records with stable ids
- position or directional intent
- intensity
- color or temperature, where color can use `warm`, `neutral`, `cool`, or `accent`

This keeps `VRWIF` inspectable and diffable without trying to encode full render-engine behavior.

## Current Repo Surface

This repo now implements an initial `VRWIF` source-spec validation, inspection, and diff path.

Supported commands:

- `rwif vrwif-validate-spec <spec> --json`
- `rwif vrwif-normalize <spec> --output <normalized.{yaml|json}> --report <report.{json|yaml}> --assumptions <manifest.{json|yaml}> --json`
- `rwif vrwif-inspect <spec> --json`
- `rwif vrwif-diff <left> <right> --json`
- `rwif vrwif-batch-normalize-analyze <report.{json|yaml}> --output <analysis.json|yaml> --json`
- `rwif vrwif-batch-normalize-review <spec...> --output-dir <dir> --output <review.json|yaml> --json`
- `rwif vrwif-batch-diff-analyze <report.{json|yaml}> --output <analysis.json|yaml> --json`
- `rwif vrwif-batch-normalize <spec...> --output-dir <dir> --report-dir <dir> --assumptions-dir <dir> --output <report.json|yaml> --json`
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
- optional object state via canonical `state`
- optional object visibility via canonical `visibility`
- optional object `orientation` and `trajectory`
- camera identity and placement plus canonical framing intent
- lighting identity plus directional or positional intent, optional temperature, and canonical lighting color

The current normalization path also:

- inserts the strict `vrwif_version`
- canonicalizes `class` into `appearance_class`
- normalizes reference-frame casing

The current inspect and diff path also:

- summarizes appearance-class roster diversity growth or shrinkage across revisions
- summarizes total object distance from origin plus the min/max object-distance range
- summarizes total object-trajectory duration plus the min/max object-trajectory duration range
- summarizes total object-trajectory path length plus the min/max object-trajectory path-length range
- summarizes total object-trajectory displacement plus the min/max object-trajectory displacement range
- summarizes total object-trajectory average speed plus the min/max object-trajectory average-speed range
- summarizes total object-trajectory peak speed plus the min/max object-trajectory peak-speed range
- summarizes total object-trajectory speed standard deviation plus the min/max object-trajectory speed-standard-deviation range
- summarizes total object-trajectory average acceleration plus the min/max object-trajectory average-acceleration range
- summarizes total object-trajectory peak acceleration plus the min/max object-trajectory peak-acceleration range
- summarizes total object-trajectory straightness plus the min/max object-trajectory straightness range
- summarizes total object-trajectory cumulative turn angle in degrees plus the min/max object-trajectory turn-angle range
- summarizes total object-trajectory peak turn angle in degrees plus the min/max object-trajectory peak-turn-angle range
- summarizes total object-trajectory turn count plus the min/max object-trajectory turn-count range
- summarizes total object-trajectory average turn angle in degrees plus the min/max object-trajectory average-turn-angle range
- summarizes total object-trajectory turn-angle standard deviation in degrees plus the min/max object-trajectory standard-deviation range
- summarizes derived camera-trajectory duration when camera keyframes are present
- summarizes derived camera-trajectory path length when camera keyframes are present
- summarizes derived camera-trajectory displacement when camera keyframes are present
- summarizes derived camera-trajectory average speed when camera keyframes are present
- summarizes derived camera-trajectory average acceleration when camera keyframes are present
- summarizes derived camera-trajectory peak acceleration when camera keyframes are present
- summarizes derived camera-trajectory straightness when camera keyframes are present
- summarizes derived camera-trajectory cumulative turn angle in degrees when camera keyframes are present
- summarizes derived camera-trajectory peak turn angle in degrees when camera keyframes are present
- summarizes derived camera-trajectory turn count when camera keyframes are present
- summarizes derived camera-trajectory average turn angle in degrees when camera keyframes are present
- summarizes derived camera-trajectory turn-angle standard deviation in degrees when camera keyframes are present
- summarizes derived camera distance from the origin when a camera is present
- summarizes total light intensity plus the min/max scene intensity range
- summarizes positioned lights separately from directional lights
- summarizes how many lights carry explicit `temperature_kelvin` values plus the min/max scene temperature range when present
- summarizes light-color roster diversity growth or shrinkage across revisions
- treats light-temperature coverage drift and light-temperature range drift as first-class scene-review signals in pairwise and batch analysis
- sorts object groups for stable review output
- sorts trajectories by `offset_seconds`
- reorders objects and lights by stable ids for cleaner diff baselines
- can emit a persisted normalization report containing source validation, normalized validation, the change summary, and the canonicalized document
- can emit a smaller assumptions manifest focused on the authoring decisions and warnings produced during canonicalization

The current inspection path reports preserved top-level `metadata` plus a normalized `realm_references` view derived from `metadata.related_realms` or `metadata.realm_references`, so VRWIF source specs can expose clean outward pointers to neighboring `RWIF`, `ARWIF`, or future realms without collapsing those bridge links into scene geometry itself.

The current inspection path reports compact scene summaries including object ids, object groups, appearance classes, canonical object state and visibility summaries, total object distance from origin, object-distance range, total object-trajectory duration, object-trajectory duration range, total object-trajectory path length, object-trajectory path-length range, total object-trajectory displacement, object-trajectory displacement range, total object-trajectory average speed, object-trajectory average-speed range, total object-trajectory peak speed, object-trajectory peak-speed range, total object-trajectory speed standard deviation, object-trajectory speed-standard-deviation range, total object-trajectory average acceleration, object-trajectory average-acceleration range, total object-trajectory peak acceleration, object-trajectory peak-acceleration range, total object-trajectory straightness, object-trajectory straightness range, total object-trajectory cumulative turn angle in degrees, object-trajectory turn-angle range in degrees, total object-trajectory peak turn angle in degrees, object-trajectory peak-turn-angle range in degrees, total object-trajectory turn count, object-trajectory turn-count range, total object-trajectory average turn angle in degrees, object-trajectory average-turn-angle range in degrees, total object-trajectory turn-angle standard deviation in degrees, object-trajectory turn-angle standard-deviation range in degrees, positioned-object counts, trajectory counts, canonical camera framing intent, camera presence, derived camera-trajectory duration, derived camera-trajectory path length, derived camera-trajectory displacement, derived camera-trajectory average speed, derived camera-trajectory peak speed, derived camera-trajectory speed standard deviation, derived camera-trajectory average acceleration, derived camera-trajectory peak acceleration, derived camera-trajectory straightness, derived camera-trajectory cumulative turn angle in degrees, derived camera-trajectory peak turn angle in degrees, derived camera-trajectory turn count, derived camera-trajectory average turn angle in degrees, derived camera-trajectory turn-angle standard deviation in degrees, derived camera distance from origin, lighting presence, light ids, light counts, total light intensity, light-intensity range, positioned-light versus directional-light counts, and canonical lighting colors.

The current diff path reports top-level metadata changes, added or removed objects, changed objects, object field deltas, and scene-level changes such as reference-frame drift, object-count changes, object-id changes, group changes, object-state changes, object-visibility changes, object-distance changes, object-trajectory duration changes, object-trajectory path-length changes, object-trajectory displacement changes, object-trajectory average-speed changes, object-trajectory peak-speed changes, object-trajectory speed-standard-deviation changes, object-trajectory average-acceleration changes, object-trajectory peak-acceleration changes, object-trajectory straightness changes, object-trajectory cumulative turn-angle changes in degrees, object-trajectory peak-turn-angle changes in degrees, object-trajectory turn-count changes, object-trajectory average-turn-angle changes in degrees, object-trajectory turn-angle standard-deviation changes in degrees, object-trajectory point-count changes, framing-intent changes, camera changes, camera-presence changes, camera-id changes, camera-trajectory presence changes, camera-trajectory duration changes, camera-trajectory path-length changes, camera-trajectory displacement changes, camera-trajectory average-speed changes, camera-trajectory peak-speed changes, camera-trajectory speed-standard-deviation changes, camera-trajectory average-acceleration changes, camera-trajectory peak-acceleration changes, camera-trajectory straightness changes, camera-trajectory cumulative turn-angle changes in degrees, camera-trajectory peak-turn-angle changes in degrees, camera-trajectory turn-count changes, camera-trajectory average-turn-angle changes in degrees, camera-trajectory turn-angle standard-deviation changes in degrees, camera-trajectory point-count changes, camera-distance changes, lighting-presence changes, light-intensity changes, light-placement deltas, lighting-color changes, lighting id changes, light-id roster changes, and object id changes.

The current batch normalization, batch inspection, and batch diff paths scale those same source-authoring and review surfaces across collections of VRWIF scene specs, returning aggregated counts plus the full per-spec or per-pair payloads.

The current batch normalization path can also emit per-spec normalization reports and smaller per-spec assumptions manifests into sibling directories so canonicalization remains auditable across collections instead of only producing rewritten scene files.

The current batch normalization analysis path builds on a saved `vrwif-batch-normalize` report, highlights recurring normalization actions such as alias resolution or unknown-field cleanup, summarizes recurring source or normalized warnings, and ranks the specs carrying the heaviest normalization burden so collection-scale cleanup work can be reviewed without opening every per-spec artifact.

The current batch normalization review path collapses those two steps into one command by running batch normalization and normalization analysis together in a single persisted review payload.

The current batch diff analysis path builds on a saved `vrwif-batch-diff` report, aggregates recurring metadata and object changes across all compared pairs, and summarizes scene-level drift such as reference-frame changes, object-state changes, object-visibility changes, object-distance drift, object-trajectory duration drift, object-trajectory path-length drift, object-trajectory displacement drift, object-trajectory average-speed drift, object-trajectory peak-speed drift, object-trajectory speed-standard-deviation drift, object-trajectory straightness drift, object-trajectory cumulative turn-angle drift in degrees, object-trajectory peak-turn-angle drift in degrees, object-trajectory turn-count drift, object-trajectory average-turn-angle drift in degrees, object-trajectory turn-angle standard-deviation drift in degrees, framing-intent changes, camera changes, camera-trajectory duration drift, camera-trajectory path-length drift, camera-trajectory displacement drift, camera-trajectory average-speed drift, camera-trajectory peak-speed drift, camera-trajectory speed-standard-deviation drift, camera-trajectory straightness drift, camera-trajectory cumulative turn-angle drift in degrees, camera-trajectory peak-turn-angle drift in degrees, camera-trajectory turn-count drift, camera-trajectory average-turn-angle drift in degrees, camera-trajectory turn-angle standard-deviation drift in degrees, camera-distance drift, trajectory deltas, light-intensity drift, light-placement deltas, lighting-color changes, and lighting identity churn.

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