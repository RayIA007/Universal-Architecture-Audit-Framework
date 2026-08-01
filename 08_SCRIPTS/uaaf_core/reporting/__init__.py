"""UAAF Reporting package — Fase 2.1 (Report Engine)."""

from .report_engine import (
    ReportEngine,
    to_json,
    to_markdown,
    write_report,
)

__all__ = [
    "ReportEngine",
    "to_json",
    "to_markdown",
    "write_report",
]