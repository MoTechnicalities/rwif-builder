# Release Notes v0.1.100

## Summary
- introduced the first operational MRWIF surface with source-spec validation, inspection, and diff
- added CLI access, focused regression coverage, and docs for multimodal correspondence review

## Details
- added a new `mrwif` package with validation, inspect, and diff modules for explicit multimodal correspondence specs
- added `mrwif-validate-spec`, `mrwif-inspect`, and `mrwif-diff` to the CLI
- defined the initial MRWIF document shape around `linked_artifacts`, `intent_mappings`, `interpretation_records`, and `revision_traces`
- documented MRWIF as an initial operational bridge realm instead of a draft-only target

## Validation
- added focused regression coverage in `tests/test_mrwif.py`
- validated the release payload with `PYTHONPATH=src /home/mogir/Desktop/Big_AI_Brain/.venv/bin/python -m unittest tests.test_vrwif tests.test_arwif tests.test_mrwif`