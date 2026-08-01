"""
Test Suite E — Robustez del Architecture Auditor.

Pruebas deterministas para escenarios extremos, corruptos y de error
en el descubrimiento, parsing y validación del auditor arquitectónico.
"""

from __future__ import annotations

import os
import sys
import unittest.mock as mock
from pathlib import Path

import pytest

# =====================================================================
# BOOTSTRAP
# =====================================================================
_TEST_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _TEST_FILE.parents[2]  # 09_TESTS/unit/ -> project root
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
_PLUGINS_DIR = _PROJECT_ROOT / "plugins"

for _dir in (_SCRIPTS_DIR, _PLUGINS_DIR):
    _s = str(_dir)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from architecture.architecture_auditor import (
    run,
    PLUGIN_ID,
    PLUGIN_VERSION,
    AUDIT_TYPE,
)
from uaaf_core.audit.audit_result import AuditStatus


# =====================================================================
# TESTS — Proyectos vacíos y sin Python
# =====================================================================
class TestEmptyAndEdgeProjects:
    def test_empty_project_completes_without_findings(self, tmp_path: Path):
        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 0
        assert result["metrics"]["module_count"] == 0
        assert result["metrics"]["package_count"] == 0
        assert result["metrics"]["findings_count"] == 0
        assert result["findings"] == []
        assert result["errors"] == []
        assert result["plugin_id"] == PLUGIN_ID
        assert result["plugin_version"] == PLUGIN_VERSION
        assert result["audit_type"] == AUDIT_TYPE

    def test_project_with_only_non_python_files(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Project", encoding="utf-8")
        (tmp_path / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        (tmp_path / "script.sh").write_text("#!/bin/bash\necho hello", encoding="utf-8")

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 0
        assert result["metrics"]["findings_count"] == 0


# =====================================================================
# TESTS — Archivos corruptos (encoding / sintaxis)
# =====================================================================
class TestCorruptFiles:
    def test_invalid_encoding_file_is_skipped_gracefully(self, tmp_path: Path):
        bad_file = tmp_path / "bad_encoding.py"
        bad_file.write_bytes(b"# -*- coding: utf-8 -*-\n\x80\x81\x82\x83\n")

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 1
        # UnicodeDecodeError is caught in _extract_imports → file skipped
        assert result["metrics"]["local_import_count"] == 0
        assert result["metrics"]["dependency_edge_count"] == 0
        assert result["findings"] == []

    def test_invalid_syntax_file_is_skipped_gracefully(self, tmp_path: Path):
        bad_file = tmp_path / "bad_syntax.py"
        bad_file.write_text("def foo(\n    pass\n", encoding="utf-8")

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 1
        # SyntaxError is caught in _extract_imports → file skipped
        assert result["metrics"]["local_import_count"] == 0
        assert result["metrics"]["dependency_edge_count"] == 0
        assert result["findings"] == []

    def test_mixed_valid_and_corrupt_files(self, tmp_path: Path):
        (tmp_path / "valid.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "bad_encoding.py").write_bytes(b"\xff\xfe")
        (tmp_path / "bad_syntax.py").write_text("class (\n", encoding="utf-8")

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 3
        assert result["metrics"]["local_import_count"] == 0
        assert result["metrics"]["findings_count"] == 0


# =====================================================================
# TESTS — Contextos extremos
# =====================================================================
class TestExtremeContexts:
    def test_deeply_nested_paths_exceeding_max_path(self, tmp_path: Path):
        # Build a path that exceeds traditional Windows MAX_PATH (260 chars)
        current = tmp_path
        for i in range(40):
            current = current / f"level_{i:02d}_abcdefghijklmnopqrstuvwxyz"
        current.mkdir(parents=True)

        py_file = current / "deep_module.py"
        py_file.write_text("import os\n", encoding="utf-8")
        assert len(str(py_file)) > 260

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 1

        discovered = result["summary"]["python_files"]
        assert len(discovered) == 1
        assert discovered[0].endswith("deep_module.py")
        assert "/" in discovered[0]  # POSIX normalized
        assert not discovered[0].startswith(str(tmp_path))  # relative

    def test_unicode_file_and_directory_names(self, tmp_path: Path):
        unicode_dir = tmp_path / "módulo_日本語_🐍"
        unicode_dir.mkdir()
        py_file = unicode_dir / "tëst_文件.py"
        py_file.write_text("import os\nimport json\n", encoding="utf-8")

        result = run({"project_path": str(tmp_path)})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 1

        modules = result["summary"]["modules"]
        assert len(modules) == 1
        assert modules[0]["name"] == "módulo_日本語_🐍.tëst_文件"
        assert modules[0]["package"] == "módulo_日本語_🐍"

        imports = result["summary"]["imports"]
        targets = {imp["target"] for imp in imports}
        assert "os" in targets
        assert "json" in targets
        assert all(imp["classification"] == "stdlib" for imp in imports)


# =====================================================================
# TESTS — Permisos y acceso
# =====================================================================
class TestPermissionScenarios:
    def test_denied_directory_in_ignored_list_is_skipped(self, tmp_path: Path):
        """
        Robustez por configuración: un directorio sin permisos que está
        en ignored_directories nunca se intenta leer.
        """
        denied = tmp_path / "denied"
        denied.mkdir()
        (denied / "secret.py").write_text("import sys\n", encoding="utf-8")

        real_scandir = os.scandir

        def fake_scandir(path):
            if "denied" in str(path):
                raise PermissionError(13, "Permission denied", str(path))
            return real_scandir(path)

        with mock.patch("os.scandir", side_effect=fake_scandir):
            result = run({
                "project_path": str(tmp_path),
                "ignored_directories": ["denied"]
            })

        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 0
        assert result["findings"] == []

    def test_unreadable_directory_is_silently_skipped_by_os_walk(self, tmp_path: Path):
        """
        Documenta comportamiento de os.walk: ante PermissionError en scandir,
        omite el directorio silenciosamente (onerror=None). El auditor no ve
        los archivos dentro del directorio denegado y completa sin errores.
        """
        readable = tmp_path / "readable"
        readable.mkdir()
        (readable / "a.py").write_text("import os\n", encoding="utf-8")

        denied = tmp_path / "denied"
        denied.mkdir()
        (denied / "b.py").write_text("import sys\n", encoding="utf-8")

        real_scandir = os.scandir

        def fake_scandir(path):
            if "denied" in str(path):
                raise PermissionError(13, "Permission denied", str(path))
            return real_scandir(path)

        with mock.patch("os.scandir", side_effect=fake_scandir):
            result = run({"project_path": str(tmp_path)})

        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 1
        discovered = result["summary"]["python_files"]
        assert all("denied" not in p for p in discovered)
        assert any("readable/a.py" in p for p in discovered)
        assert result["findings"] == []
        assert result["errors"] == []

    def test_unreadable_file_propagates_permission_error(self, tmp_path: Path):
        """
        Documenta comportamiento actual: si Path.read_text falla con PermissionError,
        el auditor no lo captura y la excepción se propaga.
        (Si se mejora la robustez, actualizar este test.)
        """
        py_file = tmp_path / "secret.py"
        py_file.write_text("import os\n", encoding="utf-8")

        real_read_text = Path.read_text

        def fake_read_text(self, *args, **kwargs):
            if self.resolve() == py_file.resolve():
                raise PermissionError(13, "Permission denied", str(self))
            return real_read_text(self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", fake_read_text):
            with pytest.raises(PermissionError, match="Permission denied"):
                run({"project_path": str(tmp_path)})


# =====================================================================
# TESTS — Contexto malformado (robustez de entrada)
# =====================================================================
class TestMalformedContext:
    def test_context_must_be_dict(self):
        with pytest.raises(TypeError, match="dictionary"):
            run("not_a_dict")

    def test_context_missing_project_path(self):
        with pytest.raises(ValueError, match="project_path"):
            run({})

    def test_context_none_project_path(self):
        with pytest.raises(ValueError, match="project_path"):
            run({"project_path": None})

    def test_context_nonexistent_project_path(self, tmp_path: Path):
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(ValueError, match="project_path"):
            run({"project_path": str(nonexistent)})

    def test_context_unknown_fields(self, tmp_path: Path):
        with pytest.raises(ValueError, match="unknown fields"):
            run({
                "project_path": str(tmp_path),
                "unexpected_key": 123
            })

    def test_context_invalid_ignored_directories_type(self, tmp_path: Path):
        with pytest.raises(ValueError, match="ignored_directories"):
            run({
                "project_path": str(tmp_path),
                "ignored_directories": "not_a_list"
            })

    def test_context_ignored_directories_with_paths(self, tmp_path: Path):
        with pytest.raises(ValueError, match="directory names"):
            run({
                "project_path": str(tmp_path),
                "ignored_directories": ["some/sub/path"]
            })

    def test_context_invalid_layers_type(self, tmp_path: Path):
        with pytest.raises(ValueError, match="layers"):
            run({
                "project_path": str(tmp_path),
                "layers": "not_a_dict"
            })

    def test_context_invalid_forbidden_imports_type(self, tmp_path: Path):
        with pytest.raises(ValueError, match="forbidden_imports"):
            run({
                "project_path": str(tmp_path),
                "forbidden_imports": 12345
            })