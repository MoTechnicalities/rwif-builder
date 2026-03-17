# rwif-builder v0.1.0

First public release of the RWIF forge pipeline.

## Highlights

- Builds real `.rwif` semantic-memory artifacts from Markdown and text corpora
- Emits a builder manifest inside the RWIF artifact for provenance and reproducibility
- Validates artifact structure and semantic-memory metadata
- Compares artifacts with manifest-aware `diff`
- Rebuilds deterministically with `patch`
- Supports both a built-in hashing baseline and an optional transformer activation path

## Why It Matters

The server repo is the engine.
This repo is the forge.

It is the place where raw text becomes Analog Wave Memory, and where the storage format itself is explained.
