# rwif-builder v0.1.7

Feature release adding ARWIF export and import as a round-trip workflow.

## What Changed

- adds `rwif arwif-export` to emit YAML or JSON source specs from ARWIF artifacts
- adds `rwif arwif-import` as a first-class import command over the strict ARWIF builder flow
- preserves playback metadata, state ordering, and oscillator-bank contents across strict export and import round trips
- extends the ARWIF integration suite with a full export -> import -> diff round-trip test
- updates the README, CLI reference, ARWIF spec, and examples guide to document round-trip usage

## Scope

This release turns the ARWIF workflow into a full authoring round trip. ARWIF artifacts can now be built, exported to source specs, imported back into artifacts, inspected, diffed, validated, and rendered from one CLI surface.