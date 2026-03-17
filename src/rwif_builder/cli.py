from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copyfile
from typing import Any

from . import __version__
from .config.loader import load_config
from .inspect.summary import inspect_artifact
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
    payload = {
        "status": "scaffolded",
        "command": "diff",
        "left": args.left,
        "right": args.right,
        "note": "Artifact diffing is planned but not implemented yet.",
    }
    return _print_payload(payload, args.json)


def handle_patch(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    output_path = args.output or config.output.path
    payload = {
        "status": "scaffolded",
        "command": "patch",
        "project": config.project,
        "base": args.base,
        "output": output_path,
        "note": "Incremental rebuild planning is reserved for the next implementation pass.",
    }
    return _print_payload(payload, args.json)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
