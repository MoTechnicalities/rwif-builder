# ARWIF Container Decision

## Decision

Keep ARWIF RWIF-compatible for `v0.1`.

## Why

The current ARWIF concept is still exploring semantics, not container pressure.

Keeping the RWIF envelope for now has concrete advantages:

- existing loaders can already parse the binary framing
- the files stay inspectable with familiar tooling
- experimentation can focus on audio semantics rather than reinventing header and packing logic
- the migration cost stays low while the format is still unstable

## What This Means

ARWIF should be treated as an audio profile over the RWIF activation-core envelope, not yet as a wholly separate container.

The compatibility boundary is:

- same magic bytes and packing rules
- different interpretation of the integer unit field
- different validation and playback semantics

## When To Split Later

ARWIF should move to a distinct container only if the audio requirements materially outgrow the RWIF envelope. Clear triggers would be:

- sample-accurate event timing
- multichannel block layouts
- envelopes or automation curves that need dedicated compact encoding
- non-integer or very high-resolution frequency encoding
- streaming-oriented chunk structure
- audio-specific compression that no longer resembles RWIF state packing

## Practical Recommendation

For the next iteration:

1. keep `RWIFACT1`
2. define ARWIF-specific metadata clearly
3. ship a validator and renderer
4. collect real usage pressure before changing the container

That gives ARWIF the fastest path from experiment to testable format while preserving an escape hatch if audio needs later demand a dedicated binary layout.