# Release Notes v0.1.94

## Summary
- added light-id roster deltas to VRWIF diff and batch analysis
- documented and regression-tested the narrower light-id count review signal

## Details
- `vrwif-diff` now reports `light_ids_count_delta` alongside `light_ids_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring light-id roster changes through `pairs_with_light_ids_count_delta` and `total_light_ids_count_delta`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`