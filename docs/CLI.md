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

## Output Rules

- human-readable by default
- `--json` available where structured output matters
- non-zero exit codes on validation or build failures
- explicit provenance in build-related output
