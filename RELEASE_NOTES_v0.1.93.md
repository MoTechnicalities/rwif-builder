# Release Notes v0.1.93

## Summary
- added speaker-channel roster deltas to ARWIF diff and batch analysis
- documented and regression-tested the narrower speaker-channel count review signal

## Details
- `arwif-diff` now reports `speaker_channels_count_delta` alongside `speaker_channels_changed`
- `arwif-batch-diff-analyze` now aggregates recurring speaker-channel roster changes through `pairs_with_speaker_channels_count_delta` and `total_speaker_channels_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`