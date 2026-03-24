# Release Notes v0.1.86

## Summary
- added listening-zone and speaker-coverage intent-diversity deltas to ARWIF diff and batch analysis
- documented and regression-tested the narrower intent-count review signals

## Details
- `arwif-diff` now reports `listening_zone_intents_count_delta` alongside `listening_zone_intents_changed`
- `arwif-diff` now reports `speaker_coverage_intents_count_delta` alongside `speaker_coverage_intents_changed`
- `arwif-batch-diff-analyze` now aggregates recurring intent-diversity changes through `pairs_with_listening_zone_intents_count_delta`, `total_listening_zone_intents_count_delta`, `pairs_with_speaker_coverage_intents_count_delta`, and `total_speaker_coverage_intents_count_delta`

## Validation
- targeted regression coverage added in `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`