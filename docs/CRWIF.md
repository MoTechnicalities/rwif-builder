# CRWIF Draft

## Purpose

`CRWIF` stands for Control Resonant Wave Information Format.

Its role is to represent action, intervention, and policy as structured reasoning artifacts.

Where semantic memory answers what something means, `CRWIF` answers what can be done about it.

## Scope

`CRWIF` should describe:

- available actions
- control surfaces
- intervention policies
- decision constraints
- actuator mappings
- action provenance

It should not try to replace domain-specific execution engines.
Its purpose is to preserve the reasoning-facing structure of control.

## Core Questions

`CRWIF` should help answer:

- What actions are available?
- Which action is appropriate in this context?
- What policy selected this action?
- What changed because the action was taken?

## Core Entities

### Action Primitive

A named operation the system can perform.

Examples:

- render artifact
- relocate source
- increase spatial spread
- trigger scene transition

### Policy Record

Describes why one action or action family is preferred.

This can include:

- selection rules
- constraints
- safety checks
- priority ordering

### Control Mapping

Links abstract action to concrete controllable parameters.

Examples:

- semantic request to parameter changes
- spatial intent to renderer controls
- revision request to artifact transformation

## Draft Shape

A practical `CRWIF` draft would likely need:

- action identifiers
- input and output constraints
- target references
- policy metadata
- execution conditions
- provenance and revision notes

## Design Principles

1. Preserve the difference between decision and execution.
2. Keep action surfaces inspectable.
3. Make control mappings explainable.
4. Store policy constraints explicitly.
5. Keep the format useful for both planning and audit.

## Relationship To This Repo

This repo does not implement `CRWIF` today.

It belongs in the broader vision because a reasoning stack becomes more complete when semantic memory and perceptual structure can be linked to actionable intervention rather than observation alone.