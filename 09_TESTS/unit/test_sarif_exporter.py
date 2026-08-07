"""Deterministic tests for the UAAF SARIF 2.1.0 exporter."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from uaaf_core.audit.audit_result import (  # noqa: E402
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
)
from uaaf_core.reporting.sarif_exporter import (  # noqa: E402
    SARIF_SCHEMA_URI,
    SARIF_VERSION,
    UAAF_INFORMATION_URI,
    SarifExporter,
    to_sarif,
)


def _result(
    *findings: AuditFinding,
    project_path: str = r"C:\Projects\Demo",
) -> AuditResult:
    return AuditResult(
        plugin_id="uaaf-orchestrator",
        plugin_version="1.0.0",
        audit_type="consolidated",
        status=(
            AuditStatus.COMPLETED_WITH_FINDINGS
            if findings
            else AuditStatus.COMPLETED
        ),
        summary={"project_path": project_path},
        metrics={"findings_count": len(findings)},
        findings=tuple(findings),
        errors=(),
        execution=AuditExecution(
            started_at="2026-08-06T12:00:00+00:00",
            completed_at="2026-08-06T12:00:01+00:00",
            duration_ms=1000,
        ),
    )


def _finding(
    *,
    code: str = "ARCH-COMPLEX-001",
    severity: FindingSeverity = FindingSeverity.WARNING,
    path: str = "src/app.py",
    message: str = "Complexity exceeds the configured threshold.",
    line: object = 12,
    details: dict[str, object] | None = None,
) -> AuditFinding:
    merged: dict[str, object] = {
        "rule": "cyclomatic_complexity",
        "source_plugin_id": "architecture-auditor",
        "source_audit_type": "architecture",
    }
    if line is not None:
        merged["line"] = line
    if details:
        merged.update(details)
    return AuditFinding(
        code=code,
        severity=severity,
        path=path,
        message=message,
        details=merged,
    )


@pytest.fixture
def exporter() -> SarifExporter:
    return SarifExporter()


def test_root_contract(exporter: SarifExporter) -> None:
    document = exporter.to_dict(_result())
    assert document["version"] == SARIF_VERSION == "2.1.0"
    assert document["$schema"] == SARIF_SCHEMA_URI
    assert isinstance(document["runs"], list)
    assert len(document["runs"]) == 1


def test_document_is_strict_json_serializable(exporter: SarifExporter) -> None:
    text = json.dumps(exporter.to_dict(_result()), allow_nan=False)
    assert json.loads(text)["version"] == "2.1.0"


def test_empty_result_has_empty_rules_and_results(exporter: SarifExporter) -> None:
    run = exporter.to_dict(_result())["runs"][0]
    assert run["tool"]["driver"]["rules"] == []
    assert run["results"] == []


def test_tool_driver_uses_uaf_metadata(exporter: SarifExporter) -> None:
    driver = exporter.to_dict(_result())["runs"][0]["tool"]["driver"]
    assert driver["name"] == "UAAF"
    assert driver["version"] == "1.0.0"
    assert driver["informationUri"] == UAAF_INFORMATION_URI


def test_accepts_canonical_mapping(exporter: SarifExporter) -> None:
    document = exporter.to_dict(_result(_finding()).to_dict())
    assert document["runs"][0]["results"][0]["ruleId"] == "ARCH-COMPLEX-001"


def test_rejects_non_result_type(exporter: SarifExporter) -> None:
    with pytest.raises(TypeError, match="AuditResult instance or a mapping"):
        exporter.to_dict("not-a-result")


def test_rejects_invalid_canonical_mapping(exporter: SarifExporter) -> None:
    invalid = _result().to_dict()
    del invalid["plugin_id"]
    with pytest.raises(ValueError, match="missing required keys"):
        exporter.to_dict(invalid)


def test_rules_are_deduplicated_and_sorted(exporter: SarifExporter) -> None:
    findings = (
        _finding(code="Z-002"),
        _finding(code="A-001", severity=FindingSeverity.INFO),
        _finding(code="Z-002", severity=FindingSeverity.ERROR),
    )
    rules = exporter.to_dict(_result(*findings))["runs"][0]["tool"]["driver"]["rules"]
    assert [rule["id"] for rule in rules] == ["A-001", "Z-002"]


def test_rule_uses_highest_observed_severity(exporter: SarifExporter) -> None:
    rules = exporter.to_dict(
        _result(
            _finding(code="X-001", severity=FindingSeverity.INFO),
            _finding(code="X-001", severity=FindingSeverity.CRITICAL),
        )
    )["runs"][0]["tool"]["driver"]["rules"]
    assert rules[0]["defaultConfiguration"]["level"] == "error"


def test_rule_description_comes_from_canonical_rule_detail(exporter: SarifExporter) -> None:
    rule = exporter.to_dict(_result(_finding()))["runs"][0]["tool"]["driver"]["rules"][0]
    assert rule["name"] == "ARCH-COMPLEX-001"
    assert rule["shortDescription"]["text"] == "cyclomatic_complexity"


def test_rule_sources_are_sorted_and_deduplicated(exporter: SarifExporter) -> None:
    first = _finding(
        code="X-001",
        details={"source_plugin_id": "zeta", "source_audit_type": "z"},
    )
    second = _finding(
        code="X-001",
        details={"source_plugin_id": "alpha", "source_audit_type": "a"},
    )
    third = _finding(
        code="X-001",
        details={"source_plugin_id": "alpha", "source_audit_type": "a"},
    )
    rule = exporter.to_dict(_result(first, second, third))["runs"][0]["tool"]["driver"]["rules"][0]
    assert rule["properties"]["sourcePluginIds"] == ["alpha", "zeta"]
    assert rule["properties"]["sourceAuditTypes"] == ["a", "z"]


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (FindingSeverity.CRITICAL, "error"),
        (FindingSeverity.ERROR, "error"),
        (FindingSeverity.WARNING, "warning"),
        (FindingSeverity.INFO, "note"),
    ],
)
def test_severity_mapping(
    exporter: SarifExporter,
    severity: FindingSeverity,
    expected: str,
) -> None:
    result = exporter.to_dict(_result(_finding(severity=severity)))["runs"][0]["results"][0]
    assert result["level"] == expected


def test_result_rule_index_matches_sorted_rules(exporter: SarifExporter) -> None:
    document = exporter.to_dict(
        _result(
            _finding(code="Z-002"),
            _finding(code="A-001"),
        )
    )
    run = document["runs"][0]
    indexes = {rule["id"]: index for index, rule in enumerate(run["tool"]["driver"]["rules"])}
    for result in run["results"]:
        assert result["ruleIndex"] == indexes[result["ruleId"]]


def test_result_message_and_safe_properties(exporter: SarifExporter) -> None:
    result = exporter.to_dict(_result(_finding()))["runs"][0]["results"][0]
    assert result["message"]["text"] == "Complexity exceeds the configured threshold."
    assert result["properties"] == {
        "sourcePluginId": "architecture-auditor",
        "sourceAuditType": "architecture",
        "uaafRule": "cyclomatic_complexity",
    }


@pytest.mark.parametrize(
    ("project_path", "message", "private_fragment"),
    [
        (
            r"C:\Users\Gervasio Robles\project",
            r"Required config not found in 'C:\Users\Gervasio Robles\project'.",
            "Gervasio Robles",
        ),
        (
            "/home/raymundo/project",
            "Required config not found in '/home/raymundo/project'.",
            "/home/raymundo",
        ),
    ],
)
def test_message_redacts_absolute_project_root(
    exporter: SarifExporter,
    project_path: str,
    message: str,
    private_fragment: str,
) -> None:
    finding = _finding(message=message)
    text = exporter.to_json(_result(finding, project_path=project_path))
    result_message = json.loads(text)["runs"][0]["results"][0]["message"]["text"]
    assert result_message == "Required config not found in '<PROJECT_ROOT>'."
    assert private_fragment not in text
    assert "<PROJECT_ROOT>" in text


def test_message_redacts_repr_escaped_windows_project_root(
    exporter: SarifExporter,
) -> None:
    project_path = (
        r"C:\Universal Architecture Audit Framework (UAAF)"
        r"\12_EXAMPLES\sample_project"
    )
    message = (
        "Required config file '.env' not found in project "
        f"{project_path!r}."
    )
    finding = _finding(message=message)
    text = exporter.to_json(_result(finding, project_path=project_path))
    result_message = json.loads(text)["runs"][0]["results"][0]["message"]["text"]
    assert result_message == (
        "Required config file '.env' not found in project '<PROJECT_ROOT>'."
    )
    assert "Universal Architecture Audit Framework" not in text
    assert "C:\\\\" not in text


def test_sensitive_or_arbitrary_details_are_not_exported(exporter: SarifExporter) -> None:
    finding = _finding(
        details={
            "secret": "do-not-export",
            "value": "do-not-export",
            "context": "do-not-export",
            "error": "do-not-export",
            "matched_pattern": "do-not-export",
        }
    )
    text = exporter.to_json(_result(finding))
    assert "do-not-export" not in text
    assert '"secret"' not in text


def test_relative_path_uses_posix_separators(exporter: SarifExporter) -> None:
    result = exporter.to_dict(_result(_finding(path=r"src\package\app.py")))["runs"][0]["results"][0]
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/package/app.py"


def test_windows_absolute_path_inside_project_becomes_relative(exporter: SarifExporter) -> None:
    finding = _finding(path=r"C:\Projects\Demo\src\app.py")
    result = exporter.to_dict(_result(finding))["runs"][0]["results"][0]
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "src/app.py"


def test_windows_absolute_path_outside_project_is_omitted(exporter: SarifExporter) -> None:
    finding = _finding(path=r"C:\Users\Raymundo\secret.py")
    results = exporter.to_dict(_result(finding))["runs"][0]["results"]
    assert results == []


def test_posix_absolute_path_inside_project_becomes_relative(exporter: SarifExporter) -> None:
    finding = _finding(path="/workspace/project/src/app.py")
    result = exporter.to_dict(
        _result(finding, project_path="/workspace/project")
    )["runs"][0]["results"][0]
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "src/app.py"


def test_posix_absolute_path_outside_project_is_omitted(exporter: SarifExporter) -> None:
    finding = _finding(path="/etc/shadow")
    results = exporter.to_dict(
        _result(finding, project_path="/workspace/project")
    )["runs"][0]["results"]
    assert results == []


@pytest.mark.parametrize("path", ["../outside.py", "..", ".", "C:relative.py"])
def test_unsafe_relative_paths_are_omitted(
    exporter: SarifExporter,
    path: str,
) -> None:
    results = exporter.to_dict(_result(_finding(path=path)))["runs"][0]["results"]
    assert results == []


def test_spaces_and_unicode_are_preserved_in_relative_path(exporter: SarifExporter) -> None:
    finding = _finding(path="src/módulo con espacio.py")
    result = exporter.to_dict(_result(finding))["runs"][0]["results"][0]
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "src/módulo con espacio.py"


def test_valid_line_creates_start_line_only(exporter: SarifExporter) -> None:
    result = exporter.to_dict(_result(_finding(line=27)))["runs"][0]["results"][0]
    region = result["locations"][0]["physicalLocation"]["region"]
    assert region == {"startLine": 27}


@pytest.mark.parametrize("line", [None, 0, -1, True, 2.5, "12"])
def test_invalid_line_is_omitted(
    exporter: SarifExporter,
    line: object,
) -> None:
    result = exporter.to_dict(_result(_finding(line=line)))["runs"][0]["results"][0]
    physical = result["locations"][0]["physicalLocation"]
    assert "region" not in physical


def test_finding_without_exportable_location_is_omitted_from_sarif(exporter: SarifExporter) -> None:
    results = exporter.to_dict(
        _result(_finding(path=r"D:\outside\file.py"))
    )["runs"][0]["results"]
    assert results == []


def test_results_are_canonically_sorted(exporter: SarifExporter) -> None:
    findings = (
        _finding(code="Z-001", path="z.py", message="z"),
        _finding(code="A-001", path="b.py", message="b"),
        _finding(code="A-001", path="a.py", message="a"),
    )
    results = exporter.to_dict(_result(*findings))["runs"][0]["results"]
    assert [(item["ruleId"], item["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]) for item in results] == [
        ("A-001", "a.py"),
        ("A-001", "b.py"),
        ("Z-001", "z.py"),
    ]


def test_input_order_does_not_change_output(exporter: SarifExporter) -> None:
    first = _finding(code="Z-001", path="z.py", message="z")
    second = _finding(code="A-001", path="a.py", message="a")
    assert exporter.to_json(_result(first, second)) == exporter.to_json(
        _result(second, first)
    )


def test_same_input_produces_same_output(exporter: SarifExporter) -> None:
    result = _result(_finding())
    assert exporter.to_json(result) == exporter.to_json(result)


def test_content_contains_no_execution_timestamps(exporter: SarifExporter) -> None:
    text = exporter.to_json(_result(_finding()))
    assert "2026-08-06T12:00:00" not in text
    assert "started_at" not in text
    assert "completed_at" not in text


def test_fingerprints_are_intentionally_omitted(exporter: SarifExporter) -> None:
    result = exporter.to_dict(_result(_finding()))["runs"][0]["results"][0]
    assert "partialFingerprints" not in result


def test_unicode_message_serializes_without_ascii_escaping(exporter: SarifExporter) -> None:
    text = exporter.to_json(_result(_finding(message="Método sin documentación.")))
    assert "Método" in text
    assert "\\u00e9" not in text


def test_custom_indent(exporter: SarifExporter) -> None:
    assert '\n    "$schema"' in exporter.to_json(_result(), indent=4)


@pytest.mark.parametrize("indent", [-1, True, 2.5, "2"])
def test_invalid_indent_is_rejected(
    exporter: SarifExporter,
    indent: object,
) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        exporter.to_json(_result(), indent=indent)  # type: ignore[arg-type]


def test_nan_in_non_exported_metrics_does_not_leak(exporter: SarifExporter) -> None:
    data = _result(_finding()).to_dict()
    data["metrics"]["invalid"] = float("nan")
    text = exporter.to_json(data)
    assert "NaN" not in text


def test_module_level_convenience_function() -> None:
    parsed = json.loads(to_sarif(_result(_finding())))
    assert parsed["version"] == "2.1.0"


def test_export_does_not_mutate_mapping(exporter: SarifExporter) -> None:
    data = _result(_finding()).to_dict()
    original = deepcopy(data)
    exporter.to_dict(data)
    assert data == original
