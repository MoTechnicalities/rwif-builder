# rwif-builder v0.1.21

Feature release extending ARWIF scene continuity and introducing the first real VRWIF review surface.

## What Changed

- adds ordered per-state `trajectory` keyframes to strict ARWIF authoring so source motion can be captured as `{ offset_seconds, position }` sequences and preserved through build, import, export, inspect, diff, and batch-review flows
- extends ARWIF with scene-bridge metadata via top-level `reference_frame` plus per-state `source_id` and `source_groups`, making cross-scene identity and grouping explicit for healthier ARWIF to VRWIF transitions
- introduces the initial VRWIF source-spec validation surface with strict checks for scene identity, reference frames, object identity and grouping, object trajectories, camera intent, and lighting intent
- adds `rwif vrwif-inspect` and `rwif vrwif-diff` so individual VRWIF scene specs can be summarized and compared without any build or render layer
- adds `rwif vrwif-batch-validate-spec`, `rwif vrwif-batch-inspect`, and `rwif vrwif-batch-diff` so multiple VRWIF specs can be reviewed as reusable aggregate reports rather than one-off terminal output
- expands the test suite, examples, README, and realm documentation so the new ARWIF bridge semantics and the partial-but-real VRWIF implementation are documented against executable behavior

## Scope

This release does two related things. On the ARWIF side, it strengthens scene continuity by carrying trajectories and stable source identity through the existing strict authoring and review path. On the VRWIF side, it turns a prose-only realm into a working source-spec review surface with validation, inspection, diff, and batch review workflows. The scope remains deliberately conservative: VRWIF now has a real schema and review contract, but still does not claim build, artifact, or render semantics.