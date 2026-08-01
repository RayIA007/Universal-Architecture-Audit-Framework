"""
UAAF Report Engine — Fase 2.1
Genera reportes Markdown y JSON a partir de un AuditResult canónico.
Determinista, sin dependencias externas.
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

# Import canonical types (best-effort; gracefully degrade to duck typing)
try:
    from uaaf_core.audit.audit_result import (
        AuditResult,
        AuditStatus,
        FindingSeverity,
    )
except Exception:  # pragma: no cover
    AuditResult = None  # type: ignore[misc,assignment]
    AuditStatus = None  # type: ignore[misc,assignment]
    FindingSeverity = None  # type: ignore[misc,assignment]


# Severity display order: highest to lowest impact
_SEVERITY_ORDER = ("critical", "error", "warning", "info")

# Visual severity markers for Markdown
_SEVERITY_MARKERS = {
    "critical": "🔴",
    "error": "🟠",
    "warning": "🟡",
    "info": "🔵",
}


class ReportEngine:
    """
    Deterministic report generator for UAAF AuditResult objects.

    Supports both ``AuditResult`` instances and plain dictionaries that
    conform to the canonical contract.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_markdown(self, result: Any) -> str:
        """Return a professional Markdown report string."""
        data = self._normalize(result)
        lines: list[str] = []

        lines.append(self._header(data))
        lines.append(self._executive_summary(data))
        lines.append(self._metrics_table(data))
        lines.append(self._findings_section(data))
        lines.append(self._execution_metadata(data))
        lines.append(self._footer(data))

        return "\n".join(lines)

    def to_json(self, result: Any, *, indent: int = 2) -> str:
        """Return a pretty-printed JSON serialization of the audit result."""
        data = self._normalize(result)
        return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=False)

    def write_report(
        self,
        result: Any,
        format: str,  # noqa: A002
        output_dir: str | Path | None = None,
    ) -> Path:
        """
        Persist a report to disk.

        Parameters
        ----------
        result:
            ``AuditResult`` instance or canonical dict.
        format:
            ``"markdown"`` | ``"md"`` | ``"json"``.
        output_dir:
            Destination directory. Defaults to ``07_OUTPUTS`` relative to the
            project root inferred from this file's location.

        Returns
        -------
        Path to the written file.
        """
        fmt = self._normalize_format(format)

        data = self._normalize(result)
        file_path = self._build_file_path(data, fmt, output_dir)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "json":
            content = self.to_json(data)
        else:
            content = self.to_markdown(data)

        file_path.write_text(content, encoding="utf-8")
        return file_path

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize(self, result: Any) -> dict[str, Any]:
        """Ensure we have a plain dict conforming to the canonical contract."""
        if AuditResult is not None and isinstance(result, AuditResult):
            return result.to_dict()

        if isinstance(result, Mapping):
            return dict(result)

        raise TypeError(
            f"result must be an AuditResult instance or a mapping, "
            f"got {type(result).__name__}"
        )

    def _normalize_format(self, fmt: str) -> str:
        fmt_lower = fmt.strip().lower()
        if fmt_lower in ("markdown", "md"):
            return "markdown"
        if fmt_lower == "json":
            return "json"
        raise ValueError(f"Unsupported format: {fmt!r}. Use 'markdown' or 'json'.")

    # ------------------------------------------------------------------
    # File naming
    # ------------------------------------------------------------------

    def _build_file_path(
        self,
        data: dict[str, Any],
        fmt: str,
        output_dir: str | Path | None,
    ) -> Path:
        if output_dir is None:
            # Infer project root from this file: 08_SCRIPTS/uaaf_core/reporting/
            project_root = Path(__file__).resolve().parents[3]
            output_dir = project_root / "07_OUTPUTS"

        out = Path(output_dir).resolve()

        plugin_id = self._safe_filename(data.get("plugin_id", "unknown"))
        audit_type = self._safe_filename(data.get("audit_type", "audit"))

        # Timestamp from execution metadata (deterministic — comes from input)
        execution = data.get("execution") or {}
        started_at = execution.get("started_at") or ""
        ts = self._extract_timestamp(started_at)

        ext = "json" if fmt == "json" else "md"
        filename = f"{ts}_{plugin_id}_{audit_type}.{ext}"

        return out / filename

    @staticmethod
    def _safe_filename(value: str) -> str:
        """Sanitize a string for use in a filename."""
        return "".join(c if c.isalnum() or c in "-_." else "_" for c in value).lower()

    @staticmethod
    def _extract_timestamp(iso_string: str) -> str:
        """
        Convert an ISO-8601 string to a compact, filesystem-safe timestamp.
        Falls back to current UTC time if the string is missing/invalid.
        """
        if not iso_string:
            return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        try:
            # Handle 'Z' suffix and fractional seconds
            cleaned = iso_string.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------
    # Markdown builders
    # ------------------------------------------------------------------

    def _header(self, data: dict[str, Any]) -> str:
        plugin_id = data.get("plugin_id", "unknown")
        plugin_version = data.get("plugin_version", "unknown")
        audit_type = data.get("audit_type", "unknown")
        status = data.get("status", "unknown")

        lines = [
            "# UAAF Audit Report",
            "",
            f"| Property | Value |",
            f"|----------|-------|",
            f"| **Plugin** | `{plugin_id}` v{plugin_version} |",
            f"| **Audit Type** | `{audit_type}` |",
            f"| **Status** | `{status}` |",
            "",
        ]
        return "\n".join(lines)

    def _executive_summary(self, data: dict[str, Any]) -> str:
        findings = data.get("findings", [])
        errors = data.get("errors", [])
        metrics = data.get("metrics", {})

        total_findings = len(findings)
        total_errors = len(errors)

        if total_findings == 0 and total_errors == 0:
            summary_text = (
                "✅ **Clean audit.** No findings or errors were detected. "
                "The codebase passed all architecture checks."
            )
        elif total_errors > 0 and total_findings == 0:
            summary_text = (
                f"⚠️ **Audit completed with {total_errors} execution error(s).** "
                f"No structural findings were produced, but the audit "
                f"encountered problems during execution."
            )
        else:
            severity_counts = self._count_by_severity(findings)
            parts = [f"**{total_findings} finding(s)** detected:"]
            for sev in _SEVERITY_ORDER:
                count = severity_counts.get(sev, 0)
                if count:
                    parts.append(f"- {count} {sev.upper()}")
            if total_errors:
                parts.append(f"- Plus {total_errors} execution error(s)")
            summary_text = "  \n".join(parts)

        summary_custom = data.get("summary", {})
        project_path = summary_custom.get("project_path", "N/A")

        lines = [
            "## Executive Summary",
            "",
            f"**Project:** `{project_path}`",
            "",
            summary_text,
            "",
        ]
        return "\n".join(lines)

    def _metrics_table(self, data: dict[str, Any]) -> str:
        metrics = data.get("metrics", {})

        if not metrics:
            return "## Metrics\n\n_No metrics available._\n"

        lines = [
            "## Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]

        # Deterministic ordering: sort keys alphabetically
        for key in sorted(metrics.keys()):
            value = metrics[key]
            # Format numbers with commas; everything else as string
            if isinstance(value, (int, float)):
                display = f"{value:,}" if isinstance(value, int) else f"{value:.2f}"
            else:
                display = str(value)
            lines.append(f"| {key} | {display} |")

        lines.append("")
        return "\n".join(lines)

    def _findings_section(self, data: dict[str, Any]) -> str:
        findings = list(data.get("findings", []))

        if not findings:
            return (
                "## Findings\n\n"
                "_No findings to report. The audit did not detect any "
                "violations in the analyzed codebase._\n"
            )

        # Group by severity in canonical order
        grouped: dict[str, list[dict[str, Any]]] = {s: [] for s in _SEVERITY_ORDER}
        for f in findings:
            sev = str(f.get("severity", "info")).lower()
            grouped.setdefault(sev, []).append(f)

        lines: list[str] = ["## Findings", ""]

        for sev in _SEVERITY_ORDER:
            group = grouped.get(sev, [])
            if not group:
                continue

            marker = _SEVERITY_MARKERS.get(sev, "⚪")
            lines.append(f"### {marker} {sev.upper()} ({len(group)})")
            lines.append("")

            # Sort within group by code, then path for determinism
            sorted_group = sorted(group, key=lambda f: (f.get("code", ""), f.get("path", "")))

            for idx, finding in enumerate(sorted_group, start=1):
                lines.extend(self._render_finding(finding, idx))

        return "\n".join(lines)

    def _render_finding(self, finding: dict[str, Any], index: int) -> list[str]:
        code = finding.get("code", "N/A")
        path = finding.get("path", "N/A")
        message = finding.get("message", "")
        details = finding.get("details", {})

        lines = [
            f"#### {index}. `{code}` — `{path}`",
            "",
            f"{message}",
            "",
        ]

        if details:
            lines.append("<details>")
            lines.append("<summary>Details</summary>")
            lines.append("")
            # Deterministic key ordering
            for key in sorted(details.keys()):
                value = details[key]
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value)
                else:
                    value_str = str(value)
                lines.append(f"- **{key}:** {value_str}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        return lines

    def _execution_metadata(self, data: dict[str, Any]) -> str:
        execution = data.get("execution", {})

        started = execution.get("started_at") or "N/A"
        completed = execution.get("completed_at") or "N/A"
        duration_ms = execution.get("duration_ms")

        duration_str = f"{duration_ms:,} ms" if duration_ms is not None else "N/A"

        lines = [
            "## Execution Metadata",
            "",
            "| Property | Value |",
            "|----------|-------|",
            f"| **Started** | `{started}` |",
            f"| **Completed** | `{completed}` |",
            f"| **Duration** | `{duration_str}` |",
            "",
        ]
        return "\n".join(lines)

    def _footer(self, data: dict[str, Any]) -> str:
        plugin_id = data.get("plugin_id", "unknown")
        plugin_version = data.get("plugin_version", "unknown")
        return (
            f"---\n\n"
            f"*Report generated by UAAF `{plugin_id}` v{plugin_version}*  \n"
            f"*Universal Architecture Audit Framework*"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_by_severity(findings: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in findings:
            sev = str(f.get("severity", "info")).lower()
            counts[sev] = counts.get(sev, 0) + 1
        return counts


# ------------------------------------------------------------------
# Convenience module-level functions
# ------------------------------------------------------------------

_default_engine = ReportEngine()


def to_markdown(result: Any) -> str:
    """Generate a Markdown report (uses the default engine)."""
    return _default_engine.to_markdown(result)


def to_json(result: Any, *, indent: int = 2) -> str:
    """Generate a JSON report (uses the default engine)."""
    return _default_engine.to_json(result, indent=indent)


def write_report(
    result: Any,
    format: str,  # noqa: A002
    output_dir: str | Path | None = None,
) -> Path:
    """Write a report to disk (uses the default engine)."""
    return _default_engine.write_report(result, format, output_dir)


__all__ = [
    "ReportEngine",
    "to_json",
    "to_markdown",
    "write_report",
]