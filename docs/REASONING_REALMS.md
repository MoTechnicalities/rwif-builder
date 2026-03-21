# Reasoning Realms

## Purpose

This document organizes the `?RWIF` family by reasoning function rather than by novelty.

The goal is not to invent a suffix for every interesting domain.
The goal is to define the minimum set of structured artifacts that materially improve AI comprehension, reasoning, and production.

Each realm below exists only if it represents a distinct kind of causal structure that an AI system can inspect, compare, revise, and use to produce better outcomes.

## Design Standard

A reasoning realm earns its place only if it improves one or more of the following:

1. comprehension: the system can understand what is present and why it matters
2. reasoning: the system can compare alternatives, infer consequences, and revise decisions
3. production: the system can generate or transform outputs reliably enough to matter

If a proposed realm cannot satisfy at least one of those criteria in a concrete way, it should not become a first-class format.

## Core Realms

### RWIF

Meaning and semantic memory.

Primary function:

- preserve concepts, associations, goals, and contextual memory

Why it matters:

- gives the system a stable semantic substrate for retrieval and long-term reasoning

Implemented here today:

- yes

Reference:

- [docs/RWIF_DEEP_DIVE.md](docs/RWIF_DEEP_DIVE.md)

### ARWIF

Sounding and acoustic structure.

Primary function:

- preserve renderable sound causality, timing, transitions, and inspectable audio intent

Why it matters:

- gives the system a structured way to understand, compare, revise, and produce sound rather than only waveform output
- spatial extensions to `ARWIF` are especially important because they let the system reason about proximity, motion, spread, envelopment, and scene placement rather than only pitch and amplitude

Implemented here today:

- yes

Reference:

- [docs/ARWIF_v0.1.md](docs/ARWIF_v0.1.md)

### VRWIF

Seeing and visual structure.

Primary function:

- preserve scene state, motion, layout, camera intent, lighting behavior, and renderable visual causality

Why it matters:

- gives the system a structured visual substrate instead of forcing it to reason only from pixels or prompts

Implemented here today:

- partial: source-spec validation, normalization, inspection, and diff

Reference:

- [docs/VRWIF.md](docs/VRWIF.md)

## Bridge Realms

### MRWIF

Multimodal correspondence.

Primary function:

- preserve how meaning maps to sound, vision, and other perceptual structures

Why it matters:

- lets the system move from semantic intent to media and from media back to semantic interpretation

Implemented here today:

- no, draft only

Reference:

- [docs/MRWIF.md](docs/MRWIF.md)

### TRWIF

Time, sequence, and transition structure.

Primary function:

- preserve event order, episodes, state changes, temporal expectations, and causal sequence

Why it matters:

- many reasoning failures are failures to model change rather than failures to model content

Implemented here today:

- no, draft only

Reference:

- [docs/TRWIF.md](docs/TRWIF.md)

## Agency Realms

### CRWIF

Control, action, and intervention.

Primary function:

- preserve available actions, policies, control surfaces, and intervention logic

Why it matters:

- gives the system a structured answer to the question: what can I do next?

Implemented here today:

- no, draft only

Reference:

- [docs/CRWIF.md](docs/CRWIF.md)

### ERWIF

Embodiment, feedback, and consequence sensing.

Primary function:

- preserve felt or measured consequence, position, interaction feedback, resistance, and environmental response

Why it matters:

- reasoning improves when action can be linked to sensed consequence rather than recorded only as an abstract command

Implemented here today:

- no, draft only

Reference:

- [docs/ERWIF.md](docs/ERWIF.md)

## Flow Across Realms

The intended reasoning flow is:

1. `RWIF` captures what something means.
2. `MRWIF` links that meaning to perceptual or structural targets.
3. `ARWIF` and `VRWIF` encode how it should sound or look.
4. `TRWIF` preserves how it changes over time.
5. `CRWIF` preserves what actions can change it.
6. `ERWIF` preserves what happened when those actions were taken.

This flow is not mandatory in every system, but it provides a disciplined model for how reasoning can move from memory to perception to action and back again.

## Current Repo Position

This repo currently proves two operational legs of that stack and a narrow third:

- `RWIF` for semantic-memory authoring
- `ARWIF` for structured sound authoring
- `VRWIF` for review-oriented visual source-spec authoring

The remaining realms are documented as design targets so the broader reasoning architecture remains coherent as the project evolves.