# Embedding Backends

## Current Backends

`rwif-builder` currently supports two embedding paths.

### Hashing

The default path is the built-in deterministic hashing provider.

Use it when you want:

- zero external model downloads
- deterministic local builds
- a frictionless first run for documentation corpora
- a baseline artifact pipeline without GPU requirements

Example:

```yaml
embedding:
  provider: hashing
  model: rwif-hash-v1
  vector_length: 256
```

### Transformers

The second path uses a Hugging Face transformer model to generate activations before DCT packing.

Use it when you want:

- higher-fidelity semantic activations than the hashing baseline
- compatibility with public sentence-transformer style models
- a closer match to the intended Analog Wave Memory pipeline story

Example:

```yaml
embedding:
  provider: transformers
  model: sentence-transformers/all-MiniLM-L6-v2
  pooling: mean
  max_length: 256
```

You can also use `sentence-transformers` as the provider alias.

See [rwif.transformers.yaml.example](../rwif.transformers.yaml.example) for a full example config.

## Installation

The hashing backend works with the base install.

The transformers backend requires additional packages:

```bash
pip install -e .[transformers]
```

## Important Tradeoff

The transformer backend still produces a compact RWIF artifact. The model is used at build time, not required as a constantly running retrieval database tier.
