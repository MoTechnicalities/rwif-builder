# rwif-builder v0.1.6

Feature release adding ARWIF-native diffing on top of the inspection workflow.

## What Changed

- adds `rwif arwif-diff` to compare two ARWIF artifacts in playback and oscillator-bank terms
- reports top-level playback metadata changes such as sample-rate and normalization differences
- reports state-count and oscillator-count deltas together with per-state oscillator changes keyed by label or fallback index
- extends the ARWIF integration suite to cover build, inspect, diff, validate, and render workflows
- updates the README, CLI reference, and example guide to document ARWIF diffing

## Scope

This release extends rwif-builder from ARWIF inspection into ARWIF comparison. ARWIF artifacts can now be built, inspected semantically, diffed in ARWIF-native terms, validated, and rendered from one CLI surface.