# Release Notes v0.1.80

## Summary
- added camera-id drift to VRWIF diff output
- carried camera-id aggregation through VRWIF batch diff analysis
- documented and regression-tested camera identity churn as a narrower signal than the existing broad camera change flag

## Details
- `vrwif-diff` now reports `camera_id_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring camera identity churn through `camera_id_changed_pairs`
- this complements `camera_changed` by separating camera identity swaps from position, framing, and trajectory edits

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`