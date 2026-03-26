from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import yaml

from ..writer.rwif_writer import load_wave_library
from .analyze import analyze_audio_input
from .analyze import diff_analysis_documents
from .analyze import inspect_analysis_document
from .analyze import validate_analysis_document
from .build import build_arwif_artifact
from .diff import diff_arwif_artifacts
from .export import export_arwif_artifact
from .importing import import_arwif_artifact
from .inspect import inspect_arwif_artifact
from .normalize import normalize_arwif_artifact
from .render import render_arwif_to_wav
from .validation import validate_arwif_artifact
from .validation import validate_arwif_spec


def batch_analyze_audio_inputs(
    input_audio_paths: list[str | Path],
    *,
    analysis_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
    analysis_format: str = "yaml",
    report_format: str = "json",
    start_seconds: float = 0.0,
    duration_seconds: float | None = None,
    channel_mode: str = "preserve",
    target_sample_rate_hz: int | None = None,
    analysis_profile: str = "basic-observation",
    query_text: str | None = None,
    attention_targets: list[str] | None = None,
    retain_targets: list[str] | None = None,
    suppress_targets: list[str] | None = None,
    answer_expectations: list[str] | None = None,
    render_goal: str | None = None,
    transformation_operations: list[str] | None = None,
    primary_output: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not input_audio_paths:
        raise ValueError("at least one input audio path must be provided")
    if analysis_format not in {"json", "yaml"}:
        raise ValueError("analysis_format must be yaml or json")
    if report_format not in {"json", "yaml"}:
        raise ValueError("report_format must be yaml or json")

    analysis_dir_path = Path(analysis_dir) if analysis_dir is not None else None
    report_dir_path = Path(report_dir) if report_dir is not None else None
    if analysis_dir_path is not None:
        analysis_dir_path.mkdir(parents=True, exist_ok=True)
    if report_dir_path is not None:
        report_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_duration_seconds = 0.0
    total_frame_count = 0
    total_estimated_onset_count = 0
    total_section_boundary_count = 0
    total_section_candidate_count = 0
    total_section_transition_count = 0
    total_section_energy_band_counts: Counter[str] = Counter()
    total_section_duration_band_counts: Counter[str] = Counter()
    total_section_position_band_counts: Counter[str] = Counter()
    total_transition_kind_counts: Counter[str] = Counter()
    max_channel_count = 0
    decode_backends: set[str] = set()

    analysis_suffix = ".json" if analysis_format == "json" else ".yaml"
    report_suffix = ".json" if report_format == "json" else ".yaml"

    for input_audio in input_audio_paths:
        input_path = Path(input_audio)
        analysis_output_path = (
            analysis_dir_path / f"{input_path.stem}.analysis{analysis_suffix}"
            if analysis_dir_path is not None
            else None
        )
        report_output_path = (
            report_dir_path / f"{input_path.stem}.report{report_suffix}"
            if report_dir_path is not None
            else None
        )

        try:
            payload = analyze_audio_input(
                input_path,
                output=analysis_output_path,
                report=report_output_path,
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
                channel_mode=channel_mode,
                target_sample_rate_hz=target_sample_rate_hz,
                analysis_profile=analysis_profile,
                query_text=query_text,
                attention_targets=attention_targets,
                retain_targets=retain_targets,
                suppress_targets=suppress_targets,
                answer_expectations=answer_expectations,
                render_goal=render_goal,
                transformation_operations=transformation_operations,
                primary_output=primary_output,
            )
        except ValueError as exc:
            payload = {
                "command": "arwif-analyze-audio",
                "input_audio": str(input_path),
                "analysis_profile": analysis_profile,
                "analysis_document_output": str(analysis_output_path) if analysis_output_path is not None else None,
                "report_output": str(report_output_path) if report_output_path is not None else None,
                "is_valid": False,
                "message": str(exc),
                "errors": [str(exc)],
                "warnings": [],
            }
            invalid_count += 1
        else:
            valid_count += 1
            total_duration_seconds += float(payload.get("analysis_window", {}).get("duration_seconds", 0.0) or 0.0)
            observation_summary = payload.get("observation_summary") if isinstance(payload.get("observation_summary"), dict) else {}
            total_frame_count += int(observation_summary.get("frame_count", 0) or 0)
            total_estimated_onset_count += int(observation_summary.get("estimated_onset_count", 0) or 0)
            total_section_boundary_count += int(observation_summary.get("section_boundary_count", 0) or 0)
            total_section_candidate_count += int(observation_summary.get("section_candidate_count", 0) or 0)
            total_section_transition_count += int(observation_summary.get("section_transition_count", 0) or 0)
            section_profile_summary = observation_summary.get("section_profile_summary") if isinstance(observation_summary.get("section_profile_summary"), dict) else {}
            transition_profile_summary = observation_summary.get("transition_profile_summary") if isinstance(observation_summary.get("transition_profile_summary"), dict) else {}
            total_section_energy_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("energy_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            total_section_duration_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("duration_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            total_section_position_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("position_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            total_transition_kind_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_profile_summary.get("transition_kind_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            decoded_audio = payload.get("decoded_audio") if isinstance(payload.get("decoded_audio"), dict) else {}
            max_channel_count = max(max_channel_count, int(decoded_audio.get("channel_count", 0) or 0))
            decode_backend = decoded_audio.get("decode_backend")
            if isinstance(decode_backend, str) and decode_backend:
                decode_backends.add(decode_backend)

        results.append(payload)

    payload = {
        "audio_inputs_processed": len(input_audio_paths),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "analysis_profile": analysis_profile,
        "analysis_dir": str(analysis_dir_path) if analysis_dir_path is not None else None,
        "report_dir": str(report_dir_path) if report_dir_path is not None else None,
        "analysis_format": analysis_format if analysis_dir_path is not None else None,
        "report_format": report_format if report_dir_path is not None else None,
        "attention_contract": {
            "query_text": query_text,
            "attention_targets": attention_targets or [],
            "retain_targets": retain_targets or [],
            "suppress_targets": suppress_targets or [],
            "answer_expectations": answer_expectations or [],
            "render_goal": render_goal,
        },
        "transformation_intent": {
            "operations": transformation_operations or [],
            "primary_output": primary_output,
        },
        "total_duration_seconds": total_duration_seconds,
        "total_frame_count": total_frame_count,
        "total_estimated_onset_count": total_estimated_onset_count,
        "total_section_boundary_count": total_section_boundary_count,
        "total_section_candidate_count": total_section_candidate_count,
        "total_section_transition_count": total_section_transition_count,
        "total_section_energy_band_counts": dict(sorted(total_section_energy_band_counts.items())),
        "total_section_duration_band_counts": dict(sorted(total_section_duration_band_counts.items())),
        "total_section_position_band_counts": dict(sorted(total_section_position_band_counts.items())),
        "total_transition_kind_counts": dict(sorted(total_transition_kind_counts.items())),
        "max_channel_count": max_channel_count,
        "decode_backends": sorted(decode_backends),
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        aggregate_format = _resolve_auxiliary_format(output_path, label="batch audio analysis output")
        _write_auxiliary_document(output_path, payload, aggregate_format)
        payload["report_output"] = str(output_path)
        payload["aggregate_report_format"] = aggregate_format

    return payload


def batch_inspect_analysis_documents(
    analysis_document_paths: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not analysis_document_paths:
        raise ValueError("at least one analysis document path must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_onset_map_count = 0
    total_section_boundary_count = 0
    total_section_candidate_count = 0
    total_section_transition_count = 0
    total_source_hypothesis_count = 0
    total_recurring_transition_motif_count = 0
    total_recurring_transition_motif_sequence_count = 0
    total_recurring_transition_motif_chain_count = 0
    total_recurring_transition_motif_phrase_count = 0
    total_recurring_transition_motif_phrase_family_count = 0
    total_recurring_transition_motif_phrase_archetype_count = 0
    total_recurring_transition_motif_phrase_contour_count = 0
    total_recurring_transition_motif_phrase_sweep_count = 0
    total_recurring_transition_motif_phrase_gesture_count = 0
    total_recurring_transition_motif_phrase_mobility_count = 0
    total_source_hypothesis_linked_transition_motif_signature_count = 0
    total_source_hypothesis_linked_transition_motif_sequence_signature_count = 0
    total_source_hypothesis_linked_transition_motif_chain_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_family_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_archetype_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_contour_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_sweep_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_gesture_signature_count = 0
    total_source_hypothesis_linked_transition_motif_phrase_mobility_signature_count = 0
    total_component_group_count = 0
    total_uncertainty_warning_count = 0
    documents_with_attention_contract = 0
    documents_with_transformation_intent = 0
    documents_with_interpretation_layers = 0
    total_interpretation_hypothesis_count = 0
    highest_stable_transition_motif_abstraction_layer_counts: Counter[str] = Counter()
    analysis_profile_counts: Counter[str] = Counter()
    codec_counts: Counter[str] = Counter()
    decode_backend_counts: Counter[str] = Counter()
    observation_layer_name_counts: Counter[str] = Counter()
    interpretation_layer_name_counts: Counter[str] = Counter()
    dominant_section_energy_band_counts: Counter[str] = Counter()
    dominant_transition_kind_counts: Counter[str] = Counter()
    dominant_transition_motif_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_sequence_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_chain_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_family_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_archetype_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_contour_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_sweep_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_gesture_signature_counts: Counter[str] = Counter()
    dominant_transition_motif_phrase_mobility_signature_counts: Counter[str] = Counter()
    source_hypothesis_class_counts: Counter[str] = Counter()
    source_hypothesis_role_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_sequence_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_chain_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_family_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_archetype_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_contour_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_sweep_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_gesture_signature_counts: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_mobility_signature_counts: Counter[str] = Counter()
    attention_target_counts: Counter[str] = Counter()
    retain_target_counts: Counter[str] = Counter()
    suppress_target_counts: Counter[str] = Counter()
    answer_expectation_counts: Counter[str] = Counter()
    render_goal_counts: Counter[str] = Counter()
    transformation_operation_counts: Counter[str] = Counter()
    transformation_primary_output_counts: Counter[str] = Counter()
    total_section_energy_band_counts: Counter[str] = Counter()
    total_section_duration_band_counts: Counter[str] = Counter()
    total_section_position_band_counts: Counter[str] = Counter()
    total_transition_kind_counts: Counter[str] = Counter()
    transition_motif_signature_counts: Counter[str] = Counter()
    transition_motif_sequence_signature_counts: Counter[str] = Counter()
    transition_motif_chain_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_family_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_archetype_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_contour_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_sweep_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_gesture_signature_counts: Counter[str] = Counter()
    transition_motif_phrase_mobility_signature_counts: Counter[str] = Counter()

    for analysis_document in analysis_document_paths:
        document_path = Path(analysis_document)
        try:
            payload = inspect_analysis_document(document_path)
        except ValueError as exc:
            payload = {
                "command": "arwif-inspect-analysis",
                "analysis_document": str(document_path),
                "is_valid": False,
                "message": str(exc),
                "errors": [str(exc)],
                "warnings": [],
            }
            invalid_count += 1
        else:
            valid_count += 1
            total_onset_map_count += int(payload.get("onset_map_count", 0) or 0)
            total_section_boundary_count += int(payload.get("section_boundary_count", 0) or 0)
            total_section_candidate_count += int(payload.get("section_candidate_count", 0) or 0)
            total_section_transition_count += int(payload.get("section_transition_count", 0) or 0)
            total_source_hypothesis_count += int(payload.get("source_hypothesis_count", 0) or 0)
            transition_motif_summary = payload.get("transition_motif_summary") if isinstance(payload.get("transition_motif_summary"), dict) else {}
            total_recurring_transition_motif_count += int(transition_motif_summary.get("recurring_motif_count", 0) or 0)
            transition_motif_sequence_summary = (
                payload.get("transition_motif_sequence_summary")
                if isinstance(payload.get("transition_motif_sequence_summary"), dict)
                else {}
            )
            transition_motif_chain_summary = (
                payload.get("transition_motif_chain_summary")
                if isinstance(payload.get("transition_motif_chain_summary"), dict)
                else {}
            )
            transition_motif_phrase_summary = (
                payload.get("transition_motif_phrase_summary")
                if isinstance(payload.get("transition_motif_phrase_summary"), dict)
                else {}
            )
            transition_motif_phrase_family_summary = (
                payload.get("transition_motif_phrase_family_summary")
                if isinstance(payload.get("transition_motif_phrase_family_summary"), dict)
                else {}
            )
            transition_motif_phrase_archetype_summary = (
                payload.get("transition_motif_phrase_archetype_summary")
                if isinstance(payload.get("transition_motif_phrase_archetype_summary"), dict)
                else {}
            )
            transition_motif_phrase_contour_summary = (
                payload.get("transition_motif_phrase_contour_summary")
                if isinstance(payload.get("transition_motif_phrase_contour_summary"), dict)
                else {}
            )
            transition_motif_phrase_sweep_summary = (
                payload.get("transition_motif_phrase_sweep_summary")
                if isinstance(payload.get("transition_motif_phrase_sweep_summary"), dict)
                else {}
            )
            transition_motif_phrase_gesture_summary = (
                payload.get("transition_motif_phrase_gesture_summary")
                if isinstance(payload.get("transition_motif_phrase_gesture_summary"), dict)
                else {}
            )
            transition_motif_phrase_mobility_summary = (
                payload.get("transition_motif_phrase_mobility_summary")
                if isinstance(payload.get("transition_motif_phrase_mobility_summary"), dict)
                else {}
            )
            total_recurring_transition_motif_sequence_count += int(
                transition_motif_sequence_summary.get("recurring_sequence_count", 0) or 0
            )
            total_recurring_transition_motif_chain_count += int(
                transition_motif_chain_summary.get("recurring_chain_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_count += int(
                transition_motif_phrase_summary.get("recurring_phrase_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_family_count += int(
                transition_motif_phrase_family_summary.get("recurring_family_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_archetype_count += int(
                transition_motif_phrase_archetype_summary.get("recurring_archetype_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_contour_count += int(
                transition_motif_phrase_contour_summary.get("recurring_contour_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_sweep_count += int(
                transition_motif_phrase_sweep_summary.get("recurring_sweep_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_gesture_count += int(
                transition_motif_phrase_gesture_summary.get("recurring_gesture_count", 0) or 0
            )
            total_recurring_transition_motif_phrase_mobility_count += int(
                transition_motif_phrase_mobility_summary.get("recurring_mobility_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_sequence_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_sequence_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_chain_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_chain_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_family_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_family_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_archetype_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_archetype_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_contour_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_contour_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_sweep_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_sweep_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_gesture_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_gesture_signature_count", 0) or 0
            )
            total_source_hypothesis_linked_transition_motif_phrase_mobility_signature_count += int(
                payload.get("source_hypothesis_linked_transition_motif_phrase_mobility_signature_count", 0) or 0
            )
            total_component_group_count += int(payload.get("component_group_count", 0) or 0)
            total_uncertainty_warning_count += int(payload.get("uncertainty_warning_count", 0) or 0)
            attention_contract = payload.get("attention_contract") if isinstance(payload.get("attention_contract"), dict) else {}
            interpretation_layer_names = [
                name for name in payload.get("interpretation_layer_names", []) if isinstance(name, str) and name
            ]
            transformation_intent = payload.get("transformation_intent") if isinstance(payload.get("transformation_intent"), dict) else {}
            interpretation_hypothesis_count = int(payload.get("interpretation_hypothesis_count", 0) or 0)
            if any(attention_contract.values()):
                documents_with_attention_contract += 1
            if interpretation_layer_names or interpretation_hypothesis_count > 0:
                documents_with_interpretation_layers += 1
            if transformation_intent:
                documents_with_transformation_intent += 1
            total_interpretation_hypothesis_count += interpretation_hypothesis_count
            highest_stable_transition_motif_abstraction_layer = (
                payload.get("highest_stable_transition_motif_abstraction_layer")
                if isinstance(payload.get("highest_stable_transition_motif_abstraction_layer"), dict)
                else {}
            )
            frontier_layer = highest_stable_transition_motif_abstraction_layer.get("layer")
            if isinstance(frontier_layer, str) and frontier_layer:
                highest_stable_transition_motif_abstraction_layer_counts.update([frontier_layer])
            source_hypothesis_class_counts.update(
                source_hypothesis_class
                for source_hypothesis_class in payload.get("source_hypothesis_classes", [])
                if isinstance(source_hypothesis_class, str) and source_hypothesis_class
            )
            source_hypothesis_role_counts.update(
                source_hypothesis_role
                for source_hypothesis_role in payload.get("source_hypothesis_roles", [])
                if isinstance(source_hypothesis_role, str) and source_hypothesis_role
            )
            source_hypothesis_linked_transition_motif_signature_counts.update(
                source_hypothesis_linked_transition_motif_signature
                for source_hypothesis_linked_transition_motif_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_signature, str)
                and source_hypothesis_linked_transition_motif_signature
            )
            source_hypothesis_linked_transition_motif_sequence_signature_counts.update(
                source_hypothesis_linked_transition_motif_sequence_signature
                for source_hypothesis_linked_transition_motif_sequence_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_sequence_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_sequence_signature, str)
                and source_hypothesis_linked_transition_motif_sequence_signature
            )
            source_hypothesis_linked_transition_motif_chain_signature_counts.update(
                source_hypothesis_linked_transition_motif_chain_signature
                for source_hypothesis_linked_transition_motif_chain_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_chain_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_chain_signature, str)
                and source_hypothesis_linked_transition_motif_chain_signature
            )
            source_hypothesis_linked_transition_motif_phrase_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_signature
                for source_hypothesis_linked_transition_motif_phrase_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_signature
            )
            source_hypothesis_linked_transition_motif_phrase_family_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_family_signature
                for source_hypothesis_linked_transition_motif_phrase_family_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_family_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_family_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_family_signature
            )
            source_hypothesis_linked_transition_motif_phrase_archetype_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_archetype_signature
                for source_hypothesis_linked_transition_motif_phrase_archetype_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_archetype_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_archetype_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_archetype_signature
            )
            source_hypothesis_linked_transition_motif_phrase_contour_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_contour_signature
                for source_hypothesis_linked_transition_motif_phrase_contour_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_contour_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_contour_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_contour_signature
            )
            source_hypothesis_linked_transition_motif_phrase_sweep_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_sweep_signature
                for source_hypothesis_linked_transition_motif_phrase_sweep_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_sweep_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_sweep_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_sweep_signature
            )
            source_hypothesis_linked_transition_motif_phrase_gesture_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_gesture_signature
                for source_hypothesis_linked_transition_motif_phrase_gesture_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_gesture_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_gesture_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_gesture_signature
            )
            source_hypothesis_linked_transition_motif_phrase_mobility_signature_counts.update(
                source_hypothesis_linked_transition_motif_phrase_mobility_signature
                for source_hypothesis_linked_transition_motif_phrase_mobility_signature in payload.get(
                    "source_hypothesis_linked_transition_motif_phrase_mobility_signatures", []
                )
                if isinstance(source_hypothesis_linked_transition_motif_phrase_mobility_signature, str)
                and source_hypothesis_linked_transition_motif_phrase_mobility_signature
            )

            analysis_profile = payload.get("analysis_profile")
            if isinstance(analysis_profile, str) and analysis_profile:
                analysis_profile_counts.update([analysis_profile])

            observed_audio = payload.get("observed_audio") if isinstance(payload.get("observed_audio"), dict) else {}
            codec = observed_audio.get("codec")
            if isinstance(codec, str) and codec:
                codec_counts.update([codec])

            provenance_summary = payload.get("provenance_summary") if isinstance(payload.get("provenance_summary"), dict) else {}
            decode_backend = provenance_summary.get("decode_backend")
            if isinstance(decode_backend, str) and decode_backend:
                decode_backend_counts.update([decode_backend])

            observation_layer_name_counts.update(
                name for name in payload.get("observation_layer_names", []) if isinstance(name, str) and name
            )
            interpretation_layer_name_counts.update(interpretation_layer_names)
            attention_target_counts.update(
                target
                for target in attention_contract.get("attention_targets", [])
                if isinstance(target, str) and target
            )
            retain_target_counts.update(
                target
                for target in attention_contract.get("retain_targets", [])
                if isinstance(target, str) and target
            )
            suppress_target_counts.update(
                target
                for target in attention_contract.get("suppress_targets", [])
                if isinstance(target, str) and target
            )
            answer_expectation_counts.update(
                expectation
                for expectation in attention_contract.get("answer_expectations", [])
                if isinstance(expectation, str) and expectation
            )
            render_goal = attention_contract.get("render_goal")
            if isinstance(render_goal, str) and render_goal:
                render_goal_counts.update([render_goal])
            transformation_operation_counts.update(
                operation
                for operation in transformation_intent.get("operations", [])
                if isinstance(operation, str) and operation
            )
            primary_output = transformation_intent.get("primary_output")
            if isinstance(primary_output, str) and primary_output:
                transformation_primary_output_counts.update([primary_output])

            section_profile_summary = payload.get("section_profile_summary") if isinstance(payload.get("section_profile_summary"), dict) else {}
            dominant_energy_band = section_profile_summary.get("dominant_energy_band")
            if isinstance(dominant_energy_band, str) and dominant_energy_band:
                dominant_section_energy_band_counts.update([dominant_energy_band])
            total_section_energy_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("energy_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            total_section_duration_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("duration_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            total_section_position_band_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (section_profile_summary.get("position_band_counts") or {}).items()
                    if isinstance(key, str)
                }
            )

            transition_profile_summary = payload.get("transition_profile_summary") if isinstance(payload.get("transition_profile_summary"), dict) else {}
            dominant_transition_kind = transition_profile_summary.get("dominant_transition_kind")
            if isinstance(dominant_transition_kind, str) and dominant_transition_kind:
                dominant_transition_kind_counts.update([dominant_transition_kind])
            total_transition_kind_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_profile_summary.get("transition_kind_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_signature = transition_motif_summary.get("dominant_motif_signature")
            if isinstance(dominant_transition_motif_signature, str) and dominant_transition_motif_signature:
                dominant_transition_motif_signature_counts.update([dominant_transition_motif_signature])
            transition_motif_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_summary.get("motif_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_sequence_signature = transition_motif_sequence_summary.get(
                "dominant_sequence_signature"
            )
            if (
                isinstance(dominant_transition_motif_sequence_signature, str)
                and dominant_transition_motif_sequence_signature
            ):
                dominant_transition_motif_sequence_signature_counts.update(
                    [dominant_transition_motif_sequence_signature]
                )
            transition_motif_sequence_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_sequence_summary.get("sequence_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_chain_signature = transition_motif_chain_summary.get(
                "dominant_chain_signature"
            )
            if isinstance(dominant_transition_motif_chain_signature, str) and dominant_transition_motif_chain_signature:
                dominant_transition_motif_chain_signature_counts.update([dominant_transition_motif_chain_signature])
            transition_motif_chain_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_chain_summary.get("chain_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_phrase_signature = transition_motif_phrase_summary.get(
                "dominant_phrase_signature"
            )
            if isinstance(dominant_transition_motif_phrase_signature, str) and dominant_transition_motif_phrase_signature:
                dominant_transition_motif_phrase_signature_counts.update([dominant_transition_motif_phrase_signature])
            transition_motif_phrase_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_summary.get("phrase_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_phrase_family_signature = transition_motif_phrase_family_summary.get(
                "dominant_family_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_family_signature, str)
                and dominant_transition_motif_phrase_family_signature
            ):
                dominant_transition_motif_phrase_family_signature_counts.update(
                    [dominant_transition_motif_phrase_family_signature]
                )
            transition_motif_phrase_family_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_family_summary.get("family_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_phrase_archetype_signature = transition_motif_phrase_archetype_summary.get(
                "dominant_archetype_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_archetype_signature, str)
                and dominant_transition_motif_phrase_archetype_signature
            ):
                dominant_transition_motif_phrase_archetype_signature_counts.update(
                    [dominant_transition_motif_phrase_archetype_signature]
                )
            transition_motif_phrase_archetype_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_archetype_summary.get("archetype_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_phrase_contour_signature = transition_motif_phrase_contour_summary.get(
                "dominant_contour_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_contour_signature, str)
                and dominant_transition_motif_phrase_contour_signature
            ):
                dominant_transition_motif_phrase_contour_signature_counts.update(
                    [dominant_transition_motif_phrase_contour_signature]
                )
            transition_motif_phrase_contour_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_contour_summary.get("contour_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            dominant_transition_motif_phrase_sweep_signature = transition_motif_phrase_sweep_summary.get(
                "dominant_sweep_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_sweep_signature, str)
                and dominant_transition_motif_phrase_sweep_signature
            ):
                dominant_transition_motif_phrase_sweep_signature_counts.update(
                    [dominant_transition_motif_phrase_sweep_signature]
                )
            dominant_transition_motif_phrase_gesture_signature = transition_motif_phrase_gesture_summary.get(
                "dominant_gesture_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_gesture_signature, str)
                and dominant_transition_motif_phrase_gesture_signature
            ):
                dominant_transition_motif_phrase_gesture_signature_counts.update(
                    [dominant_transition_motif_phrase_gesture_signature]
                )
            dominant_transition_motif_phrase_mobility_signature = transition_motif_phrase_mobility_summary.get(
                "dominant_mobility_signature"
            )
            if (
                isinstance(dominant_transition_motif_phrase_mobility_signature, str)
                and dominant_transition_motif_phrase_mobility_signature
            ):
                dominant_transition_motif_phrase_mobility_signature_counts.update(
                    [dominant_transition_motif_phrase_mobility_signature]
                )
            transition_motif_phrase_sweep_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_sweep_summary.get("sweep_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            transition_motif_phrase_gesture_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_gesture_summary.get("gesture_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )
            transition_motif_phrase_mobility_signature_counts.update(
                {
                    str(key): int(value or 0)
                    for key, value in (transition_motif_phrase_mobility_summary.get("mobility_signature_counts") or {}).items()
                    if isinstance(key, str)
                }
            )

        results.append(payload)

    payload = {
        "analysis_documents_processed": len(analysis_document_paths),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "analysis_profile_counts": dict(sorted(analysis_profile_counts.items())),
        "codec_counts": dict(sorted(codec_counts.items())),
        "decode_backend_counts": dict(sorted(decode_backend_counts.items())),
        "observation_layer_name_counts": dict(sorted(observation_layer_name_counts.items())),
        "documents_with_attention_contract": documents_with_attention_contract,
        "documents_with_interpretation_layers": documents_with_interpretation_layers,
        "documents_with_transformation_intent": documents_with_transformation_intent,
        "total_interpretation_hypothesis_count": total_interpretation_hypothesis_count,
        "interpretation_layer_name_counts": dict(sorted(interpretation_layer_name_counts.items())),
        "attention_target_counts": dict(sorted(attention_target_counts.items())),
        "retain_target_counts": dict(sorted(retain_target_counts.items())),
        "suppress_target_counts": dict(sorted(suppress_target_counts.items())),
        "answer_expectation_counts": dict(sorted(answer_expectation_counts.items())),
        "render_goal_counts": dict(sorted(render_goal_counts.items())),
        "transformation_operation_counts": dict(sorted(transformation_operation_counts.items())),
        "transformation_primary_output_counts": dict(sorted(transformation_primary_output_counts.items())),
        "total_onset_map_count": total_onset_map_count,
        "total_section_boundary_count": total_section_boundary_count,
        "total_section_candidate_count": total_section_candidate_count,
        "total_section_transition_count": total_section_transition_count,
        "total_source_hypothesis_count": total_source_hypothesis_count,
        "total_recurring_transition_motif_count": total_recurring_transition_motif_count,
        "total_recurring_transition_motif_sequence_count": total_recurring_transition_motif_sequence_count,
        "total_recurring_transition_motif_chain_count": total_recurring_transition_motif_chain_count,
        "total_recurring_transition_motif_phrase_count": total_recurring_transition_motif_phrase_count,
        "total_recurring_transition_motif_phrase_family_count": total_recurring_transition_motif_phrase_family_count,
        "total_recurring_transition_motif_phrase_archetype_count": total_recurring_transition_motif_phrase_archetype_count,
        "total_recurring_transition_motif_phrase_contour_count": total_recurring_transition_motif_phrase_contour_count,
        "total_recurring_transition_motif_phrase_sweep_count": total_recurring_transition_motif_phrase_sweep_count,
        "total_recurring_transition_motif_phrase_gesture_count": total_recurring_transition_motif_phrase_gesture_count,
        "total_recurring_transition_motif_phrase_mobility_count": total_recurring_transition_motif_phrase_mobility_count,
        "transition_motif_phrase_abstraction_totals": {
            "recurring_counts": {
                "phrase": total_recurring_transition_motif_phrase_count,
                "family": total_recurring_transition_motif_phrase_family_count,
                "archetype": total_recurring_transition_motif_phrase_archetype_count,
                "contour": total_recurring_transition_motif_phrase_contour_count,
                "sweep": total_recurring_transition_motif_phrase_sweep_count,
                "gesture": total_recurring_transition_motif_phrase_gesture_count,
                "mobility": total_recurring_transition_motif_phrase_mobility_count,
            },
            "occurrence_counts": {
                "phrase": sum(transition_motif_phrase_signature_counts.values()),
                "family": sum(transition_motif_phrase_family_signature_counts.values()),
                "archetype": sum(transition_motif_phrase_archetype_signature_counts.values()),
                "contour": sum(transition_motif_phrase_contour_signature_counts.values()),
                "sweep": sum(transition_motif_phrase_sweep_signature_counts.values()),
                "gesture": sum(transition_motif_phrase_gesture_signature_counts.values()),
                "mobility": sum(transition_motif_phrase_mobility_signature_counts.values()),
            },
        },
        "highest_stable_transition_motif_abstraction_layer_counts": dict(
            sorted(highest_stable_transition_motif_abstraction_layer_counts.items())
        ),
        "total_source_hypothesis_linked_transition_motif_signature_count": total_source_hypothesis_linked_transition_motif_signature_count,
        "total_source_hypothesis_linked_transition_motif_sequence_signature_count": total_source_hypothesis_linked_transition_motif_sequence_signature_count,
        "total_source_hypothesis_linked_transition_motif_chain_signature_count": total_source_hypothesis_linked_transition_motif_chain_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_signature_count": total_source_hypothesis_linked_transition_motif_phrase_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_family_signature_count": total_source_hypothesis_linked_transition_motif_phrase_family_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_archetype_signature_count": total_source_hypothesis_linked_transition_motif_phrase_archetype_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_contour_signature_count": total_source_hypothesis_linked_transition_motif_phrase_contour_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_sweep_signature_count": total_source_hypothesis_linked_transition_motif_phrase_sweep_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_gesture_signature_count": total_source_hypothesis_linked_transition_motif_phrase_gesture_signature_count,
        "total_source_hypothesis_linked_transition_motif_phrase_mobility_signature_count": total_source_hypothesis_linked_transition_motif_phrase_mobility_signature_count,
        "source_hypothesis_class_counts": dict(sorted(source_hypothesis_class_counts.items())),
        "source_hypothesis_role_counts": dict(sorted(source_hypothesis_role_counts.items())),
        "source_hypothesis_linked_transition_motif_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_sequence_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_sequence_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_chain_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_chain_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_family_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_family_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_archetype_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_contour_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_contour_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_sweep_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_gesture_signature_counts.items())
        ),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signature_counts": dict(
            sorted(source_hypothesis_linked_transition_motif_phrase_mobility_signature_counts.items())
        ),
        "total_component_group_count": total_component_group_count,
        "total_uncertainty_warning_count": total_uncertainty_warning_count,
        "dominant_section_energy_band_counts": dict(sorted(dominant_section_energy_band_counts.items())),
        "dominant_transition_kind_counts": dict(sorted(dominant_transition_kind_counts.items())),
        "dominant_transition_motif_signature_counts": dict(sorted(dominant_transition_motif_signature_counts.items())),
        "dominant_transition_motif_sequence_signature_counts": dict(
            sorted(dominant_transition_motif_sequence_signature_counts.items())
        ),
        "dominant_transition_motif_chain_signature_counts": dict(
            sorted(dominant_transition_motif_chain_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_family_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_family_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_archetype_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_archetype_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_contour_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_contour_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_sweep_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_sweep_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_gesture_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_gesture_signature_counts.items())
        ),
        "dominant_transition_motif_phrase_mobility_signature_counts": dict(
            sorted(dominant_transition_motif_phrase_mobility_signature_counts.items())
        ),
        "total_section_energy_band_counts": dict(sorted(total_section_energy_band_counts.items())),
        "total_section_duration_band_counts": dict(sorted(total_section_duration_band_counts.items())),
        "total_section_position_band_counts": dict(sorted(total_section_position_band_counts.items())),
        "total_transition_kind_counts": dict(sorted(total_transition_kind_counts.items())),
        "transition_motif_signature_counts": dict(sorted(transition_motif_signature_counts.items())),
        "transition_motif_sequence_signature_counts": dict(sorted(transition_motif_sequence_signature_counts.items())),
        "transition_motif_chain_signature_counts": dict(sorted(transition_motif_chain_signature_counts.items())),
        "transition_motif_phrase_signature_counts": dict(sorted(transition_motif_phrase_signature_counts.items())),
        "transition_motif_phrase_family_signature_counts": dict(
            sorted(transition_motif_phrase_family_signature_counts.items())
        ),
        "transition_motif_phrase_archetype_signature_counts": dict(
            sorted(transition_motif_phrase_archetype_signature_counts.items())
        ),
        "transition_motif_phrase_contour_signature_counts": dict(
            sorted(transition_motif_phrase_contour_signature_counts.items())
        ),
        "transition_motif_phrase_sweep_signature_counts": dict(
            sorted(transition_motif_phrase_sweep_signature_counts.items())
        ),
        "transition_motif_phrase_gesture_signature_counts": dict(
            sorted(transition_motif_phrase_gesture_signature_counts.items())
        ),
        "transition_motif_phrase_mobility_signature_counts": dict(
            sorted(transition_motif_phrase_mobility_signature_counts.items())
        ),
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch analysis inspection output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_validate_analysis_documents(
    analysis_document_paths: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not analysis_document_paths:
        raise ValueError("at least one analysis document path must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_observation_layer_count = 0
    total_source_hypothesis_count = 0
    total_component_layer_count = 0
    total_reconstructable_output_count = 0
    total_uncertainty_warning_count = 0
    documents_with_attention_contract = 0
    documents_with_interpretation_layers = 0
    documents_with_transformation_intent = 0
    analysis_profile_counts: Counter[str] = Counter()

    for analysis_document in analysis_document_paths:
        report = validate_analysis_document(Path(analysis_document))
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        stats = report.stats
        analysis_profile = stats.get("analysis_profile")
        if isinstance(analysis_profile, str) and analysis_profile:
            analysis_profile_counts.update([analysis_profile])
        total_observation_layer_count += int(stats.get("observation_layer_count", 0) or 0)
        total_source_hypothesis_count += int(stats.get("source_hypothesis_count", 0) or 0)
        total_component_layer_count += int(stats.get("component_layer_count", 0) or 0)
        total_reconstructable_output_count += int(stats.get("reconstructable_output_count", 0) or 0)
        total_uncertainty_warning_count += int(stats.get("uncertainty_warning_count", 0) or 0)
        documents_with_attention_contract += int(bool(stats.get("has_attention_contract", False)))
        documents_with_interpretation_layers += int(bool(stats.get("has_interpretation_layers", False)))
        documents_with_transformation_intent += int(bool(stats.get("has_transformation_intent", False)))
        results.append(payload)

    payload = {
        "analysis_documents_processed": len(analysis_document_paths),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "analysis_profile_counts": dict(sorted(analysis_profile_counts.items())),
        "total_observation_layer_count": total_observation_layer_count,
        "total_source_hypothesis_count": total_source_hypothesis_count,
        "total_component_layer_count": total_component_layer_count,
        "total_reconstructable_output_count": total_reconstructable_output_count,
        "total_uncertainty_warning_count": total_uncertainty_warning_count,
        "documents_with_attention_contract": documents_with_attention_contract,
        "documents_with_interpretation_layers": documents_with_interpretation_layers,
        "documents_with_transformation_intent": documents_with_transformation_intent,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch analysis validation output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_diff_analysis_documents(
    left_documents: list[str | Path],
    right_documents: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not left_documents or not right_documents:
        raise ValueError("at least one left and one right analysis document must be provided")
    if len(left_documents) != len(right_documents):
        raise ValueError("left and right analysis document collections must have the same length")

    results: list[dict[str, Any]] = []
    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0

    metadata_counter: Counter[str] = Counter()
    observed_audio_counter: Counter[str] = Counter()
    analysis_window_counter: Counter[str] = Counter()
    attention_contract_counter: Counter[str] = Counter()
    transformation_intent_counter: Counter[str] = Counter()
    basic_observation_counter: Counter[str] = Counter()
    observation_layers_added_counter: Counter[str] = Counter()
    observation_layers_removed_counter: Counter[str] = Counter()
    interpretation_layers_added_counter: Counter[str] = Counter()
    interpretation_layers_removed_counter: Counter[str] = Counter()
    source_hypothesis_classes_added_counter: Counter[str] = Counter()
    source_hypothesis_classes_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_sequence_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_sequence_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_chain_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_chain_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_family_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_counter: Counter[str] = Counter()
    source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_signatures_added_counter: Counter[str] = Counter()
    transition_motif_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_sequence_signatures_added_counter: Counter[str] = Counter()
    transition_motif_sequence_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_chain_signatures_added_counter: Counter[str] = Counter()
    transition_motif_chain_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_family_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_family_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_archetype_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_archetype_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_contour_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_contour_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_sweep_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_sweep_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_gesture_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_gesture_signatures_removed_counter: Counter[str] = Counter()
    transition_motif_phrase_mobility_signatures_added_counter: Counter[str] = Counter()
    transition_motif_phrase_mobility_signatures_removed_counter: Counter[str] = Counter()
    metadata_pair_indexes: dict[str, list[int]] = {}
    observed_audio_pair_indexes: dict[str, list[int]] = {}
    analysis_window_pair_indexes: dict[str, list[int]] = {}
    attention_contract_pair_indexes: dict[str, list[int]] = {}
    transformation_intent_pair_indexes: dict[str, list[int]] = {}
    basic_observation_pair_indexes: dict[str, list[int]] = {}
    observation_layers_added_pair_indexes: dict[str, list[int]] = {}
    observation_layers_removed_pair_indexes: dict[str, list[int]] = {}
    interpretation_layers_added_pair_indexes: dict[str, list[int]] = {}
    interpretation_layers_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_classes_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_classes_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_sequence_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_sequence_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_chain_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_chain_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_family_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_pair_indexes: dict[str, list[int]] = {}
    source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_sequence_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_sequence_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_chain_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_chain_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_family_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_family_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_archetype_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_archetype_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_contour_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_contour_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_sweep_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_sweep_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_gesture_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_gesture_signatures_removed_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_mobility_signatures_added_pair_indexes: dict[str, list[int]] = {}
    transition_motif_phrase_mobility_signatures_removed_pair_indexes: dict[str, list[int]] = {}

    source_hypothesis_count_delta_pairs = 0
    total_source_hypothesis_count_delta = 0
    interpretation_hypothesis_count_delta_pairs = 0
    total_interpretation_hypothesis_count_delta = 0
    recurring_transition_motif_count_delta_pairs = 0
    total_recurring_transition_motif_count_delta = 0
    recurring_transition_motif_sequence_count_delta_pairs = 0
    total_recurring_transition_motif_sequence_count_delta = 0
    recurring_transition_motif_chain_count_delta_pairs = 0
    total_recurring_transition_motif_chain_count_delta = 0
    recurring_transition_motif_phrase_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_count_delta = 0
    recurring_transition_motif_phrase_family_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_family_count_delta = 0
    recurring_transition_motif_phrase_archetype_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_archetype_count_delta = 0
    recurring_transition_motif_phrase_contour_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_contour_count_delta = 0
    recurring_transition_motif_phrase_sweep_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_sweep_count_delta = 0
    recurring_transition_motif_phrase_gesture_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_gesture_count_delta = 0
    recurring_transition_motif_phrase_mobility_count_delta_pairs = 0
    total_recurring_transition_motif_phrase_mobility_count_delta = 0
    component_group_count_delta_pairs = 0
    total_component_group_count_delta = 0
    onset_map_count_delta_pairs = 0
    total_onset_map_count_delta = 0
    section_boundary_count_delta_pairs = 0
    total_section_boundary_count_delta = 0
    section_candidate_count_delta_pairs = 0
    total_section_candidate_count_delta = 0
    section_transition_count_delta_pairs = 0
    total_section_transition_count_delta = 0
    uncertainty_warning_count_delta_pairs = 0
    total_uncertainty_warning_count_delta = 0
    highest_stable_transition_motif_abstraction_layer_change_pairs = 0
    highest_stable_transition_motif_abstraction_layer_rise_pairs = 0
    highest_stable_transition_motif_abstraction_layer_fall_pairs = 0
    total_highest_stable_transition_motif_abstraction_layer_step_delta = 0
    highest_stable_transition_motif_abstraction_layer_recurring_count_delta_pairs = 0
    total_highest_stable_transition_motif_abstraction_layer_recurring_count_delta = 0
    highest_stable_transition_motif_abstraction_layer_occurrence_count_delta_pairs = 0
    total_highest_stable_transition_motif_abstraction_layer_occurrence_count_delta = 0
    first_scene_hypothesis_change_pairs = 0
    first_communicative_hypothesis_change_pairs = 0
    transformation_intent_change_pairs = 0

    for pair_index, (left_document, right_document) in enumerate(zip(left_documents, right_documents, strict=True)):
        left_path = Path(left_document)
        right_path = Path(right_document)
        try:
            payload = diff_analysis_documents(left_path, right_path)
        except ValueError as exc:
            payload = {
                "command": "arwif-diff-analysis",
                "left": str(left_path),
                "right": str(right_path),
                "left_valid": False,
                "right_valid": False,
                "pair_changed": False,
                "is_valid": False,
                "message": str(exc),
                "errors": [str(exc)],
                "warnings": [],
            }
            invalid_pairs += 1
            unchanged_pairs += 1
            payload["pair_index"] = pair_index
            results.append(payload)
            continue

        payload["pair_index"] = pair_index
        pair_changed = bool(payload.get("pair_changed", False))
        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not payload.get("left_valid", False) or not payload.get("right_valid", False):
            invalid_pairs += 1

        for field in _mapping_keys(payload.get("metadata_changes")):
            metadata_counter[field] += 1
            metadata_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _mapping_keys(payload.get("observed_audio_changes")):
            observed_audio_counter[field] += 1
            observed_audio_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _mapping_keys(payload.get("analysis_window_changes")):
            analysis_window_counter[field] += 1
            analysis_window_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _mapping_keys(payload.get("attention_contract_changes")):
            attention_contract_counter[field] += 1
            attention_contract_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _mapping_keys(payload.get("transformation_intent_changes")):
            transformation_intent_counter[field] += 1
            transformation_intent_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _flatten_change_field_paths(payload.get("basic_observation_changes"), prefix=""):
            basic_observation_counter[field] += 1
            basic_observation_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("observation_layer_changes")).get("added")):
            observation_layers_added_counter[field] += 1
            observation_layers_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("observation_layer_changes")).get("removed")):
            observation_layers_removed_counter[field] += 1
            observation_layers_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("interpretation_layer_changes")).get("added")):
            interpretation_layers_added_counter[field] += 1
            interpretation_layers_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("interpretation_layer_changes")).get("removed")):
            interpretation_layers_removed_counter[field] += 1
            interpretation_layers_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("source_hypothesis_class_changes")).get("added")):
            source_hypothesis_classes_added_counter[field] += 1
            source_hypothesis_classes_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("source_hypothesis_class_changes")).get("removed")):
            source_hypothesis_classes_removed_counter[field] += 1
            source_hypothesis_classes_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_sequence_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_sequence_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_sequence_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_sequence_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_sequence_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_sequence_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_chain_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_chain_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_chain_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_chain_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_chain_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_chain_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_family_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_family_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_family_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_family_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_archetype_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_archetype_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_contour_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_contour_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_sweep_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_sweep_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_gesture_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_gesture_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_mobility_signature_changes")).get("added")
        ):
            source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(
            _mapping_optional(payload.get("source_hypothesis_linked_transition_motif_phrase_mobility_signature_changes")).get("removed")
        ):
            source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_counter[field] += 1
            source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_signature_changes")).get("added")):
            transition_motif_signatures_added_counter[field] += 1
            transition_motif_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_signature_changes")).get("removed")):
            transition_motif_signatures_removed_counter[field] += 1
            transition_motif_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_sequence_signature_changes")).get("added")):
            transition_motif_sequence_signatures_added_counter[field] += 1
            transition_motif_sequence_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_sequence_signature_changes")).get("removed")):
            transition_motif_sequence_signatures_removed_counter[field] += 1
            transition_motif_sequence_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_chain_signature_changes")).get("added")):
            transition_motif_chain_signatures_added_counter[field] += 1
            transition_motif_chain_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_chain_signature_changes")).get("removed")):
            transition_motif_chain_signatures_removed_counter[field] += 1
            transition_motif_chain_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_signature_changes")).get("added")):
            transition_motif_phrase_signatures_added_counter[field] += 1
            transition_motif_phrase_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_signature_changes")).get("removed")):
            transition_motif_phrase_signatures_removed_counter[field] += 1
            transition_motif_phrase_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_family_signature_changes")).get("added")):
            transition_motif_phrase_family_signatures_added_counter[field] += 1
            transition_motif_phrase_family_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_family_signature_changes")).get("removed")):
            transition_motif_phrase_family_signatures_removed_counter[field] += 1
            transition_motif_phrase_family_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_archetype_signature_changes")).get("added")):
            transition_motif_phrase_archetype_signatures_added_counter[field] += 1
            transition_motif_phrase_archetype_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_archetype_signature_changes")).get("removed")):
            transition_motif_phrase_archetype_signatures_removed_counter[field] += 1
            transition_motif_phrase_archetype_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_contour_signature_changes")).get("added")):
            transition_motif_phrase_contour_signatures_added_counter[field] += 1
            transition_motif_phrase_contour_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_contour_signature_changes")).get("removed")):
            transition_motif_phrase_contour_signatures_removed_counter[field] += 1
            transition_motif_phrase_contour_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_sweep_signature_changes")).get("added")):
            transition_motif_phrase_sweep_signatures_added_counter[field] += 1
            transition_motif_phrase_sweep_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_sweep_signature_changes")).get("removed")):
            transition_motif_phrase_sweep_signatures_removed_counter[field] += 1
            transition_motif_phrase_sweep_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_gesture_signature_changes")).get("added")):
            transition_motif_phrase_gesture_signatures_added_counter[field] += 1
            transition_motif_phrase_gesture_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_gesture_signature_changes")).get("removed")):
            transition_motif_phrase_gesture_signatures_removed_counter[field] += 1
            transition_motif_phrase_gesture_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_mobility_signature_changes")).get("added")):
            transition_motif_phrase_mobility_signatures_added_counter[field] += 1
            transition_motif_phrase_mobility_signatures_added_pair_indexes.setdefault(field, []).append(pair_index)
        for field in _string_list(_mapping_optional(payload.get("transition_motif_phrase_mobility_signature_changes")).get("removed")):
            transition_motif_phrase_mobility_signatures_removed_counter[field] += 1
            transition_motif_phrase_mobility_signatures_removed_pair_indexes.setdefault(field, []).append(pair_index)

        source_hypothesis_count_delta = int(payload.get("source_hypothesis_count_delta", 0) or 0)
        total_source_hypothesis_count_delta += source_hypothesis_count_delta
        if source_hypothesis_count_delta != 0:
            source_hypothesis_count_delta_pairs += 1

        interpretation_hypothesis_count_delta = int(payload.get("interpretation_hypothesis_count_delta", 0) or 0)
        total_interpretation_hypothesis_count_delta += interpretation_hypothesis_count_delta
        if interpretation_hypothesis_count_delta != 0:
            interpretation_hypothesis_count_delta_pairs += 1

        recurring_transition_motif_count_delta = int(payload.get("recurring_transition_motif_count_delta", 0) or 0)
        total_recurring_transition_motif_count_delta += recurring_transition_motif_count_delta
        if recurring_transition_motif_count_delta != 0:
            recurring_transition_motif_count_delta_pairs += 1

        recurring_transition_motif_sequence_count_delta = int(
            payload.get("recurring_transition_motif_sequence_count_delta", 0) or 0
        )
        total_recurring_transition_motif_sequence_count_delta += recurring_transition_motif_sequence_count_delta
        if recurring_transition_motif_sequence_count_delta != 0:
            recurring_transition_motif_sequence_count_delta_pairs += 1

        recurring_transition_motif_chain_count_delta = int(
            payload.get("recurring_transition_motif_chain_count_delta", 0) or 0
        )
        total_recurring_transition_motif_chain_count_delta += recurring_transition_motif_chain_count_delta
        if recurring_transition_motif_chain_count_delta != 0:
            recurring_transition_motif_chain_count_delta_pairs += 1

        recurring_transition_motif_phrase_count_delta = int(
            payload.get("recurring_transition_motif_phrase_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_count_delta += recurring_transition_motif_phrase_count_delta
        if recurring_transition_motif_phrase_count_delta != 0:
            recurring_transition_motif_phrase_count_delta_pairs += 1

        recurring_transition_motif_phrase_family_count_delta = int(
            payload.get("recurring_transition_motif_phrase_family_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_family_count_delta += recurring_transition_motif_phrase_family_count_delta
        if recurring_transition_motif_phrase_family_count_delta != 0:
            recurring_transition_motif_phrase_family_count_delta_pairs += 1
        recurring_transition_motif_phrase_archetype_count_delta = int(
            payload.get("recurring_transition_motif_phrase_archetype_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_archetype_count_delta += recurring_transition_motif_phrase_archetype_count_delta
        if recurring_transition_motif_phrase_archetype_count_delta != 0:
            recurring_transition_motif_phrase_archetype_count_delta_pairs += 1
        recurring_transition_motif_phrase_contour_count_delta = int(
            payload.get("recurring_transition_motif_phrase_contour_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_contour_count_delta += recurring_transition_motif_phrase_contour_count_delta
        if recurring_transition_motif_phrase_contour_count_delta != 0:
            recurring_transition_motif_phrase_contour_count_delta_pairs += 1
        recurring_transition_motif_phrase_sweep_count_delta = int(
            payload.get("recurring_transition_motif_phrase_sweep_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_sweep_count_delta += recurring_transition_motif_phrase_sweep_count_delta
        if recurring_transition_motif_phrase_sweep_count_delta != 0:
            recurring_transition_motif_phrase_sweep_count_delta_pairs += 1
        recurring_transition_motif_phrase_gesture_count_delta = int(
            payload.get("recurring_transition_motif_phrase_gesture_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_gesture_count_delta += recurring_transition_motif_phrase_gesture_count_delta
        if recurring_transition_motif_phrase_gesture_count_delta != 0:
            recurring_transition_motif_phrase_gesture_count_delta_pairs += 1
        recurring_transition_motif_phrase_mobility_count_delta = int(
            payload.get("recurring_transition_motif_phrase_mobility_count_delta", 0) or 0
        )
        total_recurring_transition_motif_phrase_mobility_count_delta += recurring_transition_motif_phrase_mobility_count_delta
        if recurring_transition_motif_phrase_mobility_count_delta != 0:
            recurring_transition_motif_phrase_mobility_count_delta_pairs += 1

        component_group_count_delta = int(payload.get("component_group_count_delta", 0) or 0)
        total_component_group_count_delta += component_group_count_delta
        if component_group_count_delta != 0:
            component_group_count_delta_pairs += 1

        onset_map_count_delta = int(payload.get("onset_map_count_delta", 0) or 0)
        total_onset_map_count_delta += onset_map_count_delta
        if onset_map_count_delta != 0:
            onset_map_count_delta_pairs += 1

        section_boundary_count_delta = int(payload.get("section_boundary_count_delta", 0) or 0)
        total_section_boundary_count_delta += section_boundary_count_delta
        if section_boundary_count_delta != 0:
            section_boundary_count_delta_pairs += 1

        section_candidate_count_delta = int(payload.get("section_candidate_count_delta", 0) or 0)
        total_section_candidate_count_delta += section_candidate_count_delta
        if section_candidate_count_delta != 0:
            section_candidate_count_delta_pairs += 1

        section_transition_count_delta = int(payload.get("section_transition_count_delta", 0) or 0)
        total_section_transition_count_delta += section_transition_count_delta
        if section_transition_count_delta != 0:
            section_transition_count_delta_pairs += 1

        uncertainty_warning_count_delta = int(payload.get("uncertainty_warning_count_delta", 0) or 0)
        total_uncertainty_warning_count_delta += uncertainty_warning_count_delta
        if uncertainty_warning_count_delta != 0:
            uncertainty_warning_count_delta_pairs += 1

        highest_stable_layer_change = _mapping_optional(
            payload.get("highest_stable_transition_motif_abstraction_layer_change")
        )
        highest_stable_layer_step_delta = int(highest_stable_layer_change.get("layer_step_delta", 0) or 0)
        total_highest_stable_transition_motif_abstraction_layer_step_delta += highest_stable_layer_step_delta
        if bool(highest_stable_layer_change.get("layer_changed", False)):
            highest_stable_transition_motif_abstraction_layer_change_pairs += 1

        highest_stable_layer_direction = str(highest_stable_layer_change.get("direction", "unchanged") or "unchanged")
        if highest_stable_layer_direction == "rose":
            highest_stable_transition_motif_abstraction_layer_rise_pairs += 1
        elif highest_stable_layer_direction == "fell":
            highest_stable_transition_motif_abstraction_layer_fall_pairs += 1

        highest_stable_layer_recurring_count_delta = int(highest_stable_layer_change.get("recurring_count_delta", 0) or 0)
        total_highest_stable_transition_motif_abstraction_layer_recurring_count_delta += (
            highest_stable_layer_recurring_count_delta
        )
        if highest_stable_layer_recurring_count_delta != 0:
            highest_stable_transition_motif_abstraction_layer_recurring_count_delta_pairs += 1

        highest_stable_layer_occurrence_count_delta = int(highest_stable_layer_change.get("occurrence_count_delta", 0) or 0)
        total_highest_stable_transition_motif_abstraction_layer_occurrence_count_delta += (
            highest_stable_layer_occurrence_count_delta
        )
        if highest_stable_layer_occurrence_count_delta != 0:
            highest_stable_transition_motif_abstraction_layer_occurrence_count_delta_pairs += 1

        if _mapping_optional(payload.get("first_scene_hypothesis_changes")):
            first_scene_hypothesis_change_pairs += 1
        if _mapping_optional(payload.get("first_communicative_hypothesis_changes")):
            first_communicative_hypothesis_change_pairs += 1
        if _mapping_optional(payload.get("transformation_intent_changes")):
            transformation_intent_change_pairs += 1

        results.append(payload)

    payload = {
        "pairs_compared": len(left_documents),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "is_valid": invalid_pairs == 0,
        "results": results,
        "metadata_field_frequencies": _rank_frequency_items(metadata_counter, metadata_pair_indexes, "field", changed_pairs),
        "observed_audio_field_frequencies": _rank_frequency_items(observed_audio_counter, observed_audio_pair_indexes, "field", changed_pairs),
        "analysis_window_field_frequencies": _rank_frequency_items(analysis_window_counter, analysis_window_pair_indexes, "field", changed_pairs),
        "attention_contract_field_frequencies": _rank_frequency_items(attention_contract_counter, attention_contract_pair_indexes, "field", changed_pairs),
        "transformation_intent_field_frequencies": _rank_frequency_items(transformation_intent_counter, transformation_intent_pair_indexes, "field", changed_pairs),
        "basic_observation_field_frequencies": _rank_frequency_items(basic_observation_counter, basic_observation_pair_indexes, "field", changed_pairs),
        "observation_layers_added_frequencies": _rank_frequency_items(observation_layers_added_counter, observation_layers_added_pair_indexes, "layer", changed_pairs),
        "observation_layers_removed_frequencies": _rank_frequency_items(observation_layers_removed_counter, observation_layers_removed_pair_indexes, "layer", changed_pairs),
        "interpretation_layers_added_frequencies": _rank_frequency_items(interpretation_layers_added_counter, interpretation_layers_added_pair_indexes, "layer", changed_pairs),
        "interpretation_layers_removed_frequencies": _rank_frequency_items(interpretation_layers_removed_counter, interpretation_layers_removed_pair_indexes, "layer", changed_pairs),
        "source_hypothesis_classes_added_frequencies": _rank_frequency_items(source_hypothesis_classes_added_counter, source_hypothesis_classes_added_pair_indexes, "source_hypothesis_class", changed_pairs),
        "source_hypothesis_classes_removed_frequencies": _rank_frequency_items(source_hypothesis_classes_removed_counter, source_hypothesis_classes_removed_pair_indexes, "source_hypothesis_class", changed_pairs),
        "source_hypothesis_linked_transition_motif_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_signatures_added_counter, source_hypothesis_linked_transition_motif_signatures_added_pair_indexes, "transition_motif_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_signatures_removed_counter, source_hypothesis_linked_transition_motif_signatures_removed_pair_indexes, "transition_motif_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_sequence_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_sequence_signatures_added_counter, source_hypothesis_linked_transition_motif_sequence_signatures_added_pair_indexes, "transition_motif_sequence_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_sequence_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_sequence_signatures_removed_counter, source_hypothesis_linked_transition_motif_sequence_signatures_removed_pair_indexes, "transition_motif_sequence_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_chain_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_chain_signatures_added_counter, source_hypothesis_linked_transition_motif_chain_signatures_added_pair_indexes, "transition_motif_chain_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_chain_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_chain_signatures_removed_counter, source_hypothesis_linked_transition_motif_chain_signatures_removed_pair_indexes, "transition_motif_chain_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_signatures_added_pair_indexes, "transition_motif_phrase_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_signatures_removed_pair_indexes, "transition_motif_phrase_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_family_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_family_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_family_signatures_added_pair_indexes, "transition_motif_phrase_family_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_pair_indexes, "transition_motif_phrase_family_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_pair_indexes, "transition_motif_phrase_archetype_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_pair_indexes, "transition_motif_phrase_archetype_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_pair_indexes, "transition_motif_phrase_contour_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_pair_indexes, "transition_motif_phrase_contour_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_pair_indexes, "transition_motif_phrase_sweep_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_pair_indexes, "transition_motif_phrase_sweep_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_pair_indexes, "transition_motif_phrase_gesture_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_pair_indexes, "transition_motif_phrase_gesture_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_counter, source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_pair_indexes, "transition_motif_phrase_mobility_signature", changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_frequencies": _rank_frequency_items(source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_counter, source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_pair_indexes, "transition_motif_phrase_mobility_signature", changed_pairs),
        "transition_motif_signatures_added_frequencies": _rank_frequency_items(transition_motif_signatures_added_counter, transition_motif_signatures_added_pair_indexes, "transition_motif_signature", changed_pairs),
        "transition_motif_signatures_removed_frequencies": _rank_frequency_items(transition_motif_signatures_removed_counter, transition_motif_signatures_removed_pair_indexes, "transition_motif_signature", changed_pairs),
        "transition_motif_sequence_signatures_added_frequencies": _rank_frequency_items(transition_motif_sequence_signatures_added_counter, transition_motif_sequence_signatures_added_pair_indexes, "transition_motif_sequence_signature", changed_pairs),
        "transition_motif_sequence_signatures_removed_frequencies": _rank_frequency_items(transition_motif_sequence_signatures_removed_counter, transition_motif_sequence_signatures_removed_pair_indexes, "transition_motif_sequence_signature", changed_pairs),
        "transition_motif_chain_signatures_added_frequencies": _rank_frequency_items(transition_motif_chain_signatures_added_counter, transition_motif_chain_signatures_added_pair_indexes, "transition_motif_chain_signature", changed_pairs),
        "transition_motif_chain_signatures_removed_frequencies": _rank_frequency_items(transition_motif_chain_signatures_removed_counter, transition_motif_chain_signatures_removed_pair_indexes, "transition_motif_chain_signature", changed_pairs),
        "transition_motif_phrase_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_signatures_added_counter, transition_motif_phrase_signatures_added_pair_indexes, "transition_motif_phrase_signature", changed_pairs),
        "transition_motif_phrase_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_signatures_removed_counter, transition_motif_phrase_signatures_removed_pair_indexes, "transition_motif_phrase_signature", changed_pairs),
        "transition_motif_phrase_family_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_family_signatures_added_counter, transition_motif_phrase_family_signatures_added_pair_indexes, "transition_motif_phrase_family_signature", changed_pairs),
        "transition_motif_phrase_family_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_family_signatures_removed_counter, transition_motif_phrase_family_signatures_removed_pair_indexes, "transition_motif_phrase_family_signature", changed_pairs),
        "transition_motif_phrase_archetype_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_archetype_signatures_added_counter, transition_motif_phrase_archetype_signatures_added_pair_indexes, "transition_motif_phrase_archetype_signature", changed_pairs),
        "transition_motif_phrase_archetype_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_archetype_signatures_removed_counter, transition_motif_phrase_archetype_signatures_removed_pair_indexes, "transition_motif_phrase_archetype_signature", changed_pairs),
        "transition_motif_phrase_contour_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_contour_signatures_added_counter, transition_motif_phrase_contour_signatures_added_pair_indexes, "transition_motif_phrase_contour_signature", changed_pairs),
        "transition_motif_phrase_contour_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_contour_signatures_removed_counter, transition_motif_phrase_contour_signatures_removed_pair_indexes, "transition_motif_phrase_contour_signature", changed_pairs),
        "transition_motif_phrase_sweep_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_sweep_signatures_added_counter, transition_motif_phrase_sweep_signatures_added_pair_indexes, "transition_motif_phrase_sweep_signature", changed_pairs),
        "transition_motif_phrase_sweep_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_sweep_signatures_removed_counter, transition_motif_phrase_sweep_signatures_removed_pair_indexes, "transition_motif_phrase_sweep_signature", changed_pairs),
        "transition_motif_phrase_gesture_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_gesture_signatures_added_counter, transition_motif_phrase_gesture_signatures_added_pair_indexes, "transition_motif_phrase_gesture_signature", changed_pairs),
        "transition_motif_phrase_gesture_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_gesture_signatures_removed_counter, transition_motif_phrase_gesture_signatures_removed_pair_indexes, "transition_motif_phrase_gesture_signature", changed_pairs),
        "transition_motif_phrase_mobility_signatures_added_frequencies": _rank_frequency_items(transition_motif_phrase_mobility_signatures_added_counter, transition_motif_phrase_mobility_signatures_added_pair_indexes, "transition_motif_phrase_mobility_signature", changed_pairs),
        "transition_motif_phrase_mobility_signatures_removed_frequencies": _rank_frequency_items(transition_motif_phrase_mobility_signatures_removed_counter, transition_motif_phrase_mobility_signatures_removed_pair_indexes, "transition_motif_phrase_mobility_signature", changed_pairs),
        "metadata_fields_changed_in_all_changed_pairs": _universal_items(metadata_counter, changed_pairs),
        "observed_audio_fields_changed_in_all_changed_pairs": _universal_items(observed_audio_counter, changed_pairs),
        "analysis_window_fields_changed_in_all_changed_pairs": _universal_items(analysis_window_counter, changed_pairs),
        "attention_contract_fields_changed_in_all_changed_pairs": _universal_items(attention_contract_counter, changed_pairs),
        "transformation_intent_fields_changed_in_all_changed_pairs": _universal_items(transformation_intent_counter, changed_pairs),
        "basic_observation_fields_changed_in_all_changed_pairs": _universal_items(basic_observation_counter, changed_pairs),
        "observation_layers_added_in_all_changed_pairs": _universal_items(observation_layers_added_counter, changed_pairs),
        "observation_layers_removed_in_all_changed_pairs": _universal_items(observation_layers_removed_counter, changed_pairs),
        "interpretation_layers_added_in_all_changed_pairs": _universal_items(interpretation_layers_added_counter, changed_pairs),
        "interpretation_layers_removed_in_all_changed_pairs": _universal_items(interpretation_layers_removed_counter, changed_pairs),
        "source_hypothesis_classes_added_in_all_changed_pairs": _universal_items(source_hypothesis_classes_added_counter, changed_pairs),
        "source_hypothesis_classes_removed_in_all_changed_pairs": _universal_items(source_hypothesis_classes_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_sequence_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_sequence_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_sequence_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_sequence_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_chain_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_chain_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_chain_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_chain_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_family_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_family_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_counter, changed_pairs),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs": _universal_items(source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_counter, changed_pairs),
        "transition_motif_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_signatures_added_counter, changed_pairs),
        "transition_motif_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_signatures_removed_counter, changed_pairs),
        "transition_motif_sequence_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_sequence_signatures_added_counter, changed_pairs),
        "transition_motif_sequence_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_sequence_signatures_removed_counter, changed_pairs),
        "transition_motif_chain_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_chain_signatures_added_counter, changed_pairs),
        "transition_motif_chain_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_chain_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_family_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_family_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_family_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_family_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_archetype_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_archetype_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_contour_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_contour_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_contour_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_sweep_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_sweep_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_gesture_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_gesture_signatures_removed_counter, changed_pairs),
        "transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs": _universal_items(transition_motif_phrase_mobility_signatures_added_counter, changed_pairs),
        "transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs": _universal_items(transition_motif_phrase_mobility_signatures_removed_counter, changed_pairs),
        "analysis_change_summary": {
            "pairs_with_source_hypothesis_count_delta": source_hypothesis_count_delta_pairs,
            "total_source_hypothesis_count_delta": total_source_hypothesis_count_delta,
            "pairs_with_interpretation_hypothesis_count_delta": interpretation_hypothesis_count_delta_pairs,
            "total_interpretation_hypothesis_count_delta": total_interpretation_hypothesis_count_delta,
            "pairs_with_recurring_transition_motif_count_delta": recurring_transition_motif_count_delta_pairs,
            "total_recurring_transition_motif_count_delta": total_recurring_transition_motif_count_delta,
            "pairs_with_recurring_transition_motif_sequence_count_delta": recurring_transition_motif_sequence_count_delta_pairs,
            "total_recurring_transition_motif_sequence_count_delta": total_recurring_transition_motif_sequence_count_delta,
            "pairs_with_recurring_transition_motif_chain_count_delta": recurring_transition_motif_chain_count_delta_pairs,
            "total_recurring_transition_motif_chain_count_delta": total_recurring_transition_motif_chain_count_delta,
            "pairs_with_recurring_transition_motif_phrase_count_delta": recurring_transition_motif_phrase_count_delta_pairs,
            "total_recurring_transition_motif_phrase_count_delta": total_recurring_transition_motif_phrase_count_delta,
            "pairs_with_recurring_transition_motif_phrase_family_count_delta": recurring_transition_motif_phrase_family_count_delta_pairs,
            "total_recurring_transition_motif_phrase_family_count_delta": total_recurring_transition_motif_phrase_family_count_delta,
            "pairs_with_recurring_transition_motif_phrase_archetype_count_delta": recurring_transition_motif_phrase_archetype_count_delta_pairs,
            "total_recurring_transition_motif_phrase_archetype_count_delta": total_recurring_transition_motif_phrase_archetype_count_delta,
            "pairs_with_recurring_transition_motif_phrase_contour_count_delta": recurring_transition_motif_phrase_contour_count_delta_pairs,
            "total_recurring_transition_motif_phrase_contour_count_delta": total_recurring_transition_motif_phrase_contour_count_delta,
            "pairs_with_recurring_transition_motif_phrase_sweep_count_delta": recurring_transition_motif_phrase_sweep_count_delta_pairs,
            "total_recurring_transition_motif_phrase_sweep_count_delta": total_recurring_transition_motif_phrase_sweep_count_delta,
            "pairs_with_recurring_transition_motif_phrase_gesture_count_delta": recurring_transition_motif_phrase_gesture_count_delta_pairs,
            "total_recurring_transition_motif_phrase_gesture_count_delta": total_recurring_transition_motif_phrase_gesture_count_delta,
            "pairs_with_recurring_transition_motif_phrase_mobility_count_delta": recurring_transition_motif_phrase_mobility_count_delta_pairs,
            "total_recurring_transition_motif_phrase_mobility_count_delta": total_recurring_transition_motif_phrase_mobility_count_delta,
            "pairs_with_component_group_count_delta": component_group_count_delta_pairs,
            "total_component_group_count_delta": total_component_group_count_delta,
            "pairs_with_onset_map_count_delta": onset_map_count_delta_pairs,
            "total_onset_map_count_delta": total_onset_map_count_delta,
            "pairs_with_section_boundary_count_delta": section_boundary_count_delta_pairs,
            "total_section_boundary_count_delta": total_section_boundary_count_delta,
            "pairs_with_section_candidate_count_delta": section_candidate_count_delta_pairs,
            "total_section_candidate_count_delta": total_section_candidate_count_delta,
            "pairs_with_section_transition_count_delta": section_transition_count_delta_pairs,
            "total_section_transition_count_delta": total_section_transition_count_delta,
            "pairs_with_uncertainty_warning_count_delta": uncertainty_warning_count_delta_pairs,
            "total_uncertainty_warning_count_delta": total_uncertainty_warning_count_delta,
            "pairs_with_highest_stable_transition_motif_abstraction_layer_change": highest_stable_transition_motif_abstraction_layer_change_pairs,
            "pairs_with_highest_stable_transition_motif_abstraction_layer_rise": highest_stable_transition_motif_abstraction_layer_rise_pairs,
            "pairs_with_highest_stable_transition_motif_abstraction_layer_fall": highest_stable_transition_motif_abstraction_layer_fall_pairs,
            "total_highest_stable_transition_motif_abstraction_layer_step_delta": total_highest_stable_transition_motif_abstraction_layer_step_delta,
            "pairs_with_highest_stable_transition_motif_abstraction_layer_recurring_count_delta": highest_stable_transition_motif_abstraction_layer_recurring_count_delta_pairs,
            "total_highest_stable_transition_motif_abstraction_layer_recurring_count_delta": total_highest_stable_transition_motif_abstraction_layer_recurring_count_delta,
            "pairs_with_highest_stable_transition_motif_abstraction_layer_occurrence_count_delta": highest_stable_transition_motif_abstraction_layer_occurrence_count_delta_pairs,
            "total_highest_stable_transition_motif_abstraction_layer_occurrence_count_delta": total_highest_stable_transition_motif_abstraction_layer_occurrence_count_delta,
            "pairs_with_first_scene_hypothesis_change": first_scene_hypothesis_change_pairs,
            "pairs_with_first_communicative_hypothesis_change": first_communicative_hypothesis_change_pairs,
            "pairs_with_transformation_intent_change": transformation_intent_change_pairs,
        },
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch analysis diff output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_review_analysis_documents(
    left_documents: list[str | Path],
    right_documents: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    diff_payload = batch_diff_analysis_documents(
        left_documents,
        right_documents,
    )

    review_payload = {
        "pairs_compared": diff_payload["pairs_compared"],
        "changed_pairs": diff_payload["changed_pairs"],
        "unchanged_pairs": diff_payload["unchanged_pairs"],
        "invalid_pairs": diff_payload["invalid_pairs"],
        "is_valid": diff_payload["is_valid"],
        "diff_report": diff_payload,
        "analysis": {
            "pairs_compared": diff_payload["pairs_compared"],
            "changed_pairs": diff_payload["changed_pairs"],
            "unchanged_pairs": diff_payload["unchanged_pairs"],
            "invalid_pairs": diff_payload["invalid_pairs"],
            "is_valid": diff_payload["is_valid"],
            "metadata_field_frequencies": diff_payload["metadata_field_frequencies"],
            "observed_audio_field_frequencies": diff_payload["observed_audio_field_frequencies"],
            "analysis_window_field_frequencies": diff_payload["analysis_window_field_frequencies"],
            "basic_observation_field_frequencies": diff_payload["basic_observation_field_frequencies"],
            "observation_layers_added_frequencies": diff_payload["observation_layers_added_frequencies"],
            "observation_layers_removed_frequencies": diff_payload["observation_layers_removed_frequencies"],
            "source_hypothesis_classes_added_frequencies": diff_payload["source_hypothesis_classes_added_frequencies"],
            "source_hypothesis_classes_removed_frequencies": diff_payload["source_hypothesis_classes_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_sequence_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_sequence_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_sequence_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_sequence_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_chain_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_chain_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_chain_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_chain_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_frequencies"],
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_frequencies": diff_payload["source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_frequencies"],
            "transition_motif_signatures_added_frequencies": diff_payload["transition_motif_signatures_added_frequencies"],
            "transition_motif_signatures_removed_frequencies": diff_payload["transition_motif_signatures_removed_frequencies"],
            "transition_motif_sequence_signatures_added_frequencies": diff_payload["transition_motif_sequence_signatures_added_frequencies"],
            "transition_motif_sequence_signatures_removed_frequencies": diff_payload["transition_motif_sequence_signatures_removed_frequencies"],
            "transition_motif_chain_signatures_added_frequencies": diff_payload["transition_motif_chain_signatures_added_frequencies"],
            "transition_motif_chain_signatures_removed_frequencies": diff_payload["transition_motif_chain_signatures_removed_frequencies"],
            "transition_motif_phrase_signatures_added_frequencies": diff_payload["transition_motif_phrase_signatures_added_frequencies"],
            "transition_motif_phrase_signatures_removed_frequencies": diff_payload["transition_motif_phrase_signatures_removed_frequencies"],
            "transition_motif_phrase_family_signatures_added_frequencies": diff_payload["transition_motif_phrase_family_signatures_added_frequencies"],
            "transition_motif_phrase_family_signatures_removed_frequencies": diff_payload["transition_motif_phrase_family_signatures_removed_frequencies"],
            "transition_motif_phrase_archetype_signatures_added_frequencies": diff_payload["transition_motif_phrase_archetype_signatures_added_frequencies"],
            "transition_motif_phrase_archetype_signatures_removed_frequencies": diff_payload["transition_motif_phrase_archetype_signatures_removed_frequencies"],
            "transition_motif_phrase_contour_signatures_added_frequencies": diff_payload["transition_motif_phrase_contour_signatures_added_frequencies"],
            "transition_motif_phrase_contour_signatures_removed_frequencies": diff_payload["transition_motif_phrase_contour_signatures_removed_frequencies"],
            "transition_motif_phrase_sweep_signatures_added_frequencies": diff_payload["transition_motif_phrase_sweep_signatures_added_frequencies"],
            "transition_motif_phrase_sweep_signatures_removed_frequencies": diff_payload["transition_motif_phrase_sweep_signatures_removed_frequencies"],
            "transition_motif_phrase_gesture_signatures_added_frequencies": diff_payload["transition_motif_phrase_gesture_signatures_added_frequencies"],
            "transition_motif_phrase_gesture_signatures_removed_frequencies": diff_payload["transition_motif_phrase_gesture_signatures_removed_frequencies"],
            "transition_motif_phrase_mobility_signatures_added_frequencies": diff_payload["transition_motif_phrase_mobility_signatures_added_frequencies"],
            "transition_motif_phrase_mobility_signatures_removed_frequencies": diff_payload["transition_motif_phrase_mobility_signatures_removed_frequencies"],
            "metadata_fields_changed_in_all_changed_pairs": diff_payload["metadata_fields_changed_in_all_changed_pairs"],
            "observed_audio_fields_changed_in_all_changed_pairs": diff_payload["observed_audio_fields_changed_in_all_changed_pairs"],
            "analysis_window_fields_changed_in_all_changed_pairs": diff_payload["analysis_window_fields_changed_in_all_changed_pairs"],
            "basic_observation_fields_changed_in_all_changed_pairs": diff_payload["basic_observation_fields_changed_in_all_changed_pairs"],
            "observation_layers_added_in_all_changed_pairs": diff_payload["observation_layers_added_in_all_changed_pairs"],
            "observation_layers_removed_in_all_changed_pairs": diff_payload["observation_layers_removed_in_all_changed_pairs"],
            "source_hypothesis_classes_added_in_all_changed_pairs": diff_payload["source_hypothesis_classes_added_in_all_changed_pairs"],
            "source_hypothesis_classes_removed_in_all_changed_pairs": diff_payload["source_hypothesis_classes_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_sequence_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_sequence_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_sequence_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_sequence_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_chain_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_chain_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_chain_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_chain_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_family_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs"],
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs": diff_payload["source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs"],
            "transition_motif_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_signatures_added_in_all_changed_pairs"],
            "transition_motif_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_signatures_removed_in_all_changed_pairs"],
            "transition_motif_sequence_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_sequence_signatures_added_in_all_changed_pairs"],
            "transition_motif_sequence_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_sequence_signatures_removed_in_all_changed_pairs"],
            "transition_motif_chain_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_chain_signatures_added_in_all_changed_pairs"],
            "transition_motif_chain_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_chain_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_family_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_family_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_family_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_family_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_archetype_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_archetype_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_contour_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_contour_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_contour_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_sweep_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_sweep_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_gesture_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_gesture_signatures_removed_in_all_changed_pairs"],
            "transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs": diff_payload["transition_motif_phrase_mobility_signatures_added_in_all_changed_pairs"],
            "transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs": diff_payload["transition_motif_phrase_mobility_signatures_removed_in_all_changed_pairs"],
            "analysis_change_summary": diff_payload["analysis_change_summary"],
        },
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch analysis review output")
        _write_auxiliary_document(output_path, review_payload, report_format)
        review_payload["report_output"] = str(output_path)
        review_payload["report_format"] = report_format

    return review_payload


def batch_build_arwif_artifacts(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    built_count = 0
    failed_count = 0
    total_oscillator_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.arwif"
        try:
            payload = build_arwif_artifact(spec_path, output_path)
        except ValueError as exc:
            spec_report = validate_arwif_spec(spec_path)
            payload = {
                "artifact": str(output_path),
                "spec": str(spec_path),
                "built": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            }
            failed_count += 1
        else:
            built_count += 1
            total_oscillator_count += int(payload.get("oscillator_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "built_count": built_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch build output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_import_arwif_artifacts(
    specs: list[str | Path],
    output_dir: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    imported_count = 0
    failed_count = 0
    total_oscillator_count = 0

    for spec in specs:
        spec_path = Path(spec)
        output_path = output_dir_path / f"{spec_path.stem}.arwif"
        try:
            payload = import_arwif_artifact(spec_path, output_path)
        except ValueError as exc:
            spec_report = validate_arwif_spec(spec_path)
            payload = {
                "artifact": str(output_path),
                "spec": str(spec_path),
                "imported": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            }
            failed_count += 1
        else:
            imported_count += 1
            total_oscillator_count += int(payload.get("oscillator_count", 0))

        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "imported_count": imported_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch import output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_validate_arwif_specs(
    specs: list[str | Path],
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("at least one spec must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for spec in specs:
        report = validate_arwif_spec(Path(spec))
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(report.stats.get("state_count", 0))
        total_oscillator_count += int(report.stats.get("oscillator_count", 0))
        results.append(payload)

    payload = {
        "specs_processed": len(specs),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate spec output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_validate_arwif_artifacts(
    artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
        payload = report.to_payload()
        if report.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(report.stats.get("state_count", 0))
        total_oscillator_count += _artifact_oscillator_count(artifact_path)
        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "allow_legacy": allow_legacy,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch validate output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_inspect_arwif_artifacts(
    artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    results: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0
    total_state_count = 0
    total_oscillator_count = 0
    max_frequency_hz = 0

    for artifact in artifacts:
        payload = inspect_arwif_artifact(Path(artifact), allow_legacy=allow_legacy)
        if payload.get("is_valid", False):
            valid_count += 1
        else:
            invalid_count += 1
        total_state_count += int(payload.get("state_count", 0))
        total_oscillator_count += int(payload.get("oscillator_count", 0))
        max_frequency_hz = max(max_frequency_hz, int(payload.get("max_frequency_hz") or 0))
        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "allow_legacy": allow_legacy,
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "max_frequency_hz": max_frequency_hz,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch inspect output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def _artifact_oscillator_count(artifact_path: Path) -> int:
    try:
        library = load_wave_library(artifact_path)
    except Exception:
        return 0
    return sum(len(state.units) for state in library.states)


def batch_export_arwif_artifacts(
    artifacts: list[str | Path],
    output_dir: str | Path,
    *,
    format: str | None = None,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    if format is None:
        output_suffix = ".yaml"
        export_format = "yaml"
    elif format == "json":
        output_suffix = ".json"
        export_format = "json"
    elif format == "yaml":
        output_suffix = ".yaml"
        export_format = "yaml"
    else:
        raise ValueError("format must be yaml or json")

    results: list[dict[str, Any]] = []
    exported_count = 0
    failed_count = 0
    total_state_count = 0
    total_oscillator_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        output_path = output_dir_path / f"{artifact_path.stem}.export{output_suffix}"
        try:
            payload = export_arwif_artifact(
                artifact_path,
                output_path,
                format=export_format,
                allow_legacy=allow_legacy,
            )
        except ValueError as exc:
            validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
            payload = {
                "artifact": str(artifact_path),
                "output": str(output_path),
                "format": export_format,
                "exported": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(validation_report.errors) or [str(exc)],
                "warnings": list(validation_report.warnings),
                "stats": dict(validation_report.stats),
            }
            failed_count += 1
        else:
            exported_count += 1
            total_state_count += int(payload.get("state_count", 0))
            total_oscillator_count += int(payload.get("oscillator_count", 0))
            payload["exported"] = True

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "exported_count": exported_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("is_valid", False) for result in results),
        "format": export_format,
        "output_dir": str(output_dir_path),
        "total_state_count": total_state_count,
        "total_oscillator_count": total_oscillator_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch export output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_normalize_arwif_artifacts(
    artifacts: list[str | Path],
    spec_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
    assumptions_dir: str | Path | None = None,
    format: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    spec_dir_path = Path(spec_dir)
    output_dir_path = Path(output_dir) if output_dir is not None else None
    report_dir_path = Path(report_dir) if report_dir is not None else None
    assumptions_dir_path = Path(assumptions_dir) if assumptions_dir is not None else None

    if format is None:
        spec_suffix = ".yaml"
    elif format == "json":
        spec_suffix = ".json"
    elif format == "yaml":
        spec_suffix = ".yaml"
    else:
        raise ValueError("format must be yaml or json")

    spec_dir_path.mkdir(parents=True, exist_ok=True)
    if output_dir_path is not None:
        output_dir_path.mkdir(parents=True, exist_ok=True)
    if report_dir_path is not None:
        report_dir_path.mkdir(parents=True, exist_ok=True)
    if assumptions_dir_path is not None:
        assumptions_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    normalized_count = 0
    failed_count = 0
    total_assumption_count = 0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        stem = artifact_path.stem
        spec_output_path = spec_dir_path / f"{stem}.normalized{spec_suffix}"
        output_path = output_dir_path / f"{stem}.normalized.arwif" if output_dir_path is not None else None
        report_path = report_dir_path / f"{stem}.normalized.report.json" if report_dir_path is not None else None
        assumptions_path = (
            assumptions_dir_path / f"{stem}.normalized.assumptions.json"
            if assumptions_dir_path is not None
            else None
        )

        try:
            payload = normalize_arwif_artifact(
                artifact_path,
                spec_output_path,
                output=output_path,
                report=report_path,
                assumptions=assumptions_path,
                format=format,
            )
        except ValueError as exc:
            source_report = validate_arwif_artifact(artifact_path, allow_legacy=True)
            payload = {
                "artifact": str(artifact_path),
                "spec_output": str(spec_output_path),
                "output": str(output_path) if output_path is not None else None,
                "report_output": str(report_path) if report_path is not None else None,
                "assumptions_output": str(assumptions_path) if assumptions_path is not None else None,
                "normalized": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(source_report.errors) or [str(exc)],
                "warnings": list(source_report.warnings),
                "stats": dict(source_report.stats),
            }
            failed_count += 1
        else:
            normalized_count += 1
            total_assumption_count += int(payload.get("assumption_count", 0))

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "normalized_count": normalized_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("output_is_valid", True) for result in results),
        "format": format or "yaml",
        "spec_dir": str(spec_dir_path),
        "output_dir": str(output_dir_path) if output_dir_path is not None else None,
        "report_dir": str(report_dir_path) if report_dir_path is not None else None,
        "assumptions_dir": str(assumptions_dir_path) if assumptions_dir_path is not None else None,
        "total_assumption_count": total_assumption_count,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch normalize output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_render_arwif_artifacts(
    artifacts: list[str | Path],
    output_dir: str | Path,
    *,
    allow_legacy: bool = False,
    sample_rate_override: int | None = None,
    duration_override: float | None = None,
    normalize_override: bool | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    rendered_count = 0
    failed_count = 0
    total_duration_seconds = 0.0

    for artifact in artifacts:
        artifact_path = Path(artifact)
        output_path = output_dir_path / f"{artifact_path.stem}.wav"
        try:
            payload = render_arwif_to_wav(
                artifact_path,
                output_path,
                allow_legacy=allow_legacy,
                sample_rate_override=sample_rate_override,
                duration_override=duration_override,
                normalize_override=normalize_override,
            )
        except ValueError as exc:
            validation_report = validate_arwif_artifact(artifact_path, allow_legacy=allow_legacy)
            payload = {
                "artifact": str(artifact_path),
                "output": str(output_path),
                "rendered": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(validation_report.errors) or [str(exc)],
                "warnings": list(validation_report.warnings),
                "stats": dict(validation_report.stats),
            }
            failed_count += 1
        else:
            rendered_count += 1
            total_duration_seconds += float(payload.get("duration_seconds", 0.0))
            payload["rendered"] = True

        results.append(payload)

    payload = {
        "artifacts_processed": len(artifacts),
        "rendered_count": rendered_count,
        "failed_count": failed_count,
        "is_valid": failed_count == 0 and all(result.get("rendered", False) for result in results),
        "output_dir": str(output_dir_path),
        "total_duration_seconds": total_duration_seconds,
        "results": results,
    }

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="batch render output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def batch_diff_arwif_artifacts(
    left_artifacts: list[str | Path],
    right_artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    if not left_artifacts or not right_artifacts:
        raise ValueError("at least one left and one right artifact must be provided")
    if len(left_artifacts) != len(right_artifacts):
        raise ValueError("left and right artifact collections must have the same length")

    results: list[dict[str, Any]] = []
    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    incompatible_pairs = 0
    total_metadata_fields_changed = 0
    total_changed_states = 0
    total_max_frequency_hz_delta = 0

    for pair_index, (left_artifact, right_artifact) in enumerate(zip(left_artifacts, right_artifacts, strict=True)):
        payload = diff_arwif_artifacts(left_artifact, right_artifact, allow_legacy=allow_legacy)
        payload["pair_index"] = pair_index

        summary = payload.get("change_summary", {})
        metadata_fields_changed = int(summary.get("metadata_fields_changed", 0))
        changed_states = int(summary.get("changed_states", 0))
        added_states = int(summary.get("added_states", 0))
        removed_states = int(summary.get("removed_states", 0))
        oscillator_count_delta = int(payload.get("oscillator_count_delta", 0))
        state_count_delta = int(payload.get("state_count_delta", 0))
        max_frequency_hz_delta = int(payload.get("max_frequency_hz_delta", 0))

        pair_changed = any(
            (
                metadata_fields_changed,
                changed_states,
                added_states,
                removed_states,
                oscillator_count_delta,
                state_count_delta,
                max_frequency_hz_delta,
            )
        )
        payload["pair_changed"] = pair_changed

        if pair_changed:
            changed_pairs += 1
        else:
            unchanged_pairs += 1

        if not payload.get("left_valid", False) or not payload.get("right_valid", False):
            invalid_pairs += 1
        if not payload.get("compatible_format", False):
            incompatible_pairs += 1

        total_metadata_fields_changed += metadata_fields_changed
        total_changed_states += changed_states
        total_max_frequency_hz_delta += max_frequency_hz_delta
        results.append(payload)

    payload = {
        "pairs_compared": len(results),
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "incompatible_pairs": incompatible_pairs,
        "is_valid": invalid_pairs == 0,
        "allow_legacy": allow_legacy,
        "total_metadata_fields_changed": total_metadata_fields_changed,
        "total_changed_states": total_changed_states,
        "total_max_frequency_hz_delta": total_max_frequency_hz_delta,
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


def batch_review_arwif_artifacts(
    left_artifacts: list[str | Path],
    right_artifacts: list[str | Path],
    *,
    allow_legacy: bool = False,
    output: str | Path | None = None,
) -> dict[str, Any]:
    diff_payload = batch_diff_arwif_artifacts(
        left_artifacts,
        right_artifacts,
        allow_legacy=allow_legacy,
    )
    analysis_payload = _analyze_batch_diff_payload(diff_payload)

    review_payload = {
        "pairs_compared": diff_payload["pairs_compared"],
        "changed_pairs": diff_payload["changed_pairs"],
        "unchanged_pairs": diff_payload["unchanged_pairs"],
        "invalid_pairs": diff_payload["invalid_pairs"],
        "incompatible_pairs": diff_payload["incompatible_pairs"],
        "is_valid": diff_payload["is_valid"] and analysis_payload["is_valid"],
        "allow_legacy": allow_legacy,
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


def _analyze_batch_diff_payload(report_document: dict[str, Any], *, analysis_input: str | None = None) -> dict[str, Any]:
    results = report_document.get("results")
    if not isinstance(results, list):
        raise ValueError("batch diff analysis input must contain a 'results' list")

    metadata_counter: Counter[str] = Counter()
    changed_state_counter: Counter[str] = Counter()
    added_state_counter: Counter[str] = Counter()
    removed_state_counter: Counter[str] = Counter()
    metadata_pair_indexes: dict[str, list[int]] = {}
    changed_state_pair_indexes: dict[str, list[int]] = {}
    added_state_pair_indexes: dict[str, list[int]] = {}
    removed_state_pair_indexes: dict[str, list[int]] = {}

    channel_layout_changed_pairs = 0
    listener_anchor_changed_pairs = 0
    reference_frame_changed_pairs = 0
    room_present_changed_pairs = 0
    room_changed_pairs = 0
    room_dimensions_changed_pairs = 0
    geometry_reference_present_changed_pairs = 0
    geometry_reference_changed_pairs = 0
    room_geometry_id_changed_pairs = 0
    room_geometry_class_changed_pairs = 0
    room_surface_profile_changed_pairs = 0
    surface_treatment_present_changed_pairs = 0
    surface_treatment_changed_pairs = 0
    room_surface_absorption_changed_pairs = 0
    room_surface_diffusion_changed_pairs = 0
    reflection_policy_present_changed_pairs = 0
    reflection_policy_changed_pairs = 0
    room_reflection_style_changed_pairs = 0
    room_early_reflections_changed_pairs = 0
    room_late_reverb_changed_pairs = 0
    renderer_adaptation_present_changed_pairs = 0
    renderer_adaptation_changed_pairs = 0
    room_target_playback_changed_pairs = 0
    room_spatial_priority_changed_pairs = 0
    room_downmix_policy_changed_pairs = 0
    listening_zones_changed_pairs = 0
    listening_zone_intents_changed_pairs = 0
    listening_zone_intents_count_delta_pairs = 0
    total_listening_zone_intents_count_delta = 0
    listening_zone_delta_pairs = 0
    total_listening_zone_count_delta = 0
    listening_zone_ids_count_delta_pairs = 0
    total_listening_zone_ids_count_delta = 0
    speaker_ids_changed_pairs = 0
    speaker_ids_count_delta_pairs = 0
    total_speaker_ids_count_delta = 0
    speakers_changed_pairs = 0
    speaker_channels_changed_pairs = 0
    speaker_channels_count_delta_pairs = 0
    total_speaker_channels_count_delta = 0
    speaker_roles_changed_pairs = 0
    speaker_roles_count_delta_pairs = 0
    total_speaker_roles_count_delta = 0
    speaker_coverage_intents_changed_pairs = 0
    speaker_coverage_intents_count_delta_pairs = 0
    total_speaker_coverage_intents_count_delta = 0
    speaker_count_delta_pairs = 0
    total_speaker_count_delta = 0
    max_frequency_hz_delta_pairs = 0
    total_max_frequency_hz_delta = 0
    active_channels_changed_pairs = 0
    active_channels_count_delta_pairs = 0
    total_active_channels_count_delta = 0
    channel_gains_delta_pairs = 0
    total_states_with_channel_gains_delta = 0
    positioned_state_delta_pairs = 0
    total_positioned_states_delta = 0
    trajectory_changed_pairs = 0
    trajectory_state_delta_pairs = 0
    total_states_with_trajectory_delta = 0
    trajectory_point_delta_pairs = 0
    total_trajectory_point_delta = 0
    orientation_state_delta_pairs = 0
    total_states_with_orientation_delta = 0
    spread_state_delta_pairs = 0
    total_states_with_spread_delta = 0
    source_id_state_delta_pairs = 0
    total_states_with_source_id_delta = 0
    source_groups_changed_pairs = 0
    source_groups_count_delta_pairs = 0
    total_source_groups_count_delta = 0
    distance_models_changed_pairs = 0

    changed_pairs = 0
    unchanged_pairs = 0
    invalid_pairs = 0
    incompatible_pairs = 0

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
        if not raw_result.get("compatible_format", False):
            incompatible_pairs += 1

        metadata_changes = raw_result.get("metadata_changes")
        if isinstance(metadata_changes, dict):
            for field in metadata_changes:
                metadata_counter[str(field)] += 1
                metadata_pair_indexes.setdefault(str(field), []).append(pair_index)

        for state_name in _string_list(raw_result.get("changed_states")):
            changed_state_counter[state_name] += 1
            changed_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        for state_name in _string_list(raw_result.get("added_states")):
            added_state_counter[state_name] += 1
            added_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        for state_name in _string_list(raw_result.get("removed_states")):
            removed_state_counter[state_name] += 1
            removed_state_pair_indexes.setdefault(state_name, []).append(pair_index)

        max_frequency_hz_delta = int(raw_result.get("max_frequency_hz_delta", 0) or 0)
        total_max_frequency_hz_delta += max_frequency_hz_delta
        if max_frequency_hz_delta != 0:
            max_frequency_hz_delta_pairs += 1

        spatial_changes = raw_result.get("spatial_changes")
        if isinstance(spatial_changes, dict):
            if bool(spatial_changes.get("listener_anchor_changed", False)):
                listener_anchor_changed_pairs += 1
            if bool(spatial_changes.get("reference_frame_changed", False)):
                reference_frame_changed_pairs += 1
            if bool(spatial_changes.get("room_present_changed", False)):
                room_present_changed_pairs += 1
            if bool(spatial_changes.get("room_changed", False)):
                room_changed_pairs += 1
            if bool(spatial_changes.get("room_dimensions_changed", False)):
                room_dimensions_changed_pairs += 1
            if bool(spatial_changes.get("geometry_reference_present_changed", False)):
                geometry_reference_present_changed_pairs += 1
            if bool(spatial_changes.get("geometry_reference_changed", False)):
                geometry_reference_changed_pairs += 1
            if bool(spatial_changes.get("room_geometry_id_changed", False)):
                room_geometry_id_changed_pairs += 1
            if bool(spatial_changes.get("room_geometry_class_changed", False)):
                room_geometry_class_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_profile_changed", False)):
                room_surface_profile_changed_pairs += 1
            if bool(spatial_changes.get("surface_treatment_present_changed", False)):
                surface_treatment_present_changed_pairs += 1
            if bool(spatial_changes.get("surface_treatment_changed", False)):
                surface_treatment_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_absorption_changed", False)):
                room_surface_absorption_changed_pairs += 1
            if bool(spatial_changes.get("room_surface_diffusion_changed", False)):
                room_surface_diffusion_changed_pairs += 1
            if bool(spatial_changes.get("reflection_policy_present_changed", False)):
                reflection_policy_present_changed_pairs += 1
            if bool(spatial_changes.get("reflection_policy_changed", False)):
                reflection_policy_changed_pairs += 1
            if bool(spatial_changes.get("room_reflection_style_changed", False)):
                room_reflection_style_changed_pairs += 1
            if bool(spatial_changes.get("room_early_reflections_changed", False)):
                room_early_reflections_changed_pairs += 1
            if bool(spatial_changes.get("room_late_reverb_changed", False)):
                room_late_reverb_changed_pairs += 1
            if bool(spatial_changes.get("renderer_adaptation_present_changed", False)):
                renderer_adaptation_present_changed_pairs += 1
            if bool(spatial_changes.get("renderer_adaptation_changed", False)):
                renderer_adaptation_changed_pairs += 1
            if bool(spatial_changes.get("room_target_playback_changed", False)):
                room_target_playback_changed_pairs += 1
            if bool(spatial_changes.get("room_spatial_priority_changed", False)):
                room_spatial_priority_changed_pairs += 1
            if bool(spatial_changes.get("room_downmix_policy_changed", False)):
                room_downmix_policy_changed_pairs += 1
            if bool(spatial_changes.get("listening_zones_changed", False)):
                listening_zones_changed_pairs += 1
            if bool(spatial_changes.get("listening_zone_intents_changed", False)):
                listening_zone_intents_changed_pairs += 1
            listening_zone_intents_count_delta = int(spatial_changes.get("listening_zone_intents_count_delta", 0) or 0)
            total_listening_zone_intents_count_delta += listening_zone_intents_count_delta
            if listening_zone_intents_count_delta != 0:
                listening_zone_intents_count_delta_pairs += 1
            listening_zone_count_delta = int(spatial_changes.get("listening_zone_count_delta", 0) or 0)
            total_listening_zone_count_delta += listening_zone_count_delta
            if listening_zone_count_delta != 0:
                listening_zone_delta_pairs += 1
            listening_zone_ids_count_delta = int(spatial_changes.get("listening_zone_ids_count_delta", 0) or 0)
            total_listening_zone_ids_count_delta += listening_zone_ids_count_delta
            if listening_zone_ids_count_delta != 0:
                listening_zone_ids_count_delta_pairs += 1
            if bool(spatial_changes.get("speaker_ids_changed", False)):
                speaker_ids_changed_pairs += 1
            speaker_ids_count_delta = int(spatial_changes.get("speaker_ids_count_delta", 0) or 0)
            total_speaker_ids_count_delta += speaker_ids_count_delta
            if speaker_ids_count_delta != 0:
                speaker_ids_count_delta_pairs += 1
            if bool(spatial_changes.get("speakers_changed", False)):
                speakers_changed_pairs += 1
            if bool(spatial_changes.get("speaker_channels_changed", False)):
                speaker_channels_changed_pairs += 1
            speaker_channels_count_delta = int(spatial_changes.get("speaker_channels_count_delta", 0) or 0)
            total_speaker_channels_count_delta += speaker_channels_count_delta
            if speaker_channels_count_delta != 0:
                speaker_channels_count_delta_pairs += 1
            if bool(spatial_changes.get("speaker_roles_changed", False)):
                speaker_roles_changed_pairs += 1
            speaker_roles_count_delta = int(spatial_changes.get("speaker_roles_count_delta", 0) or 0)
            total_speaker_roles_count_delta += speaker_roles_count_delta
            if speaker_roles_count_delta != 0:
                speaker_roles_count_delta_pairs += 1
            if bool(spatial_changes.get("speaker_coverage_intents_changed", False)):
                speaker_coverage_intents_changed_pairs += 1
            speaker_coverage_intents_count_delta = int(
                spatial_changes.get("speaker_coverage_intents_count_delta", 0) or 0
            )
            total_speaker_coverage_intents_count_delta += speaker_coverage_intents_count_delta
            if speaker_coverage_intents_count_delta != 0:
                speaker_coverage_intents_count_delta_pairs += 1
            speaker_count_delta = int(spatial_changes.get("speaker_count_delta", 0) or 0)
            total_speaker_count_delta += speaker_count_delta
            if speaker_count_delta != 0:
                speaker_count_delta_pairs += 1
            if bool(spatial_changes.get("channel_layout_changed", False)):
                channel_layout_changed_pairs += 1
            if bool(spatial_changes.get("active_channels_changed", False)):
                active_channels_changed_pairs += 1
            active_channels_count_delta = int(spatial_changes.get("active_channels_count_delta", 0) or 0)
            total_active_channels_count_delta += active_channels_count_delta
            if active_channels_count_delta != 0:
                active_channels_count_delta_pairs += 1
            channel_gains_delta = int(spatial_changes.get("states_with_channel_gains_delta", 0) or 0)
            total_states_with_channel_gains_delta += channel_gains_delta
            if channel_gains_delta != 0:
                channel_gains_delta_pairs += 1
            positioned_states_delta = int(spatial_changes.get("positioned_states_delta", 0) or 0)
            total_positioned_states_delta += positioned_states_delta
            if positioned_states_delta != 0:
                positioned_state_delta_pairs += 1
            if bool(spatial_changes.get("trajectories_changed", False)):
                trajectory_changed_pairs += 1
            trajectory_states_delta = int(spatial_changes.get("states_with_trajectory_delta", 0) or 0)
            total_states_with_trajectory_delta += trajectory_states_delta
            if trajectory_states_delta != 0:
                trajectory_state_delta_pairs += 1
            trajectory_points_delta = int(spatial_changes.get("trajectory_point_count_delta", 0) or 0)
            total_trajectory_point_delta += trajectory_points_delta
            if trajectory_points_delta != 0:
                trajectory_point_delta_pairs += 1
            orientation_states_delta = int(spatial_changes.get("states_with_orientation_delta", 0) or 0)
            total_states_with_orientation_delta += orientation_states_delta
            if orientation_states_delta != 0:
                orientation_state_delta_pairs += 1
            spread_states_delta = int(spatial_changes.get("states_with_spread_delta", 0) or 0)
            total_states_with_spread_delta += spread_states_delta
            if spread_states_delta != 0:
                spread_state_delta_pairs += 1
            source_id_states_delta = int(spatial_changes.get("states_with_source_id_delta", 0) or 0)
            total_states_with_source_id_delta += source_id_states_delta
            if source_id_states_delta != 0:
                source_id_state_delta_pairs += 1
            if bool(spatial_changes.get("source_groups_changed", False)):
                source_groups_changed_pairs += 1
            source_groups_count_delta = int(spatial_changes.get("source_groups_count_delta", 0) or 0)
            total_source_groups_count_delta += source_groups_count_delta
            if source_groups_count_delta != 0:
                source_groups_count_delta_pairs += 1
            if bool(spatial_changes.get("distance_models_changed", False)):
                distance_models_changed_pairs += 1

    pairs_compared = int(report_document.get("pairs_compared", len(results)))
    analysis_payload = {
        "pairs_compared": pairs_compared,
        "changed_pairs": changed_pairs,
        "unchanged_pairs": unchanged_pairs,
        "invalid_pairs": invalid_pairs,
        "incompatible_pairs": incompatible_pairs,
        "is_valid": invalid_pairs == 0,
        "metadata_field_frequencies": _rank_frequency_items(metadata_counter, metadata_pair_indexes, "field", changed_pairs),
        "changed_state_frequencies": _rank_frequency_items(changed_state_counter, changed_state_pair_indexes, "state", changed_pairs),
        "added_state_frequencies": _rank_frequency_items(added_state_counter, added_state_pair_indexes, "state", changed_pairs),
        "removed_state_frequencies": _rank_frequency_items(removed_state_counter, removed_state_pair_indexes, "state", changed_pairs),
        "states_changed_in_all_changed_pairs": _universal_items(changed_state_counter, changed_pairs),
        "metadata_fields_changed_in_all_changed_pairs": _universal_items(metadata_counter, changed_pairs),
        "states_added_in_all_changed_pairs": _universal_items(added_state_counter, changed_pairs),
        "states_removed_in_all_changed_pairs": _universal_items(removed_state_counter, changed_pairs),
        "spatial_change_summary": {
            "listener_anchor_changed_pairs": listener_anchor_changed_pairs,
            "reference_frame_changed_pairs": reference_frame_changed_pairs,
            "room_present_changed_pairs": room_present_changed_pairs,
            "room_changed_pairs": room_changed_pairs,
            "room_dimensions_changed_pairs": room_dimensions_changed_pairs,
            "geometry_reference_present_changed_pairs": geometry_reference_present_changed_pairs,
            "geometry_reference_changed_pairs": geometry_reference_changed_pairs,
            "room_geometry_id_changed_pairs": room_geometry_id_changed_pairs,
            "room_geometry_class_changed_pairs": room_geometry_class_changed_pairs,
            "room_surface_profile_changed_pairs": room_surface_profile_changed_pairs,
            "surface_treatment_present_changed_pairs": surface_treatment_present_changed_pairs,
            "surface_treatment_changed_pairs": surface_treatment_changed_pairs,
            "room_surface_absorption_changed_pairs": room_surface_absorption_changed_pairs,
            "room_surface_diffusion_changed_pairs": room_surface_diffusion_changed_pairs,
            "reflection_policy_present_changed_pairs": reflection_policy_present_changed_pairs,
            "reflection_policy_changed_pairs": reflection_policy_changed_pairs,
            "room_reflection_style_changed_pairs": room_reflection_style_changed_pairs,
            "room_early_reflections_changed_pairs": room_early_reflections_changed_pairs,
            "room_late_reverb_changed_pairs": room_late_reverb_changed_pairs,
            "renderer_adaptation_present_changed_pairs": renderer_adaptation_present_changed_pairs,
            "renderer_adaptation_changed_pairs": renderer_adaptation_changed_pairs,
            "room_target_playback_changed_pairs": room_target_playback_changed_pairs,
            "room_spatial_priority_changed_pairs": room_spatial_priority_changed_pairs,
            "room_downmix_policy_changed_pairs": room_downmix_policy_changed_pairs,
            "listening_zones_changed_pairs": listening_zones_changed_pairs,
            "listening_zone_intents_changed_pairs": listening_zone_intents_changed_pairs,
            "pairs_with_listening_zone_intents_count_delta": listening_zone_intents_count_delta_pairs,
            "total_listening_zone_intents_count_delta": total_listening_zone_intents_count_delta,
            "pairs_with_listening_zone_count_delta": listening_zone_delta_pairs,
            "total_listening_zone_count_delta": total_listening_zone_count_delta,
            "pairs_with_listening_zone_ids_count_delta": listening_zone_ids_count_delta_pairs,
            "total_listening_zone_ids_count_delta": total_listening_zone_ids_count_delta,
            "speaker_ids_changed_pairs": speaker_ids_changed_pairs,
            "pairs_with_speaker_ids_count_delta": speaker_ids_count_delta_pairs,
            "total_speaker_ids_count_delta": total_speaker_ids_count_delta,
            "speakers_changed_pairs": speakers_changed_pairs,
            "speaker_channels_changed_pairs": speaker_channels_changed_pairs,
            "pairs_with_speaker_channels_count_delta": speaker_channels_count_delta_pairs,
            "total_speaker_channels_count_delta": total_speaker_channels_count_delta,
            "speaker_roles_changed_pairs": speaker_roles_changed_pairs,
            "pairs_with_speaker_roles_count_delta": speaker_roles_count_delta_pairs,
            "total_speaker_roles_count_delta": total_speaker_roles_count_delta,
            "speaker_coverage_intents_changed_pairs": speaker_coverage_intents_changed_pairs,
            "pairs_with_speaker_coverage_intents_count_delta": speaker_coverage_intents_count_delta_pairs,
            "total_speaker_coverage_intents_count_delta": total_speaker_coverage_intents_count_delta,
            "pairs_with_speaker_count_delta": speaker_count_delta_pairs,
            "total_speaker_count_delta": total_speaker_count_delta,
            "pairs_with_max_frequency_hz_delta": max_frequency_hz_delta_pairs,
            "total_max_frequency_hz_delta": total_max_frequency_hz_delta,
            "channel_layout_changed_pairs": channel_layout_changed_pairs,
            "active_channels_changed_pairs": active_channels_changed_pairs,
            "pairs_with_active_channels_count_delta": active_channels_count_delta_pairs,
            "total_active_channels_count_delta": total_active_channels_count_delta,
            "pairs_with_channel_gain_count_delta": channel_gains_delta_pairs,
            "total_states_with_channel_gains_delta": total_states_with_channel_gains_delta,
            "pairs_with_positioned_state_delta": positioned_state_delta_pairs,
            "total_positioned_states_delta": total_positioned_states_delta,
            "trajectory_changed_pairs": trajectory_changed_pairs,
            "pairs_with_trajectory_state_delta": trajectory_state_delta_pairs,
            "total_states_with_trajectory_delta": total_states_with_trajectory_delta,
            "pairs_with_trajectory_point_delta": trajectory_point_delta_pairs,
            "total_trajectory_point_delta": total_trajectory_point_delta,
            "pairs_with_orientation_state_delta": orientation_state_delta_pairs,
            "total_states_with_orientation_delta": total_states_with_orientation_delta,
            "pairs_with_spread_state_delta": spread_state_delta_pairs,
            "total_states_with_spread_delta": total_states_with_spread_delta,
            "pairs_with_source_id_state_delta": source_id_state_delta_pairs,
            "total_states_with_source_id_delta": total_states_with_source_id_delta,
            "source_groups_changed_pairs": source_groups_changed_pairs,
            "pairs_with_source_groups_count_delta": source_groups_count_delta_pairs,
            "total_source_groups_count_delta": total_source_groups_count_delta,
            "distance_models_changed_pairs": distance_models_changed_pairs,
        },
    }

    if analysis_input is not None:
        analysis_payload["analysis_input"] = analysis_input

    return analysis_payload


def _infer_pair_changed(result: dict[str, Any]) -> bool:
    summary = result.get("change_summary")
    if isinstance(summary, dict):
        if any(
            int(summary.get(key, 0) or 0)
            for key in ("metadata_fields_changed", "added_states", "removed_states", "changed_states")
        ):
            return True
    return any(
        int(result.get(key, 0) or 0)
        for key in ("state_count_delta", "oscillator_count_delta", "max_frequency_hz_delta")
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _mapping_optional(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _mapping_keys(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key) for key in value]


def _flatten_change_field_paths(value: Any, *, prefix: str) -> list[str]:
    if not isinstance(value, dict):
        return []
    if set(value.keys()) >= {"left", "right"}:
        return [prefix] if prefix else []

    fields: list[str] = []
    for key, nested_value in value.items():
        key_name = str(key)
        nested_prefix = key_name if not prefix else f"{prefix}.{key_name}"
        fields.extend(_flatten_change_field_paths(nested_value, prefix=nested_prefix))
    return fields


def _rank_frequency_items(
    counter: Counter[str],
    pair_indexes: dict[str, list[int]],
    label: str,
    changed_pairs: int,
) -> list[dict[str, Any]]:
    denominator = changed_pairs if changed_pairs > 0 else 1
    ranked: list[dict[str, Any]] = []
    for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        ranked.append(
            {
                label: name,
                "pairs_changed": count,
                "pair_indexes": pair_indexes.get(name, []),
                "frequency": count / denominator,
            }
        )
    return ranked


def _universal_items(counter: Counter[str], changed_pairs: int) -> list[str]:
    if changed_pairs == 0:
        return []
    return sorted(name for name, count in counter.items() if count == changed_pairs)


def _resolve_auxiliary_format(output_path: Path, *, label: str) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError(f"could not infer {label} format from path; use a .json, .yaml, or .yml suffix")


def _load_auxiliary_document(input_path: Path, *, label: str) -> dict[str, Any]:
    document_format = _resolve_auxiliary_format(input_path, label=label)
    raw_text = input_path.read_text(encoding="utf-8")
    if document_format == "json":
        document = json.loads(raw_text)
    else:
        document = yaml.safe_load(raw_text)
    if not isinstance(document, dict):
        raise ValueError(f"{label} must decode to a top-level mapping")
    return document


def _write_auxiliary_document(output_path: Path, document: dict[str, Any], report_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")