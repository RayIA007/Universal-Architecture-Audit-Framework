"""
PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009B

Create unit and serialization tests for the canonical Audit Result Contract.

This commit creates:
    08_SCRIPTS/tests/audit_result_contract_test.py

Production modules are not modified.
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
    / "tests"
    / "audit_result_contract_test.py"
)

TEST_SOURCE = '"""\nUnit and serialization tests for the canonical Audit Result Contract.\n"""\n\nfrom __future__ import annotations\n\nimport json\nimport sys\nfrom pathlib import Path\n\n\nSCRIPT_FILE = Path(__file__).resolve()\nPROJECT_ROOT = SCRIPT_FILE.parents[2]\nSCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"\n\nif str(SCRIPTS_ROOT) not in sys.path:\n    sys.path.insert(0, str(SCRIPTS_ROOT))\n\nfrom uaaf_core.audit.audit_result import (\n    AuditExecution,\n    AuditFinding,\n    AuditResult,\n    AuditStatus,\n    FindingSeverity,\n    validate_audit_result,\n)\n\n\ndef main() -> int:\n    result = AuditResult(\n        plugin_id="contract-test-auditor",\n        plugin_version="1.2.3",\n        audit_type="contract-test",\n        status=AuditStatus.COMPLETED_WITH_FINDINGS,\n        summary={\n            "title": "Contract test audit",\n            "finding_count": 1,\n        },\n        metrics={\n            "files_scanned": 3,\n            "rules_executed": 2,\n        },\n        findings=(\n            AuditFinding(\n                code="TEST_FINDING",\n                severity=FindingSeverity.WARNING,\n                path="docs/example.md",\n                message="Example finding.",\n                details={\n                    "line": 7,\n                    "rule": "test-rule",\n                },\n            ),\n        ),\n        errors=(),\n        execution=AuditExecution(\n            started_at="2026-07-29T18:00:00-06:00",\n            completed_at="2026-07-29T18:00:01-06:00",\n            duration_ms=1000,\n        ),\n    )\n\n    payload = result.to_dict()\n\n    _assert_canonical_payload(payload)\n    _assert_json_serialization(payload)\n    _assert_validator_rejections(payload)\n\n    print(payload["plugin_id"])\n    print(payload["plugin_version"])\n    print(payload["audit_type"])\n    print(payload["status"])\n    print(len(payload["findings"]))\n    print(payload["execution"]["duration_ms"])\n    print("[PASS] Audit Result Contract test completed.")\n\n    return 0\n\n\ndef _assert_canonical_payload(\n    payload: dict[str, object],\n) -> None:\n    assert set(payload) == {\n        "plugin_id",\n        "plugin_version",\n        "audit_type",\n        "status",\n        "summary",\n        "metrics",\n        "findings",\n        "errors",\n        "execution",\n    }\n\n    assert payload["plugin_id"] == "contract-test-auditor"\n    assert payload["plugin_version"] == "1.2.3"\n    assert payload["audit_type"] == "contract-test"\n    assert payload["status"] == "completed_with_findings"\n\n    findings = payload["findings"]\n    assert isinstance(findings, list)\n    assert findings == [\n        {\n            "code": "TEST_FINDING",\n            "severity": "warning",\n            "path": "docs/example.md",\n            "message": "Example finding.",\n            "details": {\n                "line": 7,\n                "rule": "test-rule",\n            },\n        }\n    ]\n\n    assert payload["errors"] == []\n    assert payload["execution"] == {\n        "started_at": "2026-07-29T18:00:00-06:00",\n        "completed_at": "2026-07-29T18:00:01-06:00",\n        "duration_ms": 1000,\n    }\n\n    validate_audit_result(payload)\n\n\ndef _assert_json_serialization(\n    payload: dict[str, object],\n) -> None:\n    serialized = json.dumps(\n        payload,\n        ensure_ascii=False,\n        sort_keys=True,\n    )\n    restored = json.loads(serialized)\n\n    assert restored == payload\n    validate_audit_result(restored)\n\n\ndef _assert_validator_rejections(\n    valid_payload: dict[str, object],\n) -> None:\n    invalid_status = _clone(valid_payload)\n    invalid_status["status"] = "unknown"\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        invalid_status,\n    )\n\n    missing_key = _clone(valid_payload)\n    del missing_key["metrics"]\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        missing_key,\n    )\n\n    unexpected_key = _clone(valid_payload)\n    unexpected_key["extra"] = True\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        unexpected_key,\n    )\n\n    invalid_severity = _clone(valid_payload)\n    invalid_severity["findings"][0]["severity"] = "blocker"\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        invalid_severity,\n    )\n\n    missing_finding_field = _clone(valid_payload)\n    del missing_finding_field["findings"][0]["details"]\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        missing_finding_field,\n    )\n\n    invalid_duration = _clone(valid_payload)\n    invalid_duration["execution"]["duration_ms"] = -1\n    _expect_exception(\n        ValueError,\n        validate_audit_result,\n        invalid_duration,\n    )\n\n\ndef _clone(\n    payload: dict[str, object],\n) -> dict[str, object]:\n    return json.loads(json.dumps(payload))\n\n\ndef _expect_exception(\n    exception_type: type[Exception],\n    function: object,\n    argument: object,\n) -> None:\n    try:\n        function(argument)\n    except exception_type:\n        return\n\n    raise AssertionError(\n        f"Expected {exception_type.__name__} was not raised."\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


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

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_functions = {
        "main",
        "_assert_canonical_payload",
        "_assert_json_serialization",
        "_assert_validator_rejections",
        "_clone",
        "_expect_exception",
    }

    missing_functions = required_functions - functions

    if missing_functions:
        raise RuntimeError(
            "Audit Result Contract test is missing functions: "
            f"{', '.join(sorted(missing_functions))}."
        )

    required_fragments = (
        "AuditResult(",
        "AuditFinding(",
        "AuditExecution(",
        "json.dumps",
        "json.loads",
        '"unknown"',
        '"blocker"',
        '"duration_ms"] = -1',
        "[PASS] Audit Result Contract test completed.",
    )

    missing_fragments = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing_fragments:
        raise RuntimeError(
            "Audit Result Contract test is missing checks: "
            f"{missing_fragments}"
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    original = (
        TARGET.read_text(encoding="utf-8")
        if TARGET.exists()
        else None
    )

    if original == TEST_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print(
            "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009B "
            "already applied."
        )
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(TEST_SOURCE)

        TARGET.write_text(
            TEST_SOURCE,
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

        print(
            "[ROLLBACK] Original Audit Result Contract "
            "test restored."
        )
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                f"[ROLLBACK] Backup preserved at: {backup_path}"
            )

        return 1

    print(
        "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009B "
        "applied successfully."
    )
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Canonical payload validated.")
    print("[OK] JSON serialization round-trip covered.")
    print("[OK] Missing fields rejection covered.")
    print("[OK] Unexpected fields rejection covered.")
    print("[OK] Invalid status rejection covered.")
    print("[OK] Invalid severity rejection covered.")
    print("[OK] Invalid execution metadata rejection covered.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())