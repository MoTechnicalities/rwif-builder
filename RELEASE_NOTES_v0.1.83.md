# Release Notes v0.1.83

## Summary
- added geometry-reference presence drift to ARWIF diff and batch analysis
- documented and regression-tested the narrower geometry-reference add and remove transition

## Details
- `arwif-diff` now reports `geometry_reference_present_changed` alongside the existing broader `geometry_reference_changed` flag
- `arwif-batch-diff-analyze` now aggregates recurring geometry-reference add and remove transitions through `geometry_reference_present_changed_pairs`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`