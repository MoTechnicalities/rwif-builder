# ARWIF Analyze Audio Command Surface

## Purpose

This document defines the first concrete CLI surface for analysis-oriented ARWIF work.

Status:

- implemented for the first `basic-observation` slice
- intended to remain the contract for future deeper analysis work
- current diff and review surfaces also expose nested phrase-to-mobility abstraction ladder changes and highest stable abstraction-layer rises and falls so cross-document comparisons can show where higher-level compression still changes

The command is intentionally narrow.
It should establish a disciplined observed-audio ingestion path before the repo claims source separation, vocal extraction, or high-confidence stem regeneration.

## First Command

### `rwif arwif-analyze-audio`

### Goal

Accept a real audio file, decode it into analysis-ready form, compute structured observation summaries, and optionally persist an analysis-oriented ARWIF draft document.

This first command should not claim to recover exact stems.
It should produce a clean, inspectable observation artifact that later phases can build on.

Current implementation note:

- `.wav` input is decoded directly in-process
- `.mp3` and `.flac` input rely on local `ffmpeg` and `ffprobe` availability

## Proposed Syntax

```bash
rwif arwif-analyze-audio <input-audio-path> \
  [--output <analysis.{yaml|yml|json}>] \
  [--report <report.{yaml|yml|json}>] \
  [--start-seconds <float>] \
  [--duration-seconds <float>] \
  [--channel-mode preserve|mono|split-stereo] \
  [--target-sample-rate-hz <int>] \
  [--analysis-profile basic-observation] \
  [--source-id <string>] \
  [--json]
```

## Positional Argument

### `<input-audio-path>`

Required path to an audio file.

Initial supported input types should be:

- `.wav`
- `.flac`
- `.mp3`

## Options

### `--output`

Optional destination for the analysis-oriented ARWIF draft document.

Rules:

- suffix must be `.yaml`, `.yml`, or `.json`
- when omitted, the command may still emit a machine-readable payload with `--json`
- this output should contain the structured analysis document, not just a summary report

### `--report`

Optional destination for a smaller summary report.

Rules:

- suffix must be `.yaml`, `.yml`, or `.json`
- intended for quick inspection and automation
- may omit dense observation arrays that appear in the main analysis document

### `--start-seconds`

Optional non-negative start offset for partial analysis.

Default:

- `0.0`

Purpose:

- enable targeted experiments on smaller excerpts
- reduce cost while shaping the first analysis layer

### `--duration-seconds`

Optional positive analysis window length.

When omitted:

- analyze the full input from `--start-seconds` onward

### `--channel-mode`

Optional channel handling policy.

Allowed values:

- `preserve`
- `mono`
- `split-stereo`

Default:

- `preserve`

Semantics:

- `preserve`: analyze the decoded channel layout as-is
- `mono`: downmix to one channel before analysis
- `split-stereo`: analyze left and right channels separately when the source is stereo

### `--target-sample-rate-hz`

Optional positive integer resampling target.

When omitted:

- preserve the decoded sample rate

Purpose:

- support deterministic experiments and comparable analysis outputs

### `--analysis-profile`

Optional named analysis profile.

Current allowed value:

- `basic-observation`

Default:

- `basic-observation`

Meaning:

- decode audio
- compute observed-audio metadata
- compute basic observation summaries
- do not claim source separation

### `--source-id`

Optional stable identifier for the analyzed recording.

Purpose:

- let later review, diff, and correspondence workflows preserve identity even when file paths change

### `--json`

Emit machine-readable command output to stdout.

This should follow the repo's existing CLI contract style.

## First-Slice Behavior

The current first slice does all of the following:

1. decode the input file into analysis-ready PCM
2. capture observed audio metadata
3. apply the requested channel policy
4. apply the requested excerpt window
5. optionally resample if requested
6. compute compact observation summaries
7. emit a structured payload
8. optionally persist the analysis document and summary report

The implemented observation document now also includes lightweight temporal structure:

- `onset_map` candidates derived from positive energy-change events
- `section_boundaries` candidates derived from coarse energy-region changes
- `section_candidates` derived from boundary-delimited regions with compact `energy_band`, `duration_band`, and `position_band` hints
- `section_profile_summary` nested into the observation summary for quick structural review
- `section_transitions` derived from adjacent section candidates with compact energy and duration deltas
- `transition_profile_summary` nested into the observation summary for quick transition review
- `transition_motif_summary` nested into the observation summary for repeated transition signatures, occurrence counts, and local time anchors
- `transition_motif_sequence_summary` nested into the observation summary for repeated adjacent motif chains, occurrence counts, and local time anchors
- `transition_motif_chain_summary` nested into the observation summary for repeated three-motif chains so short phrase-like behavior is preserved beyond adjacent pairs
- `transition_motif_phrase_summary` nested into the observation summary for repeated exact motif phrases across a small length range so the analysis can preserve longer short-run structure without collapsing everything to fixed 3-step chains
- `transition_motif_phrase_family_summary` nested into the observation summary for normalized contour families built from recurring motif phrases so the analysis can expose similarity-aware phrase structure without discarding the exact phrases
- `transition_motif_phrase_archetype_summary` nested into the observation summary for broader repeated phrase shapes produced by collapsing adjacent repeated phrase-family motifs
- `transition_motif_phrase_contour_summary` nested into the observation summary for even looser repeated phrase motion contours produced by removing duration-trend detail from phrase archetypes
- `transition_motif_phrase_sweep_summary` nested into the observation summary for anchor-normalized repeated band-motion sweeps produced by removing `same_band` contour anchors when directional motion remains
- `transition_motif_phrase_gesture_summary` nested into the observation summary for polarity-agnostic repeated sweep gestures that distinguish steady-band behavior, single-direction sweeps, and reversing sweeps
- `transition_motif_phrase_mobility_summary` nested into the observation summary for conservative repeated phrase mobilities that collapse gestures into steady-band-region versus traveling-band-region behavior while preserving linked provenance
- low-confidence observation-derived `source_hypotheses` such as `transient_event_cluster`, `sustained_sectional_bed`, `stereo_program_bed`, and `foreground_call_stream`, each with explicit evidence, linked observation references, linked recurring transition motifs, linked recurring transition-motif sequences, linked recurring transition-motif chains, linked recurring transition-motif phrases, linked recurring transition-motif phrase families, linked recurring transition-motif phrase archetypes, linked recurring transition-motif phrase contours, linked recurring transition-motif phrase sweeps, local time bounds, and ambiguity notes instead of semantic instrument claims

The current first slice does not do any of the following:

- claim clean vocal extraction
- emit source stems
- identify instruments with high-confidence labels by default
- store opaque latent blobs without inspectable summaries
- pretend lossy inputs can be perfectly reversed

## Required Output Payload

The command should return a machine-readable payload shaped approximately like this:

```yaml
command: arwif-analyze-audio
input_audio: .local/audio/Baby Love.mp3
analysis_profile: basic-observation
source_id: baby-love-demo
decoded_audio:
  duration_seconds: 162.4
  sample_rate_hz: 44100
  channel_count: 2
  codec: mp3
  channel_mode: preserve
analysis_window:
  start_seconds: 0.0
  duration_seconds: 162.4
observation_summary:
  peak_amplitude: 0.98
  rms_amplitude: 0.21
  estimated_onset_count: 412
  section_boundary_count: 31
  section_candidate_count: 32
  section_transition_count: 31
  section_profile_summary:
    average_duration_seconds: 5.07
    longest_duration_seconds: 13.4
    energy_band_counts:
      low: 8
      medium: 16
      high: 8
    duration_band_counts:
      short: 5
      medium: 23
      long: 4
    position_band_counts:
      opening: 6
      middle: 20
      closing: 6
    dominant_energy_band: medium
    opening_energy_band: low
    closing_energy_band: medium
  transition_profile_summary:
    average_abs_energy_delta: 0.19
    largest_abs_energy_delta: 0.63
    transition_kind_counts:
      energy_decrease: 9
      energy_increase: 10
      energy_stable: 12
    dominant_transition_kind: energy_stable
    opening_transition_kind: energy_increase
    closing_transition_kind: energy_decrease
  transition_motif_summary:
    recurring_motif_count: 2
    motif_occurrence_count: 5
    motif_signature_counts:
      energy_increase|low|high|lengthen: 3
      energy_stable|medium|medium|stable: 2
    motif_signatures:
      - energy_increase|low|high|lengthen
      - energy_stable|medium|medium|stable
    dominant_motif_signature: energy_increase|low|high|lengthen
  transition_motif_sequence_summary:
    recurring_sequence_count: 1
    sequence_occurrence_count: 2
    sequence_signature_counts:
      energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable: 2
    sequence_signatures:
      - energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable
    dominant_sequence_signature: energy_stable|medium|medium|stable=>energy_stable|medium|medium|stable
  spectral_extent_summary:
    low_hz: 48
    high_hz: 15780
  channel_energy_summary:
    left_rms: 0.20
    right_rms: 0.22
analysis_document_output: dist/baby-love.analysis.yaml
report_output: dist/baby-love.report.json
warnings: []
is_valid: true
```

## Expected Analysis Document Shape

The first analysis document produced by this command should align with [docs/ARWIF_ANALYSIS_SCHEMA_DRAFT.md](docs/ARWIF_ANALYSIS_SCHEMA_DRAFT.md).

For the first slice, it should populate these sections:

- `analysis_metadata`
- `observed_audio`
- `observation_layers`
- `provenance`

It may leave these sections empty or minimal:

- `source_hypotheses`
- `component_layers`
- `reconstruction`
- `uncertainty_notes`

That keeps the first step honest.

## Observation Summaries For The First Slice

The initial command should prefer compact, inspectable summaries such as:

- duration
- sample rate
- channel count
- codec and decode notes
- peak amplitude
- RMS amplitude
- simple channel-energy summary
- onset count estimate
- coarse spectral extent summary
- coarse segment or section candidates
- compact section-profile summaries derived from those candidates
- compact transition summaries derived from adjacent section candidates
- compact recurring transition-motif summaries derived from repeated transition signatures
- compact recurring transition-motif-sequence summaries derived from repeated adjacent motif chains
- low-confidence source-hypothesis records derived from those observations, with explicit ambiguity notes plus local time bounds, linked observation references, linked recurring transition-motif participation, and linked recurring transition-motif-sequence participation

This is enough to make the artifact useful without prematurely promising source inference.

## Exit Rules

- exit `0` when decode and analysis succeed
- exit non-zero when the input cannot be decoded or requested output paths are invalid
- warnings should be preserved in the payload rather than hidden

## Example Commands

Analyze a full file and persist both outputs:

```bash
rwif arwif-analyze-audio .local/audio/Baby\ Love.mp3 \
  --output .local/renders/baby-love.analysis.yaml \
  --report .local/renders/baby-love.report.json \
  --source-id baby-love-demo \
  --json
```

Analyze only a short excerpt:

```bash
rwif arwif-analyze-audio .local/audio/Baby\ Love.mp3 \
  --start-seconds 30 \
  --duration-seconds 12 \
  --channel-mode split-stereo \
  --output .local/renders/baby-love-chorus.analysis.yaml \
  --json
```

## Why This Surface First

This command is the right first move because it:

- creates a real-audio ingestion path
- produces inspectable structure immediately
- stays aligned with the repo's validation and review discipline
- does not overpromise source recovery before the representation is ready
- preserves repeated local behavior that later motif and call-pattern reasoning can build on
- preserves repeated local behavior, repeated phrase-like motif chains, similarity-aware phrase families, broader phrase archetypes, and looser phrase contours that later motif and call-pattern reasoning can build on

## Likely Follow-On Commands

Once `arwif-analyze-audio` exists, the next natural commands would be:

- `rwif arwif-inspect-analysis`
- `rwif arwif-batch-inspect-analysis`
- `rwif arwif-diff-analysis`
- `rwif arwif-batch-diff-analysis`
- `rwif arwif-batch-review-analysis`
- `rwif arwif-batch-analyze-audio`
- `rwif arwif-extract-stems`

The first of those follow-on commands now exists in a narrow form:

- `rwif arwif-inspect-analysis` loads an analysis document and returns a compact structural summary, including section-profile fields, transition-profile fields, a nested phrase-to-mobility abstraction ladder, the highest stable recurring abstraction layer across motif through mobility, and first-event previews

The next review-oriented aggregation command now also exists in a narrow form:

- `rwif arwif-batch-inspect-analysis` loads multiple analysis documents and aggregates recurring structural counts, phrase-to-mobility abstraction totals, highest stable abstraction-layer counts, dominant section-energy bands, and dominant transition kinds across the set

The second now also exists in a narrow form:

- `rwif arwif-diff-analysis` compares two analysis documents and returns stable field-level and summary-level changes, including section-profile and transition-profile changes

The next pairwise review surface now also exists in a narrow form:

- `rwif arwif-batch-diff-analysis` compares many matched analysis-document pairs and aggregates recurring structural changes across the changed set, including highest stable abstraction-layer climbs and drops

The next combined review surface now also exists in a narrow form:

- `rwif arwif-batch-review-analysis` runs the matched-pair batch diff and recurring-change review together so analysis-document comparisons do not need a second interpretation step, including frontier climb and drop summaries

The third now also exists in a narrow form:

- `rwif arwif-batch-analyze-audio` applies the same observation-profile analysis across multiple inputs and aggregates the results, including section-band totals and transition-kind totals

The remaining commands should come after that, not before it.