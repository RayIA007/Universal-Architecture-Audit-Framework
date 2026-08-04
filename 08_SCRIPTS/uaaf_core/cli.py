"""Command-line interface for the UAAF unified orchestrator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from uaaf_core.orchestrator import (
    DEFAULT_OUTPUT_FORMATS,
    UnifiedOrchestrator,
    merge_exclusions,
    normalize_fail_on,
    normalize_output_formats,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the public UAAF command-line parser."""
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description=(
            "Discover and execute UAAF auditor plugins, then generate a "
            "consolidated Markdown and/or JSON report."
        ),
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Project directory to audit. Default: current directory.",
    )
    parser.add_argument(
        "--auditors",
        default="all",
        help=(
            "Comma-separated auditor names, audit types, or plugin IDs. "
            "Use 'all' to execute every discovered plugin."
        ),
    )
    parser.add_argument(
        "--output-formats",
        default=",".join(DEFAULT_OUTPUT_FORMATS),
        help="Comma-separated report formats: markdown,json.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional .yaml, .yml, .json, or .toml configuration file.",
    )
    parser.add_argument(
        "--fail-on",
        default="",
        help="Comma-separated finding severities that produce exit code 1.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIRECTORIES",
        help=(
            "Additional directory names to ignore. May be repeated or supplied "
            "as a comma-separated list."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Report destination. Default: <UAAF_ROOT>/07_OUTPUTS.",
    )
    parser.add_argument(
        "--plugins-dir",
        default=None,
        help="Plugin directory override, primarily for isolated deployments/tests.",
    )
    parser.add_argument(
        "--framework-root",
        default=None,
        help="UAAF framework root override. Default: inferred from uaaf_core.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse and normalize CLI arguments without executing an audit."""
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        args.output_formats = normalize_output_formats(args.output_formats)
        args.fail_on = normalize_fail_on(args.fail_on)
        args.exclude = merge_exclusions(args.exclude)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the unified UAAF CLI and return a process exit code."""
    args = parse_args(argv)
    try:
        orchestrator = UnifiedOrchestrator(
            framework_root=args.framework_root,
            plugins_dir=args.plugins_dir,
        )
        result = orchestrator.run(
            project_path=Path(args.project_path),
            auditors=args.auditors,
            output_formats=args.output_formats,
            config_path=args.config,
            fail_on=args.fail_on,
            exclude=args.exclude,
            output_dir=args.output_dir,
        )
    except Exception as error:
        print(f"UAAF error: {error}", file=sys.stderr)
        return 2

    consolidated = result.consolidated_result
    metrics = consolidated["metrics"]
    print(
        "UAAF audit completed: "
        f"{metrics['auditor_count']} auditor(s), "
        f"{metrics['findings_count']} finding(s)."
    )
    for report_path in result.report_paths:
        print(f"Report: {report_path}")
    return result.exit_code


__all__ = ["create_parser", "main", "parse_args"]