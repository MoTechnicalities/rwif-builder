# Release Notes v0.1.73

## Summary
- added camera-trajectory average-acceleration summaries to VRWIF inspect output
- carried camera-trajectory average-acceleration drift through VRWIF diff and batch diff analysis
- documented and regression-tested the camera-side mirror of v0.1.72

## Details
- `vrwif-inspect` scene summaries now include `camera_trajectory_average_acceleration`
- average acceleration is derived from adjacent positive-duration camera segment-speed changes using midpoint timing, and returns `0.0` when a present camera trajectory lacks enough valid segments
- `vrwif-diff` now reports `camera_trajectory_average_acceleration_delta`
- `vrwif-batch-diff-analyze` now aggregates recurring camera-trajectory average-acceleration drift across compared pairs

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`