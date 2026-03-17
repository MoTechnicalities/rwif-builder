# Tag Preparation

## Versioning Rule

Use tags for meaningful public snapshots of the builder pipeline and format documentation.

Suggested early tags:

- `v0.1.0`: first public builder release with Markdown/text pipeline, RWIF manifest, validation, diff, patch, and a verified transformer-backed build path
- `v0.1.1`: packaging or documentation cleanup only

## Annotated Tag Flow

```bash
git checkout main
git pull --ff-only origin main
git tag -a v0.1.0 -m "rwif-builder v0.1.0

First public release of the RWIF forge pipeline with Markdown/text ingestion, real RWIF artifact generation, manifest validation, artifact diffing, patch support, and a verified transformer-backed build path."
git show v0.1.0 --stat
git push origin v0.1.0
```

## Release Notes Inputs

Use these inputs when drafting a GitHub Release:

- README product framing
- RWIF deep dive updates
- new CLI capabilities
- validation and diff/patch support
- optional transformer backend path
- verified transformer build using `sentence-transformers/all-MiniLM-L6-v2`
