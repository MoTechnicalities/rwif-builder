# Release Notes v0.1.96

## Summary
- added light-color roster deltas to VRWIF diff and batch analysis
- documented and regression-tested the narrower light-color count review signal

## Details
- `vrwif-diff` now reports `light_colors_count_delta` alongside `light_colors_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring light-color roster changes through `pairs_with_light_colors_count_delta` and `total_light_colors_count_delta`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`