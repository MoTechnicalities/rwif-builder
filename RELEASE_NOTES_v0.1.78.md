# Release Notes v0.1.78

## Summary
- added object-id churn to VRWIF diff output
- carried object-id aggregation through VRWIF batch diff analysis
- documented and regression-tested the object-side identity mirror of the existing lighting-id signal

## Details
- `vrwif-diff` now reports `object_ids_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring object-id churn through `object_ids_changed_pairs`
- object identity changes are now tracked explicitly instead of only being inferred from added and removed object lists

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`