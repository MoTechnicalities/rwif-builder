from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import validate_mrwif_spec


def _linked_artifact_summary(artifact_document: Any, index: int) -> dict[str, Any]:
    artifact_mapping = dict(artifact_document) if isinstance(artifact_document, dict) else {}
    realm = artifact_mapping.get("realm") if isinstance(artifact_mapping.get("realm"), str) else None
    artifact_id = artifact_mapping.get("artifact_id") if isinstance(artifact_mapping.get("artifact_id"), str) else None
    return {
        "index": index,
        "artifact_key": artifact_id or f"artifact:{index}",
        "realm": realm,
        "artifact_id": artifact_id,
        "role": artifact_mapping.get("role"),
        "locator": artifact_mapping.get("locator"),
        "metadata": dict(artifact_mapping.get("metadata")) if isinstance(artifact_mapping.get("metadata"), dict) else {},
    }


def _intent_mapping_summary(mapping_document: Any, index: int) -> dict[str, Any]:
    mapping = dict(mapping_document) if isinstance(mapping_document, dict) else {}
    semantic_descriptors = mapping.get("semantic_descriptors") if isinstance(mapping.get("semantic_descriptors"), list) else []
    target_descriptors = mapping.get("target_descriptors") if isinstance(mapping.get("target_descriptors"), list) else []
    return {
        "index": index,
        "mapping_key": mapping.get("mapping_id") or f"intent:{index}",
        "mapping_id": mapping.get("mapping_id"),
        "semantic_descriptors": [item for item in semantic_descriptors if isinstance(item, str) and item],
        "target_realm": mapping.get("target_realm"),
        "target_descriptors": [item for item in target_descriptors if isinstance(item, str) and item],
        "confidence": float(mapping.get("confidence")) if isinstance(mapping.get("confidence"), (int, float)) else None,
        "notes": mapping.get("notes"),
    }


def _interpretation_record_summary(record_document: Any, index: int) -> dict[str, Any]:
    record = dict(record_document) if isinstance(record_document, dict) else {}
    inferred_descriptors = record.get("inferred_descriptors") if isinstance(record.get("inferred_descriptors"), list) else []
    ambiguity_notes = record.get("ambiguity_notes") if isinstance(record.get("ambiguity_notes"), list) else []
    return {
        "index": index,
        "record_key": record.get("record_id") or f"interpretation:{index}",
        "record_id": record.get("record_id"),
        "artifact_id": record.get("artifact_id"),
        "inferred_descriptors": [item for item in inferred_descriptors if isinstance(item, str) and item],
        "confidence": float(record.get("confidence")) if isinstance(record.get("confidence"), (int, float)) else None,
        "ambiguity_notes": [item for item in ambiguity_notes if isinstance(item, str) and item],
        "notes": record.get("notes"),
    }


def _revision_trace_summary(revision_document: Any, index: int) -> dict[str, Any]:
    revision = dict(revision_document) if isinstance(revision_document, dict) else {}
    requested_changes = revision.get("requested_changes") if isinstance(revision.get("requested_changes"), list) else []
    applied_changes = revision.get("applied_changes") if isinstance(revision.get("applied_changes"), list) else []
    affected_realms = revision.get("affected_realms") if isinstance(revision.get("affected_realms"), list) else []
    return {
        "index": index,
        "revision_key": revision.get("revision_id") or f"revision:{index}",
        "revision_id": revision.get("revision_id"),
        "requested_changes": [item for item in requested_changes if isinstance(item, str) and item],
        "applied_changes": [item for item in applied_changes if isinstance(item, str) and item],
        "affected_realms": [item for item in affected_realms if isinstance(item, str) and item],
        "notes": revision.get("notes"),
    }


def inspect_mrwif_spec(path: str | Path) -> dict[str, Any]:
    spec_path = Path(path)
    validation_report = validate_mrwif_spec(spec_path)
    payload = validation_report.to_payload()
    if not validation_report.is_valid or validation_report.normalized_document is None:
        return payload

    document = validation_report.normalized_document
    linked_artifacts = [_linked_artifact_summary(item, index) for index, item in enumerate(document.get("linked_artifacts") or [])]
    intent_mappings = [_intent_mapping_summary(item, index) for index, item in enumerate(document.get("intent_mappings") or [])]
    interpretation_records = [
        _interpretation_record_summary(item, index) for index, item in enumerate(document.get("interpretation_records") or [])
    ]
    revision_traces = [_revision_trace_summary(item, index) for index, item in enumerate(document.get("revision_traces") or [])]

    confidence_values = [
        float(item["confidence"])
        for collection in (intent_mappings, interpretation_records)
        for item in collection
        if isinstance(item.get("confidence"), float)
    ]

    payload.update(
        {
            "mrwif_version": document.get("mrwif_version"),
            "correspondence_id": document.get("correspondence_id"),
            "title": document.get("title"),
            "description": document.get("description"),
            "linked_artifacts": linked_artifacts,
            "intent_mappings": intent_mappings,
            "interpretation_records": interpretation_records,
            "revision_traces": revision_traces,
            "provenance": dict(document.get("provenance")) if isinstance(document.get("provenance"), dict) else {},
            "correspondence_summary": {
                "linked_artifact_count": len(linked_artifacts),
                "linked_artifact_realms": sorted(
                    {item["realm"] for item in linked_artifacts if isinstance(item.get("realm"), str) and item.get("realm")}
                ),
                "linked_artifact_ids": sorted(
                    {item["artifact_id"] for item in linked_artifacts if isinstance(item.get("artifact_id"), str) and item.get("artifact_id")}
                ),
                "intent_mapping_count": len(intent_mappings),
                "intent_mapping_ids": sorted(
                    {item["mapping_id"] for item in intent_mappings if isinstance(item.get("mapping_id"), str) and item.get("mapping_id")}
                ),
                "semantic_descriptors": sorted(
                    descriptor
                    for item in intent_mappings
                    for descriptor in item.get("semantic_descriptors") or []
                ),
                "target_realms": sorted(
                    {item["target_realm"] for item in intent_mappings if isinstance(item.get("target_realm"), str) and item.get("target_realm")}
                ),
                "target_descriptors": sorted(
                    descriptor
                    for item in intent_mappings
                    for descriptor in item.get("target_descriptors") or []
                ),
                "interpretation_record_count": len(interpretation_records),
                "interpretation_record_ids": sorted(
                    {item["record_id"] for item in interpretation_records if isinstance(item.get("record_id"), str) and item.get("record_id")}
                ),
                "interpretation_artifact_ids": sorted(
                    {item["artifact_id"] for item in interpretation_records if isinstance(item.get("artifact_id"), str) and item.get("artifact_id")}
                ),
                "inferred_descriptors": sorted(
                    descriptor
                    for item in interpretation_records
                    for descriptor in item.get("inferred_descriptors") or []
                ),
                "ambiguity_note_count": sum(len(item.get("ambiguity_notes") or []) for item in interpretation_records),
                "revision_trace_count": len(revision_traces),
                "revision_ids": sorted(
                    {item["revision_id"] for item in revision_traces if isinstance(item.get("revision_id"), str) and item.get("revision_id")}
                ),
                "affected_realms": sorted(
                    realm
                    for item in revision_traces
                    for realm in item.get("affected_realms") or []
                ),
                "requested_change_count": sum(len(item.get("requested_changes") or []) for item in revision_traces),
                "applied_change_count": sum(len(item.get("applied_changes") or []) for item in revision_traces),
                "confidence_count": len(confidence_values),
                "average_confidence": (sum(confidence_values) / len(confidence_values)) if confidence_values else None,
            },
        }
    )
    return payload