from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copyfile
from typing import Any

from .arwif.build import build_arwif_artifact
from .arwif.batch import batch_normalize_arwif_artifacts
from .arwif.diff import diff_arwif_artifacts
from .arwif.export import export_arwif_artifact
from .arwif.importing import import_arwif_artifact
from .arwif.inspect import inspect_arwif_artifact
from .arwif.normalize import normalize_arwif_artifact
from .arwif.render import render_arwif_to_wav
from .arwif.validation import validate_arwif_artifact
from .arwif.validation import validate_arwif_spec
from . import __version__
from .config.loader import load_config
from .diffing import diff_artifacts
from .inspect.summary import inspect_artifact
from .patching import patch_artifact
from .pipeline import build_artifact
from .validator.structure import validate_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rwif", description="RWIF artifact builder CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a starter rwif.yaml file")
    init_parser.add_argument("--template", default="docs", help="Starter template name")
    init_parser.add_argument("--output", default="rwif.yaml", help="Destination config path")
    init_parser.set_defaults(handler=handle_init)

    build_parser = subparsers.add_parser("build", help="Build an RWIF artifact")
    build_parser.add_argument("--config", default="rwif.yaml", help="Path to config file")
    build_parser.add_argument("--output", required=False, help="Override output artifact path")
    build_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    build_parser.set_defaults(handler=handle_build)

    validate_parser = subparsers.add_parser("validate", help="Validate an existing RWIF artifact")
    validate_parser.add_argument("artifact", help="Path to .rwif artifact")
    validate_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    validate_parser.set_defaults(handler=handle_validate)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect an existing RWIF artifact")
    inspect_parser.add_argument("artifact", help="Path to .rwif artifact")
    inspect_parser.add_argument("--summary", action="store_true", help="Show summary output")
    inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    inspect_parser.set_defaults(handler=handle_inspect)

    stats_parser = subparsers.add_parser("stats", help="Show artifact metrics")
    stats_parser.add_argument("artifact", help="Path to .rwif artifact")
    stats_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    stats_parser.set_defaults(handler=handle_stats)

    diff_parser = subparsers.add_parser("diff", help="Compare two RWIF artifacts")
    diff_parser.add_argument("left", help="First artifact path")
    diff_parser.add_argument("right", help="Second artifact path")
    diff_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    diff_parser.set_defaults(handler=handle_diff)

    patch_parser = subparsers.add_parser("patch", help="Plan or execute an incremental rebuild")
    patch_parser.add_argument("--config", default="rwif.yaml", help="Path to config file")
    patch_parser.add_argument("--base", required=True, help="Base artifact path")
    patch_parser.add_argument("--output", required=False, help="Override output artifact path")
    patch_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    patch_parser.set_defaults(handler=handle_patch)

    arwif_build_parser = subparsers.add_parser("arwif-build", help="Build an ARWIF artifact from a YAML or JSON spec")
    arwif_build_parser.add_argument("--spec", required=True, help="Path to an ARWIF build spec")
    arwif_build_parser.add_argument("--output", required=True, help="Destination .arwif path")
    arwif_build_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_build_parser.set_defaults(handler=handle_arwif_build)

    arwif_validate_spec_parser = subparsers.add_parser("arwif-validate-spec", help="Validate an ARWIF YAML or JSON source spec")
    arwif_validate_spec_parser.add_argument("spec", help="Path to an ARWIF source spec")
    arwif_validate_spec_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_validate_spec_parser.set_defaults(handler=handle_arwif_validate_spec)

    arwif_import_parser = subparsers.add_parser("arwif-import", help="Import an ARWIF YAML or JSON spec into an artifact")
    arwif_import_parser.add_argument("--spec", required=True, help="Path to an ARWIF import spec")
    arwif_import_parser.add_argument("--output", required=True, help="Destination .arwif path")
    arwif_import_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_import_parser.set_defaults(handler=handle_arwif_import)

    arwif_export_parser = subparsers.add_parser("arwif-export", help="Export an ARWIF artifact to a YAML or JSON spec")
    arwif_export_parser.add_argument("artifact", help="Path to .arwif artifact")
    arwif_export_parser.add_argument("output", help="Destination .yaml, .yml, or .json path")
    arwif_export_parser.add_argument("--format", choices=("yaml", "json"), help="Override export format")
    arwif_export_parser.add_argument("--legacy", action="store_true", help="Allow pre-spec prototype files")
    arwif_export_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_export_parser.set_defaults(handler=handle_arwif_export)

    arwif_normalize_parser = subparsers.add_parser(
        "arwif-normalize",
        help="Normalize a legacy or strict ARWIF artifact into a strict source spec and optional rebuilt artifact",
    )
    arwif_normalize_parser.add_argument("artifact", help="Path to .arwif artifact")
    arwif_normalize_parser.add_argument("--spec", required=True, help="Destination .yaml, .yml, or .json spec path")
    arwif_normalize_parser.add_argument("--output", help="Optional destination for a rebuilt strict .arwif artifact")
    arwif_normalize_parser.add_argument("--report", help="Optional destination .json, .yaml, or .yml normalization report path")
    arwif_normalize_parser.add_argument("--assumptions", help="Optional destination .json, .yaml, or .yml assumptions manifest path")
    arwif_normalize_parser.add_argument("--format", choices=("yaml", "json"), help="Override normalized spec format")
    arwif_normalize_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_normalize_parser.set_defaults(handler=handle_arwif_normalize)

    arwif_batch_normalize_parser = subparsers.add_parser(
        "arwif-batch-normalize",
        help="Normalize multiple ARWIF artifacts into strict source specs and optional auxiliary outputs",
    )
    arwif_batch_normalize_parser.add_argument("artifacts", nargs="+", help="Paths to .arwif artifacts")
    arwif_batch_normalize_parser.add_argument("--spec-dir", required=True, help="Destination directory for normalized specs")
    arwif_batch_normalize_parser.add_argument("--output-dir", help="Optional destination directory for rebuilt strict .arwif artifacts")
    arwif_batch_normalize_parser.add_argument("--report-dir", help="Optional destination directory for normalization reports")
    arwif_batch_normalize_parser.add_argument(
        "--assumptions-dir",
        help="Optional destination directory for assumptions manifests",
    )
    arwif_batch_normalize_parser.add_argument("--format", choices=("yaml", "json"), help="Override normalized spec format")
    arwif_batch_normalize_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_batch_normalize_parser.set_defaults(handler=handle_arwif_batch_normalize)

    arwif_inspect_parser = subparsers.add_parser("arwif-inspect", help="Inspect an ARWIF audio artifact")
    arwif_inspect_parser.add_argument("artifact", help="Path to .arwif artifact")
    arwif_inspect_parser.add_argument("--legacy", action="store_true", help="Allow pre-spec prototype files")
    arwif_inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_inspect_parser.set_defaults(handler=handle_arwif_inspect)

    arwif_diff_parser = subparsers.add_parser("arwif-diff", help="Compare two ARWIF audio artifacts")
    arwif_diff_parser.add_argument("left", help="First .arwif artifact path")
    arwif_diff_parser.add_argument("right", help="Second .arwif artifact path")
    arwif_diff_parser.add_argument("--legacy", action="store_true", help="Allow pre-spec prototype files")
    arwif_diff_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_diff_parser.set_defaults(handler=handle_arwif_diff)

    arwif_validate_parser = subparsers.add_parser("arwif-validate", help="Validate an ARWIF audio artifact")
    arwif_validate_parser.add_argument("artifact", help="Path to .arwif artifact")
    arwif_validate_parser.add_argument("--legacy", action="store_true", help="Allow pre-spec prototype files")
    arwif_validate_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_validate_parser.set_defaults(handler=handle_arwif_validate)

    arwif_render_parser = subparsers.add_parser("arwif-render", help="Render an ARWIF artifact to PCM WAV")
    arwif_render_parser.add_argument("artifact", help="Path to .arwif artifact")
    arwif_render_parser.add_argument("output", help="Destination .wav path")
    arwif_render_parser.add_argument("--legacy", action="store_true", help="Allow pre-spec prototype files")
    arwif_render_parser.add_argument("--sample-rate", type=int, help="Override output sample rate")
    arwif_render_parser.add_argument("--duration", type=float, help="Override default segment duration in seconds")
    arwif_render_parser.add_argument("--no-normalize", action="store_true", help="Disable peak normalization")
    arwif_render_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    arwif_render_parser.set_defaults(handler=handle_arwif_render)

    return parser


def _print_payload(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


def _print_error_payload(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        summary = payload.get("message") or "operation failed"
        print(summary)
        for key in ("errors", "warnings"):
            values = payload.get(key)
            if isinstance(values, list):
                for value in values:
                    print(f"{key[:-1]}: {value}")
    return 1


def handle_init(args: argparse.Namespace) -> int:
    template_name = args.template
    if template_name != "docs":
        raise SystemExit(f"unsupported template: {template_name}")

    template_path = Path(__file__).resolve().parents[2] / "rwif.yaml.example"
    output_path = Path(args.output)
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite existing file: {output_path}")

    copyfile(template_path, output_path)
    print(f"created starter config at {output_path}")
    return 0


def handle_build(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    payload = build_artifact(config, output_override=args.output)
    return _print_payload(payload, args.json)


def handle_validate(args: argparse.Namespace) -> int:
    report = validate_artifact(Path(args.artifact))
    _print_payload(report.to_payload(), args.json)
    return 0 if report.is_valid else 1


def handle_inspect(args: argparse.Namespace) -> int:
    payload = inspect_artifact(Path(args.artifact))
    return _print_payload(payload, args.json)


def handle_stats(args: argparse.Namespace) -> int:
    payload = inspect_artifact(Path(args.artifact))
    return _print_payload(payload, args.json)


def handle_diff(args: argparse.Namespace) -> int:
    payload = diff_artifacts(args.left, args.right)
    return _print_payload(payload, args.json)


def handle_patch(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    payload = patch_artifact(config, base=args.base, output_override=args.output)
    return _print_payload(payload, args.json)


def handle_arwif_build(args: argparse.Namespace) -> int:
    try:
        payload = build_arwif_artifact(Path(args.spec), Path(args.output))
    except ValueError as exc:
        spec_report = validate_arwif_spec(Path(args.spec))
        return _print_error_payload(
            {
                "artifact": str(Path(args.output)),
                "spec": str(Path(args.spec)),
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            },
            args.json,
        )
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


def handle_arwif_validate_spec(args: argparse.Namespace) -> int:
    report = validate_arwif_spec(Path(args.spec))
    _print_payload(report.to_payload(), args.json)
    return 0 if report.is_valid else 1


def handle_arwif_import(args: argparse.Namespace) -> int:
    try:
        payload = import_arwif_artifact(Path(args.spec), Path(args.output))
    except ValueError as exc:
        spec_report = validate_arwif_spec(Path(args.spec))
        return _print_error_payload(
            {
                "artifact": str(Path(args.output)),
                "spec": str(Path(args.spec)),
                "imported": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(spec_report.errors) or [str(exc)],
                "warnings": list(spec_report.warnings),
                "stats": dict(spec_report.stats),
            },
            args.json,
        )
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


def handle_arwif_export(args: argparse.Namespace) -> int:
    payload = export_arwif_artifact(
        Path(args.artifact),
        Path(args.output),
        format=args.format,
        allow_legacy=args.legacy,
    )
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


def handle_arwif_normalize(args: argparse.Namespace) -> int:
    try:
        payload = normalize_arwif_artifact(
            Path(args.artifact),
            Path(args.spec),
            output=Path(args.output) if args.output else None,
            report=Path(args.report) if args.report else None,
            assumptions=Path(args.assumptions) if args.assumptions else None,
            format=args.format,
        )
    except ValueError as exc:
        source_report = validate_arwif_artifact(Path(args.artifact), allow_legacy=True)
        return _print_error_payload(
            {
                "artifact": str(Path(args.artifact)),
                "spec_output": str(Path(args.spec)),
                "output": str(Path(args.output)) if args.output else None,
                "report_output": str(Path(args.report)) if args.report else None,
                "assumptions_output": str(Path(args.assumptions)) if args.assumptions else None,
                "normalized": False,
                "is_valid": False,
                "message": str(exc),
                "errors": list(source_report.errors) or [str(exc)],
                "warnings": list(source_report.warnings),
                "stats": dict(source_report.stats),
            },
            args.json,
        )
    _print_payload(payload, args.json)
    return 0 if payload.get("output_is_valid", True) else 1


def handle_arwif_batch_normalize(args: argparse.Namespace) -> int:
    payload = batch_normalize_arwif_artifacts(
        [Path(artifact) for artifact in args.artifacts],
        Path(args.spec_dir),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        report_dir=Path(args.report_dir) if args.report_dir else None,
        assumptions_dir=Path(args.assumptions_dir) if args.assumptions_dir else None,
        format=args.format,
    )
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


def handle_arwif_inspect(args: argparse.Namespace) -> int:
    payload = inspect_arwif_artifact(Path(args.artifact), allow_legacy=args.legacy)
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


def handle_arwif_diff(args: argparse.Namespace) -> int:
    payload = diff_arwif_artifacts(Path(args.left), Path(args.right), allow_legacy=args.legacy)
    _print_payload(payload, args.json)
    return 0 if payload["left_valid"] and payload["right_valid"] else 1


def handle_arwif_validate(args: argparse.Namespace) -> int:
    report = validate_arwif_artifact(Path(args.artifact), allow_legacy=args.legacy)
    _print_payload(report.to_payload(), args.json)
    return 0 if report.is_valid else 1


def handle_arwif_render(args: argparse.Namespace) -> int:
    payload = render_arwif_to_wav(
        Path(args.artifact),
        Path(args.output),
        allow_legacy=args.legacy,
        sample_rate_override=args.sample_rate,
        duration_override=args.duration,
        normalize_override=False if args.no_normalize else None,
    )
    return _print_payload(payload, args.json)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
