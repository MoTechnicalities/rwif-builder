# rwif-builder v0.1.19

Feature release expanding ARWIF batch reporting and review workflows.

## What Changed

- adds `rwif arwif-batch-inspect` so multiple strict ARWIF artifacts can be inspected in one pass with the same aggregate reporting model used across the batch surface
- extends `rwif arwif-batch-build`, `rwif arwif-batch-import`, `rwif arwif-batch-export`, `rwif arwif-batch-normalize`, `rwif arwif-batch-render`, `rwif arwif-batch-validate-spec`, `rwif arwif-batch-validate`, and `rwif arwif-batch-inspect` with top-level `--output` support for persisted JSON or YAML aggregate reports
- adds `rwif arwif-batch-diff-analyze` to summarize recurring metadata, state, and spatial change patterns from a saved batch diff report without changing the existing pairwise diff contract
- adds `rwif arwif-batch-review` as a one-shot workflow that runs batch diff and recurring-change analysis together for collection-level review
- expands the ARWIF integration suite to cover persisted aggregate batch reports, saved diff analysis, and the combined batch review path end to end
- updates the README, CLI reference, and ARWIF examples so the new batch reporting and review commands are documented as reusable automation artifacts rather than terminal-only summaries

## Scope

This release turns the ARWIF batch tooling into a more coherent review surface. Teams can now persist aggregate reports consistently across the batch command family, analyze saved diff output for recurring patterns, and run a higher-level batch review in one command. The scope remains focused on reportability and review ergonomics rather than new artifact semantics.