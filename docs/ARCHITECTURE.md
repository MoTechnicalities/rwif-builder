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

Only `cli` and `config` contain operational code in the scaffold.
The remaining packages are intentionally present now so the public shape of the project is fixed before deeper implementation work starts.
