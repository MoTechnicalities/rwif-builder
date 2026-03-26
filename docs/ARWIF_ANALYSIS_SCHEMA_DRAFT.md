# ARWIF Analysis Schema Draft

## Purpose

This document sketches an initial schema direction for analysis-grade ARWIF.

It is intentionally a draft.
The goal is to define a shape that is rich enough for reasoning and regeneration, while remaining structured enough for validation, inspection, diff, and review.

The first concrete proposed CLI surface that should emit this kind of document is defined in [docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md](docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md).

For a narrower workspace-oriented framing built around task-conditioned retention and transformation intent, see [docs/ARWIF_WORKSPACE_V0_DRAFT.md](docs/ARWIF_WORKSPACE_V0_DRAFT.md) and the conceptual examples under `examples/arwif/`.

## Governing Distinction

The current `ARWIF v0.1` profile is synthesis-oriented.

This draft is analysis-oriented.

That means the primary input is not an authored oscillator-bank spec.
The primary input is an observed recording and a set of inferred structures derived from it.

## Draft Object Model

An analysis-grade ARWIF document will likely need at least these top-level sections:

- `analysis_metadata`
- `observed_audio`
- `attention_contract`
- `observation_layers`
- `source_hypotheses`
- `interpretation_layers`
- `component_layers`
- `transformation_intent`
- `reconstruction`
- `uncertainty_notes`
- `provenance`

## 1. Analysis Metadata

This section identifies the analysis run and its operating assumptions.

Likely fields:

- `analysis_profile`
- `analysis_version`
- `created_at`
- `analyzer_id`
- `target_resolution`
- `source_format`
- `notes`

Purpose:

- declare which analysis mode produced the artifact
- distinguish future versions safely
- preserve reproducibility for review and diff

## 2. Observed Audio

This section describes the decoded evidence the system analyzed.

Likely fields:

- `path_hint`
- `duration_seconds`
- `sample_rate_hz`
- `channel_count`
- `bit_depth` when known
- `codec`
- `loudness_summary`
- `peak_summary`
- `spectral_extent_summary`

Purpose:

- preserve what the system actually observed
- separate observed evidence from inferred structure

## 3. Attention Contract

This section explains what the AI was asked to care about and what kind of later answer or output should be possible.

Likely fields:

- `query_text`
- `attention_targets`
- `retain_targets`
- `suppress_targets`
- `comparison_scope`
- `answer_expectations`
- `render_goal`

Purpose:

- distinguish task-relevant retention from full-scene archival capture
- make later reasoning and regeneration interpretable
- prevent ambiguity about why some structure was preserved and other structure was ignored

## 4. Observation Layers

These are structured summaries of measurable signal behavior.

Possible layer families:

- `spectral_frames`
- `harmonic_salience_tracks`
- `noise_energy_tracks`
- `transient_events`
- `onset_map`
- `section_boundaries`
- `tempo_hypotheses`
- `pitch_contours`

Purpose:

- provide mathematically grounded intermediate structure
- support inspection before source identity claims are made

## 5. Source Hypotheses

This section records probable sources inferred from the observed material.

Each source hypothesis may need fields such as:

- `source_id`
- `source_class`
- `role`
- `confidence`
- `time_bounds`
- `dominant_frequency_regions`
- `pitch_range`
- `energy_summary`
- `linked_components`
- `ambiguity_notes`

Example source classes:

- `lead_vocal`
- `backing_vocal`
- `bass`
- `kick`
- `snare`
- `hi_hat`
- `percussion`
- `guitar`
- `keys`
- `brass`
- `strings`
- `room`
- `unknown`

Purpose:

- make source-level reasoning possible
- preserve uncertain or overlapping assignments honestly

## 6. Interpretation Layers

This section records higher-level semantic or communicative hypotheses derived from source and event structure.

Likely fields:

- `scene_hypotheses`
- `interaction_hypotheses`
- `call_or_phrase_hypotheses`
- `semantic_hypotheses`
- `domain_notes`

Purpose:

- separate raw source inference from higher-level reasoning
- allow questions such as "what is the background animal doing?" to remain explicitly hypothetical rather than flattened into source labels

## 7. Component Layers

These are the reconstructable building blocks associated with inferred sources.

Likely component types:

- `harmonic_component_groups`
- `transient_component_events`
- `noise_component_bands`
- `envelope_tracks`
- `pitch_tracks`
- `residual_components`

Each component may need:

- `component_id`
- `component_type`
- `linked_source_id`
- `time_bounds`
- `parameters`
- `confidence`
- `reconstruction_role`

Purpose:

- bridge from description to actual regeneration capability

## 8. Transformation Intent

This section records what the AI should later do with the retained structure.

Possible fields:

- `operations`
- `retained_source_groups`
- `suppressed_source_groups`
- `mix_constraints`
- `style_preservation_notes`
- `export_preferences`

Purpose:

- preserve edit intent separately from the observed or inferred scene
- let the same observed analysis support multiple downstream outputs

## 9. Reconstruction

This section preserves how the system believes useful outputs could be regenerated.

Possible fields:

- `reconstructable_outputs`
- `source_groups`
- `render_constraints`
- `residual_energy_policy`
- `quality_estimates`
- `comparison_metrics`

Possible output groups:

- `vocals`
- `backing_vocals`
- `drums`
- `bass`
- `harmonic_bed`
- `full_mix_without_vocals`
- `residual`

Purpose:

- support stem-oriented workflows
- keep reconstruction claims explicit and reviewable

## 10. Uncertainty Notes

This section is required, not optional in spirit.

Likely fields:

- `ambiguous_regions`
- `conflicting_source_assignments`
- `compression_artifact_notes`
- `low_confidence_bands`
- `unexplained_energy_regions`

Purpose:

- prevent false precision
- make AI reasoning safer and more honest

## 11. Provenance

This section records how the artifact came to exist.

Likely fields:

- `input_file_hash`
- `decode_path`
- `preprocessing_steps`
- `analysis_parameters`
- `model_or_rule_versions`
- `related_artifacts`

Purpose:

- preserve traceability
- support deterministic review and later re-analysis

## Minimal Example Shape

```yaml
analysis_metadata:
  analysis_profile: arwif_analysis_draft
  analysis_version: 0.1-draft

observed_audio:
  path_hint: .local/audio/Baby Love.mp3
  duration_seconds: 162.4
  sample_rate_hz: 44100
  channel_count: 2
  codec: mp3

attention_contract:
  query_text: retain the instrument tracks and omit the vocals
  retain_targets:
    - accompaniment
    - drum_pattern
    - harmonic_bed
  suppress_targets:
    - lead_vocal
  render_goal: full_mix_without_vocals

observation_layers:
  transient_events: []
  section_boundaries: []
  pitch_contours: []

source_hypotheses:
  - source_id: source.lead-vocal.01
    source_class: lead_vocal
    role: principal
    confidence: 0.78
    linked_components:
      - component.harmonic.01
      - component.transient.01
    ambiguity_notes:
      - overlaps with backing vocal energy in chorus

interpretation_layers:
  scene_hypotheses:
    - hypothesis_id: scene.01
      summary: foreground lead vocal over accompaniment bed
      confidence: 0.76

component_layers:
  harmonic_component_groups:
    - component_id: component.harmonic.01
      linked_source_id: source.lead-vocal.01
      confidence: 0.74

transformation_intent:
  operations:
    - suppress_source_group: vocals
    - preserve_source_group: accompaniment

reconstruction:
  reconstructable_outputs:
    - vocals
    - accompaniment

uncertainty_notes:
  compression_artifact_notes:
    - upper-band loss reduces confidence for cymbal versus vocal air separation

provenance:
  preprocessing_steps:
    - decode mp3 to pcm
    - generate observation layers
```

## Validation Priorities

The first validation rules should emphasize:

- shape integrity
- explicit confidence ranges
- stable ids
- source-to-component linkage integrity
- clear separation between observed and inferred sections
- explicit handling of unknown or ambiguous values

## Inspection Priorities

The first inspection summaries should surface:

- source class counts
- confidence distribution
- ambiguous region counts
- reconstructable output groups
- component counts by type
- unexplained energy summaries

## Diff Priorities

The first diff summaries should surface:

- added or removed source hypotheses
- confidence changes for stable sources
- changed component assignments
- changed reconstructable output groups
- changed ambiguity and uncertainty notes

## Recommended Early Constraint

Do not start with a schema that assumes perfect isolated stems.

Start with a schema that can represent:

- observed evidence
- probable source hypotheses
- uncertainty
- partial reconstructability

That is far more realistic and far more useful.