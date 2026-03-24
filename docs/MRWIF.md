# MRWIF Draft

## Purpose

`MRWIF` stands for Multimodal Resonant Wave Information Format.

Its role is not to replace `RWIF`, `ARWIF`, or `VRWIF`.
Its role is to make their correspondences explicit.

If `RWIF` stores meaning and `ARWIF` or `VRWIF` store renderable perceptual structure, `MRWIF` stores the bridge between them.

## Scope

`MRWIF` should describe:

- semantic-to-perceptual mappings
- perceptual-to-semantic interpretations
- cross-modal identity links
- revision traces across modalities
- confidence and ambiguity in those correspondences

It should not try to store the full payloads of the domains it links.
Those belong in their native formats.

## Core Questions

`MRWIF` should help answer:

- Which acoustic or visual structures tend to satisfy a given semantic intent?
- Which semantic interpretations best explain a given rendered result?
- Which sound and scene variants still represent the same underlying identity?
- What changed in the bridge after a revision loop?

## Core Entities

### Intent Mapping

Links semantic descriptors to structured perceptual targets.

Example ideas:

- `warm` -> lower brightness, softer attack, smoother release
- `urgent` -> tighter transients, faster temporal progression, stronger contrast

### Identity Mapping

Links multiple artifacts that represent the same underlying concept.

Examples:

- one narrative character linked to a recurring sound motif and visual motif
- one product identity linked to several sonic and visual variants

### Interpretation Record

Stores how a system interpreted a rendered result.

This can include:

- inferred semantic descriptors
- confidence
- ambiguity notes
- disagreement between expected and observed perceptual traits

### Revision Trace

Stores why a change was made across modalities.

Examples:

- requested more tension, so the sound was sharpened and the lighting contrast increased
- requested more calm, so motion density and upper partial emphasis were reduced

## Draft Shape

A practical `MRWIF` draft would likely need:

- linked artifact identifiers
- semantic descriptor sets
- perceptual descriptor sets
- correspondence rules or learned weights
- confidence fields
- revision notes
- provenance metadata

## Design Principles

1. Keep links explicit.
2. Store uncertainty instead of pretending every mapping is exact.
3. Preserve revision history.
4. Treat correspondences as first-class data, not comments.
5. Avoid duplicating the full payloads of linked formats.

## Minimal v0.1 Surface

This repo now implements a minimal source-spec surface for `MRWIF`:

- validation
- inspection
- diff

The initial document shape is intentionally narrow and centers on:

- `linked_artifacts`
- `intent_mappings`
- `interpretation_records`
- `revision_traces`

That gives the repo an operational multimodal bridge without prematurely expanding into artifact serialization or learned-weight pipelines.

## Relationship To This Repo

What it does implement is the necessary precursor:

- `RWIF` as a semantic memory artifact path
- `ARWIF` as a structured sound artifact path

It now also implements the first bridge layer that can explicitly connect those neighboring domains, plus `VRWIF`, inside a shared inspectable source spec.

`MRWIF` becomes credible only once those neighboring domains are concrete enough to link.