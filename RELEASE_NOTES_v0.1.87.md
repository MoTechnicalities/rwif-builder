# Release Notes v0.1.87

## Summary
- added speaker-role diversity drift to ARWIF diff and batch analysis
- documented and regression-tested the narrower speaker-role count review signal

## Details
- `arwif-diff` now reports `speaker_roles_count_delta` alongside `speaker_roles_changed`
- `arwif-batch-diff-analyze` now aggregates recurring speaker-role diversity changes through `pairs_with_speaker_roles_count_delta` and `total_speaker_roles_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`