# ERWIF Draft

## Purpose

`ERWIF` stands for Embodied Resonant Wave Information Format.

Its role is to represent sensed consequence, feedback, and interaction outcome in a form that reasoning systems can preserve and reuse.

If `CRWIF` answers what the system can do, `ERWIF` answers what happened when it did it.

## Scope

`ERWIF` should describe:

- feedback from action
- position and orientation changes
- sensed consequence
- resistance, latency, or response behavior
- environment reaction
- outcome confidence

It should not be limited to robotics.
Any system with meaningful action-consequence loops can benefit from a structured feedback substrate.

## Core Questions

`ERWIF` should help answer:

- What did the system experience after acting?
- Did the environment respond as expected?
- What signals indicate success, resistance, or failure?
- What should be remembered about this consequence for future decisions?

## Core Entities

### Feedback Record

Represents the measured or inferred result of an action.

This can include:

- observed outcome
- deviation from expectation
- confidence
- environmental notes

### State Response

Represents how the controlled system or environment changed.

Examples:

- source moved closer than expected
- render output became brighter than intended
- listening zone response differed from model

### Embodied Trace

Represents a short sequence of action and consequence as a reusable experiential unit.

This can support:

- adaptation
- calibration
- policy revision
- memory of successful or failed interventions

## Draft Shape

A practical `ERWIF` draft would likely need:

- action references
- observed state fields
- deviation or error fields
- response metadata
- uncertainty values
- provenance and timestamping

## Design Principles

1. Preserve consequence, not just command history.
2. Keep expected and observed outcomes distinct.
3. Record uncertainty explicitly.
4. Make feedback reusable for later policy revision.
5. Support both physical and simulated environments.

## Relationship To This Repo

This repo does not implement `ERWIF` today.

It appears in the wider vision because meaningful reasoning eventually requires a memory of consequence, not only a memory of intent, structure, and action.