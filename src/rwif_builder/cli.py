from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copyfile
from typing import Any

from .arwif.build import build_arwif_artifact
from .arwif.render import render_arwif_to_wav
from .arwif.validation import validate_arwif_artifact
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
    payload = build_arwif_artifact(Path(args.spec), Path(args.output))
    _print_payload(payload, args.json)
    return 0 if payload["is_valid"] else 1


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
