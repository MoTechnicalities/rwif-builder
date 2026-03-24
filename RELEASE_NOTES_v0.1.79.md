# Release Notes v0.1.79

## Summary
- added camera trajectory-presence drift to VRWIF diff output
- carried camera trajectory-presence aggregation through VRWIF batch diff analysis
- documented and regression-tested the narrower camera static-to-moving transition signal

## Details
- `vrwif-diff` now reports `camera_has_trajectory_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring trajectory-presence transitions through `camera_has_trajectory_changed_pairs`
- this complements the broader `camera_trajectory_changed` signal by distinguishing static-to-moving and moving-to-static camera transitions from ordinary keyframe edits

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`