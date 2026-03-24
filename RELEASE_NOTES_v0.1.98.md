# Release Notes v0.1.98

## Summary
- added object-visibility roster deltas to VRWIF diff and batch analysis
- documented and regression-tested the narrower object-visibility count review signal

## Details
- `vrwif-diff` now reports `object_visibilities_count_delta` alongside `object_visibilities_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring object-visibility roster changes through `pairs_with_object_visibilities_count_delta` and `total_object_visibilities_count_delta`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`