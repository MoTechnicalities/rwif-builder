# Release Notes v0.1.85

## Summary
- added max-frequency drift to ARWIF diff and batch analysis
- documented and regression-tested the narrower spectral-bandwidth review signal

## Details
- `arwif-diff` now reports `max_frequency_hz_delta` alongside `state_count_delta` and `oscillator_count_delta`
- `arwif-batch-diff` now treats non-zero `max_frequency_hz_delta` as a pair change when structural counts are otherwise unchanged
- `arwif-batch-diff-analyze` now aggregates recurring spectral-bandwidth changes through `pairs_with_max_frequency_hz_delta` and `total_max_frequency_hz_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`