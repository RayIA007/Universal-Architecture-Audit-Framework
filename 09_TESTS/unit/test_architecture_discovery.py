"""
Test Suite B — Descubrimiento e índice del Architecture Auditor.

Pruebas deterministas para:
- _discover_python_files()
- _build_module_index()
- _module_name_from_path()
- _package_name_from_path()
- _normalize_relative_path()
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap paths
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "08_SCRIPTS"
_PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_PLUGINS_DIR))

import pytest
from typing import Any

from architecture.architecture_auditor import (
    _discover_python_files,
    _build_module_index,
    _module_name_from_path,
    _package_name_from_path,
    _normalize_relative_path,
    _DEFAULT_IGNORED_DIRECTORIES,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _make_project(base: Path, structure: dict[str, str]) -> Path:
    """Crea archivos según un dict de {ruta_relativa: contenido}."""
    for rel_path, content in structure.items():
        file_path = base / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return base


# -----------------------------------------------------------------------------
# Tests: _discover_python_files
# -----------------------------------------------------------------------------

class TestDiscoverPythonFiles:
    def test_discovers_root_and_nested_py_files(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "pass",
            "utils/helpers.py": "pass",
            "utils/nested/deep.py": "pass",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert files == ["main.py", "utils/helpers.py", "utils/nested/deep.py"]

    def test_ignores_non_py_files(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "pass",
            "readme.md": "# hi",
            "config.json": "{}",
            "data.csv": "a,b",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert files == ["main.py"]

    def test_ignores_default_excluded_directories(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "pass",
            "__pycache__/cached.cpython-312.pyc": "bin",
            ".venv/lib/site.py": "pass",
            "node_modules/pkg/index.py": "pass",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert files == ["main.py"]

    def test_ignores_custom_excluded_directories(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "src/app.py": "pass",
            "tests/test_app.py": "pass",
            "docs/conf.py": "pass",
        })
        ignored = frozenset(_DEFAULT_IGNORED_DIRECTORIES | {"tests", "docs"})
        files = _discover_python_files(project, ignored)
        assert files == ["src/app.py"]

    def test_deterministic_order(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "z.py": "pass",
            "a.py": "pass",
            "m.py": "pass",
            "sub/b.py": "pass",
            "sub/a.py": "pass",
        })
        run1 = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        run2 = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert run1 == run2
        assert run1 == ["a.py", "m.py", "sub/a.py", "sub/b.py", "z.py"]

    def test_empty_project_returns_empty(self, tmp_path: Path):
        files = _discover_python_files(tmp_path, _DEFAULT_IGNORED_DIRECTORIES)
        assert files == []

    def test_posix_paths_on_windows(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "pkg/module.py": "pass",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert all("/" in f for f in files)
        assert files == ["pkg/module.py"]

    def test_does_not_ignore_hidden_dirs_by_default(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "pass",
            ".hidden/secret.py": "pass",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert ".hidden/secret.py" in files

    def test_ignores_directories_with_no_py_files(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "src/app.py": "pass",
            "assets/logo.png": "bin",
            "assets/style.css": "body{}",
        })
        files = _discover_python_files(project, _DEFAULT_IGNORED_DIRECTORIES)
        assert files == ["src/app.py"]


# -----------------------------------------------------------------------------
# Tests: _build_module_index
# -----------------------------------------------------------------------------

class TestBuildModuleIndex:
    def test_root_module(self):
        modules, packages = _build_module_index(["main.py"])
        assert modules == [
            {
                "name": "main",
                "path": "main.py",
                "package": "",
                "is_package_initializer": False,
            }
        ]
        assert packages == []

    def test_module_in_package(self):
        modules, packages = _build_module_index(["utils/helpers.py"])
        assert modules == [
            {
                "name": "utils.helpers",
                "path": "utils/helpers.py",
                "package": "utils",
                "is_package_initializer": False,
            }
        ]
        assert packages == [
            {
                "name": "utils",
                "path": "utils",
                "modules": ["utils.helpers"],
            }
        ]

    def test_package_initializer(self):
        modules, packages = _build_module_index(["utils/__init__.py"])
        assert modules == [
            {
                "name": "utils",
                "path": "utils/__init__.py",
                "package": "utils",
                "is_package_initializer": True,
            }
        ]
        assert packages == [
            {
                "name": "utils",
                "path": "utils",
                "modules": ["utils"],
            }
        ]

    def test_nested_packages(self):
        files = [
            "app/__init__.py",
            "app/core/__init__.py",
            "app/core/engine.py",
            "app/api/routes.py",
        ]
        modules, packages = _build_module_index(files)

        module_names = {m["name"] for m in modules}
        assert module_names == {"app", "app.core", "app.core.engine", "app.api.routes"}

        package_names = {p["name"] for p in packages}
        assert package_names == {"app", "app.api", "app.core"}

        app_pkg = next(p for p in packages if p["name"] == "app")
        assert app_pkg["modules"] == ["app"]

        core_pkg = next(p for p in packages if p["name"] == "app.core")
        assert core_pkg["modules"] == ["app.core", "app.core.engine"]

    def test_multiple_modules_same_package(self):
        files = ["models/user.py", "models/order.py", "models/__init__.py"]
        modules, packages = _build_module_index(files)

        pkg = next(p for p in packages if p["name"] == "models")
        assert pkg["modules"] == ["models", "models.order", "models.user"]

    def test_deterministic_output_order(self):
        files = ["z.py", "a.py", "b/c.py", "b/a.py"]
        modules1, packages1 = _build_module_index(files)
        modules2, packages2 = _build_module_index(files)
        assert modules1 == modules2
        assert packages1 == packages2
        assert [m["name"] for m in modules1] == ["a", "b.a", "b.c", "z"]


# -----------------------------------------------------------------------------
# Tests: _module_name_from_path
# -----------------------------------------------------------------------------

class TestModuleNameFromPath:
    def test_root_file(self):
        assert _module_name_from_path("main.py") == "main"

    def test_nested_file(self):
        assert _module_name_from_path("utils/helpers.py") == "utils.helpers"

    def test_deeply_nested_file(self):
        assert _module_name_from_path("a/b/c/d.py") == "a.b.c.d"

    def test_init_file(self):
        assert _module_name_from_path("pkg/__init__.py") == "pkg"

    def test_nested_init_file(self):
        assert _module_name_from_path("a/b/__init__.py") == "a.b"


# -----------------------------------------------------------------------------
# Tests: _package_name_from_path
# -----------------------------------------------------------------------------

class TestPackageNameFromPath:
    def test_root_file(self):
        assert _package_name_from_path("main.py") == ""

    def test_nested_file(self):
        assert _package_name_from_path("utils/helpers.py") == "utils"

    def test_deeply_nested_file(self):
        assert _package_name_from_path("a/b/c/d.py") == "a.b.c"

    def test_init_file(self):
        assert _package_name_from_path("pkg/__init__.py") == "pkg"

    def test_nested_init_file(self):
        assert _package_name_from_path("a/b/__init__.py") == "a.b"


# -----------------------------------------------------------------------------
# Tests: _normalize_relative_path
# -----------------------------------------------------------------------------

class TestNormalizeRelativePath:
    def test_simple_file(self, tmp_path: Path):
        project = tmp_path / "proj"
        project.mkdir()
        file_path = project / "main.py"
        file_path.write_text("pass")
        assert _normalize_relative_path(file_path, project) == "main.py"

    def test_nested_file(self, tmp_path: Path):
        project = tmp_path / "proj"
        project.mkdir()
        file_path = project / "utils" / "helpers.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("pass")
        assert _normalize_relative_path(file_path, project) == "utils/helpers.py"