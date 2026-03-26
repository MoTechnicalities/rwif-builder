from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import subprocess
import tempfile
import wave
from pathlib import Path
from shutil import which
from typing import Any

import numpy as np
import yaml

ANALYSIS_VERSION = "0.1-draft"
ANALYZER_ID = "rwif-builder"
VALID_ANALYSIS_PROFILES = {"basic-observation"}
VALID_CHANNEL_MODES = {"preserve", "mono", "split-stereo"}
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".flac", ".mp3"}
SUPPORTED_ANALYSIS_DOCUMENT_SUFFIXES = {".json", ".yaml", ".yml"}
TRANSITION_MOTIF_ABSTRACTION_LAYER_ORDER = (
    "motif",
    "sequence",
    "chain",
    "phrase",
    "family",
    "archetype",
    "contour",
    "sweep",
    "gesture",
    "mobility",
)

TRANSITION_MOTIF_ABSTRACTION_LAYER_RANK = {
    layer: index for index, layer in enumerate(TRANSITION_MOTIF_ABSTRACTION_LAYER_ORDER)
}


@dataclass(frozen=True)
class ARWIFAnalysisValidationReport:
    analysis_document: str
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)
    normalized_document: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "analysis_document": self.analysis_document,
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


def validate_analysis_document(path: str | Path) -> ARWIFAnalysisValidationReport:
    document_path = Path(path)
    if not document_path.exists():
        return ARWIFAnalysisValidationReport(
            analysis_document=str(document_path),
            is_valid=False,
            errors=(f"analysis document does not exist: {document_path}",),
        )

    try:
        document = _load_analysis_document(document_path)
    except ValueError as exc:
        return ARWIFAnalysisValidationReport(
            analysis_document=str(document_path),
            is_valid=False,
            errors=(str(exc),),
        )

    return _validate_analysis_document_mapping(document, source=str(document_path))


def _validate_analysis_document_mapping(
    document: Any,
    *,
    source: str = "<memory>",
) -> ARWIFAnalysisValidationReport:
    if not isinstance(document, dict):
        return ARWIFAnalysisValidationReport(
            analysis_document=source,
            is_valid=False,
            errors=("analysis document must be a mapping document",),
        )

    try:
        analysis_metadata = _mapping_value(document.get("analysis_metadata"), section="analysis_metadata")
        observed_audio = _mapping_value(document.get("observed_audio"), section="observed_audio")
        observation_layers = _mapping_value(document.get("observation_layers"), section="observation_layers")
        source_hypotheses = _validate_source_hypotheses(document.get("source_hypotheses"))
        component_layers = _validate_component_layers(document.get("component_layers"))
        reconstruction = _validate_reconstruction(document.get("reconstruction"))
        uncertainty_notes = _mapping_value(document.get("uncertainty_notes"), section="uncertainty_notes")
        provenance = _mapping_value(document.get("provenance"), section="provenance")
        attention_contract = _validate_attention_contract(document.get("attention_contract"))
        interpretation_layers = _validate_interpretation_layers(document.get("interpretation_layers"))
        transformation_intent = _validate_transformation_intent(document.get("transformation_intent"))
    except ValueError as exc:
        return ARWIFAnalysisValidationReport(
            analysis_document=source,
            is_valid=False,
            errors=(str(exc),),
        )

    normalized_document = dict(document)
    normalized_document["analysis_metadata"] = analysis_metadata
    normalized_document["observed_audio"] = observed_audio
    normalized_document["observation_layers"] = observation_layers
    normalized_document["source_hypotheses"] = source_hypotheses
    normalized_document["component_layers"] = component_layers
    normalized_document["reconstruction"] = reconstruction
    normalized_document["uncertainty_notes"] = uncertainty_notes
    normalized_document["provenance"] = provenance
    if "attention_contract" in document or attention_contract:
        normalized_document["attention_contract"] = attention_contract
    if "interpretation_layers" in document or interpretation_layers:
        normalized_document["interpretation_layers"] = interpretation_layers
    if "transformation_intent" in document or transformation_intent:
        normalized_document["transformation_intent"] = transformation_intent

    stats = {
        "analysis_profile": analysis_metadata.get("analysis_profile"),
        "source_id": analysis_metadata.get("source_id"),
        "observation_layer_count": len(observation_layers),
        "source_hypothesis_count": len(source_hypotheses),
        "component_layer_count": len(component_layers),
        "reconstructable_output_count": len(_string_list(reconstruction.get("reconstructable_outputs"))),
        "uncertainty_warning_count": len(_string_list(uncertainty_notes.get("warnings"))),
        "has_attention_contract": bool(attention_contract),
        "has_interpretation_layers": bool(interpretation_layers),
        "has_transformation_intent": bool(transformation_intent),
    }
    return ARWIFAnalysisValidationReport(
        analysis_document=source,
        is_valid=True,
        stats=stats,
        normalized_document=normalized_document,
    )


def analyze_audio_input(
    input_audio: str | Path,
    *,
    output: str | Path | None = None,
    report: str | Path | None = None,
    start_seconds: float = 0.0,
    duration_seconds: float | None = None,
    channel_mode: str = "preserve",
    target_sample_rate_hz: int | None = None,
    analysis_profile: str = "basic-observation",
    source_id: str | None = None,
    query_text: str | None = None,
    attention_targets: list[str] | None = None,
    retain_targets: list[str] | None = None,
    suppress_targets: list[str] | None = None,
    answer_expectations: list[str] | None = None,
    render_goal: str | None = None,
    transformation_operations: list[str] | None = None,
    primary_output: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_audio)
    output_path = Path(output) if output is not None else None
    report_path = Path(report) if report is not None else None

    if not input_path.exists():
        raise ValueError(f"input audio file does not exist: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValueError("input audio must end in .wav, .flac, or .mp3")
    if analysis_profile not in VALID_ANALYSIS_PROFILES:
        allowed = ", ".join(sorted(VALID_ANALYSIS_PROFILES))
        raise ValueError(f"analysis_profile must be one of: {allowed}")
    if channel_mode not in VALID_CHANNEL_MODES:
        allowed = ", ".join(sorted(VALID_CHANNEL_MODES))
        raise ValueError(f"channel_mode must be one of: {allowed}")
    if start_seconds < 0.0:
        raise ValueError("start_seconds must be non-negative")
    if duration_seconds is not None and duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive when provided")
    if target_sample_rate_hz is not None and target_sample_rate_hz <= 0:
        raise ValueError("target_sample_rate_hz must be positive when provided")
    if source_id is not None and not source_id.strip():
        raise ValueError("source_id must be non-empty when provided")

    normalized_query_text = _normalized_optional_string(query_text)
    normalized_render_goal = _normalized_optional_string(render_goal)
    normalized_primary_output = _normalized_optional_string(primary_output)
    normalized_attention_targets = _normalized_cli_string_list(attention_targets)
    normalized_retain_targets = _normalized_cli_string_list(retain_targets)
    normalized_suppress_targets = _normalized_cli_string_list(suppress_targets)
    normalized_answer_expectations = _normalized_cli_string_list(answer_expectations)
    normalized_transformation_operations = _normalized_cli_string_list(transformation_operations)

    attention_contract = {
        "query_text": normalized_query_text,
        "attention_targets": normalized_attention_targets,
        "retain_targets": normalized_retain_targets,
        "suppress_targets": normalized_suppress_targets,
        "answer_expectations": normalized_answer_expectations,
        "render_goal": normalized_render_goal,
    }
    attention_contract = {
        key: value for key, value in attention_contract.items() if value is not None and value != []
    }
    transformation_intent = {
        "operations": normalized_transformation_operations,
        "primary_output": normalized_primary_output,
    }
    transformation_intent = {
        key: value for key, value in transformation_intent.items() if value is not None and value != []
    }

    decoded = _decode_audio(input_path)
    samples = decoded["samples"]
    sample_rate_hz = int(decoded["sample_rate_hz"])
    warnings = list(decoded["warnings"])

    samples = _slice_audio(samples, sample_rate_hz, start_seconds, duration_seconds)
    if samples.size == 0:
        raise ValueError("selected analysis window is empty")

    samples, channel_warnings = _apply_channel_mode(samples, channel_mode)
    warnings.extend(channel_warnings)

    if target_sample_rate_hz is not None and target_sample_rate_hz != sample_rate_hz:
        samples = _resample_audio(samples, sample_rate_hz, target_sample_rate_hz)
        sample_rate_hz = target_sample_rate_hz
        warnings.append(f"resampled decoded audio to {sample_rate_hz} Hz for analysis")

    channel_labels = _channel_labels(samples.shape[1])
    observation_summary = _build_observation_summary(samples, sample_rate_hz, channel_labels)
    analyzed_duration_seconds = samples.shape[0] / float(sample_rate_hz)
    mono = np.mean(samples, axis=1, dtype=np.float64)
    onset_map = _build_onset_map(mono, sample_rate_hz)
    section_boundaries = _estimate_section_boundaries(mono, sample_rate_hz)
    section_candidates = _build_section_candidates(mono, sample_rate_hz, analyzed_duration_seconds, section_boundaries)
    section_profile_summary = _build_section_profile_summary(section_candidates)
    section_transitions = _build_section_transitions(section_candidates)
    transition_profile_summary = _build_transition_profile_summary(section_transitions)
    transition_motif_summary = _build_transition_motif_summary(section_candidates, section_transitions)
    transition_motif_sequence_summary = _build_transition_motif_sequence_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    transition_motif_chain_summary = _build_transition_motif_chain_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    observation_summary["transition_motif_chain_summary"] = transition_motif_chain_summary
    transition_motif_phrase_summary = _build_transition_motif_phrase_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    observation_summary["transition_motif_phrase_summary"] = transition_motif_phrase_summary
    transition_motif_phrase_family_summary = _build_transition_motif_phrase_family_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_summary,
    )
    observation_summary["transition_motif_phrase_family_summary"] = transition_motif_phrase_family_summary
    transition_motif_phrase_archetype_summary = _build_transition_motif_phrase_archetype_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_family_summary,
    )
    observation_summary["transition_motif_phrase_archetype_summary"] = transition_motif_phrase_archetype_summary
    transition_motif_phrase_contour_summary = _build_transition_motif_phrase_contour_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_archetype_summary,
    )
    observation_summary["transition_motif_phrase_contour_summary"] = transition_motif_phrase_contour_summary
    transition_motif_phrase_sweep_summary = _build_transition_motif_phrase_sweep_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_contour_summary,
    )
    observation_summary["transition_motif_phrase_sweep_summary"] = transition_motif_phrase_sweep_summary
    transition_motif_phrase_gesture_summary = _build_transition_motif_phrase_gesture_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_sweep_summary,
    )
    observation_summary["transition_motif_phrase_gesture_summary"] = transition_motif_phrase_gesture_summary
    transition_motif_phrase_mobility_summary = _build_transition_motif_phrase_mobility_summary(
        section_candidates,
        section_transitions,
        transition_motif_phrase_gesture_summary,
    )
    observation_summary["transition_motif_phrase_mobility_summary"] = transition_motif_phrase_mobility_summary
    source_hypotheses = _build_source_hypotheses(
        observation_summary,
        decoded_audio={
            "channel_count": samples.shape[1],
            "codec": decoded["codec"],
            "decode_backend": decoded["decode_backend"],
        },
        analysis_window={
            "duration_seconds": analyzed_duration_seconds,
        },
        onset_map=onset_map,
        section_candidates=section_candidates,
        section_transitions=section_transitions,
        transition_motif_summary=transition_motif_summary,
        transition_motif_sequence_summary=transition_motif_sequence_summary,
        transition_motif_chain_summary=transition_motif_chain_summary,
        transition_motif_phrase_summary=transition_motif_phrase_summary,
        transition_motif_phrase_family_summary=transition_motif_phrase_family_summary,
        transition_motif_phrase_archetype_summary=transition_motif_phrase_archetype_summary,
        transition_motif_phrase_contour_summary=transition_motif_phrase_contour_summary,
        transition_motif_phrase_sweep_summary=transition_motif_phrase_sweep_summary,
        transition_motif_phrase_gesture_summary=transition_motif_phrase_gesture_summary,
        transition_motif_phrase_mobility_summary=transition_motif_phrase_mobility_summary,
    )
    interpretation_layers = _build_initial_interpretation_layers(
        source_hypotheses=source_hypotheses,
        attention_contract=attention_contract,
        transformation_intent=transformation_intent,
    )

    analysis_document = {
        "analysis_metadata": {
            "analysis_profile": analysis_profile,
            "analysis_version": ANALYSIS_VERSION,
            "analyzer_id": ANALYZER_ID,
            "source_id": source_id,
            "target_resolution": {
                "channel_mode": channel_mode,
                "sample_rate_hz": sample_rate_hz,
            },
        },
        "observed_audio": {
            "path_hint": str(input_path),
            "duration_seconds": analyzed_duration_seconds,
            "sample_rate_hz": sample_rate_hz,
            "channel_count": samples.shape[1],
            "codec": decoded["codec"],
            "original_sample_rate_hz": decoded["original_sample_rate_hz"],
            "original_channel_count": decoded["original_channel_count"],
            "analysis_window": {
                "start_seconds": start_seconds,
                "duration_seconds": analyzed_duration_seconds,
            },
        },
        "observation_layers": {
            "basic_observation_summary": observation_summary,
            "transient_events": [],
            "onset_map": onset_map,
            "section_boundaries": section_boundaries,
            "section_candidates": section_candidates,
            "section_transitions": section_transitions,
            "pitch_contours": [],
        },
        "source_hypotheses": source_hypotheses,
        "component_layers": {},
        "reconstruction": {
            "reconstructable_outputs": [],
        },
        "uncertainty_notes": {
            "warnings": list(warnings),
        },
        "provenance": {
            "input_file_hash": _sha256_file(input_path),
            "decode_backend": decoded["decode_backend"],
            "preprocessing_steps": _preprocessing_steps(decoded["decode_backend"], channel_mode, target_sample_rate_hz),
            "analysis_parameters": {
                "start_seconds": start_seconds,
                "duration_seconds": duration_seconds,
                "channel_mode": channel_mode,
                "target_sample_rate_hz": target_sample_rate_hz,
                "analysis_profile": analysis_profile,
            },
        },
    }
    if attention_contract:
        analysis_document["attention_contract"] = attention_contract
    if interpretation_layers:
        analysis_document["interpretation_layers"] = interpretation_layers
    if transformation_intent:
        analysis_document["transformation_intent"] = transformation_intent

    payload: dict[str, Any] = {
        "command": "arwif-analyze-audio",
        "input_audio": str(input_path),
        "analysis_profile": analysis_profile,
        "source_id": source_id,
        "attention_contract": attention_contract,
        "interpretation_layers": interpretation_layers,
        "transformation_intent": transformation_intent,
        "decoded_audio": {
            "duration_seconds": analyzed_duration_seconds,
            "sample_rate_hz": sample_rate_hz,
            "channel_count": samples.shape[1],
            "codec": decoded["codec"],
            "channel_mode": channel_mode,
            "decode_backend": decoded["decode_backend"],
            "original_sample_rate_hz": decoded["original_sample_rate_hz"],
            "original_channel_count": decoded["original_channel_count"],
        },
        "analysis_window": {
            "start_seconds": start_seconds,
            "duration_seconds": analyzed_duration_seconds,
        },
        "observation_summary": observation_summary,
        "source_hypothesis_count": len(source_hypotheses),
        "source_hypothesis_classes": _source_hypothesis_classes(source_hypotheses),
        "warnings": list(warnings),
        "is_valid": True,
    }

    if output_path is not None:
        analysis_format = _resolve_auxiliary_format(output_path, label="analysis output")
        _write_auxiliary_document(output_path, analysis_document, analysis_format)
        payload["analysis_document_output"] = str(output_path)
        payload["analysis_document_format"] = analysis_format

    if report_path is not None:
        report_format = _resolve_auxiliary_format(report_path, label="analysis report output")
        transition_motif_phrase_abstraction_ladder = _transition_motif_phrase_abstraction_ladder(
            observation_summary
        )
        report_document = {
            "command": payload["command"],
            "input_audio": payload["input_audio"],
            "analysis_profile": payload["analysis_profile"],
            "source_id": payload["source_id"],
            "attention_contract": dict(payload["attention_contract"]),
            "interpretation_layers": dict(payload["interpretation_layers"]),
            "transformation_intent": dict(payload["transformation_intent"]),
            "decoded_audio": dict(payload["decoded_audio"]),
            "analysis_window": dict(payload["analysis_window"]),
            "observation_summary": dict(payload["observation_summary"]),
            "observation_preview": {
                "onset_map_count": len(onset_map),
                "section_boundary_count": len(section_boundaries),
                "section_candidate_count": len(section_candidates),
                "section_transition_count": len(section_transitions),
                "section_profile_summary": section_profile_summary,
                "transition_profile_summary": transition_profile_summary,
                "transition_motif_summary": transition_motif_summary,
                "transition_motif_sequence_summary": transition_motif_sequence_summary,
                "transition_motif_chain_summary": transition_motif_chain_summary,
                "transition_motif_phrase_summary": transition_motif_phrase_summary,
                "transition_motif_phrase_family_summary": transition_motif_phrase_family_summary,
                "transition_motif_phrase_archetype_summary": transition_motif_phrase_archetype_summary,
                "transition_motif_phrase_contour_summary": transition_motif_phrase_contour_summary,
                "transition_motif_phrase_sweep_summary": transition_motif_phrase_sweep_summary,
                "transition_motif_phrase_gesture_summary": transition_motif_phrase_gesture_summary,
                "transition_motif_phrase_mobility_summary": transition_motif_phrase_mobility_summary,
                "transition_motif_phrase_abstraction_ladder": transition_motif_phrase_abstraction_ladder,
                "first_onset": onset_map[0] if onset_map else None,
                "first_section_boundary": section_boundaries[0] if section_boundaries else None,
                "first_section_candidate": section_candidates[0] if section_candidates else None,
                "first_section_transition": section_transitions[0] if section_transitions else None,
                "first_transition_motif": (_list_optional(transition_motif_summary.get("motifs")) or [None])[0] if transition_motif_summary else None,
                "first_transition_motif_sequence": (_list_optional(transition_motif_sequence_summary.get("sequences")) or [None])[0] if transition_motif_sequence_summary else None,
                "first_transition_motif_chain": (_list_optional(transition_motif_chain_summary.get("chains")) or [None])[0] if transition_motif_chain_summary else None,
                "first_transition_motif_phrase": (_list_optional(transition_motif_phrase_summary.get("phrases")) or [None])[0] if transition_motif_phrase_summary else None,
                "first_transition_motif_phrase_family": (_list_optional(transition_motif_phrase_family_summary.get("families")) or [None])[0] if transition_motif_phrase_family_summary else None,
                "first_transition_motif_phrase_archetype": (_list_optional(transition_motif_phrase_archetype_summary.get("archetypes")) or [None])[0] if transition_motif_phrase_archetype_summary else None,
                "first_transition_motif_phrase_contour": (_list_optional(transition_motif_phrase_contour_summary.get("contours")) or [None])[0] if transition_motif_phrase_contour_summary else None,
                "first_transition_motif_phrase_sweep": (_list_optional(transition_motif_phrase_sweep_summary.get("sweeps")) or [None])[0] if transition_motif_phrase_sweep_summary else None,
                "first_transition_motif_phrase_gesture": (_list_optional(transition_motif_phrase_gesture_summary.get("gestures")) or [None])[0] if transition_motif_phrase_gesture_summary else None,
                "first_transition_motif_phrase_mobility": (_list_optional(transition_motif_phrase_mobility_summary.get("mobilities")) or [None])[0] if transition_motif_phrase_mobility_summary else None,
            },
            "source_hypothesis_preview": {
                "source_hypothesis_count": len(source_hypotheses),
                "source_hypothesis_classes": _source_hypothesis_classes(source_hypotheses),
                "first_source_hypothesis": source_hypotheses[0] if source_hypotheses else None,
            },
            "warnings": list(payload["warnings"]),
            "is_valid": True,
        }
        _write_auxiliary_document(report_path, report_document, report_format)
        payload["report_output"] = str(report_path)
        payload["report_format"] = report_format

    return payload


def _build_initial_interpretation_layers(
    *,
    source_hypotheses: list[dict[str, Any]],
    attention_contract: dict[str, Any],
    transformation_intent: dict[str, Any],
) -> dict[str, Any]:
    if not attention_contract and not transformation_intent:
        return {}

    source_ids = [
        source_hypothesis.get("source_id")
        for source_hypothesis in source_hypotheses
        if isinstance(source_hypothesis, dict) and isinstance(source_hypothesis.get("source_id"), str)
    ]
    source_classes = _source_hypothesis_classes(source_hypotheses)
    attention_targets = _string_list(attention_contract.get("attention_targets"))
    retain_targets = _string_list(attention_contract.get("retain_targets"))
    suppress_targets = _string_list(attention_contract.get("suppress_targets"))
    answer_expectations = _string_list(attention_contract.get("answer_expectations"))
    query_text = _normalized_optional_string(attention_contract.get("query_text"))
    render_goal = _normalized_optional_string(attention_contract.get("render_goal"))
    transformation_operations = _string_list(transformation_intent.get("operations"))

    matched_attention_targets = sorted(target for target in attention_targets if target in set(source_classes))
    unmatched_attention_targets = sorted(target for target in attention_targets if target not in set(source_classes))

    scene_confidence = min(0.34, 0.18 + (0.04 * min(len(source_classes), 3)) + (0.04 if matched_attention_targets else 0.0))
    scene_hypotheses = [
        {
            "hypothesis_id": "scene.01",
            "label": (
                "task-conditioned scene sketch over observed source-like structures"
                if source_classes
                else "task-conditioned scene sketch without resolved source-like structures"
            ),
            "confidence": _round_float(scene_confidence),
            "confidence_band": _confidence_band(scene_confidence),
            "hypothesis_origin": "task-conditioned-observation-summary",
            "observed_source_classes": source_classes,
            "linked_source_ids": source_ids,
            "attention_targets_matched_source_classes": matched_attention_targets,
            "attention_targets_unmatched": unmatched_attention_targets,
            "supporting_observations": [
                "scene sketch is derived from observation-layer source hypotheses",
                "task inputs constrain which observed structures matter for later reasoning",
            ],
            "ambiguity_notes": [
                "This is not source separation or semantic recognition; it is a query-conditioned workspace summary.",
            ],
        }
    ]

    communicative_hypotheses: list[dict[str, Any]] = []
    if _communicative_interest_present(query_text, answer_expectations) and "foreground_call_stream" in source_classes:
        communicative_confidence = 0.22
        communicative_hypotheses.append(
            {
                "hypothesis_id": "comm.01",
                "label": "foreground call stream may carry query-relevant communicative structure",
                "confidence": _round_float(communicative_confidence),
                "confidence_band": _confidence_band(communicative_confidence),
                "hypothesis_origin": "task-conditioned-observation-summary",
                "linked_source_classes": ["foreground_call_stream"],
                "answer_expectations": answer_expectations,
                "supporting_observations": [
                    "foreground call stream was detected in the observation-derived source hypotheses",
                    "the task requests communicative or explanatory follow-up rather than only structural retention",
                ],
                "ambiguity_notes": [
                    "No semantic decoding is performed here; this only records that communicative follow-up may be relevant.",
                ],
            }
        )

    return {
        "scene_hypotheses": scene_hypotheses,
        "communicative_hypotheses": communicative_hypotheses,
        "task_conditioning_notes": {
            "status": "task-conditioned",
            "query_text_present": query_text is not None,
            "retain_target_count": len(retain_targets),
            "suppress_target_count": len(suppress_targets),
            "answer_expectation_count": len(answer_expectations),
            "transformation_operation_count": len(transformation_operations),
            "render_goal": render_goal,
        },
    }


def _communicative_interest_present(query_text: str | None, answer_expectations: list[str]) -> bool:
    haystacks = [query_text or "", *answer_expectations]
    keywords = ("say", "saying", "speech", "lyric", "lyrics", "communicat", "meaning", "summarize")
    return any(keyword in haystack.lower() for haystack in haystacks for keyword in keywords)


def inspect_analysis_document(path: str | Path) -> dict[str, Any]:
    document_path = Path(path)
    validation_report = validate_analysis_document(document_path)
    if not validation_report.is_valid or validation_report.normalized_document is None:
        if validation_report.errors:
            raise ValueError(validation_report.errors[0])
        raise ValueError("analysis document failed validation")

    document = validation_report.normalized_document
    analysis_metadata = _mapping_optional(document.get("analysis_metadata"))
    observed_audio = _mapping_optional(document.get("observed_audio"))
    attention_contract = _mapping_optional(document.get("attention_contract"))
    observation_layers = _mapping_optional(document.get("observation_layers"))
    source_hypotheses = _list_optional(document.get("source_hypotheses"))
    interpretation_layers = _mapping_optional(document.get("interpretation_layers"))
    component_layers = _mapping_optional(document.get("component_layers"))
    transformation_intent = _mapping_optional(document.get("transformation_intent"))
    reconstruction = _mapping_optional(document.get("reconstruction"))
    uncertainty_notes = _mapping_optional(document.get("uncertainty_notes"))
    provenance = _mapping_optional(document.get("provenance"))

    analysis_window = _mapping_optional(observed_audio.get("analysis_window"))
    basic_observation_summary = _mapping_optional(observation_layers.get("basic_observation_summary"))
    onset_map = _list_optional(observation_layers.get("onset_map"))
    section_boundaries = _list_optional(observation_layers.get("section_boundaries"))
    section_candidates = _list_optional(observation_layers.get("section_candidates"))
    section_transitions = _list_optional(observation_layers.get("section_transitions"))
    reconstructable_outputs = _string_list(reconstruction.get("reconstructable_outputs"))
    uncertainty_warning_count = len(_string_list(uncertainty_notes.get("warnings")))
    section_profile_summary = _mapping_optional(basic_observation_summary.get("section_profile_summary"))
    transition_profile_summary = _mapping_optional(basic_observation_summary.get("transition_profile_summary"))
    transition_motif_summary = _mapping_optional(basic_observation_summary.get("transition_motif_summary"))
    transition_motif_sequence_summary = _mapping_optional(basic_observation_summary.get("transition_motif_sequence_summary"))
    transition_motif_chain_summary = _mapping_optional(basic_observation_summary.get("transition_motif_chain_summary"))
    transition_motif_phrase_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_summary"))
    transition_motif_phrase_family_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_family_summary")
    )
    transition_motif_phrase_archetype_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_archetype_summary")
    )
    transition_motif_phrase_contour_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_contour_summary")
    )
    transition_motif_phrase_sweep_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_sweep_summary")
    )
    transition_motif_phrase_gesture_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_gesture_summary")
    )
    transition_motif_phrase_mobility_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_phrase_mobility_summary")
    )
    transition_motif_phrase_abstraction_ladder = _transition_motif_phrase_abstraction_ladder(
        basic_observation_summary
    )
    highest_stable_transition_motif_abstraction_layer = _highest_stable_transition_motif_abstraction_layer(
        basic_observation_summary
    )
    source_hypothesis_classes = _source_hypothesis_classes(source_hypotheses)
    source_hypothesis_roles = _source_hypothesis_roles(source_hypotheses)
    source_hypothesis_linked_transition_motif_signatures = _source_hypothesis_linked_transition_motif_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_sequence_signatures = _source_hypothesis_linked_transition_motif_sequence_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_chain_signatures = _source_hypothesis_linked_transition_motif_chain_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_signatures = _source_hypothesis_linked_transition_motif_phrase_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_family_signatures = _source_hypothesis_linked_transition_motif_phrase_family_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_archetype_signatures = _source_hypothesis_linked_transition_motif_phrase_archetype_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_contour_signatures = _source_hypothesis_linked_transition_motif_phrase_contour_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_sweep_signatures = _source_hypothesis_linked_transition_motif_phrase_sweep_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_gesture_signatures = _source_hypothesis_linked_transition_motif_phrase_gesture_signatures(source_hypotheses)
    source_hypothesis_linked_transition_motif_phrase_mobility_signatures = _source_hypothesis_linked_transition_motif_phrase_mobility_signatures(source_hypotheses)
    interpretation_layer_names = sorted(interpretation_layers.keys())
    interpretation_hypothesis_count = sum(
        len(value) for value in interpretation_layers.values() if isinstance(value, list)
    )
    scene_hypotheses = _list_optional(interpretation_layers.get("scene_hypotheses"))
    communicative_hypotheses = _list_optional(interpretation_layers.get("communicative_hypotheses"))

    payload = {
        "command": "arwif-inspect-analysis",
        "analysis_document": str(document_path),
        "analysis_document_format": _resolve_auxiliary_format(document_path, label="analysis document"),
        "analysis_profile": analysis_metadata.get("analysis_profile"),
        "analysis_version": analysis_metadata.get("analysis_version"),
        "analyzer_id": analysis_metadata.get("analyzer_id"),
        "source_id": analysis_metadata.get("source_id"),
        "observed_audio": {
            "path_hint": observed_audio.get("path_hint"),
            "duration_seconds": observed_audio.get("duration_seconds"),
            "sample_rate_hz": observed_audio.get("sample_rate_hz"),
            "channel_count": observed_audio.get("channel_count"),
            "codec": observed_audio.get("codec"),
            "original_sample_rate_hz": observed_audio.get("original_sample_rate_hz"),
            "original_channel_count": observed_audio.get("original_channel_count"),
        },
        "analysis_window": {
            "start_seconds": analysis_window.get("start_seconds"),
            "duration_seconds": analysis_window.get("duration_seconds"),
        },
        "attention_contract": {
            "query_text": attention_contract.get("query_text"),
            "attention_targets": _string_list(attention_contract.get("attention_targets")),
            "retain_targets": _string_list(attention_contract.get("retain_targets")),
            "suppress_targets": _string_list(attention_contract.get("suppress_targets")),
            "answer_expectations": _string_list(attention_contract.get("answer_expectations")),
            "render_goal": attention_contract.get("render_goal"),
        },
        "observation_layer_names": sorted(observation_layers.keys()),
        "onset_map_count": len(onset_map),
        "section_boundary_count": len(section_boundaries),
        "section_candidate_count": len(section_candidates),
        "section_transition_count": len(section_transitions),
        "section_profile_summary": section_profile_summary,
        "transition_profile_summary": transition_profile_summary,
        "transition_motif_summary": transition_motif_summary,
        "transition_motif_sequence_summary": transition_motif_sequence_summary,
        "transition_motif_chain_summary": transition_motif_chain_summary,
        "transition_motif_phrase_summary": transition_motif_phrase_summary,
        "transition_motif_phrase_family_summary": transition_motif_phrase_family_summary,
        "transition_motif_phrase_archetype_summary": transition_motif_phrase_archetype_summary,
        "transition_motif_phrase_contour_summary": transition_motif_phrase_contour_summary,
        "transition_motif_phrase_sweep_summary": transition_motif_phrase_sweep_summary,
        "transition_motif_phrase_gesture_summary": transition_motif_phrase_gesture_summary,
        "transition_motif_phrase_mobility_summary": transition_motif_phrase_mobility_summary,
        "transition_motif_phrase_abstraction_ladder": transition_motif_phrase_abstraction_ladder,
        "highest_stable_transition_motif_abstraction_layer": highest_stable_transition_motif_abstraction_layer,
        "first_onset": onset_map[0] if onset_map else None,
        "first_section_boundary": section_boundaries[0] if section_boundaries else None,
        "first_section_candidate": section_candidates[0] if section_candidates else None,
        "first_section_transition": section_transitions[0] if section_transitions else None,
        "first_transition_motif": (_list_optional(transition_motif_summary.get("motifs")) or [None])[0] if transition_motif_summary else None,
        "first_transition_motif_sequence": (_list_optional(transition_motif_sequence_summary.get("sequences")) or [None])[0] if transition_motif_sequence_summary else None,
        "first_transition_motif_chain": (_list_optional(transition_motif_chain_summary.get("chains")) or [None])[0] if transition_motif_chain_summary else None,
        "first_transition_motif_phrase": (_list_optional(transition_motif_phrase_summary.get("phrases")) or [None])[0] if transition_motif_phrase_summary else None,
        "first_transition_motif_phrase_family": (_list_optional(transition_motif_phrase_family_summary.get("families")) or [None])[0] if transition_motif_phrase_family_summary else None,
        "first_transition_motif_phrase_archetype": (_list_optional(transition_motif_phrase_archetype_summary.get("archetypes")) or [None])[0] if transition_motif_phrase_archetype_summary else None,
        "first_transition_motif_phrase_contour": (_list_optional(transition_motif_phrase_contour_summary.get("contours")) or [None])[0] if transition_motif_phrase_contour_summary else None,
        "first_transition_motif_phrase_sweep": (_list_optional(transition_motif_phrase_sweep_summary.get("sweeps")) or [None])[0] if transition_motif_phrase_sweep_summary else None,
        "first_transition_motif_phrase_gesture": (_list_optional(transition_motif_phrase_gesture_summary.get("gestures")) or [None])[0] if transition_motif_phrase_gesture_summary else None,
        "first_transition_motif_phrase_mobility": (_list_optional(transition_motif_phrase_mobility_summary.get("mobilities")) or [None])[0] if transition_motif_phrase_mobility_summary else None,
        "source_hypothesis_count": len(source_hypotheses),
        "source_hypothesis_classes": source_hypothesis_classes,
        "source_hypothesis_roles": source_hypothesis_roles,
        "source_hypothesis_linked_transition_motif_signature_count": len(source_hypothesis_linked_transition_motif_signatures),
        "source_hypothesis_linked_transition_motif_signatures": source_hypothesis_linked_transition_motif_signatures,
        "source_hypothesis_linked_transition_motif_sequence_signature_count": len(source_hypothesis_linked_transition_motif_sequence_signatures),
        "source_hypothesis_linked_transition_motif_sequence_signatures": source_hypothesis_linked_transition_motif_sequence_signatures,
        "source_hypothesis_linked_transition_motif_chain_signature_count": len(source_hypothesis_linked_transition_motif_chain_signatures),
        "source_hypothesis_linked_transition_motif_chain_signatures": source_hypothesis_linked_transition_motif_chain_signatures,
        "source_hypothesis_linked_transition_motif_phrase_signature_count": len(source_hypothesis_linked_transition_motif_phrase_signatures),
        "source_hypothesis_linked_transition_motif_phrase_signatures": source_hypothesis_linked_transition_motif_phrase_signatures,
        "source_hypothesis_linked_transition_motif_phrase_family_signature_count": len(source_hypothesis_linked_transition_motif_phrase_family_signatures),
        "source_hypothesis_linked_transition_motif_phrase_family_signatures": source_hypothesis_linked_transition_motif_phrase_family_signatures,
        "source_hypothesis_linked_transition_motif_phrase_archetype_signature_count": len(source_hypothesis_linked_transition_motif_phrase_archetype_signatures),
        "source_hypothesis_linked_transition_motif_phrase_archetype_signatures": source_hypothesis_linked_transition_motif_phrase_archetype_signatures,
        "source_hypothesis_linked_transition_motif_phrase_contour_signature_count": len(source_hypothesis_linked_transition_motif_phrase_contour_signatures),
        "source_hypothesis_linked_transition_motif_phrase_contour_signatures": source_hypothesis_linked_transition_motif_phrase_contour_signatures,
        "source_hypothesis_linked_transition_motif_phrase_sweep_signature_count": len(source_hypothesis_linked_transition_motif_phrase_sweep_signatures),
        "source_hypothesis_linked_transition_motif_phrase_sweep_signatures": source_hypothesis_linked_transition_motif_phrase_sweep_signatures,
        "source_hypothesis_linked_transition_motif_phrase_gesture_signature_count": len(source_hypothesis_linked_transition_motif_phrase_gesture_signatures),
        "source_hypothesis_linked_transition_motif_phrase_gesture_signatures": source_hypothesis_linked_transition_motif_phrase_gesture_signatures,
        "source_hypothesis_linked_transition_motif_phrase_mobility_signature_count": len(source_hypothesis_linked_transition_motif_phrase_mobility_signatures),
        "source_hypothesis_linked_transition_motif_phrase_mobility_signatures": source_hypothesis_linked_transition_motif_phrase_mobility_signatures,
        "first_source_hypothesis": source_hypotheses[0] if source_hypotheses else None,
        "interpretation_layer_names": interpretation_layer_names,
        "interpretation_hypothesis_count": interpretation_hypothesis_count,
        "first_scene_hypothesis": scene_hypotheses[0] if scene_hypotheses else None,
        "first_communicative_hypothesis": communicative_hypotheses[0] if communicative_hypotheses else None,
        "component_layer_names": sorted(component_layers.keys()),
        "component_group_count": _count_component_groups(component_layers),
        "transformation_intent": transformation_intent,
        "reconstructable_outputs": reconstructable_outputs,
        "uncertainty_warning_count": uncertainty_warning_count,
        "uncertainty_note_keys": sorted(uncertainty_notes.keys()),
        "provenance_summary": {
            "decode_backend": provenance.get("decode_backend"),
            "input_file_hash_present": isinstance(provenance.get("input_file_hash"), str) and bool(provenance.get("input_file_hash")),
            "preprocessing_step_count": len(_string_list(provenance.get("preprocessing_steps"))),
        },
        "basic_observation_summary": basic_observation_summary,
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    return payload


def _transition_motif_phrase_abstraction_ladder(
    basic_observation_summary: dict[str, Any],
) -> dict[str, dict[str, int]]:
    phrase_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_summary"))
    family_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_family_summary"))
    archetype_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_archetype_summary"))
    contour_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_contour_summary"))
    sweep_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_sweep_summary"))
    gesture_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_gesture_summary"))
    mobility_summary = _mapping_optional(basic_observation_summary.get("transition_motif_phrase_mobility_summary"))
    return {
        "recurring_counts": {
            "phrase": int(phrase_summary.get("recurring_phrase_count", 0) or 0),
            "family": int(family_summary.get("recurring_family_count", 0) or 0),
            "archetype": int(archetype_summary.get("recurring_archetype_count", 0) or 0),
            "contour": int(contour_summary.get("recurring_contour_count", 0) or 0),
            "sweep": int(sweep_summary.get("recurring_sweep_count", 0) or 0),
            "gesture": int(gesture_summary.get("recurring_gesture_count", 0) or 0),
            "mobility": int(mobility_summary.get("recurring_mobility_count", 0) or 0),
        },
        "occurrence_counts": {
            "phrase": int(phrase_summary.get("phrase_occurrence_count", 0) or 0),
            "family": int(family_summary.get("family_occurrence_count", 0) or 0),
            "archetype": int(archetype_summary.get("archetype_occurrence_count", 0) or 0),
            "contour": int(contour_summary.get("contour_occurrence_count", 0) or 0),
            "sweep": int(sweep_summary.get("sweep_occurrence_count", 0) or 0),
            "gesture": int(gesture_summary.get("gesture_occurrence_count", 0) or 0),
            "mobility": int(mobility_summary.get("mobility_occurrence_count", 0) or 0),
        },
    }


def _highest_stable_transition_motif_abstraction_layer(
    basic_observation_summary: dict[str, Any],
) -> dict[str, int | str]:
    transition_motif_summary = _mapping_optional(basic_observation_summary.get("transition_motif_summary"))
    transition_motif_sequence_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_sequence_summary")
    )
    transition_motif_chain_summary = _mapping_optional(
        basic_observation_summary.get("transition_motif_chain_summary")
    )
    abstraction_ladder = _transition_motif_phrase_abstraction_ladder(basic_observation_summary)
    recurring_counts = {
        "motif": int(transition_motif_summary.get("recurring_motif_count", 0) or 0),
        "sequence": int(transition_motif_sequence_summary.get("recurring_sequence_count", 0) or 0),
        "chain": int(transition_motif_chain_summary.get("recurring_chain_count", 0) or 0),
        **_mapping_optional(abstraction_ladder.get("recurring_counts")),
    }
    occurrence_counts = {
        "motif": int(transition_motif_summary.get("motif_occurrence_count", 0) or 0),
        "sequence": int(transition_motif_sequence_summary.get("sequence_occurrence_count", 0) or 0),
        "chain": int(transition_motif_chain_summary.get("chain_occurrence_count", 0) or 0),
        **_mapping_optional(abstraction_ladder.get("occurrence_counts")),
    }
    for layer in reversed(TRANSITION_MOTIF_ABSTRACTION_LAYER_ORDER):
        recurring_count = int(recurring_counts.get(layer, 0) or 0)
        if recurring_count > 0:
            return {
                "layer": layer,
                "recurring_count": recurring_count,
                "occurrence_count": int(occurrence_counts.get(layer, 0) or 0),
            }
    return {
        "layer": "none",
        "recurring_count": 0,
        "occurrence_count": 0,
    }


def _highest_stable_transition_motif_abstraction_layer_change(
    left_layer_summary: dict[str, Any],
    right_layer_summary: dict[str, Any],
) -> dict[str, Any]:
    left_layer = str(left_layer_summary.get("layer", "none") or "none")
    right_layer = str(right_layer_summary.get("layer", "none") or "none")
    left_rank = TRANSITION_MOTIF_ABSTRACTION_LAYER_RANK.get(left_layer, -1)
    right_rank = TRANSITION_MOTIF_ABSTRACTION_LAYER_RANK.get(right_layer, -1)
    layer_step_delta = right_rank - left_rank
    if layer_step_delta > 0:
        direction = "rose"
    elif layer_step_delta < 0:
        direction = "fell"
    else:
        direction = "unchanged"
    left_recurring_count = int(left_layer_summary.get("recurring_count", 0) or 0)
    right_recurring_count = int(right_layer_summary.get("recurring_count", 0) or 0)
    left_occurrence_count = int(left_layer_summary.get("occurrence_count", 0) or 0)
    right_occurrence_count = int(right_layer_summary.get("occurrence_count", 0) or 0)
    return {
        "left": {
            "layer": left_layer,
            "recurring_count": left_recurring_count,
            "occurrence_count": left_occurrence_count,
        },
        "right": {
            "layer": right_layer,
            "recurring_count": right_recurring_count,
            "occurrence_count": right_occurrence_count,
        },
        "layer_changed": left_layer != right_layer,
        "direction": direction,
        "layer_step_delta": layer_step_delta,
        "recurring_count_delta": right_recurring_count - left_recurring_count,
        "occurrence_count_delta": right_occurrence_count - left_occurrence_count,
    }


def diff_analysis_documents(
    left: str | Path,
    right: str | Path,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    left_path = Path(left)
    right_path = Path(right)

    left_summary = inspect_analysis_document(left_path)
    right_summary = inspect_analysis_document(right_path)

    metadata_changes = _selected_field_changes(
        left_summary,
        right_summary,
        ("analysis_profile", "analysis_version", "analyzer_id", "source_id"),
    )
    observed_audio_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("observed_audio")),
        _mapping_optional(right_summary.get("observed_audio")),
        (
            "path_hint",
            "duration_seconds",
            "sample_rate_hz",
            "channel_count",
            "codec",
            "original_sample_rate_hz",
            "original_channel_count",
        ),
    )
    analysis_window_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("analysis_window")),
        _mapping_optional(right_summary.get("analysis_window")),
        ("start_seconds", "duration_seconds"),
    )
    attention_contract_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("attention_contract")),
        _mapping_optional(right_summary.get("attention_contract")),
        ("query_text", "attention_targets", "retain_targets", "suppress_targets", "answer_expectations", "render_goal"),
    )
    transformation_intent_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("transformation_intent")),
        _mapping_optional(right_summary.get("transformation_intent")),
        ("operations", "primary_output"),
    )
    provenance_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("provenance_summary")),
        _mapping_optional(right_summary.get("provenance_summary")),
        ("decode_backend", "input_file_hash_present", "preprocessing_step_count"),
    )
    basic_observation_changes = _diff_basic_observation_summaries(
        _mapping_optional(left_summary.get("basic_observation_summary")),
        _mapping_optional(right_summary.get("basic_observation_summary")),
    )
    highest_stable_transition_motif_abstraction_layer_change = (
        _highest_stable_transition_motif_abstraction_layer_change(
            _mapping_optional(left_summary.get("highest_stable_transition_motif_abstraction_layer")),
            _mapping_optional(right_summary.get("highest_stable_transition_motif_abstraction_layer")),
        )
    )

    left_layers = set(_string_list(left_summary.get("observation_layer_names")))
    right_layers = set(_string_list(right_summary.get("observation_layer_names")))
    left_interpretation_layers = set(_string_list(left_summary.get("interpretation_layer_names")))
    right_interpretation_layers = set(_string_list(right_summary.get("interpretation_layer_names")))
    left_component_layers = set(_string_list(left_summary.get("component_layer_names")))
    right_component_layers = set(_string_list(right_summary.get("component_layer_names")))
    left_outputs = set(_string_list(left_summary.get("reconstructable_outputs")))
    right_outputs = set(_string_list(right_summary.get("reconstructable_outputs")))
    left_uncertainty_keys = set(_string_list(left_summary.get("uncertainty_note_keys")))
    right_uncertainty_keys = set(_string_list(right_summary.get("uncertainty_note_keys")))
    left_source_hypothesis_classes = set(_string_list(left_summary.get("source_hypothesis_classes")))
    right_source_hypothesis_classes = set(_string_list(right_summary.get("source_hypothesis_classes")))
    left_source_hypothesis_linked_transition_motif_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_sequence_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_sequence_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_sequence_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_sequence_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_chain_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_chain_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_chain_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_chain_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_family_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_family_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_family_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_family_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_archetype_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_archetype_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_archetype_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_archetype_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_contour_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_contour_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_contour_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_contour_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_sweep_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_sweep_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_sweep_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_sweep_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_gesture_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_gesture_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_gesture_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_gesture_signatures"))
    )
    left_source_hypothesis_linked_transition_motif_phrase_mobility_signatures = set(
        _string_list(left_summary.get("source_hypothesis_linked_transition_motif_phrase_mobility_signatures"))
    )
    right_source_hypothesis_linked_transition_motif_phrase_mobility_signatures = set(
        _string_list(right_summary.get("source_hypothesis_linked_transition_motif_phrase_mobility_signatures"))
    )
    left_transition_motif_signatures = set(_transition_motif_signatures(_mapping_optional(left_summary.get("transition_motif_summary"))))
    right_transition_motif_signatures = set(_transition_motif_signatures(_mapping_optional(right_summary.get("transition_motif_summary"))))
    left_transition_motif_sequence_signatures = set(
        _transition_motif_sequence_signatures(_mapping_optional(left_summary.get("transition_motif_sequence_summary")))
    )
    right_transition_motif_sequence_signatures = set(
        _transition_motif_sequence_signatures(_mapping_optional(right_summary.get("transition_motif_sequence_summary")))
    )
    left_transition_motif_chain_signatures = set(
        _transition_motif_chain_signatures(_mapping_optional(left_summary.get("transition_motif_chain_summary")))
    )
    right_transition_motif_chain_signatures = set(
        _transition_motif_chain_signatures(_mapping_optional(right_summary.get("transition_motif_chain_summary")))
    )
    left_transition_motif_phrase_signatures = set(
        _transition_motif_phrase_signatures(_mapping_optional(left_summary.get("transition_motif_phrase_summary")))
    )
    right_transition_motif_phrase_signatures = set(
        _transition_motif_phrase_signatures(_mapping_optional(right_summary.get("transition_motif_phrase_summary")))
    )
    left_transition_motif_phrase_family_signatures = set(
        _transition_motif_phrase_family_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_family_summary"))
        )
    )
    right_transition_motif_phrase_family_signatures = set(
        _transition_motif_phrase_family_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_family_summary"))
        )
    )
    left_transition_motif_phrase_archetype_signatures = set(
        _transition_motif_phrase_archetype_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_archetype_summary"))
        )
    )
    right_transition_motif_phrase_archetype_signatures = set(
        _transition_motif_phrase_archetype_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_archetype_summary"))
        )
    )
    left_transition_motif_phrase_contour_signatures = set(
        _transition_motif_phrase_contour_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_contour_summary"))
        )
    )
    right_transition_motif_phrase_contour_signatures = set(
        _transition_motif_phrase_contour_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_contour_summary"))
        )
    )
    left_transition_motif_phrase_sweep_signatures = set(
        _transition_motif_phrase_sweep_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_sweep_summary"))
        )
    )
    right_transition_motif_phrase_sweep_signatures = set(
        _transition_motif_phrase_sweep_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_sweep_summary"))
        )
    )
    left_transition_motif_phrase_gesture_signatures = set(
        _transition_motif_phrase_gesture_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_gesture_summary"))
        )
    )
    right_transition_motif_phrase_gesture_signatures = set(
        _transition_motif_phrase_gesture_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_gesture_summary"))
        )
    )
    left_transition_motif_phrase_mobility_signatures = set(
        _transition_motif_phrase_mobility_signatures(
            _mapping_optional(left_summary.get("transition_motif_phrase_mobility_summary"))
        )
    )
    right_transition_motif_phrase_mobility_signatures = set(
        _transition_motif_phrase_mobility_signatures(
            _mapping_optional(right_summary.get("transition_motif_phrase_mobility_summary"))
        )
    )
    first_scene_hypothesis_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("first_scene_hypothesis")),
        _mapping_optional(right_summary.get("first_scene_hypothesis")),
        (
            "hypothesis_id",
            "label",
            "confidence",
            "confidence_band",
            "hypothesis_origin",
            "observed_source_classes",
            "linked_source_ids",
            "attention_targets_matched_source_classes",
            "attention_targets_unmatched",
        ),
    )
    first_communicative_hypothesis_changes = _selected_field_changes(
        _mapping_optional(left_summary.get("first_communicative_hypothesis")),
        _mapping_optional(right_summary.get("first_communicative_hypothesis")),
        (
            "hypothesis_id",
            "label",
            "confidence",
            "confidence_band",
            "hypothesis_origin",
            "linked_source_classes",
            "answer_expectations",
        ),
    )

    source_hypothesis_count_delta = int(right_summary.get("source_hypothesis_count", 0) or 0) - int(
        left_summary.get("source_hypothesis_count", 0) or 0
    )
    interpretation_hypothesis_count_delta = int(right_summary.get("interpretation_hypothesis_count", 0) or 0) - int(
        left_summary.get("interpretation_hypothesis_count", 0) or 0
    )
    recurring_transition_motif_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_summary")).get("recurring_motif_count", 0) or 0
    ) - int(_mapping_optional(left_summary.get("transition_motif_summary")).get("recurring_motif_count", 0) or 0)
    recurring_transition_motif_sequence_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_sequence_summary")).get("recurring_sequence_count", 0) or 0
    ) - int(_mapping_optional(left_summary.get("transition_motif_sequence_summary")).get("recurring_sequence_count", 0) or 0)
    recurring_transition_motif_chain_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_chain_summary")).get("recurring_chain_count", 0) or 0
    ) - int(_mapping_optional(left_summary.get("transition_motif_chain_summary")).get("recurring_chain_count", 0) or 0)
    recurring_transition_motif_phrase_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_summary")).get("recurring_phrase_count", 0) or 0
    ) - int(_mapping_optional(left_summary.get("transition_motif_phrase_summary")).get("recurring_phrase_count", 0) or 0)
    recurring_transition_motif_phrase_family_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_family_summary")).get("recurring_family_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_family_summary")).get("recurring_family_count", 0) or 0
    )
    recurring_transition_motif_phrase_archetype_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_archetype_summary")).get("recurring_archetype_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_archetype_summary")).get("recurring_archetype_count", 0) or 0
    )
    recurring_transition_motif_phrase_contour_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_contour_summary")).get("recurring_contour_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_contour_summary")).get("recurring_contour_count", 0) or 0
    )
    recurring_transition_motif_phrase_sweep_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_sweep_summary")).get("recurring_sweep_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_sweep_summary")).get("recurring_sweep_count", 0) or 0
    )
    recurring_transition_motif_phrase_gesture_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_gesture_summary")).get("recurring_gesture_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_gesture_summary")).get("recurring_gesture_count", 0) or 0
    )
    recurring_transition_motif_phrase_mobility_count_delta = int(
        _mapping_optional(right_summary.get("transition_motif_phrase_mobility_summary")).get("recurring_mobility_count", 0) or 0
    ) - int(
        _mapping_optional(left_summary.get("transition_motif_phrase_mobility_summary")).get("recurring_mobility_count", 0) or 0
    )
    component_group_count_delta = int(right_summary.get("component_group_count", 0) or 0) - int(
        left_summary.get("component_group_count", 0) or 0
    )
    onset_map_count_delta = int(right_summary.get("onset_map_count", 0) or 0) - int(
        left_summary.get("onset_map_count", 0) or 0
    )
    section_boundary_count_delta = int(right_summary.get("section_boundary_count", 0) or 0) - int(
        left_summary.get("section_boundary_count", 0) or 0
    )
    section_candidate_count_delta = int(right_summary.get("section_candidate_count", 0) or 0) - int(
        left_summary.get("section_candidate_count", 0) or 0
    )
    section_transition_count_delta = int(right_summary.get("section_transition_count", 0) or 0) - int(
        left_summary.get("section_transition_count", 0) or 0
    )
    uncertainty_warning_count_delta = int(right_summary.get("uncertainty_warning_count", 0) or 0) - int(
        left_summary.get("uncertainty_warning_count", 0) or 0
    )

    payload = {
        "command": "arwif-diff-analysis",
        "left": str(left_path),
        "right": str(right_path),
        "left_valid": True,
        "right_valid": True,
        "metadata_changes": metadata_changes,
        "observed_audio_changes": observed_audio_changes,
        "analysis_window_changes": analysis_window_changes,
        "attention_contract_changes": attention_contract_changes,
        "basic_observation_changes": basic_observation_changes,
        "highest_stable_transition_motif_abstraction_layer_change": highest_stable_transition_motif_abstraction_layer_change,
        "observation_layer_changes": {
            "added": sorted(right_layers - left_layers),
            "removed": sorted(left_layers - right_layers),
        },
        "interpretation_layer_changes": {
            "added": sorted(right_interpretation_layers - left_interpretation_layers),
            "removed": sorted(left_interpretation_layers - right_interpretation_layers),
        },
        "component_layer_changes": {
            "added": sorted(right_component_layers - left_component_layers),
            "removed": sorted(left_component_layers - right_component_layers),
        },
        "first_scene_hypothesis_changes": first_scene_hypothesis_changes,
        "first_communicative_hypothesis_changes": first_communicative_hypothesis_changes,
        "transformation_intent_changes": transformation_intent_changes,
        "reconstructable_outputs_added": sorted(right_outputs - left_outputs),
        "reconstructable_outputs_removed": sorted(left_outputs - right_outputs),
        "source_hypothesis_class_changes": {
            "added": sorted(right_source_hypothesis_classes - left_source_hypothesis_classes),
            "removed": sorted(left_source_hypothesis_classes - right_source_hypothesis_classes),
        },
        "source_hypothesis_linked_transition_motif_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_signatures
                - left_source_hypothesis_linked_transition_motif_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_signatures
                - right_source_hypothesis_linked_transition_motif_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_sequence_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_sequence_signatures
                - left_source_hypothesis_linked_transition_motif_sequence_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_sequence_signatures
                - right_source_hypothesis_linked_transition_motif_sequence_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_chain_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_chain_signatures
                - left_source_hypothesis_linked_transition_motif_chain_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_chain_signatures
                - right_source_hypothesis_linked_transition_motif_chain_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_family_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_family_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_family_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_family_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_family_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_archetype_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_contour_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_contour_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_contour_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_contour_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_contour_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_sweep_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_gesture_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
            ),
        },
        "source_hypothesis_linked_transition_motif_phrase_mobility_signature_changes": {
            "added": sorted(
                right_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
            ),
            "removed": sorted(
                left_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
            ),
        },
        "transition_motif_signature_changes": {
            "added": sorted(right_transition_motif_signatures - left_transition_motif_signatures),
            "removed": sorted(left_transition_motif_signatures - right_transition_motif_signatures),
        },
        "transition_motif_sequence_signature_changes": {
            "added": sorted(right_transition_motif_sequence_signatures - left_transition_motif_sequence_signatures),
            "removed": sorted(left_transition_motif_sequence_signatures - right_transition_motif_sequence_signatures),
        },
        "transition_motif_chain_signature_changes": {
            "added": sorted(right_transition_motif_chain_signatures - left_transition_motif_chain_signatures),
            "removed": sorted(left_transition_motif_chain_signatures - right_transition_motif_chain_signatures),
        },
        "transition_motif_phrase_signature_changes": {
            "added": sorted(right_transition_motif_phrase_signatures - left_transition_motif_phrase_signatures),
            "removed": sorted(left_transition_motif_phrase_signatures - right_transition_motif_phrase_signatures),
        },
        "transition_motif_phrase_family_signature_changes": {
            "added": sorted(right_transition_motif_phrase_family_signatures - left_transition_motif_phrase_family_signatures),
            "removed": sorted(left_transition_motif_phrase_family_signatures - right_transition_motif_phrase_family_signatures),
        },
        "transition_motif_phrase_archetype_signature_changes": {
            "added": sorted(right_transition_motif_phrase_archetype_signatures - left_transition_motif_phrase_archetype_signatures),
            "removed": sorted(left_transition_motif_phrase_archetype_signatures - right_transition_motif_phrase_archetype_signatures),
        },
        "transition_motif_phrase_contour_signature_changes": {
            "added": sorted(right_transition_motif_phrase_contour_signatures - left_transition_motif_phrase_contour_signatures),
            "removed": sorted(left_transition_motif_phrase_contour_signatures - right_transition_motif_phrase_contour_signatures),
        },
        "transition_motif_phrase_sweep_signature_changes": {
            "added": sorted(right_transition_motif_phrase_sweep_signatures - left_transition_motif_phrase_sweep_signatures),
            "removed": sorted(left_transition_motif_phrase_sweep_signatures - right_transition_motif_phrase_sweep_signatures),
        },
        "transition_motif_phrase_gesture_signature_changes": {
            "added": sorted(right_transition_motif_phrase_gesture_signatures - left_transition_motif_phrase_gesture_signatures),
            "removed": sorted(left_transition_motif_phrase_gesture_signatures - right_transition_motif_phrase_gesture_signatures),
        },
        "transition_motif_phrase_mobility_signature_changes": {
            "added": sorted(right_transition_motif_phrase_mobility_signatures - left_transition_motif_phrase_mobility_signatures),
            "removed": sorted(left_transition_motif_phrase_mobility_signatures - right_transition_motif_phrase_mobility_signatures),
        },
        "uncertainty_note_keys_added": sorted(right_uncertainty_keys - left_uncertainty_keys),
        "uncertainty_note_keys_removed": sorted(left_uncertainty_keys - right_uncertainty_keys),
        "source_hypothesis_count_delta": source_hypothesis_count_delta,
        "interpretation_hypothesis_count_delta": interpretation_hypothesis_count_delta,
        "recurring_transition_motif_count_delta": recurring_transition_motif_count_delta,
        "recurring_transition_motif_sequence_count_delta": recurring_transition_motif_sequence_count_delta,
        "recurring_transition_motif_chain_count_delta": recurring_transition_motif_chain_count_delta,
        "recurring_transition_motif_phrase_count_delta": recurring_transition_motif_phrase_count_delta,
        "recurring_transition_motif_phrase_family_count_delta": recurring_transition_motif_phrase_family_count_delta,
        "recurring_transition_motif_phrase_archetype_count_delta": recurring_transition_motif_phrase_archetype_count_delta,
        "recurring_transition_motif_phrase_contour_count_delta": recurring_transition_motif_phrase_contour_count_delta,
        "recurring_transition_motif_phrase_sweep_count_delta": recurring_transition_motif_phrase_sweep_count_delta,
        "recurring_transition_motif_phrase_gesture_count_delta": recurring_transition_motif_phrase_gesture_count_delta,
        "recurring_transition_motif_phrase_mobility_count_delta": recurring_transition_motif_phrase_mobility_count_delta,
        "component_group_count_delta": component_group_count_delta,
        "onset_map_count_delta": onset_map_count_delta,
        "section_boundary_count_delta": section_boundary_count_delta,
        "section_candidate_count_delta": section_candidate_count_delta,
        "section_transition_count_delta": section_transition_count_delta,
        "uncertainty_warning_count_delta": uncertainty_warning_count_delta,
        "provenance_changes": provenance_changes,
        "change_summary": {
            "metadata_fields_changed": len(metadata_changes),
            "observed_audio_fields_changed": len(observed_audio_changes),
            "analysis_window_fields_changed": len(analysis_window_changes),
            "attention_contract_fields_changed": len(attention_contract_changes),
            "basic_observation_fields_changed": len(basic_observation_changes),
            "highest_stable_transition_motif_abstraction_layer_changed": int(
                bool(highest_stable_transition_motif_abstraction_layer_change.get("layer_changed", False))
            ),
            "highest_stable_transition_motif_abstraction_layer_step_delta": int(
                highest_stable_transition_motif_abstraction_layer_change.get("layer_step_delta", 0) or 0
            ),
            "added_observation_layers": len(right_layers - left_layers),
            "removed_observation_layers": len(left_layers - right_layers),
            "added_interpretation_layers": len(right_interpretation_layers - left_interpretation_layers),
            "removed_interpretation_layers": len(left_interpretation_layers - right_interpretation_layers),
            "added_component_layers": len(right_component_layers - left_component_layers),
            "removed_component_layers": len(left_component_layers - right_component_layers),
            "first_scene_hypothesis_changed": int(bool(first_scene_hypothesis_changes)),
            "first_communicative_hypothesis_changed": int(bool(first_communicative_hypothesis_changes)),
            "transformation_intent_fields_changed": len(transformation_intent_changes),
            "reconstructable_outputs_added": len(right_outputs - left_outputs),
            "reconstructable_outputs_removed": len(left_outputs - right_outputs),
            "interpretation_hypothesis_count_changed": int(interpretation_hypothesis_count_delta != 0),
            "source_hypothesis_classes_added": len(right_source_hypothesis_classes - left_source_hypothesis_classes),
            "source_hypothesis_classes_removed": len(left_source_hypothesis_classes - right_source_hypothesis_classes),
            "source_hypothesis_linked_transition_motif_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_signatures
                - left_source_hypothesis_linked_transition_motif_signatures
            ),
            "source_hypothesis_linked_transition_motif_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_signatures
                - right_source_hypothesis_linked_transition_motif_signatures
            ),
            "source_hypothesis_linked_transition_motif_sequence_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_sequence_signatures
                - left_source_hypothesis_linked_transition_motif_sequence_signatures
            ),
            "source_hypothesis_linked_transition_motif_sequence_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_sequence_signatures
                - right_source_hypothesis_linked_transition_motif_sequence_signatures
            ),
            "source_hypothesis_linked_transition_motif_chain_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_chain_signatures
                - left_source_hypothesis_linked_transition_motif_chain_signatures
            ),
            "source_hypothesis_linked_transition_motif_chain_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_chain_signatures
                - right_source_hypothesis_linked_transition_motif_chain_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_family_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_family_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_family_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_family_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_family_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_archetype_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_archetype_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_contour_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_contour_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_contour_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_contour_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_contour_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_sweep_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_sweep_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_gesture_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_gesture_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_added": len(
                right_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
                - left_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
            ),
            "source_hypothesis_linked_transition_motif_phrase_mobility_signatures_removed": len(
                left_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
                - right_source_hypothesis_linked_transition_motif_phrase_mobility_signatures
            ),
            "transition_motif_signatures_added": len(right_transition_motif_signatures - left_transition_motif_signatures),
            "transition_motif_signatures_removed": len(left_transition_motif_signatures - right_transition_motif_signatures),
            "transition_motif_sequence_signatures_added": len(
                right_transition_motif_sequence_signatures - left_transition_motif_sequence_signatures
            ),
            "transition_motif_sequence_signatures_removed": len(
                left_transition_motif_sequence_signatures - right_transition_motif_sequence_signatures
            ),
            "transition_motif_chain_signatures_added": len(
                right_transition_motif_chain_signatures - left_transition_motif_chain_signatures
            ),
            "transition_motif_chain_signatures_removed": len(
                left_transition_motif_chain_signatures - right_transition_motif_chain_signatures
            ),
            "transition_motif_phrase_signatures_added": len(
                right_transition_motif_phrase_signatures - left_transition_motif_phrase_signatures
            ),
            "transition_motif_phrase_signatures_removed": len(
                left_transition_motif_phrase_signatures - right_transition_motif_phrase_signatures
            ),
            "transition_motif_phrase_family_signatures_added": len(
                right_transition_motif_phrase_family_signatures - left_transition_motif_phrase_family_signatures
            ),
            "transition_motif_phrase_family_signatures_removed": len(
                left_transition_motif_phrase_family_signatures - right_transition_motif_phrase_family_signatures
            ),
            "transition_motif_phrase_archetype_signatures_added": len(
                right_transition_motif_phrase_archetype_signatures - left_transition_motif_phrase_archetype_signatures
            ),
            "transition_motif_phrase_archetype_signatures_removed": len(
                left_transition_motif_phrase_archetype_signatures - right_transition_motif_phrase_archetype_signatures
            ),
            "transition_motif_phrase_contour_signatures_added": len(
                right_transition_motif_phrase_contour_signatures - left_transition_motif_phrase_contour_signatures
            ),
            "transition_motif_phrase_contour_signatures_removed": len(
                left_transition_motif_phrase_contour_signatures - right_transition_motif_phrase_contour_signatures
            ),
            "transition_motif_phrase_sweep_signatures_added": len(
                right_transition_motif_phrase_sweep_signatures - left_transition_motif_phrase_sweep_signatures
            ),
            "transition_motif_phrase_sweep_signatures_removed": len(
                left_transition_motif_phrase_sweep_signatures - right_transition_motif_phrase_sweep_signatures
            ),
            "transition_motif_phrase_gesture_signatures_added": len(
                right_transition_motif_phrase_gesture_signatures - left_transition_motif_phrase_gesture_signatures
            ),
            "transition_motif_phrase_gesture_signatures_removed": len(
                left_transition_motif_phrase_gesture_signatures - right_transition_motif_phrase_gesture_signatures
            ),
            "transition_motif_phrase_mobility_signatures_added": len(
                right_transition_motif_phrase_mobility_signatures - left_transition_motif_phrase_mobility_signatures
            ),
            "transition_motif_phrase_mobility_signatures_removed": len(
                left_transition_motif_phrase_mobility_signatures - right_transition_motif_phrase_mobility_signatures
            ),
            "provenance_fields_changed": len(provenance_changes),
            "onset_map_count_changed": int(onset_map_count_delta != 0),
            "section_boundary_count_changed": int(section_boundary_count_delta != 0),
            "section_candidate_count_changed": int(section_candidate_count_delta != 0),
            "section_transition_count_changed": int(section_transition_count_delta != 0),
            "recurring_transition_motif_count_changed": int(recurring_transition_motif_count_delta != 0),
            "recurring_transition_motif_sequence_count_changed": int(
                recurring_transition_motif_sequence_count_delta != 0
            ),
            "recurring_transition_motif_chain_count_changed": int(recurring_transition_motif_chain_count_delta != 0),
            "recurring_transition_motif_phrase_count_changed": int(recurring_transition_motif_phrase_count_delta != 0),
            "recurring_transition_motif_phrase_family_count_changed": int(
                recurring_transition_motif_phrase_family_count_delta != 0
            ),
            "recurring_transition_motif_phrase_archetype_count_changed": int(
                recurring_transition_motif_phrase_archetype_count_delta != 0
            ),
            "recurring_transition_motif_phrase_contour_count_changed": int(
                recurring_transition_motif_phrase_contour_count_delta != 0
            ),
            "recurring_transition_motif_phrase_sweep_count_changed": int(
                recurring_transition_motif_phrase_sweep_count_delta != 0
            ),
            "recurring_transition_motif_phrase_gesture_count_changed": int(
                recurring_transition_motif_phrase_gesture_count_delta != 0
            ),
            "recurring_transition_motif_phrase_mobility_count_changed": int(
                recurring_transition_motif_phrase_mobility_count_delta != 0
            ),
        },
    }

    payload["pair_changed"] = _analysis_pair_changed(payload)

    if output is not None:
        output_path = Path(output)
        report_format = _resolve_auxiliary_format(output_path, label="analysis diff output")
        _write_auxiliary_document(output_path, payload, report_format)
        payload["report_output"] = str(output_path)
        payload["report_format"] = report_format

    return payload


def _decode_audio(input_path: Path) -> dict[str, Any]:
    suffix = input_path.suffix.lower()
    if suffix == ".wav":
        try:
            samples, sample_rate_hz = _load_wav_pcm(input_path)
            return {
                "samples": samples,
                "sample_rate_hz": sample_rate_hz,
                "codec": "wav",
                "original_sample_rate_hz": sample_rate_hz,
                "original_channel_count": samples.shape[1],
                "decode_backend": "wave",
                "warnings": [],
            }
        except ValueError:
            pass
    return _decode_audio_with_ffmpeg(input_path)


def _load_analysis_document(input_path: Path) -> dict[str, Any]:
    if input_path.suffix.lower() not in SUPPORTED_ANALYSIS_DOCUMENT_SUFFIXES:
        raise ValueError("analysis document must end in .json, .yaml, or .yml")
    try:
        with input_path.open("r", encoding="utf-8") as handle:
            if input_path.suffix.lower() == ".json":
                document = json.load(handle)
            else:
                document = yaml.safe_load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"analysis document is not valid JSON: {exc.msg}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"analysis document is not valid YAML: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("analysis document must be a mapping document")
    return document


def _load_wav_pcm(input_path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(input_path), "rb") as handle:
        channel_count = handle.getnchannels()
        sample_rate_hz = handle.getframerate()
        frame_count = handle.getnframes()
        sample_width = handle.getsampwidth()
        raw_frames = handle.readframes(frame_count)

    if channel_count <= 0 or sample_rate_hz <= 0:
        raise ValueError("wav input must declare positive channels and sample rate")

    if sample_width == 1:
        pcm = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float64)
        pcm = (pcm - 128.0) / 128.0
    elif sample_width == 2:
        pcm = np.frombuffer(raw_frames, dtype="<i2").astype(np.float64) / 32768.0
    elif sample_width == 4:
        pcm = np.frombuffer(raw_frames, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"unsupported wav sample width: {sample_width}")

    if pcm.size % channel_count != 0:
        raise ValueError("wav frame data does not align with channel count")
    return pcm.reshape(-1, channel_count), sample_rate_hz


def _decode_audio_with_ffmpeg(input_path: Path) -> dict[str, Any]:
    ffmpeg_path = which("ffmpeg")
    ffprobe_path = which("ffprobe")
    if ffmpeg_path is None:
        raise ValueError("ffmpeg is required to analyze non-WAV audio inputs")

    probe_payload = _probe_audio_with_ffprobe(input_path, ffprobe_path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        temp_wav_path = Path(handle.name)

    try:
        command = [
            ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            str(temp_wav_path),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "ffmpeg decode failed"
            raise ValueError(stderr)
        samples, sample_rate_hz = _load_wav_pcm(temp_wav_path)
    finally:
        temp_wav_path.unlink(missing_ok=True)

    return {
        "samples": samples,
        "sample_rate_hz": sample_rate_hz,
        "codec": probe_payload.get("codec", input_path.suffix.lower().lstrip(".")),
        "original_sample_rate_hz": int(probe_payload.get("sample_rate_hz", sample_rate_hz)),
        "original_channel_count": int(probe_payload.get("channel_count", samples.shape[1])),
        "decode_backend": "ffmpeg",
        "warnings": [],
    }


def _probe_audio_with_ffprobe(input_path: Path, ffprobe_path: str | None) -> dict[str, Any]:
    if ffprobe_path is None:
        return {}
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(input_path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    streams = document.get("streams")
    if not isinstance(streams, list) or not streams:
        return {}
    stream = streams[0] if isinstance(streams[0], dict) else {}
    format_payload = document.get("format") if isinstance(document.get("format"), dict) else {}
    duration = format_payload.get("duration")
    return {
        "codec": stream.get("codec_name"),
        "sample_rate_hz": _safe_int(stream.get("sample_rate")),
        "channel_count": _safe_int(stream.get("channels")),
        "duration_seconds": _safe_float(duration),
    }


def _slice_audio(samples: np.ndarray, sample_rate_hz: int, start_seconds: float, duration_seconds: float | None) -> np.ndarray:
    start_frame = int(round(start_seconds * sample_rate_hz))
    if start_frame >= samples.shape[0]:
        raise ValueError("start_seconds is beyond the end of the decoded audio")
    if duration_seconds is None:
        return samples[start_frame:]
    frame_count = max(1, int(round(duration_seconds * sample_rate_hz)))
    end_frame = min(samples.shape[0], start_frame + frame_count)
    return samples[start_frame:end_frame]


def _apply_channel_mode(samples: np.ndarray, channel_mode: str) -> tuple[np.ndarray, list[str]]:
    warnings: list[str] = []
    if channel_mode == "preserve":
        return samples, warnings
    if channel_mode == "mono":
        mono = np.mean(samples, axis=1, dtype=np.float64)
        return mono[:, np.newaxis], warnings
    if samples.shape[1] < 2:
        warnings.append("split-stereo requested for non-stereo input; preserving available channels")
    return samples, warnings


def _resample_audio(samples: np.ndarray, old_sample_rate_hz: int, new_sample_rate_hz: int) -> np.ndarray:
    if old_sample_rate_hz == new_sample_rate_hz:
        return samples
    if samples.shape[0] <= 1:
        return samples.copy()
    new_frame_count = max(1, int(round(samples.shape[0] * float(new_sample_rate_hz) / float(old_sample_rate_hz))))
    old_positions = np.linspace(0.0, 1.0, samples.shape[0], endpoint=False)
    new_positions = np.linspace(0.0, 1.0, new_frame_count, endpoint=False)
    channels = [np.interp(new_positions, old_positions, samples[:, index]) for index in range(samples.shape[1])]
    return np.stack(channels, axis=1)


def _build_observation_summary(samples: np.ndarray, sample_rate_hz: int, channel_labels: list[str]) -> dict[str, Any]:
    mono = np.mean(samples, axis=1, dtype=np.float64)
    channel_energy_summary = {
        f"{label}_rms": _round_float(_rms(samples[:, index]))
        for index, label in enumerate(channel_labels)
    }
    onset_map = _build_onset_map(mono, sample_rate_hz)
    section_boundaries = _estimate_section_boundaries(mono, sample_rate_hz)
    section_candidates = _build_section_candidates(mono, sample_rate_hz, samples.shape[0] / float(sample_rate_hz), section_boundaries)
    section_profile_summary = _build_section_profile_summary(section_candidates)
    section_transitions = _build_section_transitions(section_candidates)
    transition_profile_summary = _build_transition_profile_summary(section_transitions)
    transition_motif_summary = _build_transition_motif_summary(section_candidates, section_transitions)
    transition_motif_sequence_summary = _build_transition_motif_sequence_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    transition_motif_chain_summary = _build_transition_motif_chain_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    transition_motif_phrase_summary = _build_transition_motif_phrase_summary(
        section_candidates,
        section_transitions,
        transition_motif_summary,
    )
    low_hz, high_hz = _spectral_extent_summary(mono, sample_rate_hz)
    return {
        "peak_amplitude": _round_float(float(np.max(np.abs(samples)))),
        "rms_amplitude": _round_float(_rms(mono)),
        "estimated_onset_count": len(onset_map),
        "section_boundary_count": len(section_boundaries),
        "section_candidate_count": len(section_candidates),
        "section_transition_count": len(section_transitions),
        "section_profile_summary": section_profile_summary,
        "transition_profile_summary": transition_profile_summary,
        "transition_motif_summary": transition_motif_summary,
        "transition_motif_sequence_summary": transition_motif_sequence_summary,
        "transition_motif_chain_summary": transition_motif_chain_summary,
        "transition_motif_phrase_summary": transition_motif_phrase_summary,
        "spectral_extent_summary": {
            "low_hz": low_hz,
            "high_hz": high_hz,
        },
        "channel_energy_summary": channel_energy_summary,
        "frame_count": int(samples.shape[0]),
    }


def _estimate_onset_count(mono: np.ndarray, sample_rate_hz: int) -> int:
    return len(_build_onset_map(mono, sample_rate_hz))


def _build_onset_map(mono: np.ndarray, sample_rate_hz: int) -> list[dict[str, Any]]:
    if mono.size < 8:
        return []
    frame_size = max(256, int(sample_rate_hz * 0.02))
    hop_size = max(128, frame_size // 2)
    if mono.size < frame_size:
        frame_rms = np.array([_rms(mono)], dtype=np.float64)
    else:
        frame_rms = np.array(
            [_rms(mono[start : start + frame_size]) for start in range(0, mono.size - frame_size + 1, hop_size)],
            dtype=np.float64,
        )
    if frame_rms.size <= 1:
        return [
            {
                "offset_seconds": 0.0,
                "strength": _round_float(float(frame_rms[0])),
            }
        ] if frame_rms[0] > 0.0 else []
    delta = np.diff(frame_rms, prepend=frame_rms[0])
    positive = delta[delta > 0.0]
    if positive.size == 0:
        return []
    threshold = float(np.mean(positive) + (1.5 * np.std(positive)))
    onset_indexes = np.flatnonzero(delta > threshold)
    onset_map: list[dict[str, Any]] = []
    for onset_index in onset_indexes.tolist():
        onset_map.append(
            {
                "offset_seconds": _round_float((onset_index * hop_size) / float(sample_rate_hz)),
                "strength": _round_float(float(delta[onset_index])),
            }
        )
    return onset_map


def _estimate_section_boundaries(mono: np.ndarray, sample_rate_hz: int) -> list[dict[str, Any]]:
    if mono.size < max(sample_rate_hz, 8):
        return []
    frame_size = max(sample_rate_hz, int(sample_rate_hz * 1.0))
    hop_size = max(frame_size // 2, 1)
    frame_energies = np.array(
        [_rms(mono[start : start + frame_size]) for start in range(0, mono.size, hop_size)],
        dtype=np.float64,
    )
    if frame_energies.size <= 1:
        return []
    delta = np.abs(np.diff(frame_energies, prepend=frame_energies[0]))
    positive = delta[delta > 0.0]
    if positive.size == 0:
        return []
    threshold = float(max(np.mean(positive) * 0.75, np.percentile(positive, 50)))
    candidate_indexes = np.flatnonzero(delta > threshold)
    boundaries: list[dict[str, Any]] = []
    last_offset_seconds = -1.0
    min_spacing_seconds = max(0.5, frame_size / float(sample_rate_hz))
    for candidate_index in candidate_indexes.tolist():
        offset_seconds = (candidate_index * hop_size) / float(sample_rate_hz)
        if last_offset_seconds >= 0.0 and (offset_seconds - last_offset_seconds) < min_spacing_seconds:
            continue
        current_energy = float(frame_energies[candidate_index])
        previous_energy = float(frame_energies[max(0, candidate_index - 1)])
        boundaries.append(
            {
                "offset_seconds": _round_float(offset_seconds),
                "confidence": _round_float(float(delta[candidate_index])),
                "energy_transition": "rise" if current_energy >= previous_energy else "fall",
            }
        )
        last_offset_seconds = offset_seconds
    return boundaries


def _build_section_candidates(
    mono: np.ndarray,
    sample_rate_hz: int,
    duration_seconds: float,
    section_boundaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    boundary_offsets = [0.0]
    boundary_offsets.extend(
        float(entry.get("offset_seconds", 0.0))
        for entry in section_boundaries
        if isinstance(entry, dict) and isinstance(entry.get("offset_seconds"), (int, float))
    )
    boundary_offsets.append(float(duration_seconds))
    boundary_offsets = sorted({max(0.0, min(float(duration_seconds), offset)) for offset in boundary_offsets})
    if len(boundary_offsets) <= 1:
        return []

    mono_rms = _rms(mono)
    section_candidates: list[dict[str, Any]] = []
    for index in range(len(boundary_offsets) - 1):
        start_seconds = boundary_offsets[index]
        end_seconds = boundary_offsets[index + 1]
        if end_seconds <= start_seconds:
            continue
        start_frame = int(round(start_seconds * sample_rate_hz))
        end_frame = int(round(end_seconds * sample_rate_hz))
        segment = mono[start_frame:end_frame]
        segment_rms = _rms(segment)
        relative_energy = segment_rms / mono_rms if mono_rms > 0.0 else 0.0
        if relative_energy >= 1.15:
            energy_band = "high"
        elif relative_energy <= 0.85:
            energy_band = "low"
        else:
            energy_band = "medium"
        section_duration_seconds = end_seconds - start_seconds
        position_ratio = ((start_seconds + end_seconds) / 2.0) / float(duration_seconds) if duration_seconds > 0.0 else 0.5
        section_candidates.append(
            {
                "section_index": index,
                "start_seconds": _round_float(start_seconds),
                "end_seconds": _round_float(end_seconds),
                "duration_seconds": _round_float(section_duration_seconds),
                "rms_amplitude": _round_float(segment_rms),
                "relative_energy": _round_float(relative_energy),
                "energy_band": energy_band,
                "duration_band": _duration_band(section_duration_seconds),
                "position_band": _position_band(position_ratio),
            }
        )
    return section_candidates


def _build_section_profile_summary(section_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not section_candidates:
        return {
            "average_duration_seconds": 0.0,
            "longest_duration_seconds": 0.0,
            "energy_band_counts": {},
            "duration_band_counts": {},
            "position_band_counts": {},
            "dominant_energy_band": None,
            "opening_energy_band": None,
            "closing_energy_band": None,
        }

    durations = [float(candidate.get("duration_seconds", 0.0) or 0.0) for candidate in section_candidates]
    energy_band_counts = Counter(
        str(candidate.get("energy_band"))
        for candidate in section_candidates
        if isinstance(candidate.get("energy_band"), str) and candidate.get("energy_band")
    )
    duration_band_counts = Counter(
        str(candidate.get("duration_band"))
        for candidate in section_candidates
        if isinstance(candidate.get("duration_band"), str) and candidate.get("duration_band")
    )
    position_band_counts = Counter(
        str(candidate.get("position_band"))
        for candidate in section_candidates
        if isinstance(candidate.get("position_band"), str) and candidate.get("position_band")
    )
    dominant_energy_band = None
    if energy_band_counts:
        dominant_energy_band = sorted(energy_band_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "average_duration_seconds": _round_float(sum(durations) / len(durations)),
        "longest_duration_seconds": _round_float(max(durations)),
        "energy_band_counts": dict(sorted(energy_band_counts.items())),
        "duration_band_counts": dict(sorted(duration_band_counts.items())),
        "position_band_counts": dict(sorted(position_band_counts.items())),
        "dominant_energy_band": dominant_energy_band,
        "opening_energy_band": section_candidates[0].get("energy_band"),
        "closing_energy_band": section_candidates[-1].get("energy_band"),
    }


def _build_section_transitions(section_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(section_candidates) <= 1:
        return []

    transitions: list[dict[str, Any]] = []
    for previous_candidate, next_candidate in zip(section_candidates, section_candidates[1:]):
        previous_relative_energy = float(previous_candidate.get("relative_energy", 0.0) or 0.0)
        next_relative_energy = float(next_candidate.get("relative_energy", 0.0) or 0.0)
        previous_duration_seconds = float(previous_candidate.get("duration_seconds", 0.0) or 0.0)
        next_duration_seconds = float(next_candidate.get("duration_seconds", 0.0) or 0.0)
        energy_delta = next_relative_energy - previous_relative_energy
        duration_delta = next_duration_seconds - previous_duration_seconds
        transitions.append(
            {
                "from_section_index": int(previous_candidate.get("section_index", 0) or 0),
                "to_section_index": int(next_candidate.get("section_index", 0) or 0),
                "boundary_offset_seconds": _round_float(float(next_candidate.get("start_seconds", 0.0) or 0.0)),
                "from_energy_band": previous_candidate.get("energy_band"),
                "to_energy_band": next_candidate.get("energy_band"),
                "energy_delta": _round_float(energy_delta),
                "duration_delta_seconds": _round_float(duration_delta),
                "transition_kind": _transition_kind(energy_delta),
            }
        )
    return transitions


def _build_transition_profile_summary(section_transitions: list[dict[str, Any]]) -> dict[str, Any]:
    if not section_transitions:
        return {
            "average_abs_energy_delta": 0.0,
            "largest_abs_energy_delta": 0.0,
            "transition_kind_counts": {},
            "dominant_transition_kind": None,
            "opening_transition_kind": None,
            "closing_transition_kind": None,
        }

    absolute_energy_deltas = [abs(float(transition.get("energy_delta", 0.0) or 0.0)) for transition in section_transitions]
    transition_kind_counts = Counter(
        str(transition.get("transition_kind"))
        for transition in section_transitions
        if isinstance(transition.get("transition_kind"), str) and transition.get("transition_kind")
    )
    dominant_transition_kind = None
    if transition_kind_counts:
        dominant_transition_kind = sorted(transition_kind_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "average_abs_energy_delta": _round_float(sum(absolute_energy_deltas) / len(absolute_energy_deltas)),
        "largest_abs_energy_delta": _round_float(max(absolute_energy_deltas)),
        "transition_kind_counts": dict(sorted(transition_kind_counts.items())),
        "dominant_transition_kind": dominant_transition_kind,
        "opening_transition_kind": section_transitions[0].get("transition_kind"),
        "closing_transition_kind": section_transitions[-1].get("transition_kind"),
    }


def _build_transition_motif_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
) -> dict[str, Any]:
    if not section_transitions:
        return {
            "recurring_motif_count": 0,
            "motif_occurrence_count": 0,
            "motif_signature_counts": {},
            "motif_signatures": [],
            "dominant_motif_signature": None,
            "motifs": [],
        }

    grouped_indexes: dict[str, list[int]] = {}
    for index, transition in enumerate(section_transitions):
        if not isinstance(transition, dict):
            continue
        signature = _transition_motif_signature(transition)
        grouped_indexes.setdefault(signature, []).append(index)

    recurring_groups = [
        (signature, indexes)
        for signature, indexes in grouped_indexes.items()
        if len(indexes) >= 2
    ]
    recurring_groups.sort(key=lambda item: (-len(item[1]), item[1][0], item[0]))

    motifs: list[dict[str, Any]] = []
    motif_signature_counts: dict[str, int] = {}
    for motif_index, (signature, indexes) in enumerate(recurring_groups, start=1):
        first_transition = _mapping_optional(section_transitions[indexes[0]])
        motif_signature_counts[signature] = len(indexes)
        motifs.append(
            {
                "motif_id": f"transition_motif.{motif_index:02d}",
                "signature": signature,
                "transition_kind": first_transition.get("transition_kind"),
                "from_energy_band": first_transition.get("from_energy_band"),
                "to_energy_band": first_transition.get("to_energy_band"),
                "duration_trend": _duration_trend(float(first_transition.get("duration_delta_seconds", 0.0) or 0.0)),
                "occurrence_count": len(indexes),
                "section_transition_indexes": indexes,
                "boundary_offsets_seconds": [
                    _round_float(float(_mapping_optional(section_transitions[index]).get("boundary_offset_seconds", 0.0) or 0.0))
                    for index in indexes
                ],
                "time_bounds": _transition_motif_time_bounds(section_candidates, section_transitions, indexes),
            }
        )

    dominant_motif_signature = motifs[0]["signature"] if motifs else None
    return {
        "recurring_motif_count": len(motifs),
        "motif_occurrence_count": sum(motif["occurrence_count"] for motif in motifs),
        "motif_signature_counts": dict(sorted(motif_signature_counts.items())),
        "motif_signatures": [motif["signature"] for motif in motifs],
        "dominant_motif_signature": dominant_motif_signature,
        "motifs": motifs,
    }


def _build_transition_motif_sequence_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_summary: dict[str, Any],
) -> dict[str, Any]:
    motifs = [motif for motif in _list_optional(transition_motif_summary.get("motifs")) if isinstance(motif, dict)]
    if not motifs:
        return {
            "recurring_sequence_count": 0,
            "sequence_occurrence_count": 0,
            "sequence_signature_counts": {},
            "sequence_signatures": [],
            "dominant_sequence_signature": None,
            "sequences": [],
        }

    transition_index_to_signature: dict[int, str] = {}
    for motif in motifs:
        signature = motif.get("signature")
        if not isinstance(signature, str) or not signature:
            continue
        for index in _list_optional(motif.get("section_transition_indexes")):
            if isinstance(index, int):
                transition_index_to_signature[index] = signature

    recurring_transition_indexes = sorted(transition_index_to_signature)
    grouped_pairs: dict[str, list[list[int]]] = {}
    for left_index, right_index in zip(recurring_transition_indexes, recurring_transition_indexes[1:]):
        left_signature = transition_index_to_signature[left_index]
        right_signature = transition_index_to_signature[right_index]
        sequence_signature = f"{left_signature}=>{right_signature}"
        grouped_pairs.setdefault(sequence_signature, []).append([left_index, right_index])

    recurring_pairs = [
        (sequence_signature, occurrence_pairs)
        for sequence_signature, occurrence_pairs in grouped_pairs.items()
        if len(occurrence_pairs) >= 2
    ]
    recurring_pairs.sort(key=lambda item: (-len(item[1]), item[1][0][0], item[0]))

    sequences: list[dict[str, Any]] = []
    sequence_signature_counts: dict[str, int] = {}
    for sequence_index, (sequence_signature, occurrence_pairs) in enumerate(recurring_pairs, start=1):
        left_signature, right_signature = sequence_signature.split("=>", 1)
        sequence_signature_counts[sequence_signature] = len(occurrence_pairs)
        sequences.append(
            {
                "sequence_id": f"transition_motif_sequence.{sequence_index:02d}",
                "signature": sequence_signature,
                "left_signature": left_signature,
                "right_signature": right_signature,
                "occurrence_count": len(occurrence_pairs),
                "section_transition_index_pairs": occurrence_pairs,
                "boundary_offset_pairs_seconds": [
                    [
                        _round_float(float(_mapping_optional(section_transitions[left]).get("boundary_offset_seconds", 0.0) or 0.0)),
                        _round_float(float(_mapping_optional(section_transitions[right]).get("boundary_offset_seconds", 0.0) or 0.0)),
                    ]
                    for left, right in occurrence_pairs
                ],
                "time_bounds": _transition_motif_sequence_time_bounds(section_candidates, section_transitions, occurrence_pairs),
            }
        )

    dominant_sequence_signature = sequences[0]["signature"] if sequences else None
    return {
        "recurring_sequence_count": len(sequences),
        "sequence_occurrence_count": sum(sequence["occurrence_count"] for sequence in sequences),
        "sequence_signature_counts": dict(sorted(sequence_signature_counts.items())),
        "sequence_signatures": [sequence["signature"] for sequence in sequences],
        "dominant_sequence_signature": dominant_sequence_signature,
        "sequences": sequences,
    }


def _build_transition_motif_chain_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_summary: dict[str, Any],
) -> dict[str, Any]:
    motifs = [motif for motif in _list_optional(transition_motif_summary.get("motifs")) if isinstance(motif, dict)]
    if not motifs:
        return {
            "chain_length": 3,
            "recurring_chain_count": 0,
            "chain_occurrence_count": 0,
            "chain_signature_counts": {},
            "chain_signatures": [],
            "dominant_chain_signature": None,
            "chains": [],
        }

    transition_index_to_signature: dict[int, str] = {}
    for motif in motifs:
        signature = motif.get("signature")
        if not isinstance(signature, str) or not signature:
            continue
        for index in _list_optional(motif.get("section_transition_indexes")):
            if isinstance(index, int):
                transition_index_to_signature[index] = signature

    recurring_transition_indexes = sorted(transition_index_to_signature)
    grouped_chains: dict[str, list[list[int]]] = {}
    for start in range(len(recurring_transition_indexes) - 2):
        chain_indexes = recurring_transition_indexes[start : start + 3]
        if chain_indexes[2] - chain_indexes[0] != 2:
            continue
        chain_signatures = [transition_index_to_signature[index] for index in chain_indexes]
        chain_signature = "=>".join(chain_signatures)
        grouped_chains.setdefault(chain_signature, []).append(chain_indexes)

    recurring_chains = [
        (chain_signature, occurrence_chains)
        for chain_signature, occurrence_chains in grouped_chains.items()
        if len(occurrence_chains) >= 2
    ]
    recurring_chains.sort(key=lambda item: (-len(item[1]), item[1][0][0], item[0]))

    chains: list[dict[str, Any]] = []
    chain_signature_counts: dict[str, int] = {}
    for chain_index, (chain_signature, occurrence_chains) in enumerate(recurring_chains, start=1):
        motif_signatures = chain_signature.split("=>")
        chain_signature_counts[chain_signature] = len(occurrence_chains)
        chains.append(
            {
                "chain_id": f"transition_motif_chain.{chain_index:02d}",
                "signature": chain_signature,
                "motif_signatures": motif_signatures,
                "chain_length": len(motif_signatures),
                "occurrence_count": len(occurrence_chains),
                "section_transition_index_chains": occurrence_chains,
                "boundary_offset_chains_seconds": [
                    [
                        _round_float(
                            float(_mapping_optional(section_transitions[index]).get("boundary_offset_seconds", 0.0) or 0.0)
                        )
                        for index in chain_indexes
                    ]
                    for chain_indexes in occurrence_chains
                ],
                "time_bounds": _transition_motif_chain_time_bounds(section_candidates, section_transitions, occurrence_chains),
            }
        )

    dominant_chain_signature = chains[0]["signature"] if chains else None
    return {
        "chain_length": 3,
        "recurring_chain_count": len(chains),
        "chain_occurrence_count": sum(chain["occurrence_count"] for chain in chains),
        "chain_signature_counts": dict(sorted(chain_signature_counts.items())),
        "chain_signatures": [chain["signature"] for chain in chains],
        "dominant_chain_signature": dominant_chain_signature,
        "chains": chains,
    }


def _build_transition_motif_phrase_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_summary: dict[str, Any],
    *,
    min_phrase_length: int = 3,
    max_phrase_length: int = 5,
) -> dict[str, Any]:
    motifs = [motif for motif in _list_optional(transition_motif_summary.get("motifs")) if isinstance(motif, dict)]
    if not motifs:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_phrase_count": 0,
            "phrase_occurrence_count": 0,
            "phrase_signature_counts": {},
            "phrase_signatures": [],
            "dominant_phrase_signature": None,
            "phrases": [],
        }

    transition_index_to_signature: dict[int, str] = {}
    for motif in motifs:
        signature = motif.get("signature")
        if not isinstance(signature, str) or not signature:
            continue
        for index in _list_optional(motif.get("section_transition_indexes")):
            if isinstance(index, int):
                transition_index_to_signature[index] = signature

    recurring_transition_indexes = sorted(transition_index_to_signature)
    grouped_phrases: dict[str, list[list[int]]] = {}
    for phrase_length in range(min_phrase_length, max_phrase_length + 1):
        if len(recurring_transition_indexes) < phrase_length:
            continue
        for start in range(len(recurring_transition_indexes) - phrase_length + 1):
            phrase_indexes = recurring_transition_indexes[start : start + phrase_length]
            if any(right - left != 1 for left, right in zip(phrase_indexes, phrase_indexes[1:])):
                continue
            phrase_signature = "=>".join(transition_index_to_signature[index] for index in phrase_indexes)
            grouped_phrases.setdefault(phrase_signature, []).append(phrase_indexes)

    recurring_phrases = [
        (phrase_signature, occurrence_phrases)
        for phrase_signature, occurrence_phrases in grouped_phrases.items()
        if len(occurrence_phrases) >= 2
    ]
    recurring_phrases.sort(
        key=lambda item: (
            -len(item[1][0]),
            -len(item[1]),
            item[1][0][0],
            item[0],
        )
    )

    phrases: list[dict[str, Any]] = []
    phrase_signature_counts: dict[str, int] = {}
    for phrase_index, (phrase_signature, occurrence_phrases) in enumerate(recurring_phrases, start=1):
        motif_signatures = phrase_signature.split("=>")
        phrase_signature_counts[phrase_signature] = len(occurrence_phrases)
        phrases.append(
            {
                "phrase_id": f"transition_motif_phrase.{phrase_index:02d}",
                "signature": phrase_signature,
                "motif_signatures": motif_signatures,
                "phrase_length": len(motif_signatures),
                "occurrence_count": len(occurrence_phrases),
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": [
                    [
                        _round_float(
                            float(_mapping_optional(section_transitions[index]).get("boundary_offset_seconds", 0.0) or 0.0)
                        )
                        for index in phrase_indexes
                    ]
                    for phrase_indexes in occurrence_phrases
                ],
                "time_bounds": _transition_motif_phrase_time_bounds(section_candidates, section_transitions, occurrence_phrases),
            }
        )

    dominant_phrase_signature = phrases[0]["signature"] if phrases else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_phrase_count": len(phrases),
        "phrase_occurrence_count": sum(phrase["occurrence_count"] for phrase in phrases),
        "phrase_signature_counts": dict(sorted(phrase_signature_counts.items())),
        "phrase_signatures": [phrase["signature"] for phrase in phrases],
        "dominant_phrase_signature": dominant_phrase_signature,
        "phrases": phrases,
    }


def _build_transition_motif_phrase_family_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_summary: dict[str, Any],
) -> dict[str, Any]:
    phrases = [phrase for phrase in _list_optional(transition_motif_phrase_summary.get("phrases")) if isinstance(phrase, dict)]
    min_phrase_length = int(transition_motif_phrase_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_summary.get("max_phrase_length", 5) or 5)
    if not phrases:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_family_count": 0,
            "family_occurrence_count": 0,
            "family_signature_counts": {},
            "family_signatures": [],
            "dominant_family_signature": None,
            "families": [],
        }

    grouped_families: dict[str, list[dict[str, Any]]] = {}
    for phrase in phrases:
        phrase_signature = phrase.get("signature")
        if not isinstance(phrase_signature, str) or not phrase_signature:
            continue
        family_signature = _transition_motif_phrase_family_signature_from_phrase_signature(phrase_signature)
        grouped_families.setdefault(family_signature, []).append(phrase)

    recurring_families = sorted(
        grouped_families.items(),
        key=lambda item: (
            -max(int(member.get("phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    families: list[dict[str, Any]] = []
    family_signature_counts: dict[str, int] = {}
    for family_index, (family_signature, member_phrases) in enumerate(recurring_families, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_phrases)
        family_signature_counts[family_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_phrases
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_phrases
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        member_phrase_signatures = sorted(
            {
                str(member.get("signature"))
                for member in member_phrases
                if isinstance(member.get("signature"), str) and member.get("signature")
            }
        )
        families.append(
            {
                "family_id": f"transition_motif_phrase_family.{family_index:02d}",
                "signature": family_signature,
                "phrase_length": max(int(member.get("phrase_length", 0) or 0) for member in member_phrases),
                "occurrence_count": occurrence_count,
                "member_phrase_count": len(member_phrases),
                "member_phrase_ids": [
                    str(member.get("phrase_id"))
                    for member in member_phrases
                    if isinstance(member.get("phrase_id"), str) and member.get("phrase_id")
                ],
                "member_phrase_signatures": member_phrase_signatures,
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_family_signature = families[0]["signature"] if families else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_family_count": len(families),
        "family_occurrence_count": sum(family["occurrence_count"] for family in families),
        "family_signature_counts": dict(sorted(family_signature_counts.items())),
        "family_signatures": [family["signature"] for family in families],
        "dominant_family_signature": dominant_family_signature,
        "families": families,
    }


def _build_transition_motif_phrase_archetype_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_family_summary: dict[str, Any],
) -> dict[str, Any]:
    families = [
        family
        for family in _list_optional(transition_motif_phrase_family_summary.get("families"))
        if isinstance(family, dict)
    ]
    min_phrase_length = int(transition_motif_phrase_family_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_family_summary.get("max_phrase_length", 5) or 5)
    if not families:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_archetype_count": 0,
            "archetype_occurrence_count": 0,
            "archetype_signature_counts": {},
            "archetype_signatures": [],
            "dominant_archetype_signature": None,
            "archetypes": [],
        }

    grouped_archetypes: dict[str, list[dict[str, Any]]] = {}
    for family in families:
        family_signature = family.get("signature")
        if not isinstance(family_signature, str) or not family_signature:
            continue
        archetype_signature = _transition_motif_phrase_archetype_signature_from_family_signature(family_signature)
        grouped_archetypes.setdefault(archetype_signature, []).append(family)

    recurring_archetypes = sorted(
        grouped_archetypes.items(),
        key=lambda item: (
            -max(int(member.get("phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    archetypes: list[dict[str, Any]] = []
    archetype_signature_counts: dict[str, int] = {}
    for archetype_index, (archetype_signature, member_families) in enumerate(recurring_archetypes, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_families)
        archetype_signature_counts[archetype_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_families
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_families
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        member_phrase_ids = sorted(
            {
                phrase_id
                for member in member_families
                for phrase_id in _string_list(member.get("member_phrase_ids"))
            }
        )
        member_phrase_signatures = sorted(
            {
                phrase_signature
                for member in member_families
                for phrase_signature in _string_list(member.get("member_phrase_signatures"))
            }
        )
        archetypes.append(
            {
                "archetype_id": f"transition_motif_phrase_archetype.{archetype_index:02d}",
                "signature": archetype_signature,
                "min_phrase_length": min(int(member.get("phrase_length", 0) or 0) for member in member_families),
                "max_phrase_length": max(int(member.get("phrase_length", 0) or 0) for member in member_families),
                "occurrence_count": occurrence_count,
                "member_family_count": len(member_families),
                "member_family_ids": [
                    str(member.get("family_id"))
                    for member in member_families
                    if isinstance(member.get("family_id"), str) and member.get("family_id")
                ],
                "member_family_signatures": sorted(
                    {
                        str(member.get("signature"))
                        for member in member_families
                        if isinstance(member.get("signature"), str) and member.get("signature")
                    }
                ),
                "member_phrase_count": len(member_phrase_ids),
                "member_phrase_ids": member_phrase_ids,
                "member_phrase_signatures": member_phrase_signatures,
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_archetype_signature = archetypes[0]["signature"] if archetypes else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_archetype_count": len(archetypes),
        "archetype_occurrence_count": sum(archetype["occurrence_count"] for archetype in archetypes),
        "archetype_signature_counts": dict(sorted(archetype_signature_counts.items())),
        "archetype_signatures": [archetype["signature"] for archetype in archetypes],
        "dominant_archetype_signature": dominant_archetype_signature,
        "archetypes": archetypes,
    }


def _build_transition_motif_phrase_contour_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_archetype_summary: dict[str, Any],
) -> dict[str, Any]:
    archetypes = [
        archetype
        for archetype in _list_optional(transition_motif_phrase_archetype_summary.get("archetypes"))
        if isinstance(archetype, dict)
    ]
    min_phrase_length = int(transition_motif_phrase_archetype_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_archetype_summary.get("max_phrase_length", 5) or 5)
    if not archetypes:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_contour_count": 0,
            "contour_occurrence_count": 0,
            "contour_signature_counts": {},
            "contour_signatures": [],
            "dominant_contour_signature": None,
            "contours": [],
        }

    grouped_contours: dict[str, list[dict[str, Any]]] = {}
    for archetype in archetypes:
        archetype_signature = archetype.get("signature")
        if not isinstance(archetype_signature, str) or not archetype_signature:
            continue
        contour_signature = _transition_motif_phrase_contour_signature_from_archetype_signature(archetype_signature)
        grouped_contours.setdefault(contour_signature, []).append(archetype)

    recurring_contours = sorted(
        grouped_contours.items(),
        key=lambda item: (
            -max(int(member.get("max_phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    contours: list[dict[str, Any]] = []
    contour_signature_counts: dict[str, int] = {}
    for contour_index, (contour_signature, member_archetypes) in enumerate(recurring_contours, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_archetypes)
        contour_signature_counts[contour_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_archetypes
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_archetypes
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        contours.append(
            {
                "contour_id": f"transition_motif_phrase_contour.{contour_index:02d}",
                "signature": contour_signature,
                "min_phrase_length": min(int(member.get("min_phrase_length", 0) or 0) for member in member_archetypes),
                "max_phrase_length": max(int(member.get("max_phrase_length", 0) or 0) for member in member_archetypes),
                "occurrence_count": occurrence_count,
                "member_archetype_count": len(member_archetypes),
                "member_archetype_ids": sorted(
                    {
                        str(member.get("archetype_id"))
                        for member in member_archetypes
                        if isinstance(member.get("archetype_id"), str) and member.get("archetype_id")
                    }
                ),
                "member_archetype_signatures": sorted(
                    {
                        str(member.get("signature"))
                        for member in member_archetypes
                        if isinstance(member.get("signature"), str) and member.get("signature")
                    }
                ),
                "member_family_count": len(
                    {
                        family_id
                        for member in member_archetypes
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_ids": sorted(
                    {
                        family_id
                        for member in member_archetypes
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_signatures": sorted(
                    {
                        family_signature
                        for member in member_archetypes
                        for family_signature in _string_list(member.get("member_family_signatures"))
                    }
                ),
                "member_phrase_count": len(
                    {
                        phrase_id
                        for member in member_archetypes
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_ids": sorted(
                    {
                        phrase_id
                        for member in member_archetypes
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_signatures": sorted(
                    {
                        phrase_signature
                        for member in member_archetypes
                        for phrase_signature in _string_list(member.get("member_phrase_signatures"))
                    }
                ),
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_contour_signature = contours[0]["signature"] if contours else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_contour_count": len(contours),
        "contour_occurrence_count": sum(contour["occurrence_count"] for contour in contours),
        "contour_signature_counts": dict(sorted(contour_signature_counts.items())),
        "contour_signatures": [contour["signature"] for contour in contours],
        "dominant_contour_signature": dominant_contour_signature,
        "contours": contours,
    }


def _build_transition_motif_phrase_sweep_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_contour_summary: dict[str, Any],
) -> dict[str, Any]:
    contours = [
        contour
        for contour in _list_optional(transition_motif_phrase_contour_summary.get("contours"))
        if isinstance(contour, dict)
    ]
    min_phrase_length = int(transition_motif_phrase_contour_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_contour_summary.get("max_phrase_length", 5) or 5)
    if not contours:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_sweep_count": 0,
            "sweep_occurrence_count": 0,
            "sweep_signature_counts": {},
            "sweep_signatures": [],
            "dominant_sweep_signature": None,
            "sweeps": [],
        }

    grouped_sweeps: dict[str, list[dict[str, Any]]] = {}
    for contour in contours:
        contour_signature = contour.get("signature")
        if not isinstance(contour_signature, str) or not contour_signature:
            continue
        sweep_signature = _transition_motif_phrase_sweep_signature_from_contour_signature(contour_signature)
        grouped_sweeps.setdefault(sweep_signature, []).append(contour)

    recurring_sweeps = sorted(
        grouped_sweeps.items(),
        key=lambda item: (
            -max(int(member.get("max_phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    sweeps: list[dict[str, Any]] = []
    sweep_signature_counts: dict[str, int] = {}
    for sweep_index, (sweep_signature, member_contours) in enumerate(recurring_sweeps, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_contours)
        sweep_signature_counts[sweep_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_contours
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_contours
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        sweeps.append(
            {
                "sweep_id": f"transition_motif_phrase_sweep.{sweep_index:02d}",
                "signature": sweep_signature,
                "min_phrase_length": min(int(member.get("min_phrase_length", 0) or 0) for member in member_contours),
                "max_phrase_length": max(int(member.get("max_phrase_length", 0) or 0) for member in member_contours),
                "occurrence_count": occurrence_count,
                "member_contour_count": len(member_contours),
                "member_contour_ids": sorted(
                    {
                        str(member.get("contour_id"))
                        for member in member_contours
                        if isinstance(member.get("contour_id"), str) and member.get("contour_id")
                    }
                ),
                "member_contour_signatures": sorted(
                    {
                        str(member.get("signature"))
                        for member in member_contours
                        if isinstance(member.get("signature"), str) and member.get("signature")
                    }
                ),
                "member_archetype_count": len(
                    {
                        archetype_id
                        for member in member_contours
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_ids": sorted(
                    {
                        archetype_id
                        for member in member_contours
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_signatures": sorted(
                    {
                        archetype_signature
                        for member in member_contours
                        for archetype_signature in _string_list(member.get("member_archetype_signatures"))
                    }
                ),
                "member_family_count": len(
                    {
                        family_id
                        for member in member_contours
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_ids": sorted(
                    {
                        family_id
                        for member in member_contours
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_signatures": sorted(
                    {
                        family_signature
                        for member in member_contours
                        for family_signature in _string_list(member.get("member_family_signatures"))
                    }
                ),
                "member_phrase_count": len(
                    {
                        phrase_id
                        for member in member_contours
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_ids": sorted(
                    {
                        phrase_id
                        for member in member_contours
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_signatures": sorted(
                    {
                        phrase_signature
                        for member in member_contours
                        for phrase_signature in _string_list(member.get("member_phrase_signatures"))
                    }
                ),
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_sweep_signature = sweeps[0]["signature"] if sweeps else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_sweep_count": len(sweeps),
        "sweep_occurrence_count": sum(sweep["occurrence_count"] for sweep in sweeps),
        "sweep_signature_counts": dict(sorted(sweep_signature_counts.items())),
        "sweep_signatures": [sweep["signature"] for sweep in sweeps],
        "dominant_sweep_signature": dominant_sweep_signature,
        "sweeps": sweeps,
    }


def _build_transition_motif_phrase_gesture_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_sweep_summary: dict[str, Any],
) -> dict[str, Any]:
    sweeps = [
        sweep
        for sweep in _list_optional(transition_motif_phrase_sweep_summary.get("sweeps"))
        if isinstance(sweep, dict)
    ]
    min_phrase_length = int(transition_motif_phrase_sweep_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_sweep_summary.get("max_phrase_length", 5) or 5)
    if not sweeps:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_gesture_count": 0,
            "gesture_occurrence_count": 0,
            "gesture_signature_counts": {},
            "gesture_signatures": [],
            "dominant_gesture_signature": None,
            "gestures": [],
        }

    grouped_gestures: dict[str, list[dict[str, Any]]] = {}
    for sweep in sweeps:
        sweep_signature = sweep.get("signature")
        if not isinstance(sweep_signature, str) or not sweep_signature:
            continue
        gesture_signature = _transition_motif_phrase_gesture_signature_from_sweep_signature(sweep_signature)
        grouped_gestures.setdefault(gesture_signature, []).append(sweep)

    recurring_gestures = sorted(
        grouped_gestures.items(),
        key=lambda item: (
            -max(int(member.get("max_phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    gestures: list[dict[str, Any]] = []
    gesture_signature_counts: dict[str, int] = {}
    for gesture_index, (gesture_signature, member_sweeps) in enumerate(recurring_gestures, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_sweeps)
        gesture_signature_counts[gesture_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_sweeps
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_sweeps
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        gestures.append(
            {
                "gesture_id": f"transition_motif_phrase_gesture.{gesture_index:02d}",
                "signature": gesture_signature,
                "min_phrase_length": min(int(member.get("min_phrase_length", 0) or 0) for member in member_sweeps),
                "max_phrase_length": max(int(member.get("max_phrase_length", 0) or 0) for member in member_sweeps),
                "occurrence_count": occurrence_count,
                "member_sweep_count": len(member_sweeps),
                "member_sweep_ids": sorted(
                    {
                        str(member.get("sweep_id"))
                        for member in member_sweeps
                        if isinstance(member.get("sweep_id"), str) and member.get("sweep_id")
                    }
                ),
                "member_sweep_signatures": sorted(
                    {
                        str(member.get("signature"))
                        for member in member_sweeps
                        if isinstance(member.get("signature"), str) and member.get("signature")
                    }
                ),
                "member_contour_count": len(
                    {
                        contour_id
                        for member in member_sweeps
                        for contour_id in _string_list(member.get("member_contour_ids"))
                    }
                ),
                "member_contour_ids": sorted(
                    {
                        contour_id
                        for member in member_sweeps
                        for contour_id in _string_list(member.get("member_contour_ids"))
                    }
                ),
                "member_contour_signatures": sorted(
                    {
                        contour_signature
                        for member in member_sweeps
                        for contour_signature in _string_list(member.get("member_contour_signatures"))
                    }
                ),
                "member_archetype_count": len(
                    {
                        archetype_id
                        for member in member_sweeps
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_ids": sorted(
                    {
                        archetype_id
                        for member in member_sweeps
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_signatures": sorted(
                    {
                        archetype_signature
                        for member in member_sweeps
                        for archetype_signature in _string_list(member.get("member_archetype_signatures"))
                    }
                ),
                "member_family_count": len(
                    {
                        family_id
                        for member in member_sweeps
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_ids": sorted(
                    {
                        family_id
                        for member in member_sweeps
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_signatures": sorted(
                    {
                        family_signature
                        for member in member_sweeps
                        for family_signature in _string_list(member.get("member_family_signatures"))
                    }
                ),
                "member_phrase_count": len(
                    {
                        phrase_id
                        for member in member_sweeps
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_ids": sorted(
                    {
                        phrase_id
                        for member in member_sweeps
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_signatures": sorted(
                    {
                        phrase_signature
                        for member in member_sweeps
                        for phrase_signature in _string_list(member.get("member_phrase_signatures"))
                    }
                ),
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_gesture_signature = gestures[0]["signature"] if gestures else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_gesture_count": len(gestures),
        "gesture_occurrence_count": sum(gesture["occurrence_count"] for gesture in gestures),
        "gesture_signature_counts": dict(sorted(gesture_signature_counts.items())),
        "gesture_signatures": [gesture["signature"] for gesture in gestures],
        "dominant_gesture_signature": dominant_gesture_signature,
        "gestures": gestures,
    }


def _build_transition_motif_phrase_mobility_summary(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_phrase_gesture_summary: dict[str, Any],
) -> dict[str, Any]:
    gestures = [
        gesture
        for gesture in _list_optional(transition_motif_phrase_gesture_summary.get("gestures"))
        if isinstance(gesture, dict)
    ]
    min_phrase_length = int(transition_motif_phrase_gesture_summary.get("min_phrase_length", 3) or 3)
    max_phrase_length = int(transition_motif_phrase_gesture_summary.get("max_phrase_length", 5) or 5)
    if not gestures:
        return {
            "min_phrase_length": min_phrase_length,
            "max_phrase_length": max_phrase_length,
            "recurring_mobility_count": 0,
            "mobility_occurrence_count": 0,
            "mobility_signature_counts": {},
            "mobility_signatures": [],
            "dominant_mobility_signature": None,
            "mobilities": [],
        }

    grouped_mobilities: dict[str, list[dict[str, Any]]] = {}
    for gesture in gestures:
        gesture_signature = gesture.get("signature")
        if not isinstance(gesture_signature, str) or not gesture_signature:
            continue
        mobility_signature = _transition_motif_phrase_mobility_signature_from_gesture_signature(gesture_signature)
        grouped_mobilities.setdefault(mobility_signature, []).append(gesture)

    recurring_mobilities = sorted(
        grouped_mobilities.items(),
        key=lambda item: (
            -max(int(member.get("max_phrase_length", 0) or 0) for member in item[1]),
            -sum(int(member.get("occurrence_count", 0) or 0) for member in item[1]),
            min(
                min(indexes)
                for member in item[1]
                for indexes in _list_optional(member.get("section_transition_index_phrases"))
                if isinstance(indexes, list) and indexes
            ),
            item[0],
        ),
    )

    mobilities: list[dict[str, Any]] = []
    mobility_signature_counts: dict[str, int] = {}
    for mobility_index, (mobility_signature, member_gestures) in enumerate(recurring_mobilities, start=1):
        occurrence_count = sum(int(member.get("occurrence_count", 0) or 0) for member in member_gestures)
        mobility_signature_counts[mobility_signature] = occurrence_count
        occurrence_phrases = [
            indexes
            for member in member_gestures
            for indexes in _list_optional(member.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and indexes
        ]
        occurrence_boundaries = [
            boundary_offsets
            for member in member_gestures
            for boundary_offsets in _list_optional(member.get("boundary_offset_phrases_seconds"))
            if isinstance(boundary_offsets, list) and boundary_offsets
        ]
        mobilities.append(
            {
                "mobility_id": f"transition_motif_phrase_mobility.{mobility_index:02d}",
                "signature": mobility_signature,
                "min_phrase_length": min(int(member.get("min_phrase_length", 0) or 0) for member in member_gestures),
                "max_phrase_length": max(int(member.get("max_phrase_length", 0) or 0) for member in member_gestures),
                "occurrence_count": occurrence_count,
                "member_gesture_count": len(member_gestures),
                "member_gesture_ids": sorted(
                    {
                        str(member.get("gesture_id"))
                        for member in member_gestures
                        if isinstance(member.get("gesture_id"), str) and member.get("gesture_id")
                    }
                ),
                "member_gesture_signatures": sorted(
                    {
                        str(member.get("signature"))
                        for member in member_gestures
                        if isinstance(member.get("signature"), str) and member.get("signature")
                    }
                ),
                "member_sweep_count": len(
                    {
                        sweep_id
                        for member in member_gestures
                        for sweep_id in _string_list(member.get("member_sweep_ids"))
                    }
                ),
                "member_sweep_ids": sorted(
                    {
                        sweep_id
                        for member in member_gestures
                        for sweep_id in _string_list(member.get("member_sweep_ids"))
                    }
                ),
                "member_sweep_signatures": sorted(
                    {
                        sweep_signature
                        for member in member_gestures
                        for sweep_signature in _string_list(member.get("member_sweep_signatures"))
                    }
                ),
                "member_contour_count": len(
                    {
                        contour_id
                        for member in member_gestures
                        for contour_id in _string_list(member.get("member_contour_ids"))
                    }
                ),
                "member_contour_ids": sorted(
                    {
                        contour_id
                        for member in member_gestures
                        for contour_id in _string_list(member.get("member_contour_ids"))
                    }
                ),
                "member_contour_signatures": sorted(
                    {
                        contour_signature
                        for member in member_gestures
                        for contour_signature in _string_list(member.get("member_contour_signatures"))
                    }
                ),
                "member_archetype_count": len(
                    {
                        archetype_id
                        for member in member_gestures
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_ids": sorted(
                    {
                        archetype_id
                        for member in member_gestures
                        for archetype_id in _string_list(member.get("member_archetype_ids"))
                    }
                ),
                "member_archetype_signatures": sorted(
                    {
                        archetype_signature
                        for member in member_gestures
                        for archetype_signature in _string_list(member.get("member_archetype_signatures"))
                    }
                ),
                "member_family_count": len(
                    {
                        family_id
                        for member in member_gestures
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_ids": sorted(
                    {
                        family_id
                        for member in member_gestures
                        for family_id in _string_list(member.get("member_family_ids"))
                    }
                ),
                "member_family_signatures": sorted(
                    {
                        family_signature
                        for member in member_gestures
                        for family_signature in _string_list(member.get("member_family_signatures"))
                    }
                ),
                "member_phrase_count": len(
                    {
                        phrase_id
                        for member in member_gestures
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_ids": sorted(
                    {
                        phrase_id
                        for member in member_gestures
                        for phrase_id in _string_list(member.get("member_phrase_ids"))
                    }
                ),
                "member_phrase_signatures": sorted(
                    {
                        phrase_signature
                        for member in member_gestures
                        for phrase_signature in _string_list(member.get("member_phrase_signatures"))
                    }
                ),
                "section_transition_index_phrases": occurrence_phrases,
                "boundary_offset_phrases_seconds": occurrence_boundaries,
                "time_bounds": _transition_motif_phrase_family_time_bounds(
                    section_candidates,
                    section_transitions,
                    occurrence_phrases,
                ),
            }
        )

    dominant_mobility_signature = mobilities[0]["signature"] if mobilities else None
    return {
        "min_phrase_length": min_phrase_length,
        "max_phrase_length": max_phrase_length,
        "recurring_mobility_count": len(mobilities),
        "mobility_occurrence_count": sum(mobility["occurrence_count"] for mobility in mobilities),
        "mobility_signature_counts": dict(sorted(mobility_signature_counts.items())),
        "mobility_signatures": [mobility["signature"] for mobility in mobilities],
        "dominant_mobility_signature": dominant_mobility_signature,
        "mobilities": mobilities,
    }


def _build_source_hypotheses(
    observation_summary: dict[str, Any],
    *,
    decoded_audio: dict[str, Any],
    analysis_window: dict[str, Any],
    onset_map: list[dict[str, Any]],
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    transition_motif_summary: dict[str, Any],
    transition_motif_sequence_summary: dict[str, Any],
    transition_motif_chain_summary: dict[str, Any],
    transition_motif_phrase_summary: dict[str, Any],
    transition_motif_phrase_family_summary: dict[str, Any],
    transition_motif_phrase_archetype_summary: dict[str, Any],
    transition_motif_phrase_contour_summary: dict[str, Any],
    transition_motif_phrase_sweep_summary: dict[str, Any],
    transition_motif_phrase_gesture_summary: dict[str, Any],
    transition_motif_phrase_mobility_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    duration_seconds = float(analysis_window.get("duration_seconds", 0.0) or 0.0)
    if duration_seconds <= 0.0:
        return []

    onset_count = int(observation_summary.get("estimated_onset_count", 0) or 0)
    section_boundary_count = int(observation_summary.get("section_boundary_count", 0) or 0)
    section_candidate_count = int(observation_summary.get("section_candidate_count", 0) or 0)
    section_transition_count = int(observation_summary.get("section_transition_count", 0) or 0)
    onset_density_per_second = onset_count / duration_seconds
    channel_count = int(decoded_audio.get("channel_count", 0) or 0)
    section_profile_summary = _mapping_optional(observation_summary.get("section_profile_summary"))
    transition_profile_summary = _mapping_optional(observation_summary.get("transition_profile_summary"))
    dominant_energy_band = section_profile_summary.get("dominant_energy_band")
    average_duration_seconds = float(section_profile_summary.get("average_duration_seconds", 0.0) or 0.0)
    longest_duration_seconds = float(section_profile_summary.get("longest_duration_seconds", 0.0) or 0.0)
    average_abs_energy_delta = float(transition_profile_summary.get("average_abs_energy_delta", 0.0) or 0.0)

    hypotheses: list[dict[str, Any]] = []
    seen_classes: set[str] = set()

    def append_hypothesis(
        source_class: str,
        *,
        role: str,
        confidence: float,
        supporting_observations: list[str],
        evidence: dict[str, Any],
        ambiguity_notes: list[str],
        linked_section_indexes: list[int],
        linked_transition_indexes: list[int],
        linked_onset_offsets_seconds: list[float],
    ) -> None:
        if source_class in seen_classes:
            return
        seen_classes.add(source_class)
        hypothesis_index = len(hypotheses) + 1
        linked_transition_motifs = _source_hypothesis_linked_transition_motifs(
            transition_motif_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_sequences = _source_hypothesis_linked_transition_motif_sequences(
            transition_motif_sequence_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_chains = _source_hypothesis_linked_transition_motif_chains(
            transition_motif_chain_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrases = _source_hypothesis_linked_transition_motif_phrases(
            transition_motif_phrase_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_families = _source_hypothesis_linked_transition_motif_phrase_families(
            transition_motif_phrase_family_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_archetypes = _source_hypothesis_linked_transition_motif_phrase_archetypes(
            transition_motif_phrase_archetype_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_contours = _source_hypothesis_linked_transition_motif_phrase_contours(
            transition_motif_phrase_contour_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_sweeps = _source_hypothesis_linked_transition_motif_phrase_sweeps(
            transition_motif_phrase_sweep_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_gestures = _source_hypothesis_linked_transition_motif_phrase_gestures(
            transition_motif_phrase_gesture_summary,
            linked_transition_indexes,
        )
        linked_transition_motif_phrase_mobilities = _source_hypothesis_linked_transition_motif_phrase_mobilities(
            transition_motif_phrase_mobility_summary,
            linked_transition_indexes,
        )
        time_bounds = _source_hypothesis_time_bounds(
            duration_seconds=duration_seconds,
            section_candidates=section_candidates,
            linked_section_indexes=linked_section_indexes,
            linked_onset_offsets_seconds=linked_onset_offsets_seconds,
        )
        hypotheses.append(
            {
                "source_id": f"hypothesis.{source_class}.{hypothesis_index:02d}",
                "source_class": source_class,
                "role": role,
                "confidence": _round_float(confidence),
                "confidence_band": _confidence_band(confidence),
                "hypothesis_origin": "observation-derived",
                "time_bounds": time_bounds,
                "linked_observations": {
                    "section_indexes": linked_section_indexes,
                    "transition_indexes": linked_transition_indexes,
                    "transition_motif_ids": [entry["motif_id"] for entry in linked_transition_motifs],
                    "transition_motif_signatures": [entry["signature"] for entry in linked_transition_motifs],
                    "transition_motif_reference_count": len(linked_transition_motifs),
                    "transition_motif_sequence_ids": [entry["sequence_id"] for entry in linked_transition_motif_sequences],
                    "transition_motif_sequence_signatures": [entry["signature"] for entry in linked_transition_motif_sequences],
                    "transition_motif_sequence_reference_count": len(linked_transition_motif_sequences),
                    "transition_motif_chain_ids": [entry["chain_id"] for entry in linked_transition_motif_chains],
                    "transition_motif_chain_signatures": [entry["signature"] for entry in linked_transition_motif_chains],
                    "transition_motif_chain_reference_count": len(linked_transition_motif_chains),
                    "transition_motif_phrase_ids": [entry["phrase_id"] for entry in linked_transition_motif_phrases],
                    "transition_motif_phrase_signatures": [entry["signature"] for entry in linked_transition_motif_phrases],
                    "transition_motif_phrase_reference_count": len(linked_transition_motif_phrases),
                    "transition_motif_phrase_family_ids": [
                        entry["family_id"] for entry in linked_transition_motif_phrase_families
                    ],
                    "transition_motif_phrase_family_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_families
                    ],
                    "transition_motif_phrase_family_reference_count": len(linked_transition_motif_phrase_families),
                    "transition_motif_phrase_archetype_ids": [
                        entry["archetype_id"] for entry in linked_transition_motif_phrase_archetypes
                    ],
                    "transition_motif_phrase_archetype_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_archetypes
                    ],
                    "transition_motif_phrase_archetype_reference_count": len(linked_transition_motif_phrase_archetypes),
                    "transition_motif_phrase_contour_ids": [
                        entry["contour_id"] for entry in linked_transition_motif_phrase_contours
                    ],
                    "transition_motif_phrase_contour_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_contours
                    ],
                    "transition_motif_phrase_contour_reference_count": len(linked_transition_motif_phrase_contours),
                    "transition_motif_phrase_sweep_ids": [
                        entry["sweep_id"] for entry in linked_transition_motif_phrase_sweeps
                    ],
                    "transition_motif_phrase_sweep_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_sweeps
                    ],
                    "transition_motif_phrase_sweep_reference_count": len(linked_transition_motif_phrase_sweeps),
                    "transition_motif_phrase_gesture_ids": [
                        entry["gesture_id"] for entry in linked_transition_motif_phrase_gestures
                    ],
                    "transition_motif_phrase_gesture_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_gestures
                    ],
                    "transition_motif_phrase_gesture_reference_count": len(linked_transition_motif_phrase_gestures),
                    "transition_motif_phrase_mobility_ids": [
                        entry["mobility_id"] for entry in linked_transition_motif_phrase_mobilities
                    ],
                    "transition_motif_phrase_mobility_signatures": [
                        entry["signature"] for entry in linked_transition_motif_phrase_mobilities
                    ],
                    "transition_motif_phrase_mobility_reference_count": len(linked_transition_motif_phrase_mobilities),
                    "onset_offsets_seconds_preview": [_round_float(offset) for offset in linked_onset_offsets_seconds[:8]],
                    "onset_reference_count": len(linked_onset_offsets_seconds),
                },
                "supporting_observations": supporting_observations,
                "evidence": evidence,
                "ambiguity_notes": ambiguity_notes,
            }
        )

    all_section_indexes = [
        int(candidate.get("section_index", 0) or 0)
        for candidate in section_candidates
        if isinstance(candidate, dict)
    ]
    all_transition_indexes = list(range(len(section_transitions)))
    all_onset_offsets = [
        float(entry.get("offset_seconds", 0.0) or 0.0)
        for entry in onset_map
        if isinstance(entry, dict)
    ]
    high_salience_section_indexes = [
        int(candidate.get("section_index", 0) or 0)
        for candidate in section_candidates
        if isinstance(candidate, dict)
        and (
            str(candidate.get("energy_band")) in {"medium", "high"}
            or float(candidate.get("duration_seconds", 0.0) or 0.0) >= max(average_duration_seconds, 2.0)
        )
    ]
    strongest_transition_indexes = [
        index
        for index, transition in enumerate(section_transitions)
        if isinstance(transition, dict)
        and abs(float(transition.get("energy_delta", 0.0) or 0.0)) >= max(average_abs_energy_delta, 0.15)
    ]
    longest_section_indexes = [
        int(candidate.get("section_index", 0) or 0)
        for candidate in sorted(
            [candidate for candidate in section_candidates if isinstance(candidate, dict)],
            key=lambda candidate: (-float(candidate.get("duration_seconds", 0.0) or 0.0), int(candidate.get("section_index", 0) or 0)),
        )[:3]
    ]

    if channel_count >= 2:
        append_hypothesis(
            "stereo_program_bed",
            role="spatial_program",
            confidence=min(0.72, 0.42 + (0.06 * min(channel_count, 2)) + (0.08 if section_candidate_count >= 8 else 0.0)),
            supporting_observations=[
                "multiple decoded channels are present",
                "channel energy is tracked independently",
                "section structure suggests layered program behavior",
            ],
            evidence={
                "channel_count": channel_count,
                "section_candidate_count": section_candidate_count,
                "section_transition_count": section_transition_count,
            },
            ambiguity_notes=[
                "This does not identify instruments or stems; it only flags multi-channel structured program behavior.",
            ],
            linked_section_indexes=all_section_indexes,
            linked_transition_indexes=all_transition_indexes,
            linked_onset_offsets_seconds=[],
        )

    if onset_count >= 4 and onset_density_per_second >= 1.5:
        append_hypothesis(
            "transient_event_cluster",
            role="event_layer",
            confidence=min(0.74, 0.38 + min(0.22, onset_density_per_second / 8.0) + (0.08 if section_transition_count >= 2 else 0.0)),
            supporting_observations=[
                "onset density indicates repeated local events",
                "transition counts suggest non-uniform event flow",
            ],
            evidence={
                "estimated_onset_count": onset_count,
                "onset_density_per_second": _round_float(onset_density_per_second),
                "section_transition_count": section_transition_count,
            },
            ambiguity_notes=[
                "The event cluster may correspond to percussive attacks, articulated calls, or other transient-rich behavior.",
            ],
            linked_section_indexes=high_salience_section_indexes[:8],
            linked_transition_indexes=strongest_transition_indexes[:8],
            linked_onset_offsets_seconds=all_onset_offsets,
        )

    if section_candidate_count >= 2 and average_duration_seconds >= 0.3 and isinstance(dominant_energy_band, str) and dominant_energy_band:
        append_hypothesis(
            "sustained_sectional_bed",
            role="structural_bed",
            confidence=min(0.7, 0.36 + min(0.16, average_duration_seconds / 10.0) + (0.08 if dominant_energy_band in {"medium", "high"} else 0.0) + (0.05 if section_boundary_count >= 1 else 0.0)),
            supporting_observations=[
                "section candidates persist for non-trivial durations",
                "dominant energy band remains interpretable across sections",
            ],
            evidence={
                "section_candidate_count": section_candidate_count,
                "average_duration_seconds": _round_float(average_duration_seconds),
                "longest_duration_seconds": _round_float(longest_duration_seconds),
                "dominant_energy_band": dominant_energy_band,
            },
            ambiguity_notes=[
                "This flags a stable structural layer, not a named accompaniment or instrument family.",
            ],
            linked_section_indexes=(high_salience_section_indexes or all_section_indexes)[:12],
            linked_transition_indexes=all_transition_indexes[:12],
            linked_onset_offsets_seconds=[],
        )

    if channel_count == 1 and longest_duration_seconds >= 6.0 and average_abs_energy_delta >= 0.25:
        append_hypothesis(
            "foreground_call_stream",
            role="foreground_stream",
            confidence=min(0.76, 0.41 + min(0.14, longest_duration_seconds / 18.0) + min(0.12, average_abs_energy_delta / 2.5)),
            supporting_observations=[
                "long mono sections dominate the observed window",
                "transition energy deltas suggest foreground contour changes",
            ],
            evidence={
                "channel_count": channel_count,
                "longest_duration_seconds": _round_float(longest_duration_seconds),
                "average_abs_energy_delta": _round_float(average_abs_energy_delta),
            },
            ambiguity_notes=[
                "This does not classify the emitter semantically; it only flags a foreground call-like stream in the observations.",
            ],
            linked_section_indexes=longest_section_indexes,
            linked_transition_indexes=strongest_transition_indexes[:6],
            linked_onset_offsets_seconds=all_onset_offsets[:24],
        )

    return hypotheses


def _source_hypothesis_time_bounds(
    *,
    duration_seconds: float,
    section_candidates: list[dict[str, Any]],
    linked_section_indexes: list[int],
    linked_onset_offsets_seconds: list[float],
) -> dict[str, float]:
    section_candidates_by_index = {
        int(candidate.get("section_index", 0) or 0): candidate
        for candidate in section_candidates
        if isinstance(candidate, dict)
    }
    starts: list[float] = []
    ends: list[float] = []
    for section_index in linked_section_indexes:
        candidate = section_candidates_by_index.get(section_index)
        if not isinstance(candidate, dict):
            continue
        starts.append(float(candidate.get("start_seconds", 0.0) or 0.0))
        ends.append(float(candidate.get("end_seconds", 0.0) or 0.0))

    if linked_onset_offsets_seconds:
        starts.append(min(linked_onset_offsets_seconds))
        ends.append(min(duration_seconds, max(linked_onset_offsets_seconds) + 0.25))

    if not starts or not ends:
        return {
            "start_seconds": 0.0,
            "end_seconds": _round_float(duration_seconds),
            "duration_seconds": _round_float(duration_seconds),
        }

    start_seconds = max(0.0, min(starts))
    end_seconds = min(duration_seconds, max(ends))
    return {
        "start_seconds": _round_float(start_seconds),
        "end_seconds": _round_float(end_seconds),
        "duration_seconds": _round_float(max(0.0, end_seconds - start_seconds)),
    }


def _transition_motif_time_bounds(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    indexes: list[int],
) -> dict[str, float]:
    section_candidates_by_index = {
        int(candidate.get("section_index", 0) or 0): candidate
        for candidate in section_candidates
        if isinstance(candidate, dict)
    }
    starts: list[float] = []
    ends: list[float] = []
    for index in indexes:
        transition = _mapping_optional(section_transitions[index])
        from_section = _mapping_optional(section_candidates_by_index.get(int(transition.get("from_section_index", 0) or 0)))
        to_section = _mapping_optional(section_candidates_by_index.get(int(transition.get("to_section_index", 0) or 0)))
        if from_section:
            starts.append(float(from_section.get("start_seconds", 0.0) or 0.0))
            ends.append(float(from_section.get("end_seconds", 0.0) or 0.0))
        if to_section:
            starts.append(float(to_section.get("start_seconds", 0.0) or 0.0))
            ends.append(float(to_section.get("end_seconds", 0.0) or 0.0))
        else:
            boundary_offset = float(transition.get("boundary_offset_seconds", 0.0) or 0.0)
            starts.append(boundary_offset)
            ends.append(boundary_offset)
    start_seconds = min(starts) if starts else 0.0
    end_seconds = max(ends) if ends else start_seconds
    return {
        "start_seconds": _round_float(start_seconds),
        "end_seconds": _round_float(end_seconds),
        "duration_seconds": _round_float(max(0.0, end_seconds - start_seconds)),
    }


def _transition_motif_sequence_time_bounds(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    occurrence_pairs: list[list[int]],
) -> dict[str, float]:
    indexes = sorted({index for pair in occurrence_pairs for index in pair})
    return _transition_motif_time_bounds(section_candidates, section_transitions, indexes)


def _transition_motif_chain_time_bounds(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    occurrence_chains: list[list[int]],
) -> dict[str, float]:
    indexes = sorted({index for chain in occurrence_chains for index in chain})
    return _transition_motif_time_bounds(section_candidates, section_transitions, indexes)


def _transition_motif_phrase_time_bounds(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    occurrence_phrases: list[list[int]],
) -> dict[str, float]:
    indexes = sorted({index for phrase in occurrence_phrases for index in phrase})
    return _transition_motif_time_bounds(section_candidates, section_transitions, indexes)


def _transition_motif_phrase_family_time_bounds(
    section_candidates: list[dict[str, Any]],
    section_transitions: list[dict[str, Any]],
    occurrence_phrases: list[list[int]],
) -> dict[str, float]:
    return _transition_motif_phrase_time_bounds(section_candidates, section_transitions, occurrence_phrases)


def _source_hypothesis_linked_transition_motifs(
    transition_motif_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if not linked_transition_indexes:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_motifs: list[dict[str, str]] = []
    for motif in _list_optional(transition_motif_summary.get("motifs")):
        if not isinstance(motif, dict):
            continue
        motif_transition_indexes = {
            int(index)
            for index in _list_optional(motif.get("section_transition_indexes"))
            if isinstance(index, int)
        }
        if not motif_transition_indexes.intersection(linked_transition_index_set):
            continue
        motif_id = motif.get("motif_id")
        signature = motif.get("signature")
        if not isinstance(motif_id, str) or not motif_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_motifs.append({"motif_id": motif_id, "signature": signature})

    linked_motifs.sort(key=lambda item: (item["motif_id"], item["signature"]))
    return linked_motifs


def _source_hypothesis_linked_transition_motif_sequences(
    transition_motif_sequence_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 2:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_sequences: list[dict[str, str]] = []
    for sequence in _list_optional(transition_motif_sequence_summary.get("sequences")):
        if not isinstance(sequence, dict):
            continue
        occurrence_pairs = [
            pair
            for pair in _list_optional(sequence.get("section_transition_index_pairs"))
            if isinstance(pair, list) and len(pair) == 2
        ]
        if not any(
            isinstance(left, int) and isinstance(right, int) and left in linked_transition_index_set and right in linked_transition_index_set
            for left, right in occurrence_pairs
        ):
            continue
        sequence_id = sequence.get("sequence_id")
        signature = sequence.get("signature")
        if not isinstance(sequence_id, str) or not sequence_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_sequences.append({"sequence_id": sequence_id, "signature": signature})

    linked_sequences.sort(key=lambda item: (item["sequence_id"], item["signature"]))
    return linked_sequences


def _source_hypothesis_linked_transition_motif_chains(
    transition_motif_chain_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_chains: list[dict[str, str]] = []
    for chain in _list_optional(transition_motif_chain_summary.get("chains")):
        if not isinstance(chain, dict):
            continue
        occurrence_chains = [
            indexes
            for indexes in _list_optional(chain.get("section_transition_index_chains"))
            if isinstance(indexes, list) and len(indexes) == 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_chains
        ):
            continue
        chain_id = chain.get("chain_id")
        signature = chain.get("signature")
        if not isinstance(chain_id, str) or not chain_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_chains.append({"chain_id": chain_id, "signature": signature})

    linked_chains.sort(key=lambda item: (item["chain_id"], item["signature"]))
    return linked_chains


def _source_hypothesis_linked_transition_motif_phrases(
    transition_motif_phrase_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_phrases: list[dict[str, str]] = []
    for phrase in _list_optional(transition_motif_phrase_summary.get("phrases")):
        if not isinstance(phrase, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(phrase.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        phrase_id = phrase.get("phrase_id")
        signature = phrase.get("signature")
        if not isinstance(phrase_id, str) or not phrase_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_phrases.append({"phrase_id": phrase_id, "signature": signature})

    linked_phrases.sort(key=lambda item: (item["phrase_id"], item["signature"]))
    return linked_phrases


def _source_hypothesis_linked_transition_motif_phrase_families(
    transition_motif_phrase_family_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_families: list[dict[str, str]] = []
    for family in _list_optional(transition_motif_phrase_family_summary.get("families")):
        if not isinstance(family, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(family.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        family_id = family.get("family_id")
        signature = family.get("signature")
        if not isinstance(family_id, str) or not family_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_families.append({"family_id": family_id, "signature": signature})

    linked_families.sort(key=lambda item: (item["family_id"], item["signature"]))
    return linked_families


def _source_hypothesis_linked_transition_motif_phrase_archetypes(
    transition_motif_phrase_archetype_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_archetypes: list[dict[str, str]] = []
    for archetype in _list_optional(transition_motif_phrase_archetype_summary.get("archetypes")):
        if not isinstance(archetype, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(archetype.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        archetype_id = archetype.get("archetype_id")
        signature = archetype.get("signature")
        if not isinstance(archetype_id, str) or not archetype_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_archetypes.append({"archetype_id": archetype_id, "signature": signature})

    linked_archetypes.sort(key=lambda item: (item["archetype_id"], item["signature"]))
    return linked_archetypes


def _source_hypothesis_linked_transition_motif_phrase_contours(
    transition_motif_phrase_contour_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_contours: list[dict[str, str]] = []
    for contour in _list_optional(transition_motif_phrase_contour_summary.get("contours")):
        if not isinstance(contour, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(contour.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        contour_id = contour.get("contour_id")
        signature = contour.get("signature")
        if not isinstance(contour_id, str) or not contour_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_contours.append({"contour_id": contour_id, "signature": signature})

    linked_contours.sort(key=lambda item: (item["contour_id"], item["signature"]))
    return linked_contours


def _source_hypothesis_linked_transition_motif_phrase_sweeps(
    transition_motif_phrase_sweep_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_sweeps: list[dict[str, str]] = []
    for sweep in _list_optional(transition_motif_phrase_sweep_summary.get("sweeps")):
        if not isinstance(sweep, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(sweep.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        sweep_id = sweep.get("sweep_id")
        signature = sweep.get("signature")
        if not isinstance(sweep_id, str) or not sweep_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_sweeps.append({"sweep_id": sweep_id, "signature": signature})

    linked_sweeps.sort(key=lambda item: (item["sweep_id"], item["signature"]))
    return linked_sweeps


def _source_hypothesis_linked_transition_motif_phrase_gestures(
    transition_motif_phrase_gesture_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_gestures: list[dict[str, str]] = []
    for gesture in _list_optional(transition_motif_phrase_gesture_summary.get("gestures")):
        if not isinstance(gesture, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(gesture.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        gesture_id = gesture.get("gesture_id")
        signature = gesture.get("signature")
        if not isinstance(gesture_id, str) or not gesture_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_gestures.append({"gesture_id": gesture_id, "signature": signature})

    linked_gestures.sort(key=lambda item: (item["gesture_id"], item["signature"]))
    return linked_gestures


def _source_hypothesis_linked_transition_motif_phrase_mobilities(
    transition_motif_phrase_mobility_summary: dict[str, Any],
    linked_transition_indexes: list[int],
) -> list[dict[str, str]]:
    if len(linked_transition_indexes) < 3:
        return []

    linked_transition_index_set = set(linked_transition_indexes)
    linked_mobilities: list[dict[str, str]] = []
    for mobility in _list_optional(transition_motif_phrase_mobility_summary.get("mobilities")):
        if not isinstance(mobility, dict):
            continue
        occurrence_phrases = [
            indexes
            for indexes in _list_optional(mobility.get("section_transition_index_phrases"))
            if isinstance(indexes, list) and len(indexes) >= 3
        ]
        if not any(
            all(isinstance(index, int) and index in linked_transition_index_set for index in indexes)
            for indexes in occurrence_phrases
        ):
            continue
        mobility_id = mobility.get("mobility_id")
        signature = mobility.get("signature")
        if not isinstance(mobility_id, str) or not mobility_id:
            continue
        if not isinstance(signature, str) or not signature:
            continue
        linked_mobilities.append({"mobility_id": mobility_id, "signature": signature})

    linked_mobilities.sort(key=lambda item: (item["mobility_id"], item["signature"]))
    return linked_mobilities


def _transition_kind(energy_delta: float) -> str:
    if energy_delta >= 0.2:
        return "energy_increase"
    if energy_delta <= -0.2:
        return "energy_decrease"
    return "energy_stable"


def _duration_trend(duration_delta_seconds: float) -> str:
    if duration_delta_seconds >= 0.75:
        return "lengthen"
    if duration_delta_seconds <= -0.75:
        return "shorten"
    return "stable"


def _transition_motif_signature(transition: dict[str, Any]) -> str:
    return "|".join(
        [
            str(transition.get("transition_kind") or "unknown"),
            str(transition.get("from_energy_band") or "unknown"),
            str(transition.get("to_energy_band") or "unknown"),
            _duration_trend(float(transition.get("duration_delta_seconds", 0.0) or 0.0)),
        ]
    )


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.7:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "low"


def _duration_band(duration_seconds: float) -> str:
    if duration_seconds < 2.0:
        return "short"
    if duration_seconds > 8.0:
        return "long"
    return "medium"


def _position_band(position_ratio: float) -> str:
    if position_ratio < 0.2:
        return "opening"
    if position_ratio > 0.8:
        return "closing"
    return "middle"


def _spectral_extent_summary(mono: np.ndarray, sample_rate_hz: int) -> tuple[int, int]:
    if mono.size == 0:
        return 0, 0
    spectrum = np.abs(np.fft.rfft(mono))
    power = spectrum * spectrum
    total_power = float(np.sum(power))
    if total_power <= 0.0:
        return 0, 0
    cumulative = np.cumsum(power)
    frequencies = np.fft.rfftfreq(mono.size, d=1.0 / float(sample_rate_hz))
    low_index = int(np.searchsorted(cumulative, total_power * 0.01))
    high_index = int(np.searchsorted(cumulative, total_power * 0.99))
    low_index = min(low_index, len(frequencies) - 1)
    high_index = min(high_index, len(frequencies) - 1)
    return int(round(frequencies[low_index])), int(round(frequencies[high_index]))


def _channel_labels(channel_count: int) -> list[str]:
    if channel_count == 1:
        return ["center"]
    if channel_count == 2:
        return ["left", "right"]
    return [f"channel_{index + 1}" for index in range(channel_count)]


def _preprocessing_steps(decode_backend: str, channel_mode: str, target_sample_rate_hz: int | None) -> list[str]:
    steps = [f"decode audio using {decode_backend}", f"apply channel mode {channel_mode}"]
    if target_sample_rate_hz is not None:
        steps.append(f"resample audio to {target_sample_rate_hz} Hz")
    steps.append("compute basic observation summaries")
    return steps


def _selected_field_changes(left: dict[str, Any], right: dict[str, Any], field_names: tuple[str, ...]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for field_name in field_names:
        if left.get(field_name) != right.get(field_name):
            changes[field_name] = {
                "left": left.get(field_name),
                "right": right.get(field_name),
            }
    return changes


def _diff_basic_observation_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    changes = _selected_field_changes(
        left,
        right,
        ("peak_amplitude", "rms_amplitude", "estimated_onset_count", "frame_count"),
    )

    left_spectral = _mapping_optional(left.get("spectral_extent_summary"))
    right_spectral = _mapping_optional(right.get("spectral_extent_summary"))
    spectral_changes = _selected_field_changes(left_spectral, right_spectral, ("low_hz", "high_hz"))
    if spectral_changes:
        changes["spectral_extent_summary"] = spectral_changes

    left_channel_energy = _mapping_optional(left.get("channel_energy_summary"))
    right_channel_energy = _mapping_optional(right.get("channel_energy_summary"))
    channel_names = tuple(sorted(set(left_channel_energy) | set(right_channel_energy)))
    channel_energy_changes = _selected_field_changes(left_channel_energy, right_channel_energy, channel_names)
    if channel_energy_changes:
        changes["channel_energy_summary"] = channel_energy_changes

    left_section_profile = _mapping_optional(left.get("section_profile_summary"))
    right_section_profile = _mapping_optional(right.get("section_profile_summary"))
    section_profile_changes = _selected_field_changes(
        left_section_profile,
        right_section_profile,
        ("average_duration_seconds", "longest_duration_seconds", "dominant_energy_band", "opening_energy_band", "closing_energy_band"),
    )
    energy_band_count_changes = _selected_field_changes(
        _mapping_optional(left_section_profile.get("energy_band_counts")),
        _mapping_optional(right_section_profile.get("energy_band_counts")),
        tuple(sorted(set(_mapping_optional(left_section_profile.get("energy_band_counts"))) | set(_mapping_optional(right_section_profile.get("energy_band_counts"))))),
    )
    if energy_band_count_changes:
        section_profile_changes["energy_band_counts"] = energy_band_count_changes
    duration_band_count_changes = _selected_field_changes(
        _mapping_optional(left_section_profile.get("duration_band_counts")),
        _mapping_optional(right_section_profile.get("duration_band_counts")),
        tuple(sorted(set(_mapping_optional(left_section_profile.get("duration_band_counts"))) | set(_mapping_optional(right_section_profile.get("duration_band_counts"))))),
    )
    if duration_band_count_changes:
        section_profile_changes["duration_band_counts"] = duration_band_count_changes
    position_band_count_changes = _selected_field_changes(
        _mapping_optional(left_section_profile.get("position_band_counts")),
        _mapping_optional(right_section_profile.get("position_band_counts")),
        tuple(sorted(set(_mapping_optional(left_section_profile.get("position_band_counts"))) | set(_mapping_optional(right_section_profile.get("position_band_counts"))))),
    )
    if position_band_count_changes:
        section_profile_changes["position_band_counts"] = position_band_count_changes
    if section_profile_changes:
        changes["section_profile_summary"] = section_profile_changes

    left_transition_profile = _mapping_optional(left.get("transition_profile_summary"))
    right_transition_profile = _mapping_optional(right.get("transition_profile_summary"))
    transition_profile_changes = _selected_field_changes(
        left_transition_profile,
        right_transition_profile,
        ("average_abs_energy_delta", "largest_abs_energy_delta", "dominant_transition_kind", "opening_transition_kind", "closing_transition_kind"),
    )
    transition_kind_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_profile.get("transition_kind_counts")),
        _mapping_optional(right_transition_profile.get("transition_kind_counts")),
        tuple(sorted(set(_mapping_optional(left_transition_profile.get("transition_kind_counts"))) | set(_mapping_optional(right_transition_profile.get("transition_kind_counts"))))),
    )
    if transition_kind_count_changes:
        transition_profile_changes["transition_kind_counts"] = transition_kind_count_changes
    if transition_profile_changes:
        changes["transition_profile_summary"] = transition_profile_changes

    left_transition_motif = _mapping_optional(left.get("transition_motif_summary"))
    right_transition_motif = _mapping_optional(right.get("transition_motif_summary"))
    transition_motif_changes = _selected_field_changes(
        left_transition_motif,
        right_transition_motif,
        ("recurring_motif_count", "motif_occurrence_count", "dominant_motif_signature"),
    )
    motif_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif.get("motif_signature_counts")),
        _mapping_optional(right_transition_motif.get("motif_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif.get("motif_signature_counts")))
                | set(_mapping_optional(right_transition_motif.get("motif_signature_counts")))
            )
        ),
    )
    if motif_signature_count_changes:
        transition_motif_changes["motif_signature_counts"] = motif_signature_count_changes
    if transition_motif_changes:
        changes["transition_motif_summary"] = transition_motif_changes

    left_transition_motif_sequence = _mapping_optional(left.get("transition_motif_sequence_summary"))
    right_transition_motif_sequence = _mapping_optional(right.get("transition_motif_sequence_summary"))
    transition_motif_sequence_changes = _selected_field_changes(
        left_transition_motif_sequence,
        right_transition_motif_sequence,
        ("recurring_sequence_count", "sequence_occurrence_count", "dominant_sequence_signature"),
    )
    sequence_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_sequence.get("sequence_signature_counts")),
        _mapping_optional(right_transition_motif_sequence.get("sequence_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_sequence.get("sequence_signature_counts")))
                | set(_mapping_optional(right_transition_motif_sequence.get("sequence_signature_counts")))
            )
        ),
    )
    if sequence_signature_count_changes:
        transition_motif_sequence_changes["sequence_signature_counts"] = sequence_signature_count_changes
    if transition_motif_sequence_changes:
        changes["transition_motif_sequence_summary"] = transition_motif_sequence_changes

    left_transition_motif_chain = _mapping_optional(left.get("transition_motif_chain_summary"))
    right_transition_motif_chain = _mapping_optional(right.get("transition_motif_chain_summary"))
    transition_motif_chain_changes = _selected_field_changes(
        left_transition_motif_chain,
        right_transition_motif_chain,
        ("chain_length", "recurring_chain_count", "chain_occurrence_count", "dominant_chain_signature"),
    )
    chain_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_chain.get("chain_signature_counts")),
        _mapping_optional(right_transition_motif_chain.get("chain_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_chain.get("chain_signature_counts")))
                | set(_mapping_optional(right_transition_motif_chain.get("chain_signature_counts")))
            )
        ),
    )
    if chain_signature_count_changes:
        transition_motif_chain_changes["chain_signature_counts"] = chain_signature_count_changes
    if transition_motif_chain_changes:
        changes["transition_motif_chain_summary"] = transition_motif_chain_changes

    left_transition_motif_phrase = _mapping_optional(left.get("transition_motif_phrase_summary"))
    right_transition_motif_phrase = _mapping_optional(right.get("transition_motif_phrase_summary"))
    transition_motif_phrase_changes = _selected_field_changes(
        left_transition_motif_phrase,
        right_transition_motif_phrase,
        ("min_phrase_length", "max_phrase_length", "recurring_phrase_count", "phrase_occurrence_count", "dominant_phrase_signature"),
    )
    phrase_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase.get("phrase_signature_counts")),
        _mapping_optional(right_transition_motif_phrase.get("phrase_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase.get("phrase_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase.get("phrase_signature_counts")))
            )
        ),
    )
    if phrase_signature_count_changes:
        transition_motif_phrase_changes["phrase_signature_counts"] = phrase_signature_count_changes
    if transition_motif_phrase_changes:
        changes["transition_motif_phrase_summary"] = transition_motif_phrase_changes

    left_transition_motif_phrase_family = _mapping_optional(left.get("transition_motif_phrase_family_summary"))
    right_transition_motif_phrase_family = _mapping_optional(right.get("transition_motif_phrase_family_summary"))
    transition_motif_phrase_family_changes = _selected_field_changes(
        left_transition_motif_phrase_family,
        right_transition_motif_phrase_family,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_family_count",
            "family_occurrence_count",
            "dominant_family_signature",
        ),
    )
    phrase_family_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_family.get("family_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_family.get("family_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_family.get("family_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_family.get("family_signature_counts")))
            )
        ),
    )
    if phrase_family_signature_count_changes:
        transition_motif_phrase_family_changes["family_signature_counts"] = phrase_family_signature_count_changes
    if transition_motif_phrase_family_changes:
        changes["transition_motif_phrase_family_summary"] = transition_motif_phrase_family_changes

    left_transition_motif_phrase_archetype = _mapping_optional(left.get("transition_motif_phrase_archetype_summary"))
    right_transition_motif_phrase_archetype = _mapping_optional(right.get("transition_motif_phrase_archetype_summary"))
    transition_motif_phrase_archetype_changes = _selected_field_changes(
        left_transition_motif_phrase_archetype,
        right_transition_motif_phrase_archetype,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_archetype_count",
            "archetype_occurrence_count",
            "dominant_archetype_signature",
        ),
    )
    phrase_archetype_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_archetype.get("archetype_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_archetype.get("archetype_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_archetype.get("archetype_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_archetype.get("archetype_signature_counts")))
            )
        ),
    )
    if phrase_archetype_signature_count_changes:
        transition_motif_phrase_archetype_changes["archetype_signature_counts"] = phrase_archetype_signature_count_changes
    if transition_motif_phrase_archetype_changes:
        changes["transition_motif_phrase_archetype_summary"] = transition_motif_phrase_archetype_changes

    left_transition_motif_phrase_contour = _mapping_optional(left.get("transition_motif_phrase_contour_summary"))
    right_transition_motif_phrase_contour = _mapping_optional(right.get("transition_motif_phrase_contour_summary"))
    transition_motif_phrase_contour_changes = _selected_field_changes(
        left_transition_motif_phrase_contour,
        right_transition_motif_phrase_contour,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_contour_count",
            "contour_occurrence_count",
            "dominant_contour_signature",
        ),
    )
    phrase_contour_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_contour.get("contour_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_contour.get("contour_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_contour.get("contour_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_contour.get("contour_signature_counts")))
            )
        ),
    )
    if phrase_contour_signature_count_changes:
        transition_motif_phrase_contour_changes["contour_signature_counts"] = phrase_contour_signature_count_changes
    if transition_motif_phrase_contour_changes:
        changes["transition_motif_phrase_contour_summary"] = transition_motif_phrase_contour_changes

    left_transition_motif_phrase_sweep = _mapping_optional(left.get("transition_motif_phrase_sweep_summary"))
    right_transition_motif_phrase_sweep = _mapping_optional(right.get("transition_motif_phrase_sweep_summary"))
    transition_motif_phrase_sweep_changes = _selected_field_changes(
        left_transition_motif_phrase_sweep,
        right_transition_motif_phrase_sweep,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_sweep_count",
            "sweep_occurrence_count",
            "dominant_sweep_signature",
        ),
    )
    phrase_sweep_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_sweep.get("sweep_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_sweep.get("sweep_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_sweep.get("sweep_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_sweep.get("sweep_signature_counts")))
            )
        ),
    )
    if phrase_sweep_signature_count_changes:
        transition_motif_phrase_sweep_changes["sweep_signature_counts"] = phrase_sweep_signature_count_changes
    if transition_motif_phrase_sweep_changes:
        changes["transition_motif_phrase_sweep_summary"] = transition_motif_phrase_sweep_changes

    left_transition_motif_phrase_gesture = _mapping_optional(left.get("transition_motif_phrase_gesture_summary"))
    right_transition_motif_phrase_gesture = _mapping_optional(right.get("transition_motif_phrase_gesture_summary"))
    transition_motif_phrase_gesture_changes = _selected_field_changes(
        left_transition_motif_phrase_gesture,
        right_transition_motif_phrase_gesture,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_gesture_count",
            "gesture_occurrence_count",
            "dominant_gesture_signature",
        ),
    )
    phrase_gesture_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_gesture.get("gesture_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_gesture.get("gesture_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_gesture.get("gesture_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_gesture.get("gesture_signature_counts")))
            )
        ),
    )
    if phrase_gesture_signature_count_changes:
        transition_motif_phrase_gesture_changes["gesture_signature_counts"] = phrase_gesture_signature_count_changes
    if transition_motif_phrase_gesture_changes:
        changes["transition_motif_phrase_gesture_summary"] = transition_motif_phrase_gesture_changes

    left_transition_motif_phrase_mobility = _mapping_optional(left.get("transition_motif_phrase_mobility_summary"))
    right_transition_motif_phrase_mobility = _mapping_optional(right.get("transition_motif_phrase_mobility_summary"))
    transition_motif_phrase_mobility_changes = _selected_field_changes(
        left_transition_motif_phrase_mobility,
        right_transition_motif_phrase_mobility,
        (
            "min_phrase_length",
            "max_phrase_length",
            "recurring_mobility_count",
            "mobility_occurrence_count",
            "dominant_mobility_signature",
        ),
    )
    phrase_mobility_signature_count_changes = _selected_field_changes(
        _mapping_optional(left_transition_motif_phrase_mobility.get("mobility_signature_counts")),
        _mapping_optional(right_transition_motif_phrase_mobility.get("mobility_signature_counts")),
        tuple(
            sorted(
                set(_mapping_optional(left_transition_motif_phrase_mobility.get("mobility_signature_counts")))
                | set(_mapping_optional(right_transition_motif_phrase_mobility.get("mobility_signature_counts")))
            )
        ),
    )
    if phrase_mobility_signature_count_changes:
        transition_motif_phrase_mobility_changes["mobility_signature_counts"] = phrase_mobility_signature_count_changes
    if transition_motif_phrase_mobility_changes:
        changes["transition_motif_phrase_mobility_summary"] = transition_motif_phrase_mobility_changes

    left_abstraction_ladder = _transition_motif_phrase_abstraction_ladder(left)
    right_abstraction_ladder = _transition_motif_phrase_abstraction_ladder(right)
    abstraction_ladder_changes: dict[str, Any] = {}
    recurring_count_changes = _selected_field_changes(
        _mapping_optional(left_abstraction_ladder.get("recurring_counts")),
        _mapping_optional(right_abstraction_ladder.get("recurring_counts")),
        ("phrase", "family", "archetype", "contour", "sweep", "gesture", "mobility"),
    )
    if recurring_count_changes:
        abstraction_ladder_changes["recurring_counts"] = recurring_count_changes
    occurrence_count_changes = _selected_field_changes(
        _mapping_optional(left_abstraction_ladder.get("occurrence_counts")),
        _mapping_optional(right_abstraction_ladder.get("occurrence_counts")),
        ("phrase", "family", "archetype", "contour", "sweep", "gesture", "mobility"),
    )
    if occurrence_count_changes:
        abstraction_ladder_changes["occurrence_counts"] = occurrence_count_changes
    if abstraction_ladder_changes:
        changes["transition_motif_phrase_abstraction_ladder"] = abstraction_ladder_changes

    return changes


def _analysis_pair_changed(payload: dict[str, Any]) -> bool:
    summary = payload.get("change_summary")
    if isinstance(summary, dict) and any(int(summary.get(key, 0) or 0) for key in summary):
        return True
    return any(
        int(payload.get(key, 0) or 0)
        for key in (
            "source_hypothesis_count_delta",
            "component_group_count_delta",
            "onset_map_count_delta",
            "section_boundary_count_delta",
            "section_candidate_count_delta",
            "section_transition_count_delta",
            "uncertainty_warning_count_delta",
        )
    )


def _mapping_value(value: Any, *, section: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"analysis document section '{section}' must be a mapping")
    return dict(value)


def _mapping_optional(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_optional(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _list_value(value: Any, *, section: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"analysis document section '{section}' must be a list")
    return list(value)


def _validate_attention_contract(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("analysis document section 'attention_contract' must be a mapping")

    attention_contract = dict(value)
    _validate_optional_string_field(attention_contract, section="attention_contract", field="query_text")
    _validate_optional_string_list_field(attention_contract, section="attention_contract", field="attention_targets")
    _validate_optional_string_list_field(attention_contract, section="attention_contract", field="retain_targets")
    _validate_optional_string_list_field(attention_contract, section="attention_contract", field="suppress_targets")
    _validate_optional_string_list_field(attention_contract, section="attention_contract", field="answer_expectations")
    _validate_optional_string_field(attention_contract, section="attention_contract", field="render_goal")
    return attention_contract


def _validate_interpretation_layers(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("analysis document section 'interpretation_layers' must be a mapping")

    interpretation_layers = dict(value)
    for layer_name, layer_value in interpretation_layers.items():
        if not isinstance(layer_name, str) or not layer_name:
            raise ValueError("analysis document section 'interpretation_layers' must use non-empty string keys")
        if isinstance(layer_value, list):
            for index, item in enumerate(layer_value):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"analysis document section 'interpretation_layers.{layer_name}[{index}]' must be a mapping"
                    )
            continue
        if isinstance(layer_value, dict):
            continue
        raise ValueError(
            f"analysis document section 'interpretation_layers.{layer_name}' must be a mapping or a list of mappings"
        )
    return interpretation_layers


def _validate_transformation_intent(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("analysis document section 'transformation_intent' must be a mapping")

    transformation_intent = dict(value)
    _validate_optional_string_list_field(transformation_intent, section="transformation_intent", field="operations")
    _validate_optional_string_field(transformation_intent, section="transformation_intent", field="primary_output")
    return transformation_intent


def _validate_source_hypotheses(value: Any) -> list[dict[str, Any]]:
    source_hypotheses = _list_value(value, section="source_hypotheses")
    normalized_source_hypotheses: list[dict[str, Any]] = []
    for index, source_hypothesis in enumerate(source_hypotheses):
        section = f"source_hypotheses[{index}]"
        if not isinstance(source_hypothesis, dict):
            raise ValueError(f"analysis document section '{section}' must be a mapping")
        normalized_source_hypothesis = dict(source_hypothesis)
        _validate_required_string_field(normalized_source_hypothesis, section=section, field="source_id")
        _validate_optional_string_field(normalized_source_hypothesis, section=section, field="source_class")
        _validate_optional_string_field(normalized_source_hypothesis, section=section, field="role")
        _validate_optional_string_field(normalized_source_hypothesis, section=section, field="hypothesis_origin")
        _validate_optional_string_list_field(normalized_source_hypothesis, section=section, field="ambiguity_notes")
        _validate_optional_confidence_field(normalized_source_hypothesis, section=section, field="confidence")
        time_bounds = _validate_time_bounds(normalized_source_hypothesis.get("time_bounds"), section=f"{section}.time_bounds")
        linked_observations = _validate_linked_observations(
            normalized_source_hypothesis.get("linked_observations"),
            section=f"{section}.linked_observations",
        )
        if "time_bounds" in normalized_source_hypothesis or time_bounds:
            normalized_source_hypothesis["time_bounds"] = time_bounds
        if "linked_observations" in normalized_source_hypothesis or linked_observations:
            normalized_source_hypothesis["linked_observations"] = linked_observations
        normalized_source_hypotheses.append(normalized_source_hypothesis)
    return normalized_source_hypotheses


def _validate_component_layers(value: Any) -> dict[str, Any]:
    component_layers = _mapping_value(value, section="component_layers")
    normalized_component_layers: dict[str, Any] = {}
    for layer_name, layer_value in component_layers.items():
        if not isinstance(layer_name, str) or not layer_name:
            raise ValueError("analysis document section 'component_layers' must use non-empty string keys")
        section = f"component_layers.{layer_name}"
        if not isinstance(layer_value, list):
            raise ValueError(f"analysis document section '{section}' must be a list of mappings")
        normalized_layer: list[dict[str, Any]] = []
        for index, component in enumerate(layer_value):
            item_section = f"{section}[{index}]"
            if not isinstance(component, dict):
                raise ValueError(f"analysis document section '{item_section}' must be a mapping")
            normalized_component = dict(component)
            _validate_required_string_field(normalized_component, section=item_section, field="component_id")
            _validate_optional_string_field(normalized_component, section=item_section, field="component_type")
            _validate_optional_string_field(normalized_component, section=item_section, field="linked_source_id")
            _validate_optional_string_field(normalized_component, section=item_section, field="reconstruction_role")
            _validate_optional_confidence_field(normalized_component, section=item_section, field="confidence")
            parameters = normalized_component.get("parameters")
            if parameters is not None and not isinstance(parameters, dict):
                raise ValueError(f"analysis document section '{item_section}.parameters' must be a mapping")
            time_bounds = _validate_time_bounds(normalized_component.get("time_bounds"), section=f"{item_section}.time_bounds")
            if "time_bounds" in normalized_component or time_bounds:
                normalized_component["time_bounds"] = time_bounds
            normalized_layer.append(normalized_component)
        normalized_component_layers[layer_name] = normalized_layer
    return normalized_component_layers


def _validate_reconstruction(value: Any) -> dict[str, Any]:
    reconstruction = _mapping_value(value, section="reconstruction")
    _validate_optional_string_list_field(reconstruction, section="reconstruction", field="reconstructable_outputs")
    _validate_optional_string_list_field(reconstruction, section="reconstruction", field="render_constraints")
    _validate_optional_string_field(reconstruction, section="reconstruction", field="residual_energy_policy")
    for field in ("quality_estimates", "comparison_metrics"):
        nested_mapping = reconstruction.get(field)
        if nested_mapping is not None and not isinstance(nested_mapping, dict):
            raise ValueError(f"analysis document section 'reconstruction.{field}' must be a mapping")
    return reconstruction


def _validate_time_bounds(value: Any, *, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"analysis document section '{section}' must be a mapping")
    time_bounds = dict(value)
    for field in ("start_seconds", "end_seconds", "duration_seconds"):
        _validate_optional_non_negative_number_field(time_bounds, section=section, field=field)
    start_seconds = time_bounds.get("start_seconds")
    end_seconds = time_bounds.get("end_seconds")
    if isinstance(start_seconds, (int, float)) and isinstance(end_seconds, (int, float)) and end_seconds < start_seconds:
        raise ValueError(f"analysis document section '{section}.end_seconds' must be greater than or equal to start_seconds")
    return time_bounds


def _validate_linked_observations(value: Any, *, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"analysis document section '{section}' must be a mapping")
    linked_observations = dict(value)
    for field in ("section_indexes", "transition_indexes"):
        _validate_optional_non_negative_integer_list_field(linked_observations, section=section, field=field)
    _validate_optional_non_negative_number_list_field(
        linked_observations,
        section=section,
        field="onset_offsets_seconds_preview",
    )
    for field in tuple(linked_observations.keys()):
        if field.endswith("_ids") or field.endswith("_signatures"):
            _validate_optional_string_list_field(linked_observations, section=section, field=field)
        if field.endswith("_reference_count"):
            _validate_optional_non_negative_integer_field(linked_observations, section=section, field=field)
    return linked_observations


def _validate_required_string_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"analysis document section '{section}.{field}' must be a non-empty string")


def _validate_optional_string_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"analysis document section '{section}.{field}' must be a non-empty string")


def _validate_optional_string_list_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, list):
        raise ValueError(f"analysis document section '{section}.{field}' must be a list of non-empty strings")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"analysis document section '{section}.{field}[{index}]' must be a non-empty string"
            )


def _validate_optional_non_negative_integer_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"analysis document section '{section}.{field}' must be a non-negative integer")


def _validate_optional_non_negative_number_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < 0.0:
        raise ValueError(f"analysis document section '{section}.{field}' must be a non-negative number")


def _validate_optional_confidence_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"analysis document section '{section}.{field}' must be a number between 0.0 and 1.0")


def _validate_optional_non_negative_integer_list_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, list):
        raise ValueError(f"analysis document section '{section}.{field}' must be a list of non-negative integers")
    for index, item in enumerate(value):
        if not isinstance(item, int) or item < 0:
            raise ValueError(
                f"analysis document section '{section}.{field}[{index}]' must be a non-negative integer"
            )


def _validate_optional_non_negative_number_list_field(mapping: dict[str, Any], *, section: str, field: str) -> None:
    value = mapping.get(field)
    if value is None:
        return
    if not isinstance(value, list):
        raise ValueError(f"analysis document section '{section}.{field}' must be a list of non-negative numbers")
    for index, item in enumerate(value):
        if not isinstance(item, (int, float)) or isinstance(item, bool) or float(item) < 0.0:
            raise ValueError(
                f"analysis document section '{section}.{field}[{index}]' must be a non-negative number"
            )


def _count_component_groups(component_layers: dict[str, Any]) -> int:
    count = 0
    for value in component_layers.values():
        if isinstance(value, list):
            count += len(value)
    return count


def _source_hypothesis_classes(source_hypotheses: list[Any]) -> list[str]:
    classes = {
        str(hypothesis.get("source_class"))
        for hypothesis in source_hypotheses
        if isinstance(hypothesis, dict) and isinstance(hypothesis.get("source_class"), str) and hypothesis.get("source_class")
    }
    return sorted(classes)


def _transition_motif_signatures(transition_motif_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_summary.get("motif_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_summary.get("motif_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_sequence_signatures(transition_motif_sequence_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_sequence_summary.get("sequence_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_sequence_summary.get("sequence_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_chain_signatures(transition_motif_chain_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_chain_summary.get("chain_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_chain_summary.get("chain_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_signatures(transition_motif_phrase_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_summary.get("phrase_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_summary.get("phrase_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_family_signatures(transition_motif_phrase_family_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_family_summary.get("family_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_family_summary.get("family_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_archetype_signatures(transition_motif_phrase_archetype_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_archetype_summary.get("archetype_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_archetype_summary.get("archetype_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_contour_signatures(transition_motif_phrase_contour_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_contour_summary.get("contour_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_contour_summary.get("contour_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_sweep_signatures(transition_motif_phrase_sweep_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_sweep_summary.get("sweep_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_sweep_summary.get("sweep_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_gesture_signatures(transition_motif_phrase_gesture_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_gesture_summary.get("gesture_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_gesture_summary.get("gesture_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _transition_motif_phrase_mobility_signatures(transition_motif_phrase_mobility_summary: dict[str, Any]) -> list[str]:
    signatures = transition_motif_phrase_mobility_summary.get("mobility_signatures")
    if isinstance(signatures, list):
        return sorted({str(signature) for signature in signatures if isinstance(signature, str) and signature})
    signature_counts = _mapping_optional(transition_motif_phrase_mobility_summary.get("mobility_signature_counts"))
    return sorted(str(signature) for signature in signature_counts if isinstance(signature, str) and signature)


def _source_hypothesis_roles(source_hypotheses: list[Any]) -> list[str]:
    roles = {
        str(hypothesis.get("role"))
        for hypothesis in source_hypotheses
        if isinstance(hypothesis, dict) and isinstance(hypothesis.get("role"), str) and hypothesis.get("role")
    }
    return sorted(roles)


def _source_hypothesis_linked_transition_motif_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_sequence_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_sequence_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_chain_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_chain_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_family_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_family_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_archetype_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_archetype_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_contour_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_contour_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_sweep_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_sweep_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_gesture_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_gesture_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _source_hypothesis_linked_transition_motif_phrase_mobility_signatures(source_hypotheses: list[Any]) -> list[str]:
    signatures: set[str] = set()
    for source_hypothesis in source_hypotheses:
        if not isinstance(source_hypothesis, dict):
            continue
        linked_observations = _mapping_optional(source_hypothesis.get("linked_observations"))
        for signature in _string_list(linked_observations.get("transition_motif_phrase_mobility_signatures")):
            signatures.add(signature)
    return sorted(signatures)


def _transition_motif_phrase_family_signature_from_phrase_signature(phrase_signature: str) -> str:
    return "=>".join(
        _transition_motif_family_signature_from_motif_signature(motif_signature)
        for motif_signature in phrase_signature.split("=>")
        if motif_signature
    )


def _transition_motif_phrase_archetype_signature_from_family_signature(family_signature: str) -> str:
    motif_signatures = [motif_signature for motif_signature in family_signature.split("=>") if motif_signature]
    if not motif_signatures:
        return family_signature
    compressed_signatures = [motif_signatures[0]]
    for motif_signature in motif_signatures[1:]:
        if motif_signature != compressed_signatures[-1]:
            compressed_signatures.append(motif_signature)
    return "=>".join(compressed_signatures)


def _transition_motif_phrase_contour_signature_from_archetype_signature(archetype_signature: str) -> str:
    motif_signatures = [motif_signature for motif_signature in archetype_signature.split("=>") if motif_signature]
    if not motif_signatures:
        return archetype_signature

    contour_signatures: list[str] = []
    for motif_signature in motif_signatures:
        parts = motif_signature.split("|")
        if len(parts) == 3:
            contour_signature = f"{parts[0]}|{parts[1]}"
        else:
            contour_signature = motif_signature
        if not contour_signatures or contour_signature != contour_signatures[-1]:
            contour_signatures.append(contour_signature)
    return "=>".join(contour_signatures)


def _transition_motif_phrase_sweep_signature_from_contour_signature(contour_signature: str) -> str:
    contour_tokens = [token for token in contour_signature.split("=>") if token]
    if not contour_tokens:
        return contour_signature

    motion_tokens: list[str] = []
    for contour_token in contour_tokens:
        parts = contour_token.split("|")
        if len(parts) == 2:
            motion_tokens.append(parts[1])
        else:
            motion_tokens.append(contour_token)

    directional_tokens = [token for token in motion_tokens if token != "same_band"]
    if directional_tokens:
        normalized_tokens = directional_tokens
    else:
        normalized_tokens = ["same_band"]

    compressed_tokens: list[str] = []
    for token in normalized_tokens:
        if not compressed_tokens or token != compressed_tokens[-1]:
            compressed_tokens.append(token)
    return "=>".join(compressed_tokens)


def _transition_motif_phrase_gesture_signature_from_sweep_signature(sweep_signature: str) -> str:
    sweep_tokens = [token for token in sweep_signature.split("=>") if token]
    if not sweep_tokens:
        return sweep_signature
    if len(sweep_tokens) == 1:
        if sweep_tokens[0] == "same_band":
            return "steady_band"
        return "single_direction_sweep"
    return "reversing_sweep"


def _transition_motif_phrase_mobility_signature_from_gesture_signature(gesture_signature: str) -> str:
    if gesture_signature == "steady_band":
        return "steady_band_region"
    return "traveling_band_region"


def _transition_motif_family_signature_from_motif_signature(motif_signature: str) -> str:
    parts = motif_signature.split("|")
    if len(parts) != 4:
        return motif_signature
    transition_kind, from_energy_band, to_energy_band, duration_trend = parts
    return "|".join(
        [
            transition_kind,
            _energy_band_motion(from_energy_band, to_energy_band),
            duration_trend,
        ]
    )


def _energy_band_motion(from_energy_band: str, to_energy_band: str) -> str:
    band_rank = {"low": 0, "medium": 1, "high": 2}
    if from_energy_band == to_energy_band:
        return "same_band"
    if from_energy_band in band_rank and to_energy_band in band_rank:
        if band_rank[to_energy_band] > band_rank[from_energy_band]:
            return "rise_band"
        return "fall_band"
    return "shift_band"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _normalized_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalized_cli_string_list(value: list[str] | None) -> list[str]:
    if not value:
        return []
    normalized_items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized:
            normalized_items.append(normalized)
    return normalized_items


def _resolve_auxiliary_format(output_path: Path, *, label: str) -> str:
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    raise ValueError(f"could not infer {label} format from path; use a .json, .yaml, or .yml suffix")


def _write_auxiliary_document(output_path: Path, document: dict[str, Any], report_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "json":
        output_path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return
    output_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _sha256_file(input_path: Path) -> str:
    digest = hashlib.sha256()
    with input_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def _round_float(value: float) -> float:
    return round(float(value), 6)


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None