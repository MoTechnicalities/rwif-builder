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

### `rwif arwif-inspect`

Summarizes an ARWIF artifact in ARWIF-native terms.

Current implementation: reports playback metadata, strict or legacy validation status, state labels, oscillator counts, per-state frequency ranges, and sample oscillator entries.

### `rwif arwif-diff`

Compares two ARWIF artifacts in ARWIF-native terms.

Current implementation: reports top-level playback metadata changes, state-count and oscillator-count deltas, and state-level oscillator differences keyed by label or fallback state index.

### `rwif arwif-validate`

Validates an ARWIF audio artifact profile layered on the RWIF container.

Current implementation: checks ARWIF metadata, oscillator-bank semantics, Nyquist bounds, and legacy prototype compatibility when `--legacy` is supplied.

### `rwif arwif-render`

Renders an ARWIF artifact to mono 16-bit PCM WAV.

Current implementation: interprets each state as a sequential oscillator-bank segment, applies a simple attack/release envelope, and optionally normalizes the rendered waveform.

## Output Rules

- human-readable by default
- `--json` available where structured output matters
- non-zero exit codes on validation or build failures
- explicit provenance in build-related output
