"""
PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009A

Create the canonical result contract for all UAAF auditors.

This commit creates:
    08_SCRIPTS/uaaf_core/audit/audit_result.py

Existing production modules are not modified.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "uaaf_core"
    / "audit"
    / "audit_result.py"
)

MODULE_SOURCE = '"""\nCanonical audit-result contract for all UAAF auditors.\n\nEvery auditor must return a serializable dictionary produced from\nAuditResult or validated by validate_audit_result().\n"""\n\nfrom __future__ import annotations\n\nfrom dataclasses import asdict, dataclass, field\nfrom enum import Enum\nfrom typing import Any, Mapping\n\n\nclass AuditStatus(str, Enum):\n    """Canonical lifecycle states for an audit execution."""\n\n    COMPLETED = "completed"\n    COMPLETED_WITH_FINDINGS = "completed_with_findings"\n    COMPLETED_WITH_ERRORS = "completed_with_errors"\n    FAILED = "failed"\n\n\nclass FindingSeverity(str, Enum):\n    """Canonical severity levels for audit findings."""\n\n    INFO = "info"\n    WARNING = "warning"\n    ERROR = "error"\n    CRITICAL = "critical"\n\n\n@dataclass(frozen=True, slots=True)\nclass AuditFinding:\n    """One normalized, actionable audit finding."""\n\n    code: str\n    severity: FindingSeverity\n    path: str\n    message: str\n    details: dict[str, Any] = field(default_factory=dict)\n\n    def to_dict(self) -> dict[str, Any]:\n        payload = asdict(self)\n        payload["severity"] = self.severity.value\n        return payload\n\n\n@dataclass(frozen=True, slots=True)\nclass AuditExecution:\n    """Execution metadata shared by every auditor."""\n\n    started_at: str | None = None\n    completed_at: str | None = None\n    duration_ms: int | None = None\n\n    def to_dict(self) -> dict[str, Any]:\n        return asdict(self)\n\n\n@dataclass(frozen=True, slots=True)\nclass AuditResult:\n    """Canonical result returned by every UAAF auditor."""\n\n    plugin_id: str\n    plugin_version: str\n    audit_type: str\n    status: AuditStatus\n    summary: dict[str, Any] = field(default_factory=dict)\n    metrics: dict[str, Any] = field(default_factory=dict)\n    findings: tuple[AuditFinding, ...] = field(default_factory=tuple)\n    errors: tuple[str, ...] = field(default_factory=tuple)\n    execution: AuditExecution = field(default_factory=AuditExecution)\n\n    def to_dict(self) -> dict[str, Any]:\n        payload = {\n            "plugin_id": self.plugin_id,\n            "plugin_version": self.plugin_version,\n            "audit_type": self.audit_type,\n            "status": self.status.value,\n            "summary": dict(self.summary),\n            "metrics": dict(self.metrics),\n            "findings": [\n                finding.to_dict()\n                for finding in self.findings\n            ],\n            "errors": list(self.errors),\n            "execution": self.execution.to_dict(),\n        }\n\n        validate_audit_result(payload)\n        return payload\n\n\ndef validate_audit_result(\n    result: Mapping[str, Any],\n) -> None:\n    """Validate a dictionary against the canonical audit-result contract."""\n    if not isinstance(result, Mapping):\n        raise TypeError("Audit result must be a mapping.")\n\n    required_keys = {\n        "plugin_id",\n        "plugin_version",\n        "audit_type",\n        "status",\n        "summary",\n        "metrics",\n        "findings",\n        "errors",\n        "execution",\n    }\n\n    actual_keys = set(result)\n    missing_keys = required_keys - actual_keys\n    unexpected_keys = actual_keys - required_keys\n\n    if missing_keys:\n        raise ValueError(\n            "Audit result is missing required keys: "\n            f"{sorted(missing_keys)}"\n        )\n\n    if unexpected_keys:\n        raise ValueError(\n            "Audit result contains unexpected keys: "\n            f"{sorted(unexpected_keys)}"\n        )\n\n    _require_non_empty_string(result["plugin_id"], "plugin_id")\n    _require_non_empty_string(\n        result["plugin_version"],\n        "plugin_version",\n    )\n    _require_non_empty_string(result["audit_type"], "audit_type")\n\n    valid_statuses = {status.value for status in AuditStatus}\n    if result["status"] not in valid_statuses:\n        raise ValueError(\n            "Invalid audit status: "\n            f"{result[\'status\']!r}. "\n            f"Expected one of {sorted(valid_statuses)}."\n        )\n\n    if not isinstance(result["summary"], Mapping):\n        raise TypeError("summary must be a mapping.")\n\n    if not isinstance(result["metrics"], Mapping):\n        raise TypeError("metrics must be a mapping.")\n\n    _validate_findings(result["findings"])\n    _validate_errors(result["errors"])\n    _validate_execution(result["execution"])\n\n\ndef _validate_findings(findings: Any) -> None:\n    if not isinstance(findings, list):\n        raise TypeError("findings must be a list.")\n\n    valid_severities = {\n        severity.value\n        for severity in FindingSeverity\n    }\n\n    required_keys = {\n        "code",\n        "severity",\n        "path",\n        "message",\n        "details",\n    }\n\n    for index, finding in enumerate(findings):\n        if not isinstance(finding, Mapping):\n            raise TypeError(\n                f"findings[{index}] must be a mapping."\n            )\n\n        actual_keys = set(finding)\n\n        if actual_keys != required_keys:\n            raise ValueError(\n                f"findings[{index}] must contain exactly "\n                f"{sorted(required_keys)}."\n            )\n\n        _require_non_empty_string(\n            finding["code"],\n            f"findings[{index}].code",\n        )\n        _require_non_empty_string(\n            finding["path"],\n            f"findings[{index}].path",\n        )\n        _require_non_empty_string(\n            finding["message"],\n            f"findings[{index}].message",\n        )\n\n        if finding["severity"] not in valid_severities:\n            raise ValueError(\n                f"Invalid findings[{index}].severity: "\n                f"{finding[\'severity\']!r}."\n            )\n\n        if not isinstance(finding["details"], Mapping):\n            raise TypeError(\n                f"findings[{index}].details must be a mapping."\n            )\n\n\ndef _validate_errors(errors: Any) -> None:\n    if not isinstance(errors, list):\n        raise TypeError("errors must be a list.")\n\n    for index, error in enumerate(errors):\n        _require_non_empty_string(\n            error,\n            f"errors[{index}]",\n        )\n\n\ndef _validate_execution(execution: Any) -> None:\n    if not isinstance(execution, Mapping):\n        raise TypeError("execution must be a mapping.")\n\n    required_keys = {\n        "started_at",\n        "completed_at",\n        "duration_ms",\n    }\n\n    if set(execution) != required_keys:\n        raise ValueError(\n            "execution must contain exactly "\n            f"{sorted(required_keys)}."\n        )\n\n    for key in ("started_at", "completed_at"):\n        value = execution[key]\n        if value is not None and not isinstance(value, str):\n            raise TypeError(\n                f"execution.{key} must be a string or None."\n            )\n\n    duration_ms = execution["duration_ms"]\n    if (\n        duration_ms is not None\n        and (\n            not isinstance(duration_ms, int)\n            or isinstance(duration_ms, bool)\n            or duration_ms < 0\n        )\n    ):\n        raise ValueError(\n            "execution.duration_ms must be a non-negative "\n            "integer or None."\n        )\n\n\ndef _require_non_empty_string(\n    value: Any,\n    field_name: str,\n) -> None:\n    if not isinstance(value, str) or not value.strip():\n        raise ValueError(\n            f"{field_name} must be a non-empty string."\n        )\n\n\n__all__ = [\n    "AuditExecution",\n    "AuditFinding",\n    "AuditResult",\n    "AuditStatus",\n    "FindingSeverity",\n    "validate_audit_result",\n]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    classes = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_classes = {
        "AuditStatus",
        "FindingSeverity",
        "AuditFinding",
        "AuditExecution",
        "AuditResult",
    }
    required_functions = {
        "validate_audit_result",
        "_validate_findings",
        "_validate_errors",
        "_validate_execution",
        "_require_non_empty_string",
    }

    missing_classes = required_classes - classes
    missing_functions = required_functions - functions

    if missing_classes:
        raise RuntimeError(
            "Audit Result Contract is missing classes: "
            f"{', '.join(sorted(missing_classes))}."
        )

    if missing_functions:
        raise RuntimeError(
            "Audit Result Contract is missing functions: "
            f"{', '.join(sorted(missing_functions))}."
        )

    required_fragments = (
        '"plugin_id"',
        '"plugin_version"',
        '"audit_type"',
        '"status"',
        '"summary"',
        '"metrics"',
        '"findings"',
        '"errors"',
        '"execution"',
        '"completed_with_findings"',
        '"critical"',
    )

    missing_fragments = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing_fragments:
        raise RuntimeError(
            "Audit Result Contract is missing fields or values: "
            f"{missing_fragments}"
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    original = (
        TARGET.read_text(encoding="utf-8")
        if TARGET.exists()
        else None
    )

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print(
            "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009A "
            "already applied."
        )
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(MODULE_SOURCE)

        TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        if original is None:
            if TARGET.exists():
                TARGET.unlink()
        else:
            TARGET.write_text(
                original,
                encoding="utf-8",
                newline="",
            )

        print("[ROLLBACK] Original Audit Result Contract restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                f"[ROLLBACK] Backup preserved at: {backup_path}"
            )

        return 1

    print(
        "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009A "
        "applied successfully."
    )
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Canonical AuditResult model created.")
    print("[OK] Canonical AuditFinding model created.")
    print("[OK] Canonical execution metadata created.")
    print("[OK] Audit statuses standardized.")
    print("[OK] Finding severities standardized.")
    print("[OK] Runtime contract validator created.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())