# ARWIF Analysis Mission

## Purpose

This document defines the longer-term ARWIF target that goes beyond the current `v0.1` synthesis-oriented profile.

The current ARWIF implementation is useful, but narrow.
It treats structured sound primarily as authored oscillator-bank instructions plus reviewable metadata.

The larger ambition is different:

ARWIF should eventually become an analysis-grade representation of inferred underlying audio structure, so AI systems can inspect, reason over, revise, and regenerate the causal components of recorded sound.

More specifically, ARWIF should become an AI workspace file for sound.
It should preserve not only what was observed, but also what the AI was asked to pay attention to, what it inferred, what it chose to retain or suppress, and what kind of audible output it should later regenerate.

## Core Claim

An input recording such as `.wav`, `.flac`, or `.mp3` should not be treated as the final truth of the sound.

It should be treated as observed evidence.

ARWIF analysis should combine:

- the observed signal
- mathematical audio analysis
- source and instrument priors
- stylistic and production priors
- uncertainty tracking

to produce the best plausible structured model of the underlying sound sources and their behavior.

That model is the real target artifact.

## AI Workspace Framing

ARWIF does not need to be a perfect archival mirror of the source recording.

In many workflows, the more useful target is a task-conditioned sound workspace that preserves:

- the observed recording as evidence
- the active attention contract for the current task
- the inferred entities, source relationships, and uncertainties relevant to that task
- the intended transformation or regeneration target

Examples include:

- retain accompaniment and suppress lead vocal
- isolate likely dolphin background sounds behind whale calls
- preserve drum, bass, and vocal structure while ignoring room noise

Under that framing, ARWIF can be lossy by design while still being highly useful for AI reasoning.
The loss is acceptable when it is intentional, explicit, and aligned with the request.

## What This Is Not

This mission does not require claiming that a lossy recording can always be reversed into the exact historical waveform that existed before compression, mixing, mastering, or degradation.

That claim would usually be indefensible.

The realistic claim is stronger in practice and cleaner in theory:

ARWIF should preserve the best recoverable and most plausible causal audio structure that can be inferred from the available signal plus learned acoustic knowledge.

## Why This Matters

If ARWIF remains only a typed procedural synthesis format, it will remain useful but limited.

If ARWIF grows into an analysis-grade structure format, it can support workflows such as:

- vocal extraction
- accompaniment isolation
- source-level revision
- cleaner stem regeneration
- arrangement comparison across versions
- acoustic reasoning rather than only waveform handling
- writing inferred sonic structure back into semantic memory and multimodal bridge layers

That is the scale of capability the repo originally points toward.

## The Representation Goal

ARWIF analysis should not store only one kind of audio data.

It should store multiple layers of structure:

1. observed signal evidence
2. task or attention contract
3. inferred source tracks or sound entities
4. harmonic, transient, and noise decomposition
5. time-varying envelopes and pitch trajectories
6. source identity, role, and interpretation hypotheses
7. confidence and ambiguity notes
8. regeneration-ready parameters or constraints

The format should help an AI answer questions such as:

- What sources are probably present?
- Which energy belongs to the lead vocal versus backing parts?
- Which events are transient percussion versus sustained harmonic content?
- Which parts are stable enough to regenerate cleanly?
- What changed between two mixes or masters?
- Which inferences are strong and which remain uncertain?

## Mission Boundary

The mission is not to simulate a full digital audio workstation inside one file format.

The mission is to preserve enough structured acoustic causality that:

- analysis is inspectable
- attention is explicit
- revision is intentional
- regeneration is tractable
- uncertainty is explicit
- AI reasoning is materially improved over raw waveform or spectrogram access alone

## Relationship To ARWIF v0.1

`ARWIF v0.1` remains valid as a narrow structured-synthesis profile.

That profile proves several important workflow properties:

- typed authoring
- validation
- inspection
- diffing
- export and import
- rendering
- batch review

Those properties should be preserved as ARWIF grows.

But `v0.1` is not the full long-term target.
It is the first disciplined slice.

## Working Definition

The long-term ARWIF analysis target is:

> a structured, inspectable, revision-friendly AI workspace representation of observed sound, inferred entities, task-conditioned attention, and causal acoustic relationships, suitable for reasoning, selective retention, extraction, and regeneration.

## Design Principles

1. Treat recordings as evidence, not as the whole ontology.
2. Preserve the active attention contract rather than assuming every workflow requires full retention.
3. Prefer source and behavior models over raw sample dumps.
4. Preserve uncertainty rather than pretending every decomposition is exact.
5. Keep the representation explainable enough for inspection and diff.
6. Preserve enough structure for downstream regeneration of the retained target.
7. Keep synthesis-oriented and analysis-oriented profiles distinguishable.

## Practical Consequence For This Repo

This repo should now treat ARWIF as having two clearly different trajectories:

- `ARWIF synthesis profile`: the currently implemented authored-sound path
- `ARWIF analysis profile`: the planned inferred-audio path for decomposition, reasoning, and source reconstruction

That distinction should drive future schema work, CLI design, and release slicing.

The first concrete proposed CLI surface for that second path is documented in [docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md](docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md).