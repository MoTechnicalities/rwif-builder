# RWIF Deep Dive

## The Manifesto

This repository is the forge for Analog Wave Memory.

RWIF stands for Resonant Wave Information Format.

The server repository is the engine: it serves RWIF-backed memory over MCP and routes retrieval.
This repository is where raw text is transformed into the compact artifact that engine actually runs on.

That means this is the right place to explain the storage model itself.

## The Problem With Raster RAG

Most retrieval pipelines in industry still default to what you can fairly call rasterized memory:

- encode every chunk into a dense vector
- keep the full dense grid around
- load or serve it from a vector database
- pay the memory and infrastructure cost forever

That workflow is convenient because it is familiar, not because it is elegant.

Dense storage treats every dimension as equally persistent infrastructure. The result is a retrieval stack that is often bottlenecked by storage footprint, service overhead, and hardware locality rather than by the actual semantic signal that matters.

RWIF starts from a different premise: retrieval state should be compressible into a portable artifact.

## The Math

The central mathematical move is simple:

1. Start with an activation vector for a chunk of text.
2. Estimate a background vector across the corpus.
3. Subtract that background so the stored signal emphasizes what is distinctive.
4. Apply the Discrete Cosine Transform (DCT) to move from the original coordinate basis into a frequency basis.
5. Keep only the strongest coefficients.
6. Store those coefficients as sparse atomic wave units instead of keeping the entire dense vector.

In code terms, the core representation is a list of frequency-amplitude pairs.

If the dense activation is a vector $x \in \mathbb{R}^n$ and the background estimate is $b$, RWIF stores a sparse approximation of:

$$
c = \mathrm{DCT}(x - b)
$$

Instead of keeping all $n$ coefficients, the builder keeps only the top $k$ coefficients by magnitude, where $k$ is typically much smaller than $n$.

So the stored state is not the full dense grid. It is the dominant spectral structure of the thought.

In practical terms, the familiar choice is “top 128 coefficients,” because that is a reasonable operating point between fidelity and compactness. It is not magic. It is a compression choice with a clear interpretation: preserve the strongest semantic frequencies and discard the lower-energy tail.

## Why Top Coefficients Matter

A dense vector stores every coordinate whether that coordinate carries meaningful differentiating signal or not.

RWIF assumes that much of the useful semantic structure can be represented by a relatively small number of strong frequency components. The builder therefore stores a sparse wave description:

- frequency index
- amplitude

That is the heart of the format.

The artifact does not need to remember every single dense coordinate to remain useful for retrieval. It needs to preserve the topology of the semantic signal strongly enough that interference scoring still surfaces the right neighbors.

## The Vector Graphic Analogy

This is the right mental model.

Raster graphics store a dense field of pixels.
Vector graphics store a compact description of shape.

Traditional vector-database storage is closer to raster memory: keep the full dense field.
RWIF aims to behave more like vector memory: keep a compact structural description of the thought.

That does not mean every possible workload prefers RWIF. It means the format is optimized around a different tradeoff:

- fewer always-resident numbers
- more portable retrieval state
- stronger emphasis on compact semantic shape over raw dense persistence

## The Hardware Reality

This is where the approach becomes operationally interesting.

Local AI development is increasingly constrained by VRAM and memory bandwidth. Developers can run a model, or hold a large dense retrieval index, or both badly. That tension is part of what makes always-on dense vector infrastructure expensive on local and edge hardware.

RWIF changes the pressure profile.

The heavy transformer work happens during build time, not continuously at retrieval-serving time. After activations are generated and transformed, the stored artifact is a compact binary-plus-metadata package.

That means:

- the model can be used offline to forge the artifact
- the shipped store is smaller than the dense activation matrix it came from
- retrieval no longer requires hosting the entire original dense corpus representation as a service-layer dependency

The point is not that hardware stops mattering. The point is that RWIF moves the expensive step to artifact creation and reduces the footprint of what must remain deployed afterwards.

That is why this approach speaks directly to local AI developers. The bottleneck is not just model quality. It is the cost of keeping semantic infrastructure alive once the model has done its job.

## The On-Disk Contract

RWIF currently uses an activation-core binary envelope with two parts:

1. a compact JSON header
2. a packed sequence of atomic wave units

The JSON header carries:

- library metadata
- per-state metadata
- vector length
- top-k setting
- offsets and counts for wave units

The packed binary region carries the actual sparse coefficient data as `(frequency_index, amplitude)` pairs.

This is why the format is simultaneously inspectable and efficient:

- human-readable structural metadata in the header
- compact numeric payload in the body

For semantic memory artifacts, the builder also stores:

- `format = rwif_semantic_memory`
- `semantic_memory_version = 1`
- `rwif_builder_manifest`
- semantic memory payloads under the memory-store metadata chain

## Why Manifest-Aware Builds Matter

The builder is not just a serializer.
It is the provenance layer for the format.

The manifest records:

- source paths
- source hashes
- source types
- chunk counts
- vector length
- embedding backend and model
- chunking policy
- builder version

That matters because a storage format only becomes trustworthy when you can answer:

- where did this store come from?
- what content was packed into it?
- what embedding path produced it?
- what changed between this artifact and the previous one?

This is why `diff` and `patch` belong in the builder repo. Artifact evolution is part of the format story.

## Why This Can Feel Better Than A Database

The strongest argument is not ideology. It is workflow.

If a developer can:

- point the builder at a docs directory
- generate a validated artifact
- inspect it locally
- diff it against the previous version
- ship it with the application

then semantic retrieval starts to look less like database administration and more like artifact production.

That is the leverage.

## What This Repo Must Continue To Explain

As the implementation grows, this document should deepen in these directions:

- exact chunk identity rules
- reconstruction and interference scoring details
- background estimation strategy
- how top-k compression affects fidelity
- when hashing is sufficient and when transformer activations are worth the build cost
- where RWIF is a strong fit and where a dense vector service is still the better tradeoff

## Precision Over Mythology

This repo should be ambitious but not mystical.

The right claim is not “RWIF kills every vector database.”
The right claim is narrower and stronger:

RWIF offers a compact, manifest-aware, file-backed way to store semantic retrieval state by preserving the dominant spectral structure of activations rather than shipping the full dense grid.

That is enough to be novel. It does not need hype on top of it.
