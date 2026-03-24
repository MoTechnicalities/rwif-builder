# Release Notes v0.1.81

## Summary
- added camera-presence drift to VRWIF diff output
- added speaker-id drift to ARWIF diff output
- carried both narrower identity and presence signals through batch diff analysis and regression coverage

## Details
- `vrwif-diff` now reports `camera_present_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring camera add and remove transitions through `camera_present_changed_pairs`
- `arwif-diff` now reports `speaker_ids_changed` alongside the existing broader `speakers_changed` flag
- `arwif-batch-diff-analyze` now aggregates recurring speaker identity churn through `speaker_ids_changed_pairs`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py` and `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`