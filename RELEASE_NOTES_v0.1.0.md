# rwif-builder v0.1.0

First public release of the RWIF forge pipeline.

## Highlights

- Builds real `.rwif` semantic-memory artifacts from Markdown and text corpora
- Emits a builder manifest inside the RWIF artifact for provenance and reproducibility
- Validates artifact structure and semantic-memory metadata
- Compares artifacts with manifest-aware `diff`
- Rebuilds deterministically with `patch`
- Supports both a built-in hashing baseline and a verified transformer activation path

## Why It Matters

The server repo is the engine.
This repo is the forge.

It is the place where raw text becomes Analog Wave Memory, and where the storage format itself is explained.

## What Ships In v0.1.0

- a real end-to-end builder for Markdown and text corpora
- a compatible RWIF semantic-memory writer and validator
- manifest-aware artifact `diff` and `patch`
- hashing and transformer embedding paths
- a deep-dive explanation of the DCT-packed storage model

## Verified Transformer Path

The optional transformer backend was verified with `sentence-transformers/all-MiniLM-L6-v2`, producing a valid RWIF artifact with vector length `384`.
