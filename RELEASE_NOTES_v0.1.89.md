# Release Notes v0.1.89

## Summary
- added source-group roster deltas to ARWIF diff and batch analysis
- documented and regression-tested the narrower source-group count review signal

## Details
- `arwif-diff` now reports `source_groups_count_delta` alongside `source_groups_changed`
- `arwif-batch-diff-analyze` now aggregates recurring source-group roster changes through `pairs_with_source_groups_count_delta` and `total_source_groups_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`