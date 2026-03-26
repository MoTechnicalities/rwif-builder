# ARWIF Workspace v0 Draft

## Purpose

This document defines a minimal draft for ARWIF as an AI workspace file for sound.

It is narrower than a full long-term ARWIF analysis ontology.
It is broader than the current implemented `basic-observation` analysis slice.

The goal is to define the smallest useful structure that lets an AI:

- remember what sound was observed
- remember what the task asked it to pay attention to
- preserve the inferred entities and relationships relevant to that task
- record what should later be retained, suppressed, answered, or regenerated

This draft is conceptual.
It is not yet the current CLI contract.

## Core Claim

ARWIF workspace documents do not need to preserve everything from the source recording.

They need to preserve everything materially relevant to the current task.

That makes ARWIF intentionally selective.
It is a saved AI reasoning state for sound, not only an archival audio container.

## Minimum Sections

The minimum useful workspace document should contain these sections:

1. `analysis_metadata`
2. `observed_audio`
3. `attention_contract`
4. `observation_layers`
5. `source_hypotheses`
6. `interpretation_layers`
7. `transformation_intent`
8. `reconstruction`
9. `uncertainty_notes`
10. `provenance`

## Section Intent

### `analysis_metadata`

Identifies the workspace profile, version, and analysis run.

### `observed_audio`

Records the source evidence the AI actually analyzed.

### `attention_contract`

Records the active question or request.
This is required in spirit because it explains why some structure was retained and some was ignored.

### `observation_layers`

Stores measurable evidence such as events, transitions, section boundaries, or recurring patterns.

### `source_hypotheses`

Stores the entities the AI believes are present, such as vocals, accompaniment, whale calls, dolphin whistles, or environmental noise.

### `interpretation_layers`

Stores higher-level hypotheses built on top of source structure, such as scene roles, interaction patterns, or tentative semantic interpretations.

### `transformation_intent`

Stores the requested action on the scene, such as suppress vocals, isolate dolphin background sounds, or retain only percussion.

### `reconstruction`

Stores what outputs the AI believes it can later regenerate or answer from the retained structure.

### `uncertainty_notes`

Stores ambiguity, confidence limits, and unresolved competing explanations.

### `provenance`

Stores how the workspace document was built and what assumptions or models participated.

## Minimal Required Questions

Any usable ARWIF workspace document should make these questions answerable:

1. What sound evidence was analyzed?
2. What was the AI asked to do?
3. What entities did the AI infer?
4. What did the AI decide to retain or suppress?
5. What uncertainty remains?
6. What answer or output should later be possible?

## Examples

Two conceptual examples are included under `examples/arwif/`:

- `BABY_LOVE_workspace_accompaniment_only.analysis.yaml`
- `WHALE_DOLPHIN_workspace_query.analysis.yaml`

These examples are intended to clarify the shape of a task-conditioned ARWIF workspace document.
They are not yet consumed by the current synthesis-oriented `arwif-build` command.