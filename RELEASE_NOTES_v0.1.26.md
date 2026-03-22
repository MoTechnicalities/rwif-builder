# rwif-builder v0.1.26

Feature release adding one-shot VRWIF normalization review and published RWIF realm links.

## What Changed

- adds `rwif vrwif-batch-normalize-review <spec...> --output-dir <dir> [--output <review.{json|yaml}>]` so teams can normalize a collection of VRWIF specs and immediately receive the accompanying normalization analysis in one command instead of manually chaining batch normalize and batch normalize analyze
- packages the one-shot VRWIF normalize-review payload as a combined report containing both the underlying normalization results and the collection-level analysis, mirroring the existing review-oriented workflow pattern already used for batch diff review
- fixes the RWIF builder manifest path so top-level `metadata` from `rwif.yaml` is actually preserved in built semantic-memory artifacts instead of being silently dropped during build
- surfaces persisted RWIF cross-realm references during `rwif inspect` through manifest `metadata` and a dedicated `realm_references` field, making semantic-memory artifacts able to point cleanly to related `ARWIF`, `VRWIF`, and future realm artifacts or specs
- refreshes the README, the RWIF deep dive, the VRWIF guide, the starter config example, and the integration suite so both the new VRWIF review workflow and the RWIF realm-link contract are documented and validated end to end

## Scope

This release continues the current architecture rather than broadening it. `VRWIF` remains a source-authoring and review realm, now with a more ergonomic one-shot normalization review path. `RWIF` remains the semantic-memory center, but now preserves and exposes the metadata needed to point outward to neighboring realms instead of forcing those references to remain implicit or external to the built artifact.