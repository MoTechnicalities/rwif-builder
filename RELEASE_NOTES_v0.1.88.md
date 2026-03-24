# Release Notes v0.1.88

## Summary
- added speaker-id roster deltas to ARWIF diff and batch analysis
- documented and regression-tested the narrower speaker-id count review signal

## Details
- `arwif-diff` now reports `speaker_ids_count_delta` alongside `speaker_ids_changed`
- `arwif-batch-diff-analyze` now aggregates recurring speaker-id roster changes through `pairs_with_speaker_ids_count_delta` and `total_speaker_ids_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`