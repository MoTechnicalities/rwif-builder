# rwif-builder v0.1.5

Feature release adding ARWIF-native inspection to the builder surface.

## What Changed

- adds `rwif arwif-inspect` to summarize ARWIF playback metadata and oscillator-bank contents
- reports strict or legacy validation status together with state-level frequency and amplitude summaries
- extends the ARWIF integration suite to cover build, inspect, validate, and render as one workflow
- updates the README, CLI reference, and example guide to document the new inspection step

## Scope

This release rounds out the ARWIF authoring toolchain in rwif-builder. ARWIF artifacts can now be built, inspected semantically, validated, and rendered from one CLI surface.