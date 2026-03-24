# Release Notes v0.1.95

## Summary
- added appearance-class roster deltas to VRWIF diff and batch analysis
- documented and regression-tested the narrower appearance-class count review signal

## Details
- `vrwif-diff` now reports `appearance_classes_count_delta` alongside `appearance_classes_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring appearance-class roster changes through `pairs_with_appearance_classes_count_delta` and `total_appearance_classes_count_delta`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`