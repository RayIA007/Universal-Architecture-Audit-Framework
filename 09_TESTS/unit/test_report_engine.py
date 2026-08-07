"""
Test Suite G: Report Engine — Fase 2.1
Deterministic tests for Markdown/JSON generation and file I/O.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Bootstrap
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pytest

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
)
from uaaf_core.reporting.report_engine import ReportEngine


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def engine() -> ReportEngine:
    return ReportEngine()


@pytest.fixture
def empty_result() -> AuditResult:
    return AuditResult(
        plugin_id="test-plugin",
        plugin_version="1.0.0",
        audit_type="test",
        status=AuditStatus.COMPLETED,
        summary={"project_path": "/tmp/demo"},
        metrics={"files_scanned": 42},
        findings=(),
        errors=(),
        execution=AuditExecution(
            started_at="2026-08-01T10:00:00+00:00",
            completed_at="2026-08-01T10:00:05+00:00",
            duration_ms=5000,
        ),
    )


@pytest.fixture
def result_with_findings() -> AuditResult:
    return AuditResult(
        plugin_id="architecture-auditor",
        plugin_version="1.5.1",
        audit_type="architecture",
        status=AuditStatus.COMPLETED_WITH_FINDINGS,
        summary={"project_path": "/home/user/project"},
        metrics={
            "python_file_count": 10,
            "module_count": 8,
            "findings_count": 4,
        },
        findings=(
            AuditFinding(
                code="ARCH-CYCLE-001",
                severity=FindingSeverity.ERROR,
                path="module_a",
                message="Circular dependency detected: module_a -> module_b -> module_a",
                details={"cycle_nodes": ["module_a", "module_b"], "rule": "dependency_cycle"},
            ),
            AuditFinding(
                code="ARCH-LAYER-001",
                severity=FindingSeverity.WARNING,
                path="infra.db",
                message="Layer violation detected.",
                details={"source_layer": "infra", "target_layer": "domain", "rule": "layer_violation"},
            ),
            AuditFinding(
                code="ARCH-FORBIDDEN-001",
                severity=FindingSeverity.ERROR,
                path="app.main",
                message="Forbidden import detected.",
                details={"target": "banned.lib", "rule": "forbidden_import"},
            ),
            AuditFinding(
                code="ARCH-INIT-001",
                severity=FindingSeverity.WARNING,
                path="utils",
                message="Missing __init__.py.",
                details={"package": "utils", "rule": "missing_package_initializer"},
            ),
        ),
        errors=(),
        execution=AuditExecution(
            started_at="2026-08-01T12:30:00+00:00",
            completed_at="2026-08-01T12:30:02+00:00",
            duration_ms=2345,
        ),
    )


@pytest.fixture
def result_with_errors_only() -> AuditResult:
    return AuditResult(
        plugin_id="test-plugin",
        plugin_version="1.0.0",
        audit_type="test",
        status=AuditStatus.COMPLETED_WITH_ERRORS,
        summary={"project_path": "/tmp/demo"},
        metrics={},
        findings=(),
        errors=("Disk full during scan", "Permission denied on /etc/shadow"),
        execution=AuditExecution(
            started_at="2026-08-01T11:00:00+00:00",
            completed_at="2026-08-01T11:00:01+00:00",
            duration_ms=1000,
        ),
    )


# =====================================================================
# Normalization & Validation
# =====================================================================

def test_normalize_accepts_dict(engine: ReportEngine) -> None:
    data = {
        "plugin_id": "p",
        "plugin_version": "1",
        "audit_type": "t",
        "status": "completed",
        "summary": {},
        "metrics": {},
        "findings": [],
        "errors": [],
        "execution": {"started_at": None, "completed_at": None, "duration_ms": None},
    }
    normalized = engine._normalize(data)
    assert normalized == data


def test_normalize_accepts_audit_result_instance(engine: ReportEngine, empty_result: AuditResult) -> None:
    normalized = engine._normalize(empty_result)
    assert normalized["plugin_id"] == "test-plugin"
    assert normalized["status"] == "completed"


def test_normalize_rejects_invalid_type(engine: ReportEngine) -> None:
    with pytest.raises(TypeError):
        engine._normalize("not a result")


def test_normalize_format_markdown(engine: ReportEngine) -> None:
    assert engine._normalize_format("markdown") == "markdown"
    assert engine._normalize_format("md") == "markdown"
    assert engine._normalize_format("  MD  ") == "markdown"


def test_normalize_format_json(engine: ReportEngine) -> None:
    assert engine._normalize_format("json") == "json"
    assert engine._normalize_format("  JSON  ") == "json"


def test_normalize_format_invalid(engine: ReportEngine) -> None:
    with pytest.raises(ValueError):
        engine._normalize_format("xml")


# =====================================================================
# File path construction
# =====================================================================

def test_build_file_path_defaults(engine: ReportEngine, empty_result: AuditResult) -> None:
    data = empty_result.to_dict()
    path = engine._build_file_path(data, "markdown", None)
    assert path.name.startswith("20260801_100000_")
    assert path.name.endswith("_test-plugin_test.md")
    assert "07_OUTPUTS" in path.as_posix()


def test_build_file_path_custom_dir(engine: ReportEngine, empty_result: AuditResult) -> None:
    data = empty_result.to_dict()
    with tempfile.TemporaryDirectory() as tmpdir:
        custom = Path(tmpdir) / "uaaf_reports"
        path = engine._build_file_path(data, "json", custom)
        # Use resolve() to normalize Windows 8.3 vs long path names
        assert path.parent.resolve() == custom.resolve()
        assert path.suffix == ".json"


def test_safe_filename(engine: ReportEngine) -> None:
    assert engine._safe_filename("My Plugin!") == "my_plugin_"
    assert engine._safe_filename("v1.2.3") == "v1.2.3"


def test_extract_timestamp_valid(engine: ReportEngine) -> None:
    assert engine._extract_timestamp("2026-08-01T15:30:45+00:00") == "20260801_153045"


def test_extract_timestamp_with_z(engine: ReportEngine) -> None:
    assert engine._extract_timestamp("2026-08-01T15:30:45Z") == "20260801_153045"


def test_extract_timestamp_empty_fallback(engine: ReportEngine) -> None:
    result = engine._extract_timestamp("")
    assert len(result) == 15  # YYYYMMDD_HHMMSS


# =====================================================================
# Markdown generation
# =====================================================================

def test_markdown_contains_header(engine: ReportEngine, empty_result: AuditResult) -> None:
    md = engine.to_markdown(empty_result)
    assert "# UAAF Audit Report" in md
    assert "`test-plugin` v1.0.0" in md
    assert "`test`" in md


def test_markdown_empty_findings_shows_clean_message(engine: ReportEngine, empty_result: AuditResult) -> None:
    md = engine.to_markdown(empty_result)
    assert "Clean audit" in md
    assert "No findings to report" in md


def test_markdown_metrics_table(engine: ReportEngine, empty_result: AuditResult) -> None:
    md = engine.to_markdown(empty_result)
    assert "## Metrics" in md
    assert "files_scanned" in md
    assert "42" in md


def test_markdown_execution_metadata(engine: ReportEngine, empty_result: AuditResult) -> None:
    md = engine.to_markdown(empty_result)
    assert "## Execution Metadata" in md
    assert "2026-08-01T10:00:00+00:00" in md
    assert "5,000 ms" in md


def test_markdown_grouped_by_severity(engine: ReportEngine, result_with_findings: AuditResult) -> None:
    md = engine.to_markdown(result_with_findings)

    error_pos = md.find("ERROR")
    warning_pos = md.find("WARNING")
    assert error_pos != -1
    assert warning_pos != -1
    assert error_pos < warning_pos

    assert "ARCH-CYCLE-001" in md
    assert "ARCH-FORBIDDEN-001" in md
    assert "ARCH-LAYER-001" in md
    assert "ARCH-INIT-001" in md


def test_markdown_finding_details_collapsible(engine: ReportEngine, result_with_findings: AuditResult) -> None:
    md = engine.to_markdown(result_with_findings)
    assert "<details>" in md
    assert "<summary>Details</summary>" in md


def test_markdown_errors_only_result(engine: ReportEngine, result_with_errors_only: AuditResult) -> None:
    md = engine.to_markdown(result_with_errors_only)
    assert "execution error" in md


def test_markdown_footer_present(engine: ReportEngine, empty_result: AuditResult) -> None:
    md = engine.to_markdown(empty_result)
    assert "Universal Architecture Audit Framework" in md


# =====================================================================
# JSON generation
# =====================================================================

def test_json_pretty_printed(engine: ReportEngine, empty_result: AuditResult) -> None:
    json_str = engine.to_json(empty_result)
    parsed = json.loads(json_str)
    assert parsed["plugin_id"] == "test-plugin"


def test_json_custom_indent(engine: ReportEngine, empty_result: AuditResult) -> None:
    json_2 = engine.to_json(empty_result, indent=2)
    json_4 = engine.to_json(empty_result, indent=4)
    # Verify that indent=4 uses deeper indentation than indent=2
    assert '\n  "plugin_id"' in json_2
    assert '\n    "plugin_id"' in json_4


def test_json_contains_all_fields(engine: ReportEngine, result_with_findings: AuditResult) -> None:
    json_str = engine.to_json(result_with_findings)
    parsed = json.loads(json_str)
    assert "findings" in parsed
    assert len(parsed["findings"]) == 4
    assert parsed["status"] == "completed_with_findings"


# =====================================================================
# Determinism
# =====================================================================

def test_markdown_is_deterministic(engine: ReportEngine, result_with_findings: AuditResult) -> None:
    md1 = engine.to_markdown(result_with_findings)
    md2 = engine.to_markdown(result_with_findings)
    assert md1 == md2


def test_json_is_deterministic(engine: ReportEngine, result_with_findings: AuditResult) -> None:
    j1 = engine.to_json(result_with_findings)
    j2 = engine.to_json(result_with_findings)
    assert j1 == j2


def test_same_dict_produces_same_markdown(engine: ReportEngine) -> None:
    data = {
        "plugin_id": "p",
        "plugin_version": "1",
        "audit_type": "t",
        "status": "completed",
        "summary": {"project_path": "/tmp"},
        "metrics": {"a": 1},
        "findings": [],
        "errors": [],
        "execution": {"started_at": "2026-01-01T00:00:00Z", "completed_at": None, "duration_ms": None},
    }
    md1 = engine.to_markdown(data)
    md2 = engine.to_markdown(data)
    assert md1 == md2


# =====================================================================
# File I/O
# =====================================================================

def test_write_report_markdown(engine: ReportEngine, empty_result: AuditResult) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine.write_report(empty_result, "markdown", tmpdir)
        assert path.exists()
        assert path.suffix == ".md"
        content = path.read_text(encoding="utf-8")
        assert "# UAAF Audit Report" in content


def test_write_report_json(engine: ReportEngine, empty_result: AuditResult) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine.write_report(empty_result, "json", tmpdir)
        assert path.exists()
        assert path.suffix == ".json"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert parsed["plugin_id"] == "test-plugin"


def test_write_report_creates_parent_dirs(engine: ReportEngine, empty_result: AuditResult) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir) / "a" / "b" / "c"
        path = engine.write_report(empty_result, "markdown", nested)
        assert path.exists()


def test_write_report_filename_contains_expected_parts(engine: ReportEngine, empty_result: AuditResult) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine.write_report(empty_result, "markdown", tmpdir)
        name = path.name
        assert "test-plugin" in name
        assert "test" in name
        assert name.endswith(".md")


# =====================================================================
# Edge cases
# =====================================================================

def test_empty_metrics(engine: ReportEngine) -> None:
    result = AuditResult(
        plugin_id="p",
        plugin_version="1",
        audit_type="t",
        status=AuditStatus.COMPLETED,
        summary={},
        metrics={},
        findings=(),
        errors=(),
        execution=AuditExecution(),
    )
    md = engine.to_markdown(result)
    assert "No metrics available" in md


def test_finding_without_details(engine: ReportEngine) -> None:
    result = AuditResult(
        plugin_id="p",
        plugin_version="1",
        audit_type="t",
        status=AuditStatus.COMPLETED_WITH_FINDINGS,
        summary={},
        metrics={},
        findings=(
            AuditFinding(
                code="X-001",
                severity=FindingSeverity.INFO,
                path="foo.py",
                message="Just a note.",
                details={},
            ),
        ),
        errors=(),
        execution=AuditExecution(),
    )
    md = engine.to_markdown(result)
    assert "Just a note." in md
    assert "<details>" not in md


def test_module_level_convenience_functions(empty_result: AuditResult) -> None:
    from uaaf_core.reporting.report_engine import to_markdown, to_json, write_report

    md = to_markdown(empty_result)
    assert "# UAAF Audit Report" in md

    j = to_json(empty_result)
    assert json.loads(j)["plugin_id"] == "test-plugin"

    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_report(empty_result, "json", tmpdir)
        assert path.exists()

# =====================================================================
# SARIF generation — Fase 3.5
# =====================================================================


def test_normalize_format_sarif(engine: ReportEngine) -> None:
    assert engine._normalize_format("sarif") == "sarif"
    assert engine._normalize_format("  SARIF  ") == "sarif"


def test_build_file_path_sarif(engine: ReportEngine, empty_result: AuditResult) -> None:
    data = empty_result.to_dict()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine._build_file_path(data, "sarif", tmpdir)
        assert path.suffix == ".sarif"
        assert path.name.endswith("_test-plugin_test.sarif")


def test_to_sarif_generates_valid_root(
    engine: ReportEngine,
    result_with_findings: AuditResult,
) -> None:
    parsed = json.loads(engine.to_sarif(result_with_findings))
    assert parsed["version"] == "2.1.0"
    assert len(parsed["runs"]) == 1
    assert len(parsed["runs"][0]["results"]) == 4


def test_write_report_sarif(engine: ReportEngine, empty_result: AuditResult) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine.write_report(empty_result, "sarif", tmpdir)
        assert path.exists()
        assert path.suffix == ".sarif"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert parsed["version"] == "2.1.0"


def test_module_level_to_sarif(empty_result: AuditResult) -> None:
    from uaaf_core.reporting.report_engine import to_sarif

    parsed = json.loads(to_sarif(empty_result))
    assert parsed["runs"][0]["tool"]["driver"]["name"] == "UAAF"
