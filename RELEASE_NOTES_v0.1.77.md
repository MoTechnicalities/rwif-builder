# Release Notes v0.1.77

## Summary
- added direct object-count drift to VRWIF diff output
- carried object-count aggregation through VRWIF batch diff analysis
- documented and regression-tested the new scene-composition review signal

## Details
- `vrwif-diff` now reports `object_count_delta`
- `vrwif-batch-diff-analyze` now aggregates recurring object-count changes through `pairs_with_object_count_delta` and `total_object_count_delta`
- scene composition changes no longer require callers to infer count deltas indirectly from added and removed object lists

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`