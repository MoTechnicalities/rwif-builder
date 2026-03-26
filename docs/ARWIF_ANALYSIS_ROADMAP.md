# ARWIF Analysis Roadmap

## Purpose

This roadmap describes a disciplined path from the current ARWIF synthesis-oriented profile toward an analysis-grade ARWIF capable of representing inferred source structure from real recordings.

The governing constraint is not maximum DSP sophistication.
The governing constraint is whether each stage improves:

1. AI comprehension
2. AI reasoning
3. AI-guided production

## Strategic Thesis

The safest way to reach analysis-grade ARWIF is not to jump directly to perfect source separation.

The safer path is:

1. ingest real audio
2. preserve structured observations
3. preserve task-conditioned attention and retention intent
4. add disciplined decomposition layers
5. add limited reconstruction
6. add source-level inference and regeneration

That keeps the project testable and keeps claims aligned with what the code actually does.

## Cross-Cutting Requirement: Attention Contracts

Every later phase should assume that ARWIF is an AI workspace file, not merely a passive analysis dump.

That means the representation should preserve:

1. what the source audio was
2. what the AI was asked to focus on
3. what the AI chose to retain or suppress
4. what output or answer the user expects later

Examples:

- keep instrument structure and omit vocals
- isolate background dolphin sounds behind whale calls
- retain the drum pattern and harmonic bed while ignoring crowd noise

Without that layer, later regeneration and question answering will be ambiguous.
The system will not know whether an absent signal was never present, was intentionally ignored, or was actively removed.

## Phase 0: Current State

Current repo status:

- typed authored-sound profile exists
- validation, inspect, diff, export, import, render, and batch operations exist
- spatial metadata progression exists for channel-aware, object-aware, and initial room-aware context
- no implemented real-audio ingestion or source-inference path exists yet

This phase should be treated as foundation, not failure.

## Phase 1: Real Audio Ingestion

### Goal

Accept real recordings as analysis inputs without yet claiming source recovery.

### Likely Scope

- decode `.wav`, `.flac`, and `.mp3`
- normalize sample-rate and channel metadata for analysis
- preserve source file provenance
- compute deterministic analysis windows and frame metadata

### Deliverables

- CLI path for audio analysis import
- artifact or spec form for observed-audio metadata
- inspection output for timing, channels, duration, sample rate, and energy summaries

The first concrete CLI contract for this phase is defined in [docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md](docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md).

### Success Standard

ARWIF can represent observed audio evidence consistently enough for later decomposition work.

## Phase 2: Observed Structure Layer

### Goal

Represent the recording in a richer mathematical form than raw samples alone.

### Likely Scope

- time-frequency summaries
- harmonic/noise split candidates
- onset and transient maps
- envelope traces
- pitch and salience candidates
- section and phrase boundary candidates

### Deliverables

- initial analysis schema for observation tracks
- inspect and diff support for observed structure
- report outputs that summarize stable repeated patterns
- explicit support for carrying attention-relevant evidence forward into later phases

### Success Standard

An AI can inspect the artifact and see structured evidence for how the recording behaves over time.

## Phase 3: Inferred Source Hypotheses

### Goal

Move from observed structure to probable source-level decomposition.

### Likely Scope

- vocal versus accompaniment split
- coarse source classes such as drums, bass, harmonic bed, lead vocal, backing vocal
- confidence scores and overlap notes
- explicit ambiguity where multiple explanations remain plausible
- query-conditioned source prioritization so the artifact can retain only the structures relevant to the requested task

### Deliverables

- source hypothesis records
- confidence-aware inspect and diff views
- batch review surfaces for recurring source changes across candidates
- a persisted attention contract that explains why certain sources were retained, suppressed, or left unresolved

### Success Standard

The artifact can answer what sources are probably present and how certain those inferences are.

## Phase 4: Reconstructable Structural Components

### Goal

Store enough structured information to support meaningful regeneration.

### Likely Scope

- harmonic partial groups
- transient event objects
- noise-band components
- source envelopes and pitch trajectories
- residual and unexplained energy tracking

### Deliverables

- regeneration-oriented component schema
- comparison metrics between source audio and reconstructed output
- partial re-render support from inferred components

### Success Standard

ARWIF can regenerate useful approximations of inferred stems or source groups, not only descriptive summaries.

## Phase 5: Stem-Oriented Operations

### Goal

Support AI-guided extraction and transformation workflows.

### Likely Scope

- export probable vocal stem
- export accompaniment stem
- mute or isolate source groups
- compare multiple decomposition candidates
- preserve revision trails across extraction attempts

### Deliverables

- CLI operations for stem-oriented export
- review and diff support for competing analysis outputs
- provenance and confidence reporting for extracted results

### Success Standard

The system can perform useful extraction workflows while still preserving uncertainty and provenance.

## Phase 6: Semantic And Multimodal Integration

### Goal

Connect inferred audio structure back to meaning and multimodal correspondence.

### Likely Scope

- write source identities and descriptors into `RWIF`-adjacent memory
- connect inferred sonic motifs to `MRWIF` correspondence records
- support reasoning over intent, style, and perceptual fit

### Success Standard

Audio analysis becomes part of the broader reasoning stack rather than a disconnected DSP sidecar.

## Release Discipline

The repo should resist overclaiming.

Each release slice should be judged by:

1. what new structure it represents
2. what AI-visible reasoning value it adds
3. whether it supports validation, inspection, diff, and review
4. whether it preserves explicit uncertainty where needed

## Recommended Early Milestones

The first practical milestones should be:

1. `arwif-analyze-audio` for real-file ingestion and observation summaries
2. observation-schema draft with inspect support
3. diffable source-hypothesis schema for coarse source classes
4. limited vocal-versus-accompaniment workflow before finer-grained decomposition

## Risk Areas

Major risks include:

- pretending inference is exact when it is not
- storing opaque latent blobs with little inspection value
- making regeneration claims before component models are strong enough
- allowing schema growth to outrun validation and review tooling

## Best Framing

The right promise is not:

"ARWIF perfectly reconstructs lost original audio."

The right promise is:

"ARWIF incrementally captures the most useful recoverable and task-relevant structure of recorded sound in a form AI can inspect, compare, revise, and regenerate."