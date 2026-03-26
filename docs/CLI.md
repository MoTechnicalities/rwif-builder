# CLI Contract

## Commands

### `rwif init`

Creates a starter `rwif.yaml` file from a template.

### `rwif build`

Builds an `.rwif` artifact from source material and config.

Current implementation: real for Markdown and text sources.

### `rwif validate`

Checks structural, metadata, and manifest integrity of an artifact.

Current implementation: validates the RWIF header, semantic-memory metadata, builder manifest, and per-state record payloads.

### `rwif inspect`

Shows summary metadata or record-level information for an artifact.

Current implementation: summary inspection.

### `rwif stats`

Emits machine-readable metrics for CI and automation.

Current implementation: summary metrics alias over the inspection surface.

### `rwif diff`

Compares two artifacts and reports source, metadata, and content deltas.

Current implementation: compares manifest-level source additions, removals, changes, vector-length shifts, and pipeline-config changes.

### `rwif patch`

Plans or executes an incremental rebuild based on changed inputs.

Current implementation: detects source-level and pipeline-level changes against a base artifact manifest, then either copies the base artifact when nothing changed or performs a deterministic rebuild.

### `rwif arwif-build`

Builds an ARWIF artifact from a YAML or JSON oscillator spec.

Current implementation: runs strict ARWIF source-spec validation first, emits a strict ARWIF `v0.1` artifact only when the spec is valid, validates the generated file immediately, and returns both spec-validation and artifact-validation metadata.

### `rwif arwif-batch-build`

Builds multiple ARWIF artifacts from YAML or JSON oscillator specs.
Current implementation: accepts `.wav`, `.flac`, or `.mp3` input, decodes the audio into analysis-ready PCM, supports partial-window analysis via `--start-seconds` and `--duration-seconds`, supports `preserve`, `mono`, and `split-stereo` channel policies, can optionally resample to `--target-sample-rate-hz`, computes a compact `basic-observation` summary including peak amplitude, RMS amplitude, onset estimate, section-boundary count, section-candidate count, section-transition count, channel-energy summary, coarse spectral extent, a nested `section_profile_summary`, a nested `transition_profile_summary`, a nested `transition_motif_summary` for repeated transition signatures with time anchors, a nested `transition_motif_sequence_summary` for repeated adjacent motif chains, a nested `transition_motif_chain_summary` for repeated three-motif chains, a nested `transition_motif_phrase_summary` for repeated exact motif phrases across a small variable-length range, a nested `transition_motif_phrase_family_summary` for normalized contour families built from those recurring phrases, a nested `transition_motif_phrase_archetype_summary` that collapses repeated adjacent family motifs into broader phrase-shape archetypes, and a nested `transition_motif_phrase_contour_summary` that drops duration-trend detail from archetypes to expose even looser motion contours. The persisted analysis document includes lightweight `onset_map`, `section_boundaries`, `section_candidates`, and `section_transitions` observation layers. The current slice also emits low-confidence observation-derived `source_hypotheses` such as `transient_event_cluster`, `sustained_sectional_bed`, `stereo_program_bed`, and `foreground_call_stream`, each with explicit evidence, local time bounds, linked observation references, linked transition-motif participation, linked transition-motif-sequence participation, linked transition-motif-chain participation, linked transition-motif-phrase participation, linked transition-motif-phrase-family participation, linked transition-motif-phrase-archetype participation, and linked transition-motif-phrase-contour participation rather than instrument claims. Section candidates now carry compact `duration_band` and `position_band` hints, section transitions expose adjacent energy/duration deltas plus a compact `transition_kind`, recurring transition motifs summarize repeated local behavior, recurring transition-motif sequences summarize repeated adjacent motif chains, recurring transition-motif chains summarize longer short-phrase behavior, recurring transition-motif phrases preserve exact recurring 3-to-5 step runs, recurring transition-motif phrase families preserve similarity-aware contour groupings above those exact runs, recurring transition-motif phrase archetypes preserve even broader repeated phrase shapes by collapsing adjacent repeated family motifs, recurring transition-motif phrase contours preserve the broadest repeated band-motion shapes by removing duration-trend detail from those archetypes, and compact reports include an `observation_preview` with first-event previews, first-motif preview, first motif-sequence preview, first motif-chain preview, first motif-phrase preview, first motif-phrase-family preview, first motif-phrase-archetype preview, first motif-phrase-contour preview, both profile summaries, motif summaries, and a source-hypothesis preview. WAV input is handled directly in-process; compressed formats rely on the local `ffmpeg` and `ffprobe` tools when available.

Current implementation: accepts one or more strict ARWIF source specs, writes artifacts into `--output-dir`, reuses the same strict build flow as `arwif-build`, and returns an aggregated result payload with per-spec build results plus collection-level counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

Current implementation: loads a `.json`, `.yaml`, or `.yml` analysis document produced by the analysis track, validates the presence and shape of the top-level analysis sections, and returns a compact summary covering observed-audio metadata, the current analysis window, available observation layers, section-profile, transition-profile, transition-motif, transition-motif-sequence, transition-motif-chain, transition-motif-phrase, transition-motif-phrase-family, transition-motif-phrase-archetype, transition-motif-phrase-contour, and transition-motif-phrase-sweep summary fields, first-event, first-motif, first-motif-sequence, first-motif-chain, first-motif-phrase, first-motif-phrase-family, first-motif-phrase-archetype, first-motif-phrase-contour, and first-motif-phrase-sweep previews, source-hypothesis count, source-hypothesis classes and roles, source-hypothesis-linked transition-motif signatures, source-hypothesis-linked transition-motif-sequence signatures, source-hypothesis-linked transition-motif-chain signatures, source-hypothesis-linked transition-motif-phrase signatures, source-hypothesis-linked transition-motif-phrase-family signatures, source-hypothesis-linked transition-motif-phrase-archetype signatures, source-hypothesis-linked transition-motif-phrase-contour signatures, source-hypothesis-linked transition-motif-phrase-sweep signatures, the first source hypothesis including linked observation references, linked motif participation, linked motif-sequence participation, linked motif-chain participation, linked motif-phrase participation, linked motif-phrase-family participation, linked motif-phrase-archetype participation, linked motif-phrase-contour participation, linked motif-phrase-sweep participation, and time bounds when present, component-layer count, reconstructable outputs, uncertainty-warning count, and basic provenance details.
### `rwif arwif-batch-import`

Imports multiple ARWIF YAML or JSON specs into ARWIF artifacts.

Current implementation: loads and validates multiple `.json`, `.yaml`, or `.yml` analysis documents produced by the analysis track, aggregates codec and decode-backend counts, aggregates observation-layer presence counts, totals onset, section, transition, recurring-transition-motif, recurring-transition-motif-sequence, recurring-transition-motif-chain, recurring-transition-motif-phrase, recurring-transition-motif-phrase-family, recurring-transition-motif-phrase-archetype, recurring-transition-motif-phrase-contour, recurring-transition-motif-phrase-sweep, recurring-transition-motif-phrase-gesture, recurring-transition-motif-phrase-mobility, hypothesis, component, and warning counts, aggregates source-hypothesis classes, roles, linked transition-motif signatures, linked transition-motif-sequence signatures, linked transition-motif-chain signatures, linked transition-motif-phrase signatures, linked transition-motif-phrase-family signatures, linked transition-motif-phrase-archetype signatures, linked transition-motif-phrase-contour signatures, linked transition-motif-phrase-sweep signatures, linked transition-motif-phrase-gesture signatures, and linked transition-motif-phrase-mobility signatures, summarizes dominant section-energy, transition-kind, transition-motif-signature, transition-motif-sequence-signature, transition-motif-chain-signature, transition-motif-phrase-signature, transition-motif-phrase-family-signature, transition-motif-phrase-archetype-signature, transition-motif-phrase-contour-signature, transition-motif-phrase-sweep-signature, transition-motif-phrase-gesture-signature, and transition-motif-phrase-mobility-signature frequencies, and can optionally persist the aggregated inspection report as `.json`, `.yaml`, or `.yml`.
Current implementation: accepts one or more strict ARWIF source specs, writes artifacts into `--output-dir`, reuses the same import path as `arwif-import`, and returns an aggregated result payload with per-spec import results plus collection-level counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-validate-spec`
Current implementation: compares matched `--left` and `--right` analysis documents pairwise using the same field-level summary logic as `arwif-diff-analysis`, aggregates recurring metadata, observed-audio, analysis-window, and basic-observation changes across changed pairs, tracks source-hypothesis class additions and removals, tracks source-hypothesis-linked transition-motif signature additions and removals, tracks source-hypothesis-linked transition-motif-sequence signature additions and removals, tracks source-hypothesis-linked transition-motif-chain signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-family signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-archetype signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-contour signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-sweep signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-gesture signature additions and removals, tracks source-hypothesis-linked transition-motif-phrase-mobility signature additions and removals, tracks recurring transition-motif signature additions and removals, tracks recurring transition-motif-sequence signature additions and removals, tracks recurring transition-motif-chain signature additions and removals, tracks recurring transition-motif-phrase signature additions and removals, tracks recurring transition-motif-phrase-family signature additions and removals, tracks recurring transition-motif-phrase-archetype signature additions and removals, tracks recurring transition-motif-phrase-contour signature additions and removals, tracks recurring transition-motif-phrase-sweep signature additions and removals, tracks recurring transition-motif-phrase-gesture signature additions and removals, tracks recurring transition-motif-phrase-mobility signature additions and removals, totals section, transition, recurring-motif, recurring-motif-sequence, recurring-motif-chain, recurring-motif-phrase, recurring-motif-phrase-family, recurring-motif-phrase-archetype, recurring-motif-phrase-contour, recurring-motif-phrase-sweep, recurring-motif-phrase-gesture, and recurring-motif-phrase-mobility count deltas across the batch, tracks observation-layer additions and removals, and can optionally persist the aggregated batch diff report as `.json`, `.yaml`, or `.yml`.

Validates multiple ARWIF YAML or JSON source specs.

Current implementation: accepts one or more strict ARWIF source specs, reuses the same validation path as `arwif-validate-spec`, and returns an aggregated result payload with per-spec validation details plus collection-level valid and invalid counts.
Current implementation: accepts pairwise `--left` and `--right` analysis-document collections like `arwif-batch-diff-analysis`, computes the per-pair diff report and exposes the recurring metadata, observed-audio, analysis-window, observation-layer, source-hypothesis-class, source-hypothesis-linked motif-signature, source-hypothesis-linked motif-sequence-signature, source-hypothesis-linked motif-chain-signature, source-hypothesis-linked motif-phrase-signature, source-hypothesis-linked motif-phrase-family-signature, source-hypothesis-linked motif-phrase-archetype-signature, source-hypothesis-linked motif-phrase-contour-signature, source-hypothesis-linked motif-phrase-sweep-signature, source-hypothesis-linked motif-phrase-gesture-signature, source-hypothesis-linked motif-phrase-mobility-signature, transition-motif-signature, transition-motif-sequence-signature, transition-motif-chain-signature, transition-motif-phrase-signature, transition-motif-phrase-family-signature, transition-motif-phrase-archetype-signature, transition-motif-phrase-contour-signature, transition-motif-phrase-sweep-signature, transition-motif-phrase-gesture-signature, transition-motif-phrase-mobility-signature, and structural count-delta summaries together in one combined review payload, and can optionally persist the aggregated review report as `.json`, `.yaml`, or `.yml`.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-diff`

Current implementation: accepts explicit pairwise `--left` and `--right` artifact collections of equal length, reuses the same comparison path as `arwif-diff`, and returns an aggregated result payload with per-pair diffs plus collection-level counts for changed, unchanged, invalid, incompatible, and changed-state totals.
Compares multiple ARWIF artifact pairs.

Current implementation: accepts explicit pairwise `--left` and `--right` artifact collections of equal length, reuses the same comparison path as `arwif-diff`, and returns an aggregated result payload with per-pair diffs plus collection-level counts for changed, unchanged, invalid, incompatible, and changed-state totals.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.
Current implementation: aggregates recurring metadata, observed-audio, analysis-window, and basic-observation changes across all compared pairs, including section, transition, recurring-motif, and recurring-motif-sequence count deltas, and can optionally persist the analysis result as `.json`, `.yaml`, or `.yml`.

### `rwif arwif-batch-diff-analyze`

Analyzes an aggregated ARWIF batch diff report.
Current implementation: combines the `rwif-batch-diff` and `rwif-batch-diff-analyze` workflows into one persisted review payload.

Current implementation: accepts a previously saved `arwif-batch-diff` report in `.json`, `.yaml`, or `.yml` format, aggregates recurring metadata and state changes across pairs, summarizes spatial drift counts including narrower room-presence drift, geometry-reference presence drift, surface-treatment presence drift, reflection-policy presence drift, renderer-adaptation presence drift, listening-zone intent-diversity drift, listening-zone roster drift, speaker-channel roster drift, speaker-role diversity drift, speaker-coverage intent-diversity drift, and speaker-id churn plus speaker-id and source-group roster deltas alongside broader room and speaker changes, and can optionally persist the analysis result as `.json`, `.yaml`, or `.yml` based on the output suffix.

### `rwif arwif-batch-review`

Runs ARWIF batch diff and recurring-change analysis in one command.

Current implementation: accepts pairwise `--left` and `--right` artifact collections like `arwif-batch-diff`, computes the per-pair diff report and the higher-level recurring-change analysis together, and can optionally persist the combined review result as `.json`, `.yaml`, or `.yml` based on the output suffix.

Concrete example flow using the shipped Level 3 room-aware fixtures:

```bash
rwif arwif-build --spec examples/arwif/ROOM_REVIEW_baseline_v0_1.yaml --output dist/ROOM_REVIEW_baseline_v0_1.arwif --json
rwif arwif-build --spec examples/arwif/ROOM_REVIEW_candidate_v0_1.yaml --output dist/ROOM_REVIEW_candidate_v0_1.arwif --json
rwif arwif-batch-review --left dist/ROOM_REVIEW_baseline_v0_1.arwif --right dist/ROOM_REVIEW_candidate_v0_1.arwif --output dist/ROOM_REVIEW_batch_review.json --json
```

### `rwif arwif-batch-export`

Exports multiple ARWIF artifacts to YAML or JSON specs.

Current implementation: accepts one or more `.arwif` artifacts, writes strict source-spec-compatible documents into `--output-dir`, defaults to YAML unless `--format json` is supplied, reuses the same export path as `arwif-export`, and returns an aggregated result payload with per-artifact export details plus collection-level counts for exported files, states, and oscillators.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-render`

Renders multiple ARWIF artifacts to mono 16-bit PCM WAV.

Current implementation: accepts one or more `.arwif` artifacts, writes `.wav` files into `--output-dir`, reuses the same render path as `arwif-render`, and returns an aggregated result payload with per-artifact render details plus collection-level counts and total rendered duration.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-validate`

Validates multiple ARWIF audio artifacts.

Current implementation: accepts one or more `.arwif` artifacts, reuses the same validation path as `arwif-validate`, supports `--legacy`, and returns an aggregated result payload with per-artifact validation details plus collection-level valid and invalid counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-inspect`

Inspects multiple ARWIF audio artifacts.

Current implementation: accepts one or more `.arwif` artifacts, reuses the same inspection path as `arwif-inspect`, supports `--legacy`, and returns an aggregated result payload with per-artifact inspection details plus collection-level valid and invalid counts, total states, total oscillators, and the maximum observed frequency.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-validate-spec`

Validates an ARWIF YAML or JSON source spec before build or import.

Current implementation: checks top-level metadata, state-level overrides, oscillator-bank entries, and Nyquist bounds, then returns field-level errors and warnings without writing an artifact.

### `rwif arwif-analyze-audio`

Analyzes a real audio file into an ARWIF-oriented observation report.

Current implementation: accepts `.wav`, `.flac`, or `.mp3` input, decodes the audio into analysis-ready PCM, supports partial-window analysis via `--start-seconds` and `--duration-seconds`, supports `preserve`, `mono`, and `split-stereo` channel policies, can optionally resample to `--target-sample-rate-hz`, and now accepts optional task-conditioned workspace inputs including `--query-text`, repeatable `--attention-target`, `--retain-target`, `--suppress-target`, `--answer-expectation`, repeatable `--transform-operation`, plus `--render-goal` and `--primary-output`. It computes a compact `basic-observation` summary including peak amplitude, RMS amplitude, onset estimate, section-boundary count, section-candidate count, section-transition count, channel-energy summary, coarse spectral extent, a nested `section_profile_summary`, a nested `transition_profile_summary`, a nested `transition_motif_summary` for repeated transition signatures with time anchors, and a nested `transition_motif_sequence_summary` for repeated adjacent motif chains with time anchors. The persisted analysis document includes lightweight `onset_map`, `section_boundaries`, `section_candidates`, and `section_transitions` observation layers, and when task inputs are provided it also emits initial `attention_contract`, low-confidence `interpretation_layers`, and `transformation_intent` scaffolding. The current slice also emits low-confidence observation-derived `source_hypotheses` such as `transient_event_cluster`, `sustained_sectional_bed`, `stereo_program_bed`, and `foreground_call_stream`, each with explicit evidence, local time bounds, linked observation references, linked transition-motif participation, and linked transition-motif-sequence participation rather than instrument claims. Section candidates now carry compact `duration_band` and `position_band` hints, section transitions expose adjacent energy/duration deltas plus a compact `transition_kind`, recurring transition motifs summarize repeated local behavior, recurring transition-motif sequences summarize repeated adjacent motif-chain behavior, and compact reports include an `observation_preview` with first-event previews, first-motif preview, first-motif-sequence preview, both profile summaries, motif summaries, a source-hypothesis preview, and any provided workspace task fields. WAV input is handled directly in-process; compressed formats rely on the local `ffmpeg` and `ffprobe` tools when available.

### `rwif arwif-batch-analyze-audio`

Analyzes multiple real audio files into ARWIF-oriented observation reports.

Current implementation: applies the same first-slice observation analysis as `arwif-analyze-audio` to each input file, supports the same analysis-window, channel-mode, resampling, profile, and workspace task-input options across the full batch, can optionally persist per-input analysis documents to `--analysis-dir`, can optionally persist per-input compact reports to `--report-dir`, and can optionally write an aggregated batch report as `.json`, `.yaml`, or `.yml` summarizing valid and invalid inputs, total analyzed duration, frame totals, onset totals, section-boundary totals, section-candidate totals, section-transition totals, aggregate section energy-band and duration-band counts, aggregate transition-kind counts, maximum channel count, decode backends encountered, and the task-conditioned `attention_contract` / `transformation_intent` values applied across the batch.

### `rwif arwif-inspect-analysis`

Inspects an analysis-oriented ARWIF YAML or JSON document.

Current implementation: loads a `.json`, `.yaml`, or `.yml` analysis document produced by the analysis track, validates the presence and shape of the top-level analysis sections, validates optional workspace-style `attention_contract`, `interpretation_layers`, and `transformation_intent` fields when present, and now also validates nested `observation_layers`, `source_hypotheses`, `component_layers`, `reconstruction`, and core `provenance` structures before inspection. It then returns a compact summary covering observed-audio metadata, the current analysis window, optional workspace-style `attention_contract` fields, available observation layers, section-profile, transition-profile, transition-motif, and transition-motif-sequence summary fields, a nested transition-motif-phrase abstraction ladder spanning phrase through mobility counts, the highest stable recurring abstraction layer across motif through mobility, first-event, first-motif, and first-motif-sequence previews, source-hypothesis count, source-hypothesis classes and roles, source-hypothesis-linked transition-motif signatures, source-hypothesis-linked transition-motif-sequence signatures, optional `interpretation_layers` summaries including layer names and first scene or communicative hypothesis previews, the first source hypothesis including linked observation references, linked motif participation, linked motif-sequence participation, and time bounds when present, component-layer count, optional `transformation_intent`, reconstructable outputs, uncertainty-warning count, and basic provenance details.

### `rwif arwif-validate-analysis`

Validates an analysis-oriented ARWIF YAML or JSON document.

Current implementation: loads a `.json`, `.yaml`, or `.yml` analysis document produced by the analysis track, validates the presence and shape of the required top-level analysis sections, validates optional workspace-style `attention_contract`, `interpretation_layers`, and `transformation_intent` fields when present, validates nested `observation_layers`, `source_hypotheses`, `component_layers`, `reconstruction`, and core `provenance` structures, and returns a compact validation payload with validity, error and warning lists, plus summary stats covering the analysis profile, source id, section counts, reconstructable output count, uncertainty-warning count, and whether workspace-style sections are present.

### `rwif arwif-batch-validate-analysis`

Validates multiple analysis-oriented ARWIF YAML or JSON documents.

Current implementation: accepts one or more `.json`, `.yaml`, or `.yml` analysis documents produced by the analysis track, reuses the same validation path as `arwif-validate-analysis`, and returns an aggregated result payload with per-document validation details plus collection-level valid and invalid counts, aggregate section and reconstructable-output totals, aggregate uncertainty-warning totals, analysis-profile frequencies, and counts for how many documents contain workspace-style `attention_contract`, `interpretation_layers`, and `transformation_intent` sections.

### `rwif arwif-batch-inspect-analysis`

Inspects multiple analysis-oriented ARWIF YAML or JSON documents.

Current implementation: loads and validates multiple `.json`, `.yaml`, or `.yml` analysis documents produced by the analysis track, aggregates codec and decode-backend counts, aggregates observation-layer presence counts, totals onset, section, transition, recurring-transition-motif, recurring-transition-motif-sequence, hypothesis, component, and warning counts, exposes nested transition-motif-phrase abstraction totals spanning phrase through mobility recurring and occurrence counts, counts the highest stable recurring abstraction layer reached by each document across motif through mobility, aggregates source-hypothesis classes, roles, linked transition-motif signatures, and linked transition-motif-sequence signatures, and now also aggregates compact workspace-style coverage including how many documents contain an `attention_contract`, `interpretation_layers`, or `transformation_intent`, total interpretation-hypothesis counts, interpretation-layer-name frequencies, attention-target and retain or suppress-target frequencies, render-goal frequencies, and transformation operation and primary-output frequencies. It also summarizes dominant section-energy, transition-kind, transition-motif-signature, and transition-motif-sequence-signature frequencies, and can optionally persist the aggregated inspection report as `.json`, `.yaml`, or `.yml`.

### `rwif arwif-batch-diff-analysis`

Compares multiple analysis-oriented ARWIF document pairs.

Current implementation: compares matched `--left` and `--right` analysis documents pairwise using the same field-level summary logic as `arwif-diff-analysis`, aggregates recurring metadata, observed-audio, analysis-window, optional workspace-style `attention_contract` and `transformation_intent` field changes, and basic-observation changes across changed pairs, including nested phrase-to-mobility abstraction ladder field changes, interpretation-layer additions and removals, first scene and communicative hypothesis changes, interpretation-hypothesis count deltas, tracks highest stable abstraction-layer rises and falls across motif through mobility, tracks source-hypothesis class additions and removals, tracks source-hypothesis-linked transition-motif signature additions and removals, tracks source-hypothesis-linked transition-motif-sequence signature additions and removals, tracks recurring transition-motif signature additions and removals, tracks recurring transition-motif-sequence signature additions and removals, totals section, transition, recurring-motif, recurring-motif-sequence, and interpretation-hypothesis count deltas across the batch, tracks observation-layer additions and removals, and can optionally persist the aggregated batch diff report as `.json`, `.yaml`, or `.yml`.

### `rwif arwif-batch-review-analysis`

Runs analysis-document batch diff and recurring-change review in one command.

Current implementation: accepts pairwise `--left` and `--right` analysis-document collections like `arwif-batch-diff-analysis`, computes the per-pair diff report and exposes the recurring metadata, observed-audio, analysis-window, optional workspace-style attention, interpretation, and transformation changes, observation-layer, source-hypothesis-class, source-hypothesis-linked motif-signature, source-hypothesis-linked motif-sequence-signature, transition-motif-signature, transition-motif-sequence-signature, nested phrase-to-mobility abstraction ladder field changes, highest stable abstraction-layer climbs and drops, and structural count-delta summaries together in one combined review payload, and can optionally persist the aggregated review report as `.json`, `.yaml`, or `.yml`.

### `rwif arwif-diff-analysis`

Compares two analysis-oriented ARWIF YAML or JSON documents.

Current implementation: loads and validates both analysis documents, including optional workspace-style `attention_contract`, `interpretation_layers`, and `transformation_intent` sections when present, compares compact analysis metadata, observed-audio metadata, analysis-window settings, optional workspace-style `attention_contract`, `interpretation_layers`, first scene and communicative hypothesis previews, `transformation_intent`, basic observation summaries including section-profile, transition-profile, transition-motif, transition-motif-sequence, transition-motif-chain, transition-motif-phrase, transition-motif-phrase-family, transition-motif-phrase-archetype, transition-motif-phrase-contour, transition-motif-phrase-sweep, and nested phrase-to-mobility abstraction ladder summaries, compares the highest stable recurring abstraction layer reached across motif through mobility, source-hypothesis class sets, source-hypothesis-linked transition-motif signature sets, source-hypothesis-linked transition-motif-sequence signature sets, source-hypothesis-linked transition-motif-chain signature sets, source-hypothesis-linked transition-motif-phrase signature sets, source-hypothesis-linked transition-motif-phrase-family signature sets, source-hypothesis-linked transition-motif-phrase-archetype signature sets, source-hypothesis-linked transition-motif-phrase-contour signature sets, source-hypothesis-linked transition-motif-phrase-sweep signature sets, recurring transition-motif signature sets, recurring transition-motif-sequence signature sets, recurring transition-motif-chain signature sets, recurring transition-motif-phrase signature sets, recurring transition-motif-phrase-family signature sets, recurring transition-motif-phrase-archetype signature sets, recurring transition-motif-phrase-contour signature sets, recurring transition-motif-phrase-sweep signature sets, observation-layer presence, interpretation-layer presence, component-layer presence, reconstructable outputs, uncertainty-note keys, summary count deltas including interpretation-hypothesis counts, and provenance basics, then optionally persists the resulting diff report as `.json`, `.yaml`, or `.yml`.

### `rwif arwif-import`

Imports an ARWIF YAML or JSON spec into an ARWIF artifact.

Current implementation: wraps the strict ARWIF builder flow with an import-oriented command surface so exported specs can be round-tripped back into artifacts, reusing the same source-spec validation as `arwif-build`.

### `rwif arwif-export`

Exports an ARWIF artifact to a YAML or JSON source spec.

Current implementation: writes a strict-spec-compatible document capturing playback metadata, state-level metadata, and oscillator-bank contents so the artifact can be imported again.

### `rwif arwif-normalize`

Normalizes a legacy or strict ARWIF artifact into a strict ARWIF `v0.1` source spec and optional rebuilt artifact.

Current implementation: loads the source artifact in legacy-compatible mode, injects strict defaults for missing playback metadata, preserves non-reserved metadata, writes a strict YAML or JSON spec, can rebuild a strict artifact from that normalized spec, can emit a separate normalization report in JSON or YAML based on the `--report` file suffix, and can emit a smaller assumptions manifest based on the `--assumptions` file suffix for automation that only needs normalization decisions and warnings.

### `rwif arwif-batch-normalize`

Normalizes multiple legacy or strict ARWIF artifacts into strict ARWIF `v0.1` source specs and optional auxiliary outputs.

Current implementation: accepts one or more artifact paths, writes normalized specs into `--spec-dir`, can optionally rebuild strict artifacts into `--output-dir`, can emit JSON normalization reports into `--report-dir`, can emit JSON assumptions manifests into `--assumptions-dir`, and returns an aggregated result payload with per-artifact outcomes plus collection-level counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-inspect`

Summarizes an ARWIF artifact in ARWIF-native terms.

Current implementation: reports playback metadata, preserved non-reserved library `metadata`, derived `realm_references`, structured room metadata when present, strict or legacy validation status, state labels, oscillator counts, per-state frequency ranges, sample oscillator entries, and a compact spatial summary covering channel layout, source placement, and room-aware geometry-reference, surface-treatment, reflection-policy, renderer-adaptation, listening-zone intent, and speaker-placement plus speaker-role and speaker-coverage context.

### `rwif arwif-diff`

Compares two ARWIF artifacts in ARWIF-native terms.

Current implementation: reports top-level playback metadata changes, left and right spatial summaries, a compact spatial-change summary including room-aware deltas for room presence, geometry-reference presence, geometry reference, surface-treatment presence, surface treatment, reflection-policy presence, reflection policy, renderer-adaptation presence, renderer adaptation, listening zones, listening-zone intent diversity, listening-zone roster size, speaker ids, speaker-id roster size, speakers, speaker-channel roster size, speaker-role diversity, speaker-coverage intent diversity, and source-group roster size, state-count, oscillator-count, and max-frequency deltas, and state-level oscillator differences keyed by label or fallback state index.

### `rwif arwif-validate`

Validates an ARWIF audio artifact profile layered on the RWIF container.

Current implementation: checks ARWIF metadata, initial object-based and room-aware spatial semantics including room geometry reference, surface treatment, reflection policy, renderer adaptation hints, canonical listening-zone intents, speaker-channel bindings, canonical speaker roles, and speaker coverage intent, oscillator-bank semantics, Nyquist bounds, and legacy prototype compatibility when `--legacy` is supplied.

### `rwif arwif-render`

Renders an ARWIF artifact to 16-bit PCM WAV.

Current implementation: interprets each state as a sequential oscillator-bank segment, applies a simple attack/release envelope, projects states across channels when `channel_layout` and `channel_gains` are present, and optionally normalizes the rendered waveform.

### `rwif vrwif-validate-spec`

Validates a VRWIF source spec.

Current implementation: checks scene identity, reference-frame semantics, object, camera, and lighting structures, canonical object state, canonical object visibility, canonical camera framing intents, and canonical lighting colors, top-level and per-entity metadata mappings, and trajectory ordering without writing any artifacts.

### `rwif vrwif-normalize`

Normalizes a VRWIF source spec into a canonical strict source document.

Current implementation: rewrites a source spec into a deterministic ordering, can emit a normalization report and an assumptions manifest, and validates the normalized document before writing it.

### `rwif vrwif-batch-normalize`

Normalizes multiple VRWIF source specs.

Current implementation: accepts one or more source specs, writes normalized specs into `--output-dir`, can optionally emit per-spec normalization reports and assumptions manifests, and returns an aggregated result payload with collection-level counts.

### `rwif vrwif-batch-normalize-analyze`

Analyzes a saved VRWIF batch normalization report.

Current implementation: aggregates recurring normalization actions and warning patterns from a previously saved batch-normalization payload, and can optionally persist the analysis as `.json`, `.yaml`, or `.yml`.

### `rwif vrwif-batch-normalize-review`

Runs VRWIF batch normalization and normalization analysis in one command.

Current implementation: combines the `vrwif-batch-normalize` and `vrwif-batch-normalize-analyze` workflows into one persisted review payload.

### `rwif vrwif-inspect`

Summarizes a VRWIF source spec in VRWIF-native terms.

Current implementation: reports scene identity, preserved top-level `metadata`, derived `realm_references`, object, camera, and lighting summaries, and a compact `scene_summary` covering grouping, canonical object state, canonical object visibility, object-distance totals and range, object-trajectory duration totals and range, object-trajectory path-length totals and range, object-trajectory displacement totals and range, object-trajectory average-speed totals and range, object-trajectory peak-speed totals and range, object-trajectory speed-standard-deviation totals and range, object-trajectory average-acceleration totals and range, object-trajectory peak-acceleration totals and range, object-trajectory straightness totals and range, object-trajectory cumulative turn-angle totals and range in degrees, object-trajectory peak-turn-angle totals and range in degrees, object-trajectory turn-count totals and range, object-trajectory average-turn-angle totals and range in degrees, object-trajectory turn-angle standard-deviation totals and range in degrees, trajectory, canonical camera framing intent, camera presence, derived camera-trajectory duration, derived camera-trajectory path length, derived camera-trajectory displacement, derived camera-trajectory average speed, derived camera-trajectory peak speed, derived camera-trajectory speed standard deviation, derived camera-trajectory average acceleration, derived camera-trajectory peak acceleration, derived camera-trajectory straightness, derived camera-trajectory turn angle in degrees, derived camera-trajectory peak turn angle in degrees, derived camera-trajectory turn count, derived camera-trajectory average turn angle in degrees, derived camera-trajectory turn-angle standard deviation in degrees, derived camera distance from origin, lighting presence, light counts, light-intensity totals and range, positioned-light versus directional-light counts, light-temperature coverage and range, and canonical lighting colors.

### `rwif vrwif-batch-inspect`

Inspects multiple VRWIF source specs.

Current implementation: reuses the same inspection path as `vrwif-inspect`, returning per-spec inspection payloads plus collection-level counts for valid specs, total objects, total lights, and scenes carrying cameras.

### `rwif vrwif-diff`

Compares two VRWIF source specs.

Current implementation: reports top-level metadata changes, added or removed objects, changed objects, object field deltas, and scene-level changes such as reference-frame drift, object-count drift, object-id drift, object-id roster drift, group changes, object-group roster drift, object-state drift, object-visibility drift, object-distance total and range drift, object-trajectory duration total and range drift, object-trajectory path-length total and range drift, object-trajectory displacement total and range drift, object-trajectory average-speed total and range drift, object-trajectory peak-speed total and range drift, object-trajectory speed-standard-deviation total and range drift, object-trajectory average-acceleration total and range drift, object-trajectory peak-acceleration total and range drift, object-trajectory straightness total and range drift, object-trajectory cumulative turn-angle total and range drift in degrees, object-trajectory peak-turn-angle total and range drift in degrees, object-trajectory turn-count total and range drift, object-trajectory average-turn-angle total and range drift in degrees, object-trajectory turn-angle standard-deviation total and range drift in degrees, object-trajectory point-count drift, explicit framing-intent drift, camera changes, camera-presence drift, camera-id drift, camera-trajectory presence drift, camera-trajectory duration drift, camera-trajectory path-length drift, camera-trajectory displacement drift, camera-trajectory average-speed drift, camera-trajectory peak-speed drift, camera-trajectory speed-standard-deviation drift, camera-trajectory average-acceleration drift, camera-trajectory peak-acceleration drift, camera-trajectory straightness drift, camera-trajectory turn-angle drift in degrees, camera-trajectory peak-turn-angle drift in degrees, camera-trajectory turn-count drift, camera-trajectory average-turn-angle drift in degrees, camera-trajectory turn-angle standard-deviation drift in degrees, camera-trajectory point-count drift, camera-distance drift, lighting-presence drift, light-intensity total and range drift, positioned-light and directional-light deltas, light-temperature coverage and range drift, lighting-color drift, lighting identity churn, light-id roster drift, and object identity churn.

### `rwif vrwif-batch-diff`

Compares multiple VRWIF source spec pairs.

Current implementation: accepts explicit pairwise `--left` and `--right` collections of equal length, reuses the same comparison path as `vrwif-diff`, and returns an aggregated diff payload with collection-level change counts.

### `rwif vrwif-batch-diff-analyze`

Analyzes a saved VRWIF batch diff report.

Current implementation: aggregates recurring metadata, object, and scene-level changes across all compared pairs, including object-count, object-id, object-id roster size, object-group roster size, object-state, object-visibility, object-distance, object-trajectory duration, object-trajectory path length, object-trajectory displacement, object-trajectory average speed, object-trajectory peak speed, object-trajectory speed standard deviation, object-trajectory average acceleration, object-trajectory peak acceleration, object-trajectory straightness, object-trajectory cumulative turn angle in degrees, object-trajectory peak turn angle in degrees, object-trajectory turn count, object-trajectory average turn angle in degrees, object-trajectory turn-angle standard deviation in degrees, object-trajectory point count, framing-intent, camera-presence, camera-id, camera-trajectory presence, camera-trajectory duration, camera-trajectory path length, camera-trajectory displacement, camera-trajectory average speed, camera-trajectory peak speed, camera-trajectory speed standard deviation, camera-trajectory average acceleration, camera-trajectory peak acceleration, camera-trajectory straightness, camera-trajectory turn angle in degrees, camera-trajectory peak turn angle in degrees, camera-trajectory turn count, camera-trajectory average turn angle in degrees, camera-trajectory turn-angle standard deviation in degrees, camera-trajectory point count, camera-distance, light-intensity, light-placement, light-temperature, lighting-color, lighting-id drift, and light-id roster drift counts, and can optionally persist the analysis result as `.json`, `.yaml`, or `.yml`.

### `rwif vrwif-batch-review`

Runs VRWIF batch diff and recurring-change analysis together.

Current implementation: combines the `vrwif-batch-diff` and `vrwif-batch-diff-analyze` workflows into one persisted review payload.

## Output Rules

- human-readable by default
- `--json` available where structured output matters
- non-zero exit codes on validation or build failures
- explicit provenance in build-related output
