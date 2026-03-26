# ARWIF v0.1 Mini-Spec

ARWIF stands for Analog Resident Wave Information Format.

Version `0.1` is a narrow audio profile layered on top of the existing RWIF activation-core container. It is intended for compact storage of oscillator-bank instructions, not for PCM sample storage.

For the longer-term analysis-oriented ARWIF direction, see [docs/ARWIF_ANALYSIS_MISSION.md](docs/ARWIF_ANALYSIS_MISSION.md), [docs/ARWIF_ANALYSIS_ROADMAP.md](docs/ARWIF_ANALYSIS_ROADMAP.md), [docs/ARWIF_ANALYSIS_SCHEMA_DRAFT.md](docs/ARWIF_ANALYSIS_SCHEMA_DRAFT.md), and [docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md](docs/ARWIF_ANALYSIS_COMMAND_SURFACE.md). Those documents describe the intended path toward inferred source structure from real recordings rather than the current authored-synthesis profile.

## Scope

ARWIF `v0.1` describes:

- a RWIF-compatible binary envelope
- integer-Hz oscillator definitions stored in RWIF atomic wave units
- sequential segment playback
- optional per-segment envelope and gain controls

It does not yet describe:

- full room-aware acoustic rendering or speaker-environment adaptation
- streaming or chunked playback
- compressed payloads
- sample-accurate event scheduling
- arbitrary wavetable synthesis

See [docs/ARWIF_SPATIAL_ROADMAP.md](docs/ARWIF_SPATIAL_ROADMAP.md) for the forward-looking design path toward channel-aware, object-based, room-aware, and field-synthesis spatial ARWIF tiers.

See [docs/ARWIF_ANALYSIS_ROADMAP.md](docs/ARWIF_ANALYSIS_ROADMAP.md) for the forward-looking analysis path toward real-audio ingestion, source hypotheses, reconstructable components, and stem-oriented reasoning workflows.

The current toolchain also accepts a minimal spatial metadata surface beyond the mono baseline:

- Level 1 channel-aware metadata via top-level `channel_layout` and per-state `channel_gains`
- an initial Level 2 object-metadata slice via top-level `listener_anchor` and `reference_frame`, plus per-state `source_id`, `source_groups`, `position`, `trajectory`, `orientation`, `spread`, and `distance_model`
- an initial Level 3 room-aware slice via top-level `room` metadata for room dimensions, geometry reference, surface profile, surface treatment, reflection policy, renderer adaptation hints, listening zones, and speaker placement with compact speaker role and coverage intent

The reference renderer can emit multichannel PCM WAV for declared Level 1 layouts. Level 2 and the initial Level 3 metadata are currently preserved for authoring, validation, inspection, diffing, export, and batch review rather than being rendered as a full object-based or room-adaptive spatial mix.

## Container

ARWIF reuses the RWIF activation-core envelope:

- magic header: `RWIFACT1`
- header prefix: little-endian `<8sI>`
- JSON header block
- packed atomic wave units using `<Id>`

That means generic RWIF tooling can still parse the file structure, even if it does not understand the audio semantics.

## Required Library Metadata

Strict ARWIF `v0.1` files should place these fields in `library_metadata`:

- `format = arwif_audio`
- `arwif_version = 1`
- `frequency_unit = hz`
- `playback_model = continuous_oscillator_bank`
- `sample_rate_hz = <positive integer>`
- `default_duration_seconds = <positive float>`

Optional library metadata:

- `title`
- `listener_anchor` as `{ x, y, z }` finite coordinates describing the reference listening origin
- `reference_frame` as one of `listener`, `scene`, or `world` to declare how spatial coordinates should be interpreted
- `room` as a mapping that may contain:
  - `dimensions` with positive finite `width_m`, `depth_m`, and `height_m`
  - `geometry_reference` as a mapping with optional:
    - `geometry_id` as a stable non-empty string identifier for a referenced room model or venue archetype
    - `geometry_class` as one of `shoebox`, `fan`, `arena`, `corridor`, or `irregular`
  - `surface_profile` as one of `dry`, `damped`, `neutral`, `reflective`, or `diffuse`
  - `surface_treatment` as a mapping with optional:
    - `absorption` as one of `low`, `balanced`, or `high`
    - `diffusion` as one of `focused`, `balanced`, or `scattered`
  - `reflection_policy` as a mapping with optional:
    - `style` as one of `direct`, `balanced`, or `enveloping`
    - `early_reflections` as one of `reduced`, `natural`, or `emphasized`
    - `late_reverb` as one of `dry`, `controlled`, or `lush`
  - `renderer_adaptation_hints` as a mapping with optional:
    - `target_playback` as one of `headphones`, `stereo_speakers`, `multichannel_room`, or `portable_device`
    - `spatial_priority` as one of `precision`, `balanced`, or `envelopment`
    - `downmix_policy` as one of `preserve_positions`, `preserve_focus`, or `preserve_energy`
  - `listening_zones` as a list of `{ zone_id, anchor, radius_m, intent? }` mappings, where `intent` may be one of `focused`, `balanced`, `diffuse`, or `casual`
  - `speakers` as a list of `{ speaker_id, anchor, channel?, role?, coverage_intent? }` mappings, where `channel` must match the declared `channel_layout` when present, `role` may be one of `main`, `surround`, `height`, or `fill`, and `coverage_intent` may be one of `focused`, `balanced`, `wide`, or `ambient`
- `normalize` as boolean, default `true`
- `default_phase_radians`, default `0.0`
- `default_attack_ms`, default `5.0`
- `default_release_ms`, default `5.0`

## State Semantics

Each RWIF state is interpreted as one sequential audio segment.

States are rendered in file order.
All atomic wave units inside a state are rendered simultaneously as a summed oscillator bank.

State metadata may override library defaults with:

- `duration_seconds`
- `phase_radians`
- `gain`
- `source_id` as a stable non-empty identifier for a sound object across revisions or downstream realms
- `source_groups` as a list of non-empty grouping labels for coarse scene membership
- `position` as `{ x, y, z }` finite coordinates for object placement
- `trajectory` as a non-empty list of `{ offset_seconds, position }` keyframes with non-negative, non-decreasing offsets inside the state duration
- `orientation` as `{ x, y, z }` finite coordinates for object-facing intent
- `spread` as a non-negative finite scalar for source diffuseness
- `distance_model` as one of `none`, `inverse`, `linear`, or `exponential`
- `attack_ms`
- `release_ms`

## Atomic Wave Unit Semantics

ARWIF `v0.1` reinterprets the RWIF unit fields as:

- `frequency_index` slot: integer frequency in Hz
- `amplitude` slot: linear amplitude scalar

This is a semantic reinterpretation of the RWIF unit struct. In semantic-memory RWIF, the integer slot is a transformed coefficient index. In ARWIF, it is oscillator frequency.

## Compatibility Field Note

The RWIF `vector_length` field is retained for envelope compatibility with existing loaders, but ARWIF decoders should not treat it as a hard frequency bound.

For ARWIF `v0.1`, frequency validation is based on `sample_rate_hz` and Nyquist, not on `vector_length`.

## Rendering Model

The reference renderer produces 16-bit PCM WAV output.

When no `channel_layout` is present, output is mono.
When a supported `channel_layout` is present, the renderer emits a multichannel WAV and applies each state's `channel_gains` across the declared layout.

For each segment:

1. create a time grid using `sample_rate_hz`
2. synthesize one sine oscillator per atomic wave unit
3. sum the oscillators into a mono state signal
4. apply gain and a simple attack/release envelope
5. project that state signal across channels using `channel_gains` when present
6. concatenate segments in order
7. normalize if enabled

## Authoring Spec

The reference builder command accepts a YAML or JSON spec and writes a strict ARWIF `v0.1` artifact.

Minimum shape:

```yaml
title: C major triad
sample_rate_hz: 48000
default_duration_seconds: 1.0

states:
  - label: CEG
    duration_seconds: 1.0
    oscillators:
      - hz: 261
        amplitude: 0.8
      - hz: 330
        amplitude: 0.7
      - hz: 392
        amplitude: 0.6
```

Supported top-level fields:

- `title`
- `description`
- `channel_layout` as one of `mono`, `stereo`, `quad`, `5.1`, or `7.1`
- `listener_anchor` as a mapping with finite `x`, `y`, and `z` coordinates
- `reference_frame` as one of `listener`, `scene`, or `world`
- `room` for structured room-aware context including dimensions, geometry reference, surface profile, surface treatment, reflection policy, renderer adaptation hints, listening zones, and speaker placement with canonical speaker roles and coverage intent
- `sample_rate_hz`
- `default_duration_seconds`
- `default_phase_radians`
- `default_attack_ms`
- `default_release_ms`
- `normalize`
- `metadata` for additional library metadata
- `states`

Supported per-state fields:

- `label`
- `duration_seconds`
- `phase_radians`
- `gain`
- `source_id` as a non-empty string
- `source_groups` as a list of non-empty strings
- `channel_gains` as a mapping of layout channel labels to finite gain values
- `position` as a mapping with finite `x`, `y`, and `z` coordinates
- `trajectory` as a non-empty list of `{ offset_seconds, position }` keyframes with non-negative, non-decreasing offsets that do not exceed the effective state duration
- `orientation` as a mapping with finite `x`, `y`, and `z` coordinates
- `spread` as a non-negative finite scalar
- `distance_model` as one of `none`, `inverse`, `linear`, or `exponential`
- `attack_ms`
- `release_ms`
- `vector_length`
- `top_k`
- `metadata` for additional state metadata
- `oscillators`, where each oscillator is `{ hz, amplitude }`

Reference command:

```bash
rwif arwif-validate-spec examples/arwif/CEG_v0_1.yaml --json
rwif arwif-build --spec examples/arwif/CEG_v0_1.yaml --output dist/CEG_v0_1.arwif --json
rwif arwif-batch-build first.yaml second.yaml --output-dir dist/built_arwif --json
rwif arwif-batch-diff --left dist/alpha.baseline.arwif dist/beta.baseline.arwif --right dist/alpha.candidate.arwif dist/beta.candidate.arwif --output dist/batch-diff-report.json --json
rwif arwif-batch-export dist/alpha.arwif dist/beta.arwif --output-dir dist/exported_specs --format yaml --json
rwif arwif-batch-render dist/alpha.arwif dist/beta.arwif --output-dir dist/rendered_wav --json
```

The reference tooling validates source specs before build and import. That validation checks:

- required top-level fields and types
- per-state override types
- per-oscillator `hz` and `amplitude` values
- Nyquist compliance against `sample_rate_hz`
- reserved metadata keys that will be overridden by strict ARWIF library metadata

Invalid specs should fail before any artifact is written.

For collection-scale authoring, the reference CLI also supports building multiple strict specs into one output directory while keeping the same validation semantics as single-spec `arwif-build`.

For collection-scale comparison, the reference CLI also supports diffing multiple explicit left and right artifact pairs in one command while keeping the same state-level and metadata diff semantics as single-artifact `arwif-diff`, and can optionally persist the aggregated comparison report as JSON or YAML for review pipelines.

For collection-scale spec emission, the reference CLI also supports exporting multiple validated artifacts into one target directory while keeping the same strict-spec-compatible document structure as single-artifact `arwif-export`.

For collection-scale playback export, the reference CLI also supports rendering multiple validated artifacts into one output directory while keeping the same synthesis semantics as single-artifact `arwif-render`.

## Export And Round Trip

Reference tooling also supports artifact-to-spec export and spec-to-artifact import:

```bash
rwif arwif-export dist/CEG_v0_1.arwif dist/CEG_v0_1.export.yaml --json
rwif arwif-validate-spec dist/CEG_v0_1.export.yaml --json
rwif arwif-import --spec dist/CEG_v0_1.export.yaml --output dist/CEG_v0_1.roundtrip.arwif --json
rwif arwif-diff dist/CEG_v0_1.arwif dist/CEG_v0_1.roundtrip.arwif --json
```

For strict ARWIF `v0.1` artifacts produced by the reference builder, the exported spec is intended to round-trip without changing playback metadata, state ordering, or oscillator-bank contents.

The current inspection path also reports preserved non-reserved top-level `metadata` plus a normalized `realm_references` view derived from `metadata.related_realms` or `metadata.realm_references`, so ARWIF artifacts can expose clean outward pointers to neighboring `RWIF`, `VRWIF`, or future realms without treating those bridges as first-class playback fields.

The current inspection path also reports a compact `spatial_summary` that identifies the declared layout, the active channels actually used by non-zero gains, the listener anchor and reference frame when present, structured room context such as dimensions, geometry-reference summaries, surface profile, surface-treatment summaries, reflection-policy summaries, renderer-adaptation summaries, listening-zone summaries, and speaker-placement summaries including stable speaker ids plus canonical speaker roles and coverage intent, how many states carry stable source identity, which source groups appear overall, how many states carry positioned, trajectory, or oriented object metadata, how many trajectory keyframes are present overall, how many states declare spread, and which distance models appear in the artifact.

The current diff path also reports `left_spatial_summary`, `right_spatial_summary`, and `spatial_changes` so channel-aware, object-based, and initial room-aware revisions can be reviewed without reading the entire per-state metadata diff, including active-channel roster deltas, narrower room-presence drift, geometry-reference presence drift, surface-treatment presence drift, reflection-policy presence drift, renderer-adaptation presence drift, speaker-id churn, listening-zone roster deltas, speaker-channel roster deltas, speaker-id roster deltas, source-group roster deltas, max-frequency drift, listening-zone or speaker-coverage intent-diversity drift, and speaker-role diversity drift when channel activation breadth, room context, physical speaker identities, listening-zone roster size, speaker binding breadth, speaker roster size, source-routing breadth, spectral bandwidth, intent diversity, or role diversity change without broader geometry, role, or coverage changes.

For a concrete room-aware review workflow, the shipped example pair `examples/arwif/ROOM_REVIEW_baseline_v0_1.yaml` and `examples/arwif/ROOM_REVIEW_candidate_v0_1.yaml` is designed to exercise the current Level 3 batch-review surface end to end.

## Legacy Prototype Files

Pre-spec ARWIF prototype files may omit the strict metadata fields while still reusing the `RWIFACT1` envelope and oscillator-bank interpretation.

Reference tooling may support these files in a legacy-compatibility mode, but they should not be considered fully compliant ARWIF `v0.1` artifacts.

The reference normalization path upgrades those artifacts into a strict source spec and optional rebuilt strict artifact:

```bash
rwif arwif-normalize examples/arwif/CEG_legacy.arwif --spec dist/CEG_legacy.normalized.yaml --output dist/CEG_legacy.normalized.arwif --report dist/CEG_legacy.normalized.report.json --assumptions dist/CEG_legacy.normalized.assumptions.json --json
rwif arwif-validate dist/CEG_legacy.normalized.arwif --json
```

Normalization currently:

- loads the source artifact in legacy-compatible mode
- injects defaults for missing strict playback metadata fields
- preserves non-reserved library metadata and state metadata
- writes a strict ARWIF `v0.1` source spec that passes `arwif-validate-spec`
- optionally rebuilds a strict artifact from that normalized spec
- optionally writes a normalization report artifact containing source validation, preserved metadata, normalized-spec validation, normalized content counts, and rebuilt-artifact validation when an output artifact is requested
- optionally writes an assumptions manifest artifact containing injected defaults, preserved library/state metadata fields, and source, normalized-spec, or rebuilt-artifact warnings in a smaller machine-readable document

For migration work across a collection of files, the reference CLI also supports batching the same normalization flow:

```bash
rwif arwif-batch-normalize old-a.arwif old-b.arwif --spec-dir dist/normalized_specs --output-dir dist/normalized_artifacts --report-dir dist/normalization_reports --assumptions-dir dist/assumptions --json
```

Batch normalization keeps the single-artifact normalization semantics, but writes outputs into predictable directories and returns an aggregated machine-readable summary that includes per-artifact payloads and collection-level counts.