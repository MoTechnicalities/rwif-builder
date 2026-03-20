# rwif-builder

Build portable `.rwif` semantic-memory artifacts from local content.

`rwif-builder` is the companion project to the semantic-memory MCP server. The server exposes RWIF-backed stores for retrieval and governed writes. RWIF stands for Resonant Wave Information Format. This repo focuses on the authoring side: ingesting source material, normalizing it, chunking it deterministically, and packaging it into validated `.rwif` artifacts that are easy to inspect, diff, and ship.

## Why This Repo Exists

A file-backed semantic store only becomes practical when authoring is simpler than standing up a service-heavy indexing stack.

This project exists to make `.rwif` creation feel operationally lighter than a database workflow:

- point the tool at local content
- build a deterministic artifact
- validate what was produced
- inspect the resulting store before shipping it
- rebuild cleanly when the source corpus changes

## Product Direction

`rwif-builder` is intentionally narrow.

It is not another retrieval server.
It is not a hosted indexing platform.
It is not a general-purpose ETL framework.

It is a build pipeline and inspection toolkit for RWIF artifacts.

## MVP Scope

Version `0.1.0` is aimed at these workflows:

- ingest local Markdown, text, and directory trees first
- normalize records into one internal schema
- chunk content deterministically
- write a portable `.rwif` artifact
- emit a reproducible build manifest
- validate store structure and metadata
- inspect summary stats and record samples
- compare two artifacts with a human-readable diff
- rebuild deterministically from a base artifact with `patch`

Deferred until later:

- GUI tooling
- hosted services
- collaborative authoring
- remote crawlers and connectors
- advanced in-place semantic editing

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
rwif init --template docs
rwif build --config rwif.yaml --output dist/docs.rwif
rwif validate dist/docs.rwif
rwif inspect dist/docs.rwif --json
```

## CLI Surface

```text
rwif init
rwif build
rwif validate
rwif inspect
rwif stats
rwif diff
rwif patch
rwif arwif-batch-build
rwif arwif-batch-render
rwif arwif-batch-normalize
rwif arwif-build
rwif arwif-diff
rwif arwif-export
rwif arwif-import
rwif arwif-inspect
rwif arwif-normalize
rwif arwif-validate-spec
rwif arwif-validate
rwif arwif-render
```

The current implementation supports `init`, `build`, `validate`, `inspect`, `stats`, `diff`, `patch`, `arwif-batch-build`, `arwif-batch-render`, `arwif-batch-normalize`, `arwif-build`, `arwif-diff`, `arwif-export`, `arwif-import`, `arwif-inspect`, `arwif-normalize`, `arwif-validate-spec`, `arwif-validate`, and `arwif-render`.

## Configuration

A typical project config looks like this:

```yaml
project: customer-docs
version: 0.1.0

sources:
  - path: ./docs
    include: ["**/*.md", "**/*.txt"]

chunking:
  strategy: markdown_sections
  max_tokens: 400
  overlap_tokens: 40

embedding:
  provider: hashing
  model: rwif-hash-v1
  vector_length: 256

top_k_waves: 96

output:
  path: ./dist/customer-docs.rwif

metadata:
  domain: support
  language: en
```

See [docs/MVP.md](docs/MVP.md) for the scope contract and [docs/RWIF_DEEP_DIVE.md](docs/RWIF_DEEP_DIVE.md) for the storage-model documentation.

See [docs/EMBEDDING_BACKENDS.md](docs/EMBEDDING_BACKENDS.md) for the hashing and transformer activation paths.

See [docs/ARWIF_v0.1.md](docs/ARWIF_v0.1.md) for the first ARWIF audio profile draft and [docs/ARWIF_CONTAINER_DECISION.md](docs/ARWIF_CONTAINER_DECISION.md) for the container-strategy analysis.

An end-to-end ARWIF authoring path is now available:

```bash
rwif arwif-normalize examples/arwif/CEG_legacy.arwif --spec dist/CEG_legacy.normalized.yaml --output dist/CEG_legacy.normalized.arwif --report dist/CEG_legacy.normalized.report.json --assumptions dist/CEG_legacy.normalized.assumptions.json --json
rwif arwif-batch-build first.yaml second.yaml --output-dir dist/built_arwif --json
rwif arwif-batch-normalize old-a.arwif old-b.arwif --spec-dir dist/normalized_specs --output-dir dist/normalized_artifacts --report-dir dist/normalization_reports --assumptions-dir dist/assumptions --json
rwif arwif-batch-render dist/a.arwif dist/b.arwif --output-dir dist/rendered_wav --json
rwif arwif-validate-spec examples/arwif/CEG_v0_1.yaml --json
rwif arwif-build --spec examples/arwif/CEG_v0_1.yaml --output dist/CEG_v0_1.arwif --json
rwif arwif-export dist/CEG_v0_1.arwif dist/CEG_v0_1.export.yaml --json
rwif arwif-import --spec dist/CEG_v0_1.export.yaml --output dist/CEG_v0_1.roundtrip.arwif --json
rwif arwif-inspect dist/CEG_v0_1.arwif --json
rwif arwif-diff dist/CEG_v0_1.arwif examples/arwif/CEG_v0_1.arwif --json
rwif arwif-validate dist/CEG_v0_1.arwif --json
rwif arwif-render dist/CEG_v0_1.arwif dist/CEG_v0_1.wav --json
```

`rwif arwif-build` and `rwif arwif-import` now run the same strict source-spec validation used by `rwif arwif-validate-spec`, so malformed YAML or JSON specs fail with field-level diagnostics before any artifact is written.

`rwif arwif-normalize` upgrades legacy or loosely specified ARWIF artifacts into a strict ARWIF `v0.1` source spec, can optionally rebuild a strict artifact from that normalized spec, can emit a full machine-readable normalization report, and can emit a smaller assumptions manifest that isolates injected defaults, preserved metadata, and validation warnings as `.json`, `.yaml`, or `.yml` based on the output filename.

`rwif arwif-batch-build` scales the strict ARWIF source-spec build flow across multiple YAML or JSON specs, writing artifacts into a target directory and returning aggregate build counts plus per-spec validation results.

`rwif arwif-batch-normalize` scales that same migration flow across multiple artifacts in one command, writing normalized specs into a target directory and optionally collecting rebuilt artifacts, reports, and assumptions manifests into sibling directories with an aggregated JSON result payload.

`rwif arwif-batch-render` scales ARWIF WAV export across multiple artifacts in one command, writing `.wav` files into a target directory while returning collection-level render counts and total rendered duration.

## On-Disk Contract

The builder writes a real RWIF semantic-memory artifact, not a sidecar export format.

- RWIF activation-core binary envelope
- JSON header with library metadata and per-state metadata
- `format = rwif_semantic_memory`
- `semantic_memory_version = 1`
- builder manifest stored in `rwif_builder_manifest`

That keeps artifacts compatible with the server while letting the builder own reproducibility and provenance metadata.

## Transformer Path

The default builder experience uses the deterministic hashing backend so anyone can build a valid RWIF artifact immediately.

For public users who want a more faithful transformer activation path before DCT packing, install the optional dependencies:

```bash
pip install -e .[transformers]
```

Then switch the config to a transformer-backed model:

```yaml
embedding:
  provider: transformers
  model: sentence-transformers/all-MiniLM-L6-v2
  pooling: mean
  max_length: 256
```

## Relationship To The Server Repo

- `semantic-memory-mcp-server`: serve, route, and govern RWIF-backed memory over MCP
- `rwif-builder`: create, validate, inspect, and update RWIF artifacts

That split keeps runtime concerns separate from authoring and keeps the storage format documented where it is produced.

## Related Project

For RWIF-backed semantic memory server and federated retrieval, see the companion repo:

[Semantic Memory MCP Server](https://github.com/MoTechnicalities/semantic-memory-mcp-server)

## Roadmap

1. Make `build` and `validate` real end-to-end flows.
2. Add deterministic manifest generation and artifact diffs.
3. Add incremental patch planning from source-hash changes.
4. Expand format docs with concrete binary-layout and indexing notes.

## Release Ops

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [TAG_PREPARATION.md](TAG_PREPARATION.md)
- [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md)
- [RELEASE_NOTES_v0.1.11.md](RELEASE_NOTES_v0.1.11.md)
- [RELEASE_NOTES_v0.1.12.md](RELEASE_NOTES_v0.1.12.md)
- [RELEASE_NOTES_v0.1.13.md](RELEASE_NOTES_v0.1.13.md)
- [RELEASE_NOTES_v0.1.14.md](RELEASE_NOTES_v0.1.14.md)
