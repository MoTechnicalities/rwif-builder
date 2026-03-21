# rwif-builder v0.1.24

Feature release adding compact VRWIF normalization assumptions manifests.

## What Changed

- adds `rwif vrwif-normalize --assumptions <manifest.{json|yaml}>` so a single VRWIF normalization pass can emit a smaller audit artifact focused on canonicalization decisions and warnings alongside the normalized strict spec and optional full report
- adds `rwif vrwif-batch-normalize --assumptions-dir <dir>` so each spec in a batch normalization run can emit its own compact assumptions manifest while the aggregate batch output still reports total assumptions across the collection
- derives the VRWIF assumptions manifest from the existing normalization report data, surfacing alias resolution, stable reordering, trajectory sorting, dropped unknown fields, and validation warnings without duplicating the full normalized document
- keeps the new output aligned with the existing ARWIF auditability pattern so teams can choose between the full normalization report and a smaller reasoning-focused manifest depending on review needs
- extends the VRWIF integration suite and refreshes the README plus VRWIF guide so assumptions-manifest generation is documented as part of the shipped normalization workflow

## Scope

This release stays within the current VRWIF source-authoring realm. It does not add build or render semantics. Instead, it strengthens normalization auditability by giving teams a compact machine-readable explanation of the assumptions and cleanup decisions made during canonicalization, both for single specs and batch normalization runs.