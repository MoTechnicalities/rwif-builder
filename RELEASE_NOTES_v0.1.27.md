# rwif-builder v0.1.27

Feature release adding ARWIF inspect parity for outward realm references.

## What Changed

- updates `rwif arwif-inspect <artifact> --json` so inspection payloads now expose preserved non-reserved top-level library `metadata` instead of limiting the summary to playback and spatial fields alone
- derives a dedicated `realm_references` field during ARWIF inspection from `metadata.related_realms` or `metadata.realm_references`, giving ARWIF artifacts the same clean outward bridge surface that recent RWIF inspection gained for related `ARWIF`, `VRWIF`, and future realms
- keeps the ARWIF build and authoring contract unchanged by treating outward realm links as preserved metadata rather than introducing new reserved playback-schema fields
- extends the ARWIF integration suite with an end-to-end build-and-inspect case that verifies cross-realm links survive artifact creation and appear in the public inspection JSON payload
- refreshes the README, CLI reference, and ARWIF v0.1 guide so the inspect contract explicitly documents preserved metadata and normalized outward realm references

## Scope

This release keeps the realm boundaries disciplined. `ARWIF` remains an audio reasoning and authoring surface, not a general bridge schema, but its inspection output now exposes the preserved metadata needed to point cleanly into neighboring realms. That brings `ARWIF` into parity with the recent `RWIF` bridge work without broadening the underlying artifact format.