# Release Notes v0.1.84

## Summary
- added surface-treatment, reflection-policy, and renderer-adaptation presence drift to ARWIF diff and batch analysis
- documented and regression-tested the narrower room-context add and remove transitions

## Details
- `arwif-diff` now reports `surface_treatment_present_changed` alongside `surface_treatment_changed`
- `arwif-diff` now reports `reflection_policy_present_changed` alongside `reflection_policy_changed`
- `arwif-diff` now reports `renderer_adaptation_present_changed` alongside `renderer_adaptation_changed`
- `arwif-batch-diff-analyze` now aggregates recurring room-context add and remove transitions through `surface_treatment_present_changed_pairs`, `reflection_policy_present_changed_pairs`, and `renderer_adaptation_present_changed_pairs`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`