# rwif-builder v0.1.25

Feature release adding VRWIF batch normalization analysis.

## What Changed

- adds `rwif vrwif-batch-normalize-analyze <report.{json|yaml}>` so teams can analyze a saved `vrwif-batch-normalize` report instead of manually inspecting many per-spec normalization outputs
- summarizes recurring normalization actions across a batch, including canonicalization behaviors such as strict version insertion, alias resolution, unknown-field cleanup, and other normalization-summary counters already emitted by the normalizer
- summarizes recurring source and normalized warning or error messages across the collection and ranks the specs with the highest normalization burden for faster cleanup review
- derives normalization assumption burden directly from the saved batch report, so the analysis remains useful even when `vrwif-batch-normalize` was run without `--assumptions-dir`
- extends the VRWIF integration suite and refreshes the README plus VRWIF guide so the new report-analysis workflow is documented alongside the existing normalize, assumptions, diff-analysis, and review surfaces

## Scope

This release stays inside the current VRWIF source-authoring and review realm. It does not add artifact build or render behavior. Instead, it closes a collection-scale auditability gap by making normalization reports themselves reviewable as a first-class analysis surface, so recurring cleanup patterns across many scene specs can be identified without opening each normalized file or assumptions manifest individually.
