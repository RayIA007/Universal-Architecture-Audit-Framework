"""
Unit and serialization tests for the canonical Audit Result Contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)


def main() -> int:
    result = AuditResult(
        plugin_id="contract-test-auditor",
        plugin_version="1.2.3",
        audit_type="contract-test",
        status=AuditStatus.COMPLETED_WITH_FINDINGS,
        summary={
            "title": "Contract test audit",
            "finding_count": 1,
        },
        metrics={
            "files_scanned": 3,
            "rules_executed": 2,
        },
        findings=(
            AuditFinding(
                code="TEST_FINDING",
                severity=FindingSeverity.WARNING,
                path="docs/example.md",
                message="Example finding.",
                details={
                    "line": 7,
                    "rule": "test-rule",
                },
            ),
        ),
        errors=(),
        execution=AuditExecution(
            started_at="2026-07-29T18:00:00-06:00",
            completed_at="2026-07-29T18:00:01-06:00",
            duration_ms=1000,
        ),
    )

    payload = result.to_dict()

    _assert_canonical_payload(payload)
    _assert_json_serialization(payload)
    _assert_validator_rejections(payload)

    print(payload["plugin_id"])
    print(payload["plugin_version"])
    print(payload["audit_type"])
    print(payload["status"])
    print(len(payload["findings"]))
    print(payload["execution"]["duration_ms"])
    print("[PASS] Audit Result Contract test completed.")

    return 0


def _assert_canonical_payload(
    payload: dict[str, object],
) -> None:
    assert set(payload) == {
        "plugin_id",
        "plugin_version",
        "audit_type",
        "status",
        "summary",
        "metrics",
        "findings",
        "errors",
        "execution",
    }

    assert payload["plugin_id"] == "contract-test-auditor"
    assert payload["plugin_version"] == "1.2.3"
    assert payload["audit_type"] == "contract-test"
    assert payload["status"] == "completed_with_findings"

    findings = payload["findings"]
    assert isinstance(findings, list)
    assert findings == [
        {
            "code": "TEST_FINDING",
            "severity": "warning",
            "path": "docs/example.md",
            "message": "Example finding.",
            "details": {
                "line": 7,
                "rule": "test-rule",
            },
        }
    ]

    assert payload["errors"] == []
    assert payload["execution"] == {
        "started_at": "2026-07-29T18:00:00-06:00",
        "completed_at": "2026-07-29T18:00:01-06:00",
        "duration_ms": 1000,
    }

    validate_audit_result(payload)


def _assert_json_serialization(
    payload: dict[str, object],
) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
    )
    restored = json.loads(serialized)

    assert restored == payload
    validate_audit_result(restored)


def _assert_validator_rejections(
    valid_payload: dict[str, object],
) -> None:
    invalid_status = _clone(valid_payload)
    invalid_status["status"] = "unknown"
    _expect_exception(
        ValueError,
        validate_audit_result,
        invalid_status,
    )

    missing_key = _clone(valid_payload)
    del missing_key["metrics"]
    _expect_exception(
        ValueError,
        validate_audit_result,
        missing_key,
    )

    unexpected_key = _clone(valid_payload)
    unexpected_key["extra"] = True
    _expect_exception(
        ValueError,
        validate_audit_result,
        unexpected_key,
    )

    invalid_severity = _clone(valid_payload)
    invalid_severity["findings"][0]["severity"] = "blocker"
    _expect_exception(
        ValueError,
        validate_audit_result,
        invalid_severity,
    )

    missing_finding_field = _clone(valid_payload)
    del missing_finding_field["findings"][0]["details"]
    _expect_exception(
        ValueError,
        validate_audit_result,
        missing_finding_field,
    )

    invalid_duration = _clone(valid_payload)
    invalid_duration["execution"]["duration_ms"] = -1
    _expect_exception(
        ValueError,
        validate_audit_result,
        invalid_duration,
    )


def _clone(
    payload: dict[str, object],
) -> dict[str, object]:
    return json.loads(json.dumps(payload))


def _expect_exception(
    exception_type: type[Exception],
    function: object,
    argument: object,
) -> None:
    try:
        function(argument)
    except exception_type:
        return

    raise AssertionError(
        f"Expected {exception_type.__name__} was not raised."
    )


if __name__ == "__main__":
    raise SystemExit(main())
