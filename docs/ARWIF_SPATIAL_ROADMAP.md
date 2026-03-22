# ARWIF Spatial Roadmap

## Purpose

This document describes the likely path from `ARWIF v0.1` as a mono sequential oscillator-bank format toward a more spatially expressive family of sound representations.

The governing constraint is not merely acoustic sophistication.
The governing constraint is whether each spatial tier improves:

1. AI comprehension
2. AI reasoning
3. AI production

If a spatial feature is impressive but opaque, it is the wrong next step.

## Design Thesis

Multi-channel ARWIF should not be treated as a simple speaker-count expansion.

The real opportunity is to evolve ARWIF from a description of sound over time into a description of sound in space and time.

That means preserving spatial acoustic intent in a way that is:

- understandable by reasoning systems
- adaptable to multiple render targets
- precise enough to produce deterministic output where needed

## Spatial Tiers

| Tier | Name | Description |
| --- | --- | --- |
| Level 1 | Channel-aware | Layout metadata plus oscillator or state assignments for known channel topologies. |
| Level 2 | Object-based | Source positions, trajectories, spread, and distance behavior independent of fixed speaker routing. |
| Level 3 | Room-aware | Acoustic scene modeling including room geometry, surface behavior, speaker placement, and listening zones. |
| Level 4 | Field-synthesis | Physically informed sound-field intent for high-end renderers capable of advanced spatial reconstruction. |

## Tier Evaluation Standard

Each tier should be judged by three questions:

1. What can an AI understand better because of this tier?
2. What decisions can an AI make better because of this tier?
3. What outputs can an AI produce more reliably because of this tier?

## Level 1: Channel-aware

### Goal

Support deterministic multichannel playback on known layouts.

Current repo status:

- implemented as top-level `channel_layout` plus per-state `channel_gains`
- rendered output can now target multichannel PCM WAV for supported layouts
- still limited to channel-aware routing rather than object-based or room-aware spatial rendering

### Likely Schema Elements

- `channel_layout`
- `channel_labels`
- per-state channel gains
- per-oscillator channel assignment or weighting
- downmix or compatibility policy

### Reasoning Value

- easy to validate
- easy to diff
- easy to author
- immediately useful for production pipelines

### Best Framing

This is the practical baseline.
It makes ARWIF spatially usable before it becomes deeply spatially intelligent.

## Level 2: Object-based

### Goal

Represent sound sources as spatial entities rather than fixed channel payloads.

### Likely Schema Elements

- `position`
- `trajectory`
- `orientation`
- `spread`
- `distance_model`
- source groups
- listener anchor or reference frame

### Reasoning Value

This is the strongest tier for AI reasoning.

It lets systems work in interpretable spatial concepts such as:

- near or far
- above or below
- centered or surrounding
- approaching or receding
- narrow or diffuse

### Best Framing

This is probably the center of gravity for spatial ARWIF.
It makes spatial intent comprehensible and adaptable across playback targets.

## Level 3: Room-aware

### Goal

Bind spatial audio to an acoustic scene instead of only a source scene.

Current repo status:

- initial support can now preserve validated room-aware context through top-level `room` metadata covering room dimensions, surface profile, listening zones, and initial speaker placement
- inspect, diff, export, and batch review can now summarize those room-aware fields without pretending to solve full room-adaptive rendering

### Likely Schema Elements

- room dimensions or geometry reference
- surface absorption or diffusion classes
- speaker coordinates
- listening zones
- reflection policy
- renderer adaptation hints

### Reasoning Value

This tier helps AI systems reason about environmental context rather than only source placement.

Examples:

- intimate versus monumental
- enclosed versus open
- direct versus reverberant
- focused versus diffuse

### Constraint

This tier should favor meaningful acoustic abstractions over maximal simulation detail.
If the room model becomes too physically dense too early, it will become harder to reason over and harder to author.

## Level 4: Field-synthesis

### Goal

Support advanced renderers that can approximate a target sound field instead of only routing channels or placing objects.

### Likely Schema Elements

- wavefront or field constraints
- spatial energy targets
- reconstruction mode
- renderer capability requirements
- fidelity policy

### Reasoning Value

This tier is valuable for high-end production, research systems, or specialized arrays.

Its direct reasoning value is weaker unless it is wrapped in interpretable abstractions.
Raw field parameters alone are not a good reasoning interface.

### Best Framing

This is an advanced mode, not the baseline promise of spatial ARWIF.

## Recommended Roadmap

The practical progression is:

1. implement `Level 1` first
2. define `Level 2` as the strategic spatial model
3. extend into `Level 3` with disciplined room abstractions
4. reserve `Level 4` for advanced renderers and specialized deployments

This order keeps the format useful, interpretable, and incrementally buildable.

## Production And Reasoning Principles

Spatial ARWIF should prefer:

- interpretable spatial intent over renderer-specific complexity
- authored source meaning over fixed playback assumptions
- one structured scene with multiple render targets
- explicit comparison and revision support
- stable abstractions before advanced acoustics

## What Spatial ARWIF Should Let An AI Ask

A good spatial ARWIF system should let an AI reason in questions like:

- Should this source feel close or distant?
- Should this cue surround the listener or confront them directly?
- Should the scene feel architectural, intimate, suspended, or diffuse?
- What changed spatially between these two versions?
- Which renderer target preserves the intended spatial meaning best?

These are the kinds of questions that make spatial audio compatible with semantic reasoning rather than only signal processing.

## Realistic Claim Boundary

Encoding room geometry or field hints does not guarantee exact reconstruction of an original acoustic field in arbitrary playback environments.

The defensible claim is stronger and clearer than that:

Spatial ARWIF should preserve enough structured spatial intent, source behavior, and environmental context that a capable renderer can realize an appropriate spatial sound field for the target playback situation.

That is the right promise.

## Relationship To The Larger Format Family

Spatial ARWIF belongs inside the wider reasoning stack:

- `RWIF` preserves what the sound means
- `ARWIF` preserves how it sounds and where it lives in space
- `MRWIF` preserves how spatial sonic structure maps back to semantic intent
- `TRWIF` preserves how that spatial scene changes over time

That makes spatial audio part of a reasoning system, not just a rendering feature.