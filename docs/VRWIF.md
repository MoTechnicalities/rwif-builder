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

## Design Principles

1. Preserve visual causality, not only visual output.
2. Keep the model inspectable and diffable.
3. Distinguish scene intent from final render strategy.
4. Represent salience and emphasis explicitly when possible.
5. Keep the schema narrow enough for reasoning systems to use reliably.

## Relationship To This Repo

This repo does not implement `VRWIF` today.

It appears in the wider format-family vision because structured vision is the natural companion to `ARWIF` structured sound and `RWIF` semantic memory.