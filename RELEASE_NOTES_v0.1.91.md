# Release Notes v0.1.91

## Summary
- added object-group roster deltas to VRWIF diff and batch analysis
- documented and regression-tested the narrower object-group count review signal

## Details
- `vrwif-diff` now reports `object_groups_count_delta` alongside `object_groups_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring object-group roster changes through `pairs_with_object_groups_count_delta` and `total_object_groups_count_delta`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`