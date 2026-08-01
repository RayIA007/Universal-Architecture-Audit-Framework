"""
Test Suite A — Contrato y configuración del Architecture Auditor.

Pruebas deterministas para:
- project_path válido e inválido
- audit_type correcto e incorrecto
- campos desconocidos en context
- tipos inválidos en configuraciones
- valores predeterminados
- serialización exacta de AuditResult
- validate_audit_result() pasa
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap paths (mismo patrón que usa el plugin)
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "08_SCRIPTS"
_PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_PLUGINS_DIR))

import pytest
from typing import Any

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from architecture.architecture_auditor import (
    run,
    _validate_context,
    _validate_ignored_directories,
    _DEFAULT_IGNORED_DIRECTORIES,
    AUDIT_TYPE,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Crea un directorio de proyecto temporal mínimo."""
    (tmp_path / "main.py").write_text("pass\n")
    utils_dir = tmp_path / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)
    (utils_dir / "helpers.py").write_text("pass\n")
    return tmp_path


@pytest.fixture
def valid_context(temp_project: Path) -> dict[str, Any]:
    """Retorna un contexto mínimo válido para el auditor."""
    return {
        "project_path": str(temp_project),
        "audit_type": AUDIT_TYPE,
    }


# -----------------------------------------------------------------------------
# Tests: project_path
# -----------------------------------------------------------------------------

class TestProjectPath:
    def test_valid_project_path_as_string(self, temp_project: Path):
        context = {"project_path": str(temp_project), "audit_type": AUDIT_TYPE}
        result = run(context)
        assert result["summary"]["project_path"] == str(temp_project)

    def test_valid_project_path_as_path_object(self, temp_project: Path):
        context = {"project_path": temp_project, "audit_type": AUDIT_TYPE}
        result = run(context)
        assert result["summary"]["project_path"] == str(temp_project)

    def test_invalid_project_path_not_exists(self):
        context = {"project_path": "/nonexistent/path/12345", "audit_type": AUDIT_TYPE}
        with pytest.raises(ValueError, match="project_path must reference an existing directory"):
            run(context)

    def test_invalid_project_path_is_file(self, tmp_path: Path):
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("hello")
        context = {"project_path": str(file_path), "audit_type": AUDIT_TYPE}
        with pytest.raises(ValueError, match="project_path must reference an existing directory"):
            run(context)

    def test_invalid_project_path_none(self):
        context = {"project_path": None, "audit_type": AUDIT_TYPE}
        with pytest.raises(ValueError, match="context must contain a valid project_path"):
            run(context)

    def test_invalid_project_path_int(self):
        context = {"project_path": 42, "audit_type": AUDIT_TYPE}
        with pytest.raises(ValueError, match="context must contain a valid project_path"):
            run(context)

    def test_missing_project_path(self):
        context = {"audit_type": AUDIT_TYPE}
        with pytest.raises(ValueError, match="context must contain a valid project_path"):
            run(context)


# -----------------------------------------------------------------------------
# Tests: audit_type
# -----------------------------------------------------------------------------

class TestAuditType:
    def test_correct_audit_type(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        assert result["audit_type"] == AUDIT_TYPE

    def test_none_audit_type_uses_default(self, temp_project: Path):
        context = {"project_path": str(temp_project)}
        result = run(context)
        assert result["audit_type"] == AUDIT_TYPE

    def test_incorrect_audit_type(self, temp_project: Path):
        context = {"project_path": str(temp_project), "audit_type": "security"}
        with pytest.raises(ValueError, match="audit_type must be"):
            run(context)

    def test_empty_audit_type(self, temp_project: Path):
        context = {"project_path": str(temp_project), "audit_type": ""}
        with pytest.raises(ValueError, match="audit_type must be"):
            run(context)


# -----------------------------------------------------------------------------
# Tests: campos desconocidos en context
# -----------------------------------------------------------------------------

class TestUnknownFields:
    def test_single_unknown_field_raises(self, valid_context: dict[str, Any]):
        valid_context["unknown_field"] = "value"
        with pytest.raises(ValueError, match="context contains unknown fields"):
            run(valid_context)

    def test_multiple_unknown_fields_raises(self, valid_context: dict[str, Any]):
        valid_context["foo"] = 1
        valid_context["bar"] = 2
        with pytest.raises(ValueError, match="context contains unknown fields"):
            run(valid_context)

    def test_all_known_fields_accepted(self, tmp_path: Path):
        project = tmp_path / "clean_proj"
        project.mkdir()
        (project / "main.py").write_text("pass\n")
        utils_dir = project / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")   # ← evita finding
        (utils_dir / "helpers.py").write_text("pass\n")

        context = {
            "project_path": str(project),
            "audit_type": AUDIT_TYPE,
            "ignored_directories": [".git"],
            "forbidden_imports": [],
            "layers": {"order": ["domain"], "mapping": {"domain": ["*"]}},
            "require_package_initializers": True,
        }
        result = run(context)
        assert result["status"] == "completed"
        assert result["findings"] == []


# -----------------------------------------------------------------------------
# Tests: tipos inválidos en configuraciones
# -----------------------------------------------------------------------------

class TestInvalidTypes:
    def test_ignored_directories_not_collection(self, valid_context: dict[str, Any]):
        valid_context["ignored_directories"] = "not_a_list"
        with pytest.raises(ValueError, match="ignored_directories must be a collection"):
            run(valid_context)

    def test_ignored_directories_entry_not_string(self, valid_context: dict[str, Any]):
        valid_context["ignored_directories"] = [".git", 42]
        with pytest.raises(ValueError, match="ignored_directories entries must be non-empty strings"):
            run(valid_context)

    def test_ignored_directories_entry_empty_string(self, valid_context: dict[str, Any]):
        valid_context["ignored_directories"] = [""]
        with pytest.raises(ValueError, match="ignored_directories entries must be non-empty strings"):
            run(valid_context)

    def test_ignored_directories_entry_is_path(self, valid_context: dict[str, Any]):
        valid_context["ignored_directories"] = ["some/path"]
        with pytest.raises(ValueError, match="ignored_directories entries must be directory names"):
            run(valid_context)

    def test_context_not_dict(self):
        with pytest.raises(TypeError, match="context must be a dictionary"):
            run("not_a_dict")

    def test_context_none(self):
        with pytest.raises(TypeError, match="context must be a dictionary"):
            run(None)


# -----------------------------------------------------------------------------
# Tests: valores predeterminados
# -----------------------------------------------------------------------------

class TestDefaultValues:
    def test_default_ignored_directories_contains_expected(self):
        assert ".git" in _DEFAULT_IGNORED_DIRECTORIES
        assert "__pycache__" in _DEFAULT_IGNORED_DIRECTORIES
        assert ".venv" in _DEFAULT_IGNORED_DIRECTORIES
        assert "venv" in _DEFAULT_IGNORED_DIRECTORIES
        assert "node_modules" in _DEFAULT_IGNORED_DIRECTORIES

    def test_default_findings_empty(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        assert result["findings"] == []

    def test_default_errors_empty(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        assert result["errors"] == []

    def test_default_execution_fields_populated(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        assert isinstance(result["execution"]["started_at"], str)
        assert isinstance(result["execution"]["completed_at"], str)
        assert isinstance(result["execution"]["duration_ms"], int)
        assert result["execution"]["duration_ms"] >= 0

    def test_default_metrics_populated(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        # Proyecto temporal: main.py + utils/helpers.py
        assert result["metrics"]["python_file_count"] == 2
        assert result["metrics"]["module_count"] == 2
        assert result["metrics"]["package_count"] == 1  # utils
        assert result["metrics"]["local_import_count"] == 0
        assert result["metrics"]["dependency_edge_count"] == 0
        assert result["metrics"]["circular_dependency_count"] == 0
        assert result["metrics"]["forbidden_import_count"] == 0
        assert result["metrics"]["layer_violation_count"] == 0
        assert result["metrics"]["missing_package_initializer_count"] == 0
        assert result["metrics"]["findings_count"] == 0

    def test_default_summary_populated(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        assert len(result["summary"]["modules"]) == 2
        assert len(result["summary"]["packages"]) == 1
        assert result["summary"]["dependency_cycles"] == []
        assert result["summary"]["python_files"] == ["main.py", "utils/helpers.py"]


# -----------------------------------------------------------------------------
# Tests: serialización exacta de AuditResult
# -----------------------------------------------------------------------------

class TestAuditResultSerialization:
    def test_empty_result_exact_serialization(self):
        result = AuditResult(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            audit_type="architecture",
            status=AuditStatus.COMPLETED,
        ).to_dict()

        assert result == {
            "plugin_id": "test-plugin",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }

    def test_result_with_finding_exact_serialization(self):
        finding = AuditFinding(
            code="ARCH-TEST-001",
            severity=FindingSeverity.WARNING,
            path="src/module.py",
            message="Test message",
            details={"key": "value"},
        )
        result = AuditResult(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            audit_type="architecture",
            status=AuditStatus.COMPLETED_WITH_FINDINGS,
            summary={"count": 1},
            metrics={"files": 5},
            findings=(finding,),
            errors=("minor glitch",),
            execution=AuditExecution(
                started_at="2026-07-31T22:00:00Z",
                completed_at="2026-07-31T22:01:00Z",
                duration_ms=60000,
            ),
        ).to_dict()

        assert result == {
            "plugin_id": "test-plugin",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed_with_findings",
            "summary": {"count": 1},
            "metrics": {"files": 5},
            "findings": [
                {
                    "code": "ARCH-TEST-001",
                    "severity": "warning",
                    "path": "src/module.py",
                    "message": "Test message",
                    "details": {"key": "value"},
                }
            ],
            "errors": ["minor glitch"],
            "execution": {
                "started_at": "2026-07-31T22:00:00Z",
                "completed_at": "2026-07-31T22:01:00Z",
                "duration_ms": 60000,
            },
        }

    def test_finding_is_frozen(self):
        finding = AuditFinding(
            code="ARCH-001",
            severity=FindingSeverity.ERROR,
            path="a.py",
            message="msg",
        )
        with pytest.raises(AttributeError):
            finding.code = "NEW"

    def test_audit_result_is_frozen(self):
        result = AuditResult(
            plugin_id="p",
            plugin_version="1",
            audit_type="t",
            status=AuditStatus.COMPLETED,
        )
        with pytest.raises(AttributeError):
            result.plugin_id = "new"


# -----------------------------------------------------------------------------
# Tests: validate_audit_result() pasa
# -----------------------------------------------------------------------------

class TestValidateAuditResult:
    def test_valid_minimal_result_passes(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        validate_audit_result(payload)  # no debe lanzar

    def test_valid_result_with_findings_passes(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed_with_findings",
            "summary": {"total": 10},
            "metrics": {"files": 5},
            "findings": [
                {
                    "code": "ARCH-001",
                    "severity": "error",
                    "path": "src/a.py",
                    "message": "Cycle detected",
                    "details": {"cycle": ["a", "b"]},
                }
            ],
            "errors": [],
            "execution": {
                "started_at": "2026-07-31T22:00:00Z",
                "completed_at": "2026-07-31T22:01:00Z",
                "duration_ms": 60000,
            },
        }
        validate_audit_result(payload)  # no debe lanzar

    def test_run_output_passes_validation(self, valid_context: dict[str, Any]):
        result = run(valid_context)
        validate_audit_result(result)  # no debe lanzar

    def test_missing_key_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            # execution intencionalmente omitido
        }
        with pytest.raises(ValueError, match="missing required keys"):
            validate_audit_result(payload)

    def test_extra_key_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
            "extra": "value",
        }
        with pytest.raises(ValueError, match="unexpected keys"):
            validate_audit_result(payload)

    def test_invalid_status_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "done",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        with pytest.raises(ValueError, match="Invalid audit status"):
            validate_audit_result(payload)

    def test_empty_plugin_id_fails(self):
        payload = {
            "plugin_id": "",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        with pytest.raises(ValueError, match="plugin_id must be a non-empty string"):
            validate_audit_result(payload)

    def test_invalid_finding_severity_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [
                {
                    "code": "ARCH-001",
                    "severity": "urgent",
                    "path": "a.py",
                    "message": "msg",
                    "details": {},
                }
            ],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        with pytest.raises(ValueError, match="Invalid findings"):
            validate_audit_result(payload)

    def test_finding_missing_key_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [
                {
                    "code": "ARCH-001",
                    "severity": "error",
                    "path": "a.py",
                    "message": "msg",
                    # details intencionalmente omitido
                }
            ],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        with pytest.raises(ValueError, match=r"findings\[0\] must contain exactly"):
            validate_audit_result(payload)

    def test_negative_duration_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": -1,
            },
        }
        with pytest.raises(ValueError, match="duration_ms must be a non-negative"):
            validate_audit_result(payload)

    def test_bool_duration_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": True,
            },
        }
        with pytest.raises(ValueError, match="duration_ms must be a non-negative"):
            validate_audit_result(payload)

    def test_non_string_error_fails(self):
        payload = {
            "plugin_id": "p",
            "plugin_version": "1.0.0",
            "audit_type": "architecture",
            "status": "completed",
            "summary": {},
            "metrics": {},
            "findings": [],
            "errors": [42],
            "execution": {
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
            },
        }
        with pytest.raises(ValueError, match=r"errors\[0\] must be a non-empty string"):
            validate_audit_result(payload)

    def test_non_mapping_result_fails(self):
        with pytest.raises(TypeError, match="Audit result must be a mapping"):
            validate_audit_result("not_a_dict")