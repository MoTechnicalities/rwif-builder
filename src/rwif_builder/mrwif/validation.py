from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

import yaml

MRWIF_VERSION = 1
KNOWN_REALMS = ("rwif", "arwif", "vrwif", "trwif", "crwif", "erwif")


@dataclass(frozen=True)
class MRWIFSpecValidationReport:
    spec: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)
    normalized_document: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "spec": self.spec,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }
        if self.normalized_document is not None:
            payload["normalized_document"] = dict(self.normalized_document)
        return payload


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _is_confidence(value: Any) -> bool:
    return _is_number(value) and 0.0 <= float(value) <= 1.0


def _deep_copy_document(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy_document(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy_document(item) for item in value]
    return value


def _load_spec_document(spec_path: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    try:
        with spec_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except Exception as exc:
        return None, (str(exc),)

    if document is None:
        return None, ("MRWIF spec file is empty",)
    if not isinstance(document, dict):
        return None, ("MRWIF spec must be a mapping",)
    return document, ()


def _non_empty_string_list(
    value: Any,
    *,
    context: str,
    field_name: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{context}.{field_name} must be a list")
        return []

    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{context}.{field_name}[{index}] must be a non-empty string")
            continue
        strings.append(item)
    return strings


def _validate_linked_artifact(
    artifact_document: Any,
    *,
    index: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[str | None, str | None]:
    context = f"linked_artifacts[{index}]"
    if not isinstance(artifact_document, dict):
        errors.append(f"{context} must be a mapping")
        return None, None

    allowed_keys = {"realm", "artifact_id", "role", "locator", "metadata"}
    unknown_keys = sorted(key for key in artifact_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    realm = artifact_document.get("realm")
    if not isinstance(realm, str) or not realm:
        errors.append(f"{context}.realm must be a non-empty string")
    elif realm not in KNOWN_REALMS:
        warnings.append(f"{context}.realm is not yet a recognized realm constant: {realm}")

    artifact_id = artifact_document.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        errors.append(f"{context}.artifact_id must be a non-empty string")

    role = artifact_document.get("role")
    if role is not None and (not isinstance(role, str) or not role):
        errors.append(f"{context}.role must be a non-empty string when provided")

    locator = artifact_document.get("locator")
    if locator is not None and (not isinstance(locator, str) or not locator):
        errors.append(f"{context}.locator must be a non-empty string when provided")

    if "metadata" in artifact_document and artifact_document.get("metadata") is not None and not isinstance(artifact_document.get("metadata"), dict):
        errors.append(f"{context}.metadata must be a mapping")

    return realm if isinstance(realm, str) and realm else None, artifact_id if isinstance(artifact_id, str) and artifact_id else None


def _validate_intent_mapping(
    mapping_document: Any,
    *,
    index: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[str | None, list[str], str | None, list[str], float | None]:
    context = f"intent_mappings[{index}]"
    if not isinstance(mapping_document, dict):
        errors.append(f"{context} must be a mapping")
        return None, [], None, [], None

    allowed_keys = {
        "mapping_id",
        "semantic_descriptors",
        "target_realm",
        "target_descriptors",
        "confidence",
        "notes",
    }
    unknown_keys = sorted(key for key in mapping_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    mapping_id = mapping_document.get("mapping_id")
    if not isinstance(mapping_id, str) or not mapping_id:
        errors.append(f"{context}.mapping_id must be a non-empty string")

    semantic_descriptors = _non_empty_string_list(
        mapping_document.get("semantic_descriptors"),
        context=context,
        field_name="semantic_descriptors",
        errors=errors,
    )
    target_realm = mapping_document.get("target_realm")
    if not isinstance(target_realm, str) or not target_realm:
        errors.append(f"{context}.target_realm must be a non-empty string")
    elif target_realm not in KNOWN_REALMS:
        warnings.append(f"{context}.target_realm is not yet a recognized realm constant: {target_realm}")

    target_descriptors = _non_empty_string_list(
        mapping_document.get("target_descriptors"),
        context=context,
        field_name="target_descriptors",
        errors=errors,
    )

    confidence_value = mapping_document.get("confidence")
    if confidence_value is None:
        confidence = None
    elif not _is_confidence(confidence_value):
        errors.append(f"{context}.confidence must be a finite number between 0.0 and 1.0")
        confidence = None
    else:
        confidence = float(confidence_value)

    notes = mapping_document.get("notes")
    if notes is not None and (not isinstance(notes, str) or not notes):
        errors.append(f"{context}.notes must be a non-empty string when provided")

    return (
        mapping_id if isinstance(mapping_id, str) and mapping_id else None,
        semantic_descriptors,
        target_realm if isinstance(target_realm, str) and target_realm else None,
        target_descriptors,
        confidence,
    )


def _validate_interpretation_record(
    record_document: Any,
    *,
    index: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[str | None, str | None, list[str], int, float | None]:
    context = f"interpretation_records[{index}]"
    if not isinstance(record_document, dict):
        errors.append(f"{context} must be a mapping")
        return None, None, [], 0, None

    allowed_keys = {"record_id", "artifact_id", "inferred_descriptors", "confidence", "ambiguity_notes", "notes"}
    unknown_keys = sorted(key for key in record_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    record_id = record_document.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        errors.append(f"{context}.record_id must be a non-empty string")

    artifact_id = record_document.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        errors.append(f"{context}.artifact_id must be a non-empty string")

    inferred_descriptors = _non_empty_string_list(
        record_document.get("inferred_descriptors"),
        context=context,
        field_name="inferred_descriptors",
        errors=errors,
    )

    ambiguity_notes = _non_empty_string_list(
        record_document.get("ambiguity_notes", []),
        context=context,
        field_name="ambiguity_notes",
        errors=errors,
    ) if "ambiguity_notes" in record_document else []

    confidence_value = record_document.get("confidence")
    if confidence_value is None:
        confidence = None
    elif not _is_confidence(confidence_value):
        errors.append(f"{context}.confidence must be a finite number between 0.0 and 1.0")
        confidence = None
    else:
        confidence = float(confidence_value)

    notes = record_document.get("notes")
    if notes is not None and (not isinstance(notes, str) or not notes):
        errors.append(f"{context}.notes must be a non-empty string when provided")

    return (
        record_id if isinstance(record_id, str) and record_id else None,
        artifact_id if isinstance(artifact_id, str) and artifact_id else None,
        inferred_descriptors,
        len(ambiguity_notes),
        confidence,
    )


def _validate_revision_trace(
    revision_document: Any,
    *,
    index: int,
    errors: list[str],
    warnings: list[str],
) -> tuple[str | None, list[str], list[str], list[str]]:
    context = f"revision_traces[{index}]"
    if not isinstance(revision_document, dict):
        errors.append(f"{context} must be a mapping")
        return None, [], [], []

    allowed_keys = {"revision_id", "requested_changes", "applied_changes", "affected_realms", "notes"}
    unknown_keys = sorted(key for key in revision_document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"{context} contains unknown fields ignored by the reference builder: {', '.join(unknown_keys)}")

    revision_id = revision_document.get("revision_id")
    if not isinstance(revision_id, str) or not revision_id:
        errors.append(f"{context}.revision_id must be a non-empty string")

    requested_changes = _non_empty_string_list(
        revision_document.get("requested_changes"),
        context=context,
        field_name="requested_changes",
        errors=errors,
    )
    applied_changes = _non_empty_string_list(
        revision_document.get("applied_changes"),
        context=context,
        field_name="applied_changes",
        errors=errors,
    )
    affected_realms = _non_empty_string_list(
        revision_document.get("affected_realms", []),
        context=context,
        field_name="affected_realms",
        errors=errors,
    ) if "affected_realms" in revision_document else []

    notes = revision_document.get("notes")
    if notes is not None and (not isinstance(notes, str) or not notes):
        errors.append(f"{context}.notes must be a non-empty string when provided")

    return revision_id if isinstance(revision_id, str) and revision_id else None, requested_changes, applied_changes, affected_realms


def validate_mrwif_spec(path: str | Path) -> MRWIFSpecValidationReport:
    spec_path = Path(path)
    document, load_errors = _load_spec_document(spec_path)
    if load_errors:
        return MRWIFSpecValidationReport(spec=str(spec_path), is_valid=False, errors=load_errors)
    assert document is not None
    return validate_mrwif_spec_document(document, source=str(spec_path))


def validate_mrwif_spec_document(document: dict[str, Any], *, source: str = "<memory>") -> MRWIFSpecValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    allowed_keys = {
        "mrwif_version",
        "correspondence_id",
        "title",
        "description",
        "linked_artifacts",
        "intent_mappings",
        "interpretation_records",
        "revision_traces",
        "provenance",
    }
    unknown_keys = sorted(key for key in document if key not in allowed_keys)
    if unknown_keys:
        warnings.append(f"MRWIF spec contains unknown top-level fields ignored by the reference builder: {', '.join(unknown_keys)}")

    mrwif_version = document.get("mrwif_version", MRWIF_VERSION)
    if mrwif_version != MRWIF_VERSION:
        errors.append(f"mrwif_version must be {MRWIF_VERSION}")

    correspondence_id = document.get("correspondence_id")
    if not isinstance(correspondence_id, str) or not correspondence_id:
        errors.append("correspondence_id must be a non-empty string")

    title = document.get("title")
    if title is not None and (not isinstance(title, str) or not title):
        errors.append("title must be a non-empty string when provided")

    description = document.get("description")
    if description is not None and (not isinstance(description, str) or not description):
        errors.append("description must be a non-empty string when provided")

    if "provenance" in document and document.get("provenance") is not None and not isinstance(document.get("provenance"), dict):
        errors.append("provenance must be a mapping")

    linked_artifacts_document = document.get("linked_artifacts")
    linked_artifact_realms: set[str] = set()
    linked_artifact_ids: set[str] = set()
    if not isinstance(linked_artifacts_document, list):
        errors.append("linked_artifacts must be a list")
        linked_artifact_count = 0
    else:
        if not linked_artifacts_document:
            errors.append("linked_artifacts must contain at least one linked artifact")
        for index, artifact_document in enumerate(linked_artifacts_document):
            realm, artifact_id = _validate_linked_artifact(artifact_document, index=index, errors=errors, warnings=warnings)
            if realm:
                linked_artifact_realms.add(realm)
            if artifact_id:
                linked_artifact_ids.add(artifact_id)
        linked_artifact_count = len(linked_artifacts_document)

    intent_mappings_document = document.get("intent_mappings", [])
    intent_mapping_ids: set[str] = set()
    semantic_descriptors: set[str] = set()
    target_realms: set[str] = set()
    target_descriptors: set[str] = set()
    confidence_values: list[float] = []
    if not isinstance(intent_mappings_document, list):
        errors.append("intent_mappings must be a list")
        intent_mapping_count = 0
    else:
        for index, mapping_document in enumerate(intent_mappings_document):
            mapping_id, mapping_semantic_descriptors, target_realm, mapping_target_descriptors, confidence = _validate_intent_mapping(
                mapping_document,
                index=index,
                errors=errors,
                warnings=warnings,
            )
            if mapping_id:
                intent_mapping_ids.add(mapping_id)
            semantic_descriptors.update(mapping_semantic_descriptors)
            if target_realm:
                target_realms.add(target_realm)
            target_descriptors.update(mapping_target_descriptors)
            if confidence is not None:
                confidence_values.append(confidence)
        intent_mapping_count = len(intent_mappings_document)

    interpretation_records_document = document.get("interpretation_records", [])
    interpretation_record_ids: set[str] = set()
    interpretation_artifact_ids: set[str] = set()
    inferred_descriptors: set[str] = set()
    ambiguity_note_count = 0
    if not isinstance(interpretation_records_document, list):
        errors.append("interpretation_records must be a list")
        interpretation_record_count = 0
    else:
        for index, record_document in enumerate(interpretation_records_document):
            record_id, artifact_id, record_inferred_descriptors, record_ambiguity_note_count, confidence = _validate_interpretation_record(
                record_document,
                index=index,
                errors=errors,
                warnings=warnings,
            )
            if record_id:
                interpretation_record_ids.add(record_id)
            if artifact_id:
                interpretation_artifact_ids.add(artifact_id)
            inferred_descriptors.update(record_inferred_descriptors)
            ambiguity_note_count += record_ambiguity_note_count
            if confidence is not None:
                confidence_values.append(confidence)
        interpretation_record_count = len(interpretation_records_document)

    revision_traces_document = document.get("revision_traces", [])
    revision_ids: set[str] = set()
    affected_realms: set[str] = set()
    requested_change_count = 0
    applied_change_count = 0
    if not isinstance(revision_traces_document, list):
        errors.append("revision_traces must be a list")
        revision_trace_count = 0
    else:
        for index, revision_document in enumerate(revision_traces_document):
            revision_id, requested_changes, applied_changes, revision_affected_realms = _validate_revision_trace(
                revision_document,
                index=index,
                errors=errors,
                warnings=warnings,
            )
            if revision_id:
                revision_ids.add(revision_id)
            affected_realms.update(revision_affected_realms)
            requested_change_count += len(requested_changes)
            applied_change_count += len(applied_changes)
        revision_trace_count = len(revision_traces_document)

    stats = {
        "correspondence_id": correspondence_id,
        "linked_artifact_count": linked_artifact_count,
        "linked_artifact_realms": sorted(linked_artifact_realms),
        "linked_artifact_ids": sorted(linked_artifact_ids),
        "intent_mapping_count": intent_mapping_count,
        "intent_mapping_ids": sorted(intent_mapping_ids),
        "semantic_descriptors": sorted(semantic_descriptors),
        "target_realms": sorted(target_realms),
        "target_descriptors": sorted(target_descriptors),
        "interpretation_record_count": interpretation_record_count,
        "interpretation_record_ids": sorted(interpretation_record_ids),
        "interpretation_artifact_ids": sorted(interpretation_artifact_ids),
        "inferred_descriptors": sorted(inferred_descriptors),
        "ambiguity_note_count": ambiguity_note_count,
        "revision_trace_count": revision_trace_count,
        "revision_ids": sorted(revision_ids),
        "affected_realms": sorted(affected_realms),
        "requested_change_count": requested_change_count,
        "applied_change_count": applied_change_count,
        "confidence_count": len(confidence_values),
    }
    if confidence_values:
        stats["average_confidence"] = sum(confidence_values) / len(confidence_values)

    normalized_document = _deep_copy_document(document)
    normalized_document.setdefault("mrwif_version", MRWIF_VERSION)
    normalized_document.setdefault("intent_mappings", [])
    normalized_document.setdefault("interpretation_records", [])
    normalized_document.setdefault("revision_traces", [])

    return MRWIFSpecValidationReport(
        spec=source,
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        stats=stats,
        normalized_document=normalized_document if not errors else None,
    )