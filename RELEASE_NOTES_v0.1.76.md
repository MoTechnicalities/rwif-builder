# Release Notes v0.1.76

## Summary
- added camera-trajectory point-count drift to VRWIF diff output
- carried camera-trajectory point-count aggregation through VRWIF batch diff analysis
- documented and regression-tested the camera-side mirror of the existing object trajectory point-count signal

## Details
- `vrwif-diff` now reports `camera_trajectory_point_count_delta`
- `vrwif-batch-diff-analyze` now aggregates recurring camera trajectory keyframe-count changes through `pairs_with_camera_trajectory_point_delta` and `total_camera_trajectory_point_delta`
- inspect output already exposed `camera_trajectory_point_count`; this slice completes the review path so camera keyframe-density drift is visible in pairwise and batch analysis

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif`