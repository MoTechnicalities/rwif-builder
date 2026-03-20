# rwif-builder v0.1.11

Feature release adding ARWIF normalization assumptions manifests.

## What Changed

- extends `rwif arwif-normalize` with `--assumptions <output.{json|yaml|yml}>` to emit a machine-readable assumptions manifest alongside the normalized spec and optional full report
- derives the manifest from the same normalization audit data so injected defaults, preserved library metadata, preserved per-state metadata, and validation warnings stay consistent with the full report artifact
- records summary counts for assumption entries, injected defaults, preserved metadata fields, and warning categories so CI can gate migrations without parsing the full report body
- keeps the existing `--report` artifact for full validation and content audit while introducing a smaller contract for migration review and automation
- extends the ARWIF integration suite to verify assumptions-manifest generation and content end to end
- updates the README, CLI reference, ARWIF mini-spec, and examples guide to document assumptions manifests

## Scope

This release makes ARWIF normalization easier to operationalize in automation. Teams migrating legacy prototype files can now keep a concise assumptions manifest focused on the decisions and warnings that matter for review, while still emitting the full normalization report when a deeper audit trail is needed.