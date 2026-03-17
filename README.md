# rwif-builder

Build portable `.rwif` semantic-memory artifacts from local content.

`rwif-builder` is the companion project to the semantic-memory MCP server. The server exposes RWIF-backed stores for retrieval and governed writes. This repo focuses on the authoring side: ingesting source material, normalizing it, chunking it deterministically, and packaging it into validated `.rwif` artifacts that are easy to inspect, diff, and ship.

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

---

## Related Project

For RWIF-backed semantic memory server and federated retrieval, see the companion repo:

[Semantic Memory MCP Server](https://github.com/your-org/semantic-memory-mcp-server)
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
```

The current implementation supports `init`, `build`, `validate`, `inspect`, `stats`, `diff`, and `patch` for Markdown and text corpora.

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

## Roadmap

1. Make `build` and `validate` real end-to-end flows.
2. Add deterministic manifest generation and artifact diffs.
3. Add incremental patch planning from source-hash changes.
4. Expand format docs with concrete binary-layout and indexing notes.

## Release Ops

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [TAG_PREPARATION.md](TAG_PREPARATION.md)
- [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md)
