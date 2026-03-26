from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import yaml

from .diff import diff_mrwif_specs
from .validation import validate_mrwif_spec


def batch_validate_mrwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_linked_artifact_count = 0
    total_intent_mapping_count = 0
    total_interpretation_record_count = 0
    total_revision_trace_count = 0

    for spec in specs:
        report = validate_mrwif_spec(Path(spec))
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_linked_artifact_count += int(report.stats.get("linked_artifact_count", 0))
        total_intent_mapping_count += int(report.stats.get("intent_mapping_count", 0))
        total_interpretation_record_count += int(report.stats.get("interpretation_record_count", 0))
        total_revision_trace_count += int(report.stats.get("revision_trace_count", 0))
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_linked_artifact_count": total_linked_artifact_count,
        "total_intent_mapping_count": total_intent_mapping_count,
        "total_interpretation_record_count": total_interpretation_record_count,
        "total_revision_trace_count": total_revision_trace_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate spec output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_inspect_mrwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    from .inspect import inspect_mrwif_spec

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_linked_artifact_count = 0
    total_intent_mapping_count = 0
    total_interpretation_record_count = 0
    total_revision_trace_count = 0
    linked_realms: set[str] = set()
    target_realms: set[str] = set()
    semantic_descriptors: set[str] = set()

    for spec in specs:
        payload = inspect_mrwif_spec(Path(spec))
        if payload.get("is_valid", False):
            valid_count += 1
        else:
            invalid_count += 1

        summary = payload.get("correspondence_summary") if isinstance(payload.get("correspondence_summary"), dict) else {}
        total_linked_artifact_count += int(summary.get("linked_artifact_count", 0))
        total_intent_mapping_count += int(summary.get("intent_mapping_count", 0))
        total_interpretation_record_count += int(summary.get("interpretation_record_count", 0))
        total_revision_trace_count += int(summary.get("revision_trace_count", 0))

        linked_realms.update(
            realm for realm in (summary.get("linked_artifact_realms") or []) if isinstance(realm, str) and realm
        )
        target_realms.update(
            realm for realm in (summary.get("target_realms") or []) if isinstance(realm, str) and realm
        )
        semantic_descriptors.update(
            descriptor for descriptor in (summary.get("semantic_descriptors") or []) if isinstance(descriptor, str) and descriptor
        )
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_linked_artifact_count": total_linked_artifact_count,
        "total_intent_mapping_count": total_intent_mapping_count,
        "total_interpretation_record_count": total_interpretation_record_count,
        "total_revision_trace_count": total_revision_trace_count,
        "linked_realms": sorted(linked_realms),
        "target_realms": sorted(target_realms),
        "semantic_descriptors": sorted(semantic_descriptors),
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch inspect output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_diff_mrwif_specs(
    left_specs: list[str | Path],
    right_specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not left_specs or not right_specs:
        raise ValueError("at least one left and one right spec must be provided")
    if len(left_specs) != len(right_specs):
        raise ValueError("left and right spec collections must have the same length")

    results: list[dict[str, Any]] = []
    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    total_metadata_fields_changed = 0
    total_changed_linked_artifacts = 0
    total_changed_intent_mappings = 0
    total_changed_interpretation_records = 0
    total_changed_revision_traces = 0

    for pair_index, (left_spec, right_spec) in enumerate(zip(left_specs, right_specs, strict=True)):
        payload = diff_mrwif_specs(left_spec, right_spec)
        payload["pair_index"] = pair_index

        summary = payload.get("change_summary") if isinstance(payload.get("change_summary"), dict) else {}
        pair_changed = _infer_pair_changed(payload)
        payload["pair_changed"] = pair_changed

        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not payload.get("left_valid", False) or not payload.get("right_valid", False):
            invalid_pairs += 1

        total_metadata_fields_changed += int(summary.get("metadata_fields_changed", 0))
        total_changed_linked_artifacts += int(summary.get("changed_linked_artifacts", 0))
        total_changed_intent_mappings += int(summary.get("changed_intent_mappings", 0))
        total_changed_interpretation_records += int(summary.get("changed_interpretation_records", 0))
        total_changed_revision_traces += int(summary.get("changed_revision_traces", 0))
        results.append(payload)

    payload = {
        "pairs_compared": len(results),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "is_valid": invalid_pairs == 0,
        "total_metadata_fields_changed": total_metadata_fields_changed,
        "total_changed_linked_artifacts": total_changed_linked_artifacts,
        "total_changed_intent_mappings": total_changed_intent_mappings,
        "total_changed_interpretation_records": total_changed_interpretation_records,
        "total_changed_revision_traces": total_changed_revision_traces,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch diff output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def analyze_batch_diff_report(
    input_path: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    report_path = Path(input_path)
    report_document = _load_auxiliary_document(report_path, label="batch diff analysis input")
    analysis_payload = _analyze_batch_diff_payload(report_document, analysis_input=str(report_path))

    if output is not None:
        analysis_output_path = Path(output)
        report_format = _resolve_auxiliary_format(analysis_output_path, label="batch diff analysis output")
        _write_auxiliary_document(analysis_output_path, analysis_payload, report_format)
        analysis_payload["report_output"] = str(analysis_output_path)
        analysis_payload["report_format"] = report_format

    return analysis_payload


def batch_review_mrwif_specs(
    left_specs: list[str | Path],
    right_specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    diff_payload = batch_diff_mrwif_specs(left_specs, right_specs)
    analysis_payload = _analyze_batch_diff_payload(diff_payload)

    review_payload = {
        "pairs_compared": diff_payload["pairs_compared"],
        "changed_pairs": diff_payload["changed_pairs"],
        "unchanged_pairs": diff_payload["unchanged_pairs"],
        "invalid_pairs": diff_payload["invalid_pairs"],
        "is_valid": diff_payload["is_valid"] and analysis_payload["is_valid"],
        "diff_report": diff_payload,
        "analysis": analysis_payload,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch review output")
        _write_auxiliary_document(output_path, review_payload, report_format)
        review_payload["report_output"] = str(output_path)
        review_payload["report_format"] = report_format

    return review_payload


def _resolve_auxiliary_format(output_path: Path, *, label: str) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError(f"{label} must end in .json, .yaml, or .yml")


def _write_auxiliary_document(output_path: Path, document: dict[str, Any], report_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        if report_format == "json":
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            return
        yaml.safe_dump(document, handle, sort_keys=False)


def _load_auxiliary_document(input_path: Path, *, label: str) -> dict[str, Any]:
    report_format = _resolve_auxiliary_format(input_path, label=label)
    with input_path.open("r", encoding="utf-8") as handle:
        if report_format == "json":
            document = json.load(handle)
        else:
            document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a mapping document")
    return document


def _infer_pair_changed(result: dict[str, Any]) -> bool:
    summary = result.get("change_summary")
    if isinstance(summary, dict) and any(
        int(summary.get(key, 0) or 0)
        for key in (
            "metadata_fields_changed",
            "added_linked_artifacts",
            "removed_linked_artifacts",
            "changed_linked_artifacts",
            "added_intent_mappings",
            "removed_intent_mappings",
            "changed_intent_mappings",
            "added_interpretation_records",
            "removed_interpretation_records",
            "changed_interpretation_records",
            "added_revision_traces",
            "removed_revision_traces",
            "changed_revision_traces",
        )
    ):
        return True

    metadata_changes = result.get("metadata_changes")
    if isinstance(metadata_changes, dict) and metadata_changes:
        return True

    return False


def _analyze_batch_diff_payload(report_document: dict[str, Any], *, analysis_input: str | None = None) -> dict[str, Any]:
    results = report_document.get("results")
    if not isinstance(results, list):
        raise ValueError("batch diff analysis input must contain a 'results' list")

    metadata_counter: Counter[str] = Counter()
    added_linked_artifact_counter: Counter[str] = Counter()
    removed_linked_artifact_counter: Counter[str] = Counter()
    added_intent_mapping_counter: Counter[str] = Counter()
    removed_intent_mapping_counter: Counter[str] = Counter()
    added_interpretation_counter: Counter[str] = Counter()
    removed_interpretation_counter: Counter[str] = Counter()
    added_revision_counter: Counter[str] = Counter()
    removed_revision_counter: Counter[str] = Counter()

    metadata_pair_indexes: dict[str, list[int]] = {}
    added_linked_artifact_pair_indexes: dict[str, list[int]] = {}
    removed_linked_artifact_pair_indexes: dict[str, list[int]] = {}
    added_intent_mapping_pair_indexes: dict[str, list[int]] = {}
    removed_intent_mapping_pair_indexes: dict[str, list[int]] = {}
    added_interpretation_pair_indexes: dict[str, list[int]] = {}
    removed_interpretation_pair_indexes: dict[str, list[int]] = {}
    added_revision_pair_indexes: dict[str, list[int]] = {}
    removed_revision_pair_indexes: dict[str, list[int]] = {}

    linked_artifact_realms_changed_pairs = 0
    linked_artifact_ids_changed_pairs = 0
    linked_artifact_ids_count_delta_pairs = 0
    total_linked_artifact_ids_count_delta = 0
    intent_mapping_ids_changed_pairs = 0
    intent_mapping_ids_count_delta_pairs = 0
    total_intent_mapping_ids_count_delta = 0
    semantic_descriptors_changed_pairs = 0
    semantic_descriptors_count_delta_pairs = 0
    total_semantic_descriptors_count_delta = 0
    target_realms_changed_pairs = 0
    target_realms_count_delta_pairs = 0
    total_target_realms_count_delta = 0
    target_descriptors_changed_pairs = 0
    target_descriptors_count_delta_pairs = 0
    total_target_descriptors_count_delta = 0
    interpretation_record_ids_changed_pairs = 0
    interpretation_record_ids_count_delta_pairs = 0
    total_interpretation_record_ids_count_delta = 0
    interpretation_artifact_ids_changed_pairs = 0
    interpretation_artifact_ids_count_delta_pairs = 0
    total_interpretation_artifact_ids_count_delta = 0
    inferred_descriptors_changed_pairs = 0
    inferred_descriptors_count_delta_pairs = 0
    total_inferred_descriptors_count_delta = 0
    ambiguity_note_count_delta_pairs = 0
    total_ambiguity_note_count_delta = 0
    revision_ids_changed_pairs = 0
    revision_ids_count_delta_pairs = 0
    total_revision_ids_count_delta = 0
    affected_realms_changed_pairs = 0
    affected_realms_count_delta_pairs = 0
    total_affected_realms_count_delta = 0
    requested_change_count_delta_pairs = 0
    total_requested_change_count_delta = 0
    applied_change_count_delta_pairs = 0
    total_applied_change_count_delta = 0

    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0

    for index, raw_result in enumerate(results):
        if not isinstance(raw_result, dict):
            continue

        pair_index = int(raw_result.get("pair_index", index))
        pair_changed = bool(raw_result.get("pair_changed", _infer_pair_changed(raw_result)))
        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not raw_result.get("left_valid", False) or not raw_result.get("right_valid", False):
            invalid_pairs += 1

        metadata_changes = raw_result.get("metadata_changes")
        if isinstance(metadata_changes, dict):
            for field in metadata_changes:
                field_name = str(field)
                metadata_counter[field_name] += 1
                metadata_pair_indexes.setdefault(field_name, []).append(pair_index)

        for item in _string_list(raw_result.get("added_linked_artifacts")):
            added_linked_artifact_counter[item] += 1
            added_linked_artifact_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("removed_linked_artifacts")):
            removed_linked_artifact_counter[item] += 1
            removed_linked_artifact_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("added_intent_mappings")):
            added_intent_mapping_counter[item] += 1
            added_intent_mapping_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("removed_intent_mappings")):
            removed_intent_mapping_counter[item] += 1
            removed_intent_mapping_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("added_interpretation_records")):
            added_interpretation_counter[item] += 1
            added_interpretation_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("removed_interpretation_records")):
            removed_interpretation_counter[item] += 1
            removed_interpretation_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("added_revision_traces")):
            added_revision_counter[item] += 1
            added_revision_pair_indexes.setdefault(item, []).append(pair_index)
        for item in _string_list(raw_result.get("removed_revision_traces")):
            removed_revision_counter[item] += 1
            removed_revision_pair_indexes.setdefault(item, []).append(pair_index)

        correspondence_changes = raw_result.get("correspondence_changes")
        if isinstance(correspondence_changes, dict):
            if bool(correspondence_changes.get("linked_artifact_realms_changed", False)):
                linked_artifact_realms_changed_pairs += 1
            if bool(correspondence_changes.get("linked_artifact_ids_changed", False)):
                linked_artifact_ids_changed_pairs += 1
            delta = int(correspondence_changes.get("linked_artifact_ids_count_delta", 0) or 0)
            total_linked_artifact_ids_count_delta += delta
            if delta != 0:
                linked_artifact_ids_count_delta_pairs += 1

            if bool(correspondence_changes.get("intent_mapping_ids_changed", False)):
                intent_mapping_ids_changed_pairs += 1
            delta = int(correspondence_changes.get("intent_mapping_ids_count_delta", 0) or 0)
            total_intent_mapping_ids_count_delta += delta
            if delta != 0:
                intent_mapping_ids_count_delta_pairs += 1

            if bool(correspondence_changes.get("semantic_descriptors_changed", False)):
                semantic_descriptors_changed_pairs += 1
            delta = int(correspondence_changes.get("semantic_descriptors_count_delta", 0) or 0)
            total_semantic_descriptors_count_delta += delta
            if delta != 0:
                semantic_descriptors_count_delta_pairs += 1

            if bool(correspondence_changes.get("target_realms_changed", False)):
                target_realms_changed_pairs += 1
            delta = int(correspondence_changes.get("target_realms_count_delta", 0) or 0)
            total_target_realms_count_delta += delta
            if delta != 0:
                target_realms_count_delta_pairs += 1

            if bool(correspondence_changes.get("target_descriptors_changed", False)):
                target_descriptors_changed_pairs += 1
            delta = int(correspondence_changes.get("target_descriptors_count_delta", 0) or 0)
            total_target_descriptors_count_delta += delta
            if delta != 0:
                target_descriptors_count_delta_pairs += 1

            if bool(correspondence_changes.get("interpretation_record_ids_changed", False)):
                interpretation_record_ids_changed_pairs += 1
            delta = int(correspondence_changes.get("interpretation_record_ids_count_delta", 0) or 0)
            total_interpretation_record_ids_count_delta += delta
            if delta != 0:
                interpretation_record_ids_count_delta_pairs += 1

            if bool(correspondence_changes.get("interpretation_artifact_ids_changed", False)):
                interpretation_artifact_ids_changed_pairs += 1
            delta = int(correspondence_changes.get("interpretation_artifact_ids_count_delta", 0) or 0)
            total_interpretation_artifact_ids_count_delta += delta
            if delta != 0:
                interpretation_artifact_ids_count_delta_pairs += 1

            if bool(correspondence_changes.get("inferred_descriptors_changed", False)):
                inferred_descriptors_changed_pairs += 1
            delta = int(correspondence_changes.get("inferred_descriptors_count_delta", 0) or 0)
            total_inferred_descriptors_count_delta += delta
            if delta != 0:
                inferred_descriptors_count_delta_pairs += 1

            delta = int(correspondence_changes.get("ambiguity_note_count_delta", 0) or 0)
            total_ambiguity_note_count_delta += delta
            if delta != 0:
                ambiguity_note_count_delta_pairs += 1

            if bool(correspondence_changes.get("revision_ids_changed", False)):
                revision_ids_changed_pairs += 1
            delta = int(correspondence_changes.get("revision_ids_count_delta", 0) or 0)
            total_revision_ids_count_delta += delta
            if delta != 0:
                revision_ids_count_delta_pairs += 1

            if bool(correspondence_changes.get("affected_realms_changed", False)):
                affected_realms_changed_pairs += 1
            delta = int(correspondence_changes.get("affected_realms_count_delta", 0) or 0)
            total_affected_realms_count_delta += delta
            if delta != 0:
                affected_realms_count_delta_pairs += 1

            delta = int(correspondence_changes.get("requested_change_count_delta", 0) or 0)
            total_requested_change_count_delta += delta
            if delta != 0:
                requested_change_count_delta_pairs += 1

            delta = int(correspondence_changes.get("applied_change_count_delta", 0) or 0)
            total_applied_change_count_delta += delta
            if delta != 0:
                applied_change_count_delta_pairs += 1

    analysis_payload = {
        "pairs_compared": int(report_document.get("pairs_compared", len(results))),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "is_valid": invalid_pairs == 0,
        "metadata_field_frequencies": _rank_counter_items(metadata_counter, metadata_pair_indexes),
        "added_linked_artifact_frequencies": _rank_counter_items(added_linked_artifact_counter, added_linked_artifact_pair_indexes),
        "removed_linked_artifact_frequencies": _rank_counter_items(removed_linked_artifact_counter, removed_linked_artifact_pair_indexes),
        "added_intent_mapping_frequencies": _rank_counter_items(added_intent_mapping_counter, added_intent_mapping_pair_indexes),
        "removed_intent_mapping_frequencies": _rank_counter_items(removed_intent_mapping_counter, removed_intent_mapping_pair_indexes),
        "added_interpretation_record_frequencies": _rank_counter_items(added_interpretation_counter, added_interpretation_pair_indexes),
        "removed_interpretation_record_frequencies": _rank_counter_items(removed_interpretation_counter, removed_interpretation_pair_indexes),
        "added_revision_trace_frequencies": _rank_counter_items(added_revision_counter, added_revision_pair_indexes),
        "removed_revision_trace_frequencies": _rank_counter_items(removed_revision_counter, removed_revision_pair_indexes),
        "correspondence_change_summary": {
            "linked_artifact_realms_changed_pairs": linked_artifact_realms_changed_pairs,
            "linked_artifact_ids_changed_pairs": linked_artifact_ids_changed_pairs,
            "pairs_with_linked_artifact_ids_count_delta": linked_artifact_ids_count_delta_pairs,
            "total_linked_artifact_ids_count_delta": total_linked_artifact_ids_count_delta,
            "intent_mapping_ids_changed_pairs": intent_mapping_ids_changed_pairs,
            "pairs_with_intent_mapping_ids_count_delta": intent_mapping_ids_count_delta_pairs,
            "total_intent_mapping_ids_count_delta": total_intent_mapping_ids_count_delta,
            "semantic_descriptors_changed_pairs": semantic_descriptors_changed_pairs,
            "pairs_with_semantic_descriptors_count_delta": semantic_descriptors_count_delta_pairs,
            "total_semantic_descriptors_count_delta": total_semantic_descriptors_count_delta,
            "target_realms_changed_pairs": target_realms_changed_pairs,
            "pairs_with_target_realms_count_delta": target_realms_count_delta_pairs,
            "total_target_realms_count_delta": total_target_realms_count_delta,
            "target_descriptors_changed_pairs": target_descriptors_changed_pairs,
            "pairs_with_target_descriptors_count_delta": target_descriptors_count_delta_pairs,
            "total_target_descriptors_count_delta": total_target_descriptors_count_delta,
            "interpretation_record_ids_changed_pairs": interpretation_record_ids_changed_pairs,
            "pairs_with_interpretation_record_ids_count_delta": interpretation_record_ids_count_delta_pairs,
            "total_interpretation_record_ids_count_delta": total_interpretation_record_ids_count_delta,
            "interpretation_artifact_ids_changed_pairs": interpretation_artifact_ids_changed_pairs,
            "pairs_with_interpretation_artifact_ids_count_delta": interpretation_artifact_ids_count_delta_pairs,
            "total_interpretation_artifact_ids_count_delta": total_interpretation_artifact_ids_count_delta,
            "inferred_descriptors_changed_pairs": inferred_descriptors_changed_pairs,
            "pairs_with_inferred_descriptors_count_delta": inferred_descriptors_count_delta_pairs,
            "total_inferred_descriptors_count_delta": total_inferred_descriptors_count_delta,
            "pairs_with_ambiguity_note_count_delta": ambiguity_note_count_delta_pairs,
            "total_ambiguity_note_count_delta": total_ambiguity_note_count_delta,
            "revision_ids_changed_pairs": revision_ids_changed_pairs,
            "pairs_with_revision_ids_count_delta": revision_ids_count_delta_pairs,
            "total_revision_ids_count_delta": total_revision_ids_count_delta,
            "affected_realms_changed_pairs": affected_realms_changed_pairs,
            "pairs_with_affected_realms_count_delta": affected_realms_count_delta_pairs,
            "total_affected_realms_count_delta": total_affected_realms_count_delta,
            "pairs_with_requested_change_count_delta": requested_change_count_delta_pairs,
            "total_requested_change_count_delta": total_requested_change_count_delta,
            "pairs_with_applied_change_count_delta": applied_change_count_delta_pairs,
            "total_applied_change_count_delta": total_applied_change_count_delta,
        },
    }

    if analysis_input is not None:
        analysis_payload["analysis_input"] = analysis_input

    return analysis_payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _rank_counter_items(counter: Counter[str], pair_indexes: dict[str, list[int]]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "count": count,
            "pair_indexes": sorted(pair_indexes.get(name, [])),
        }
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]