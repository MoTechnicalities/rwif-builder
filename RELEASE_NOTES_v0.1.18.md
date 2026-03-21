# rwif-builder v0.1.18

Feature release adding Level 1 spatial ARWIF rendering and spatial review summaries.

## What Changed

- teaches `rwif arwif-render` to emit multichannel 16-bit PCM WAV when a strict ARWIF artifact declares a supported `channel_layout`
- applies per-state `channel_gains` across the declared channel layout during reference rendering while preserving the existing mono path when no layout is present
- extends `rwif arwif-inspect` with a compact `spatial_summary` covering the declared layout, active channels, and the number of states carrying explicit channel gains
- extends `rwif arwif-diff` with left and right spatial summaries plus a small `spatial_changes` block so channel-aware revisions are visible without reading the full metadata diff
- fixes the ARWIF channel-aware round-trip integration test so it is actually discovered by `unittest`, and expands the suite to validate the new render and summary behavior end to end
- updates the README, CLI reference, and ARWIF mini-spec to document the new Level 1 spatial rendering and review surface

## Scope

This release turns the first spatial ARWIF slice into a real output and review path. Strict ARWIF artifacts can now carry channel-aware intent from source spec to artifact, render that intent into multichannel WAV for supported layouts, and surface the resulting spatial structure through inspect and diff workflows. The scope remains intentionally narrow: this is channel-aware routing, not object-based or room-aware spatial audio.