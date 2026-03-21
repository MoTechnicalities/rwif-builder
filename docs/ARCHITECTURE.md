# Architecture

## Package Layout

```text
rwif_builder/
  cli.py
  config/
  ingest/
  normalize/
  chunking/
  embedding/
  manifest/
  writer/
  validator/
  inspect/
  patch/
  utils/
```

## Responsibilities

- `cli`: public command surface
- `config`: config loading and schema validation
- `ingest`: adapters from source files into internal document records
- `normalize`: canonical record model before chunking
- `chunking`: deterministic segmentation of normalized content
- `embedding`: provider abstraction for vector or semantic feature generation
- `manifest`: reproducibility metadata and provenance output
- `writer`: RWIF artifact emission
- `validator`: post-build integrity checks
- `inspect`: human and machine-readable artifact introspection
- `patch`: incremental rebuild planning and execution
- `utils`: shared helpers

## Current State

The repo is no longer just a scaffold.

Operational code now exists across the RWIF authoring path and the ARWIF audio profile path, including validation, inspection, diffing, export/import, normalization, rendering, and batch workflows.

## Format Family Mapping

The broader vision described in [docs/VISION.md](docs/VISION.md) treats this repo as an authoring toolchain for a family of reasoning-oriented formats.

The current implementation maps onto that vision in a narrow but concrete way:

- `RWIF`: implemented here as the semantic-memory artifact builder, validator, inspector, differ, and patching toolchain
- `ARWIF`: implemented here as the first structured sound profile layered on the RWIF container, with build, validate, inspect, diff, normalize, export, import, render, and batch operations
- `MRWIF`, `TRWIF`, and future companions: not implemented here today, but documented as follow-on design targets in [docs/MRWIF.md](docs/MRWIF.md), [docs/TRWIF.md](docs/TRWIF.md), and [docs/VISION.md](docs/VISION.md)

In that framing, `rwif-builder` is the first practical authoring environment for the format family, even though only the RWIF and ARWIF tracks are operational today.
