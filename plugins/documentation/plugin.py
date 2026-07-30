"""
Functional Documentation Auditor MVP.

The plugin scans a project directory, identifies Markdown files, performs
minimal content-quality checks, and returns a structured audit result.
"""

from __future__ import annotations
from uaaf_core.audit.audit_result import AuditExecution, AuditFinding, AuditResult, AuditStatus, FindingSeverity

from pathlib import Path
from typing import Any


IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
}


def run(context: Any) -> dict[str, Any]:
    """Scan the target project and return a documentation audit."""
    project_path = _resolve_project_path(context)

    files_scanned = 0
    markdown_files: list[str] = []
    empty_markdown_files: list[str] = []
    markdown_files_without_h1: list[str] = []
    findings: list[dict[str, str]] = []
    errors: list[str] = []

    total_lines = 0
    total_words = 0

    for path in project_path.rglob("*"):
        if _is_ignored(path, project_path):
            continue

        if not path.is_file():
            continue

        files_scanned += 1

        if path.suffix.lower() not in {".md", ".markdown"}:
            continue

        relative_path = path.relative_to(project_path).as_posix()

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative_path}: {exc}")
            continue

        markdown_files.append(relative_path)

        stripped_content = content.strip()

        if not stripped_content:
            empty_markdown_files.append(relative_path)
            findings.append(
                _build_finding(
                    code="DOC_EMPTY_FILE",
                    severity="warning",
                    path=relative_path,
                    message="Markdown file is empty.",
                )
            )
            continue

        lines = content.splitlines()
        total_lines += len(lines)
        total_words += len(content.split())

        if not _has_level_one_heading(lines):
            markdown_files_without_h1.append(relative_path)
            findings.append(
                _build_finding(
                    code="DOC_MISSING_H1",
                    severity="warning",
                    path=relative_path,
                    message=(
                        "Markdown file does not contain a level-one heading."
                    ),
                )
            )

    findings_count = len(findings) + len(errors)

    normalized_findings = tuple(
        AuditFinding(
            code=finding["code"],
            severity=FindingSeverity(finding["severity"]),
            path=finding["path"],
            message=finding["message"],
            details={},
        )
        for finding in sorted(
            findings,
            key=lambda item: (item["path"], item["code"]),
        )
    )

    return AuditResult(
        plugin_id="documentation-auditor",
        plugin_version="1.0.0",
        audit_type="documentation",
        status=(
            AuditStatus.COMPLETED_WITH_FINDINGS
            if findings_count
            else AuditStatus.COMPLETED
        ),
        summary={
            "project_path": str(project_path),
            "markdown_files": sorted(markdown_files),
            "empty_markdown_files": sorted(empty_markdown_files),
            "markdown_files_without_h1": sorted(
                markdown_files_without_h1
            ),
        },
        metrics={
            "files_scanned": files_scanned,
            "markdown_file_count": len(markdown_files),
            "total_markdown_lines": total_lines,
            "total_markdown_words": total_words,
            "empty_markdown_file_count": len(empty_markdown_files),
            "markdown_files_without_h1_count": len(
                markdown_files_without_h1
            ),
            "findings_count": findings_count,
        },
        findings=normalized_findings,
        errors=tuple(errors),
        execution=AuditExecution(),
    ).to_dict()


def _resolve_project_path(context: Any) -> Path:
    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary.")

    raw_project_path = context.get("project_path")

    if not isinstance(raw_project_path, (str, Path)):
        raise ValueError(
            "context must contain a valid project_path."
        )

    project_path = Path(raw_project_path).resolve()

    if not project_path.is_dir():
        raise FileNotFoundError(
            f"Project directory not found: {project_path}"
        )

    return project_path


def _is_ignored(path: Path, project_path: Path) -> bool:
    relative_parts = path.relative_to(project_path).parts
    return any(
        part in IGNORED_DIRECTORY_NAMES
        for part in relative_parts
    )


def _has_level_one_heading(lines: list[str]) -> bool:
    return any(
        line.lstrip().startswith("# ")
        for line in lines
    )


def _build_finding(
    *,
    code: str,
    severity: str,
    path: str,
    message: str,
) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "message": message,
    }


class DocumentationAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "DocumentationAuditorPlugin",
    "run",
]
