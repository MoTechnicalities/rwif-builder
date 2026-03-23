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

Current implementation: accepts one or more strict ARWIF source specs, writes artifacts into `--output-dir`, reuses the same strict build flow as `arwif-build`, and returns an aggregated result payload with per-spec build results plus collection-level counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-import`

Imports multiple ARWIF YAML or JSON specs into ARWIF artifacts.

Current implementation: accepts one or more strict ARWIF source specs, writes artifacts into `--output-dir`, reuses the same import path as `arwif-import`, and returns an aggregated result payload with per-spec import results plus collection-level counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-validate-spec`

Validates multiple ARWIF YAML or JSON source specs.

Current implementation: accepts one or more strict ARWIF source specs, reuses the same validation path as `arwif-validate-spec`, and returns an aggregated result payload with per-spec validation details plus collection-level valid and invalid counts.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-diff`

Compares multiple ARWIF artifact pairs.

Current implementation: accepts explicit pairwise `--left` and `--right` artifact collections of equal length, reuses the same comparison path as `arwif-diff`, and returns an aggregated result payload with per-pair diffs plus collection-level counts for changed, unchanged, invalid, incompatible, and changed-state totals.
An optional `--output` path can persist that aggregated report as `.json`, `.yaml`, or `.yml` based on the destination suffix.

### `rwif arwif-batch-diff-analyze`

Analyzes an aggregated ARWIF batch diff report.

Current implementation: accepts a previously saved `arwif-batch-diff` report in `.json`, `.yaml`, or `.yml` format, aggregates recurring metadata and state changes across pairs, summarizes spatial drift counts, and can optionally persist the analysis result as `.json`, `.yaml`, or `.yml` based on the output suffix.

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

Current implementation: reports top-level playback metadata changes, left and right spatial summaries, a compact spatial-change summary including room-aware deltas for geometry reference, surface treatment, reflection policy, renderer adaptation, listening zones, listening-zone intents, speakers, speaker roles, and speaker coverage intent, state-count and oscillator-count deltas, and state-level oscillator differences keyed by label or fallback state index.

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

Current implementation: reports scene identity, preserved top-level `metadata`, derived `realm_references`, object, camera, and lighting summaries, and a compact `scene_summary` covering grouping, canonical object state, canonical object visibility, object-distance totals and range, object-trajectory duration totals and range, object-trajectory path-length totals and range, object-trajectory displacement totals and range, object-trajectory average-speed totals and range, object-trajectory peak-speed totals and range, object-trajectory speed-standard-deviation totals and range, object-trajectory straightness totals and range, object-trajectory cumulative turn-angle totals and range in degrees, object-trajectory peak-turn-angle totals and range in degrees, object-trajectory turn-count totals and range, object-trajectory average-turn-angle totals and range in degrees, object-trajectory turn-angle standard-deviation totals and range in degrees, trajectory, canonical camera framing intent, camera presence, derived camera-trajectory duration, derived camera-trajectory path length, derived camera-trajectory displacement, derived camera-trajectory average speed, derived camera-trajectory peak speed, derived camera-trajectory speed standard deviation, derived camera-trajectory straightness, derived camera-trajectory turn angle in degrees, derived camera-trajectory peak turn angle in degrees, derived camera-trajectory turn count, derived camera-trajectory average turn angle in degrees, derived camera-trajectory turn-angle standard deviation in degrees, derived camera distance from origin, lighting presence, light-intensity totals and range, positioned-light versus directional-light counts, light-temperature coverage and range, and canonical lighting colors.

### `rwif vrwif-batch-inspect`

Inspects multiple VRWIF source specs.

Current implementation: reuses the same inspection path as `vrwif-inspect`, returning per-spec inspection payloads plus collection-level counts for valid specs, total objects, total lights, and scenes carrying cameras.

### `rwif vrwif-diff`

Compares two VRWIF source specs.

Current implementation: reports top-level metadata changes, added or removed objects, changed objects, object field deltas, and scene-level changes such as reference-frame drift, group changes, object-state drift, object-visibility drift, object-distance total and range drift, object-trajectory duration total and range drift, object-trajectory path-length total and range drift, object-trajectory displacement total and range drift, object-trajectory average-speed total and range drift, object-trajectory peak-speed total and range drift, object-trajectory speed-standard-deviation total and range drift, object-trajectory straightness total and range drift, object-trajectory cumulative turn-angle total and range drift in degrees, object-trajectory peak-turn-angle total and range drift in degrees, object-trajectory turn-count total and range drift, object-trajectory average-turn-angle total and range drift in degrees, object-trajectory turn-angle standard-deviation total and range drift in degrees, explicit framing-intent drift, camera changes, camera-trajectory duration drift, camera-trajectory path-length drift, camera-trajectory displacement drift, camera-trajectory average-speed drift, camera-trajectory peak-speed drift, camera-trajectory speed-standard-deviation drift, camera-trajectory straightness drift, camera-trajectory turn-angle drift in degrees, camera-trajectory peak-turn-angle drift in degrees, camera-trajectory turn-count drift, camera-trajectory average-turn-angle drift in degrees, camera-trajectory turn-angle standard-deviation drift in degrees, camera-distance drift, light-intensity total and range drift, positioned-light and directional-light deltas, light-temperature coverage and range drift, lighting-color drift, and lighting identity churn.

### `rwif vrwif-batch-diff`

Compares multiple VRWIF source spec pairs.

Current implementation: accepts explicit pairwise `--left` and `--right` collections of equal length, reuses the same comparison path as `vrwif-diff`, and returns an aggregated diff payload with collection-level change counts.

### `rwif vrwif-batch-diff-analyze`

Analyzes a saved VRWIF batch diff report.

Current implementation: aggregates recurring metadata, object, and scene-level changes across all compared pairs, including object-state, object-visibility, object-distance, object-trajectory duration, object-trajectory path length, object-trajectory displacement, object-trajectory average speed, object-trajectory peak speed, object-trajectory speed standard deviation, object-trajectory straightness, object-trajectory cumulative turn angle in degrees, object-trajectory peak turn angle in degrees, object-trajectory turn count, object-trajectory average turn angle in degrees, object-trajectory turn-angle standard deviation in degrees, framing-intent, camera-trajectory duration, camera-trajectory path length, camera-trajectory displacement, camera-trajectory average speed, camera-trajectory peak speed, camera-trajectory speed standard deviation, camera-trajectory straightness, camera-trajectory turn angle in degrees, camera-trajectory peak turn angle in degrees, camera-trajectory turn count, camera-trajectory average turn angle in degrees, camera-trajectory turn-angle standard deviation in degrees, camera-distance, light-intensity, light-placement, light-temperature, and lighting-color drift counts, and can optionally persist the analysis result as `.json`, `.yaml`, or `.yml`.

### `rwif vrwif-batch-review`

Runs VRWIF batch diff and recurring-change analysis together.

Current implementation: combines the `vrwif-batch-diff` and `vrwif-batch-diff-analyze` workflows into one persisted review payload.

## Output Rules

- human-readable by default
- `--json` available where structured output matters
- non-zero exit codes on validation or build failures
- explicit provenance in build-related output
