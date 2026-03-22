# rwif-builder v0.1.28

Feature release adding VRWIF inspect parity for outward realm references.

## What Changed

- updates `rwif vrwif-inspect <spec> --json` so inspection payloads now expose preserved top-level `metadata` instead of limiting the summary to scene, object, camera, and lighting structure alone
- derives a dedicated `realm_references` field during VRWIF inspection from `metadata.related_realms` or `metadata.realm_references`, giving VRWIF specs the same clean outward bridge surface that RWIF and ARWIF inspection now expose
- keeps the VRWIF source-schema boundary unchanged by treating outward realm links as preserved scene metadata rather than promoting them into first-class geometry or render fields
- extends the VRWIF integration suite with an end-to-end inspection case that verifies cross-realm links appear in the public inspection JSON payload for valid scene specs
- refreshes the README, CLI reference, and VRWIF guide so the inspect contract explicitly documents preserved metadata and normalized outward realm references

## Scope

This release continues the recent bridge-contract cleanup without broadening realm semantics. `VRWIF` remains a visual reasoning and review surface, not a multimodal bridge schema, but its inspection output now exposes the metadata needed to point cleanly into neighboring realms. That brings `VRWIF` into parity with the recent `RWIF` and `ARWIF` bridge work while keeping scene structure and cross-realm linkage clearly separated.