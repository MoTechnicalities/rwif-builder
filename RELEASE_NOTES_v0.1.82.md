# Release Notes v0.1.82

## Summary
- added lighting-presence review signals to VRWIF inspect, diff, and batch analysis
- added room-presence drift to ARWIF diff and batch analysis
- documented and regression-tested the narrower presence transitions in both realms

## Details
- `vrwif-inspect` scene summaries now include `lighting_present`
- `vrwif-diff` now reports `lighting_present_changed`
- `vrwif-batch-diff-analyze` now aggregates recurring lighting add and remove transitions through `lighting_present_changed_pairs`
- `arwif-diff` now reports `room_present_changed` alongside the existing broader `room_changed` flag
- `arwif-batch-diff-analyze` now aggregates recurring room add and remove transitions through `room_present_changed_pairs`

## Validation
- targeted regression coverage added in `tests/test_vrwif.py` and `tests/test_arwif.py`
- intended validation flow remains `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif`