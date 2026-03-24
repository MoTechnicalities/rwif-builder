from __future__ import annotations

from pathlib import Path
from typing import Any

from .inspect import inspect_mrwif_spec

_METADATA_KEYS = (
    "mrwif_version",
    "correspondence_id",
    "title",
    "description",
)


def diff_mrwif_specs(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_path = Path(left)
    right_path = Path(right)

    left_payload = inspect_mrwif_spec(left_path)
    right_payload = inspect_mrwif_spec(right_path)

    metadata_changes = {
        key: {"left": left_payload.get(key), "right": right_payload.get(key)}
        for key in _METADATA_KEYS
        if left_payload.get(key) != right_payload.get(key)
    }

    left_linked_artifacts = _summary_map(left_payload.get("linked_artifacts"), "artifact_key", "artifact")
    right_linked_artifacts = _summary_map(right_payload.get("linked_artifacts"), "artifact_key", "artifact")
    left_intent_mappings = _summary_map(left_payload.get("intent_mappings"), "mapping_key", "intent")
    right_intent_mappings = _summary_map(right_payload.get("intent_mappings"), "mapping_key", "intent")
    left_interpretations = _summary_map(left_payload.get("interpretation_records"), "record_key", "interpretation")
    right_interpretations = _summary_map(right_payload.get("interpretation_records"), "record_key", "interpretation")
    left_revisions = _summary_map(left_payload.get("revision_traces"), "revision_key", "revision")
    right_revisions = _summary_map(right_payload.get("revision_traces"), "revision_key", "revision")

    linked_artifact_changes = _changed_item_descriptions(left_linked_artifacts, right_linked_artifacts)
    intent_mapping_changes = _changed_item_descriptions(left_intent_mappings, right_intent_mappings)
    interpretation_record_changes = _changed_item_descriptions(left_interpretations, right_interpretations)
    revision_trace_changes = _changed_item_descriptions(left_revisions, right_revisions)

    return {
        "left": str(left_path),
        "right": str(right_path),
        "left_valid": bool(left_payload.get("is_valid", False)),
        "right_valid": bool(right_payload.get("is_valid", False)),
        "metadata_changes": metadata_changes,
        "left_correspondence_summary": dict(left_payload.get("correspondence_summary") or {}),
        "right_correspondence_summary": dict(right_payload.get("correspondence_summary") or {}),
        "correspondence_changes": _correspondence_changes(left_payload, right_payload),
        "added_linked_artifacts": linked_artifact_changes["added"],
        "removed_linked_artifacts": linked_artifact_changes["removed"],
        "changed_linked_artifacts": linked_artifact_changes["changed"],
        "linked_artifact_changes": linked_artifact_changes["descriptions"],
        "added_intent_mappings": intent_mapping_changes["added"],
        "removed_intent_mappings": intent_mapping_changes["removed"],
        "changed_intent_mappings": intent_mapping_changes["changed"],
        "intent_mapping_changes": intent_mapping_changes["descriptions"],
        "added_interpretation_records": interpretation_record_changes["added"],
        "removed_interpretation_records": interpretation_record_changes["removed"],
        "changed_interpretation_records": interpretation_record_changes["changed"],
        "interpretation_record_changes": interpretation_record_changes["descriptions"],
        "added_revision_traces": revision_trace_changes["added"],
        "removed_revision_traces": revision_trace_changes["removed"],
        "changed_revision_traces": revision_trace_changes["changed"],
        "revision_trace_changes": revision_trace_changes["descriptions"],
        "change_summary": {
            "metadata_fields_changed": len(metadata_changes),
            "added_linked_artifacts": len(linked_artifact_changes["added"]),
            "removed_linked_artifacts": len(linked_artifact_changes["removed"]),
            "changed_linked_artifacts": len(linked_artifact_changes["changed"]),
            "added_intent_mappings": len(intent_mapping_changes["added"]),
            "removed_intent_mappings": len(intent_mapping_changes["removed"]),
            "changed_intent_mappings": len(intent_mapping_changes["changed"]),
            "added_interpretation_records": len(interpretation_record_changes["added"]),
            "removed_interpretation_records": len(interpretation_record_changes["removed"]),
            "changed_interpretation_records": len(interpretation_record_changes["changed"]),
            "added_revision_traces": len(revision_trace_changes["added"]),
            "removed_revision_traces": len(revision_trace_changes["removed"]),
            "changed_revision_traces": len(revision_trace_changes["changed"]),
        },
    }


def _summary_map(summaries: Any, key_field: str, fallback_prefix: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(summaries, list):
        return result
    for index, summary in enumerate(summaries):
        if not isinstance(summary, dict):
            continue
        key = str(summary.get(key_field) or f"{fallback_prefix}:{index}")
        if key in result:
            key = f"{key}#{index}"
        result[key] = summary
    return result


def _signature(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key != "index"}


def _changed_item_descriptions(left_map: dict[str, dict[str, Any]], right_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    left_keys = set(left_map)
    right_keys = set(right_map)
    changed = sorted(key for key in left_keys & right_keys if _signature(left_map[key]) != _signature(right_map[key]))
    return {
        "added": sorted(right_keys - left_keys),
        "removed": sorted(left_keys - right_keys),
        "changed": changed,
        "descriptions": {
            key: {
                "field_changes": {
                    field: {"left": left_map[key].get(field), "right": right_map[key].get(field)}
                    for field in sorted(set(left_map[key]) | set(right_map[key]))
                    if field != "index" and left_map[key].get(field) != right_map[key].get(field)
                }
            }
            for key in changed
        },
    }


def _count_delta(left_summary: dict[str, Any], right_summary: dict[str, Any], key: str) -> int:
    return int(right_summary.get(key, 0) or 0) - int(left_summary.get(key, 0) or 0)


def _float_delta(left_summary: dict[str, Any], right_summary: dict[str, Any], key: str) -> float | None:
    left_value = left_summary.get(key)
    right_value = right_summary.get(key)
    if left_value is None and right_value is None:
        return None
    return float(right_value or 0.0) - float(left_value or 0.0)


def _correspondence_changes(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> dict[str, Any]:
    left_summary = dict(left_payload.get("correspondence_summary") or {})
    right_summary = dict(right_payload.get("correspondence_summary") or {})
    return {
        "linked_artifact_count_delta": _count_delta(left_summary, right_summary, "linked_artifact_count"),
        "linked_artifact_realms_changed": left_summary.get("linked_artifact_realms") != right_summary.get("linked_artifact_realms"),
        "linked_artifact_realms_count_delta": len(right_summary.get("linked_artifact_realms") or []) - len(left_summary.get("linked_artifact_realms") or []),
        "linked_artifact_ids_changed": left_summary.get("linked_artifact_ids") != right_summary.get("linked_artifact_ids"),
        "linked_artifact_ids_count_delta": len(right_summary.get("linked_artifact_ids") or []) - len(left_summary.get("linked_artifact_ids") or []),
        "intent_mapping_count_delta": _count_delta(left_summary, right_summary, "intent_mapping_count"),
        "intent_mapping_ids_changed": left_summary.get("intent_mapping_ids") != right_summary.get("intent_mapping_ids"),
        "intent_mapping_ids_count_delta": len(right_summary.get("intent_mapping_ids") or []) - len(left_summary.get("intent_mapping_ids") or []),
        "semantic_descriptors_changed": left_summary.get("semantic_descriptors") != right_summary.get("semantic_descriptors"),
        "semantic_descriptors_count_delta": len(right_summary.get("semantic_descriptors") or []) - len(left_summary.get("semantic_descriptors") or []),
        "target_realms_changed": left_summary.get("target_realms") != right_summary.get("target_realms"),
        "target_realms_count_delta": len(right_summary.get("target_realms") or []) - len(left_summary.get("target_realms") or []),
        "target_descriptors_changed": left_summary.get("target_descriptors") != right_summary.get("target_descriptors"),
        "target_descriptors_count_delta": len(right_summary.get("target_descriptors") or []) - len(left_summary.get("target_descriptors") or []),
        "interpretation_record_count_delta": _count_delta(left_summary, right_summary, "interpretation_record_count"),
        "interpretation_record_ids_changed": left_summary.get("interpretation_record_ids") != right_summary.get("interpretation_record_ids"),
        "interpretation_record_ids_count_delta": len(right_summary.get("interpretation_record_ids") or []) - len(left_summary.get("interpretation_record_ids") or []),
        "interpretation_artifact_ids_changed": left_summary.get("interpretation_artifact_ids") != right_summary.get("interpretation_artifact_ids"),
        "interpretation_artifact_ids_count_delta": len(right_summary.get("interpretation_artifact_ids") or []) - len(left_summary.get("interpretation_artifact_ids") or []),
        "inferred_descriptors_changed": left_summary.get("inferred_descriptors") != right_summary.get("inferred_descriptors"),
        "inferred_descriptors_count_delta": len(right_summary.get("inferred_descriptors") or []) - len(left_summary.get("inferred_descriptors") or []),
        "ambiguity_note_count_delta": _count_delta(left_summary, right_summary, "ambiguity_note_count"),
        "revision_trace_count_delta": _count_delta(left_summary, right_summary, "revision_trace_count"),
        "revision_ids_changed": left_summary.get("revision_ids") != right_summary.get("revision_ids"),
        "revision_ids_count_delta": len(right_summary.get("revision_ids") or []) - len(left_summary.get("revision_ids") or []),
        "affected_realms_changed": left_summary.get("affected_realms") != right_summary.get("affected_realms"),
        "affected_realms_count_delta": len(right_summary.get("affected_realms") or []) - len(left_summary.get("affected_realms") or []),
        "requested_change_count_delta": _count_delta(left_summary, right_summary, "requested_change_count"),
        "applied_change_count_delta": _count_delta(left_summary, right_summary, "applied_change_count"),
        "average_confidence_delta": _float_delta(left_summary, right_summary, "average_confidence"),
    }