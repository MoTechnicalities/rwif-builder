# TRWIF Draft

## Purpose

`TRWIF` stands for Temporal Resonant Wave Information Format.

Its purpose is to represent time, sequence, episodes, and transition structure as first-class reasoning data.

Many reasoning failures are not failures of perception or semantics alone.
They are failures to represent how states change.

`TRWIF` is meant to address that gap.

## Scope

`TRWIF` should describe:

- ordered events
- state transitions
- causal timelines
- episodic traces
- temporal uncertainty
- pacing and rhythm at an abstract level

It should not replace `ARWIF` timing for sound rendering or `VRWIF` timing for scene rendering.
Instead, it should represent higher-level temporal structure that can coordinate those formats.

## Core Questions

`TRWIF` should help answer:

- What happened first, next, and last?
- Which transition caused the current state?
- Where did a sequence diverge from expectation?
- Which sound and visual changes belong to the same episode?

## Core Entities

### Episode

A bounded unit of temporal experience or task progress.

Examples:

- a scene arc
- a user interaction sequence
- a musical phrase
- a plan execution window

### Transition

A directed change from one state to another.

This should carry:

- source state
- destination state
- trigger or cause
- timing metadata
- confidence or ambiguity

### Event Trace

An ordered record of what occurred and what followed.

This can support:

- debugging
- reasoning review
- plan reconstruction
- multimodal synchronization

### Temporal Constraint

Represents expectations about order, delay, duration, recurrence, or simultaneity.

Examples:

- event B must follow event A
- sound transition and camera transition should align within a small tolerance
- this identity cue should recur after a period of calm

## Draft Shape

A practical `TRWIF` draft would likely need:

- state identifiers
- event identifiers
- transition edges
- timestamps or relative ordering fields
- duration and cadence fields
- causal notes
- confidence and uncertainty metadata

## Design Principles

1. Represent change explicitly.
2. Keep transitions inspectable.
3. Separate abstract temporal logic from media-specific render timing.
4. Preserve causality and uncertainty together.
5. Make the format useful for both reasoning and synchronization.

## Relationship To This Repo

This repo does not implement `TRWIF` today.

It does, however, already demonstrate why temporal structure matters:

- `RWIF` artifacts preserve ordered states and provenance
- `ARWIF` artifacts already depend on state order and segment progression for playback

`TRWIF` would generalize that notion of sequence into a reusable reasoning substrate rather than leaving it embedded only inside domain-specific formats.