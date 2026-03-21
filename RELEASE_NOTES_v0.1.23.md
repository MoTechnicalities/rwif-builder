# rwif-builder v0.1.23

Feature release making VRWIF normalization auditable.

## What Changed

- adds `rwif vrwif-normalize --report <report.{json|yaml}>` so a single VRWIF scene spec can emit a persisted normalization report alongside the canonical strict output spec
- adds `rwif vrwif-batch-normalize --report-dir <dir>` so each spec in a batch normalization pass can emit its own persisted normalization report while the aggregate batch payload remains available through `--output`
- includes source validation, normalized validation, normalization summary counters, and the canonicalized normalized document in the persisted VRWIF normalization reports
- keeps the VRWIF normalization contract aligned with the existing strict source-spec surface rather than introducing any artifact or render semantics
- expands the VRWIF integration suite and refreshes the README plus VRWIF doc so report-oriented normalization is documented as part of the shipped source-authoring workflow

## Scope

This release does not broaden VRWIF into a builder or renderer. It strengthens the existing source-spec workflow by making canonicalization inspectable and auditable, both for single-scene and collection-scale normalization runs. Teams can now preserve not just the rewritten strict spec, but also the machine-readable reasoning about how and why that spec was normalized.