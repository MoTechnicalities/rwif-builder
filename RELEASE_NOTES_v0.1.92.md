# Release Notes v0.1.92

## Summary
- added listening-zone roster deltas to ARWIF diff and batch analysis
- documented and regression-tested the narrower listening-zone ID count review signal

## Details
- `arwif-diff` now reports `listening_zone_ids_count_delta` alongside `listening_zones_changed`
- `arwif-batch-diff-analyze` now aggregates recurring listening-zone roster changes through `pairs_with_listening_zone_ids_count_delta` and `total_listening_zone_ids_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`