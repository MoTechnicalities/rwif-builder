# Release Notes v0.1.72

## Summary
- added object-trajectory average-acceleration summaries to VRWIF inspect output
- carried object-trajectory average-acceleration drift through VRWIF diff and batch diff analysis
- documented and regression-tested the new review surface

## Details
- `vrwif-inspect` scene summaries now include `object_trajectory_average_acceleration_total` plus `object_trajectory_average_acceleration_range`
- average acceleration is derived from adjacent positive-duration segment-speed changes using midpoint timing, and returns `0.0` when a present trajectory lacks enough valid segments
- `vrwif-diff` now reports `object_trajectory_average_acceleration_total_delta` and `object_trajectory_average_acceleration_range_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring object-trajectory average-acceleration drift across compared pairs

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`