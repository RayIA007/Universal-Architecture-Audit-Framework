"""
Test Suite C — Imports y grafo del Architecture Auditor.

Pruebas deterministas para:
- _extract_imports()
- _classify_import()
- _resolve_relative_import()
- Clasificación: stdlib / third_party / local / unknown
- Imports absolutos vs relativos
- Detección de edges locales
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
    _extract_imports,
    _classify_import,
    _resolve_relative_import,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _make_project(base: Path, structure: dict[str, str]) -> Path:
    for rel_path, content in structure.items():
        file_path = base / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return base


# -----------------------------------------------------------------------------
# Tests: _classify_import
# -----------------------------------------------------------------------------

class TestClassifyImport:
    def test_local_module_exact_match(self):
        local_mods = {"utils", "models.user"}
        local_pkgs = {"app"}
        stdlib = {"os", "json"}
        assert _classify_import("utils", local_mods, local_pkgs, stdlib) == "local"
        assert _classify_import("models.user", local_mods, local_pkgs, stdlib) == "local"

    def test_local_package_exact_match(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = {"os"}
        assert _classify_import("app", local_mods, local_pkgs, stdlib) == "local"

    def test_local_submodule_prefix(self):
        local_mods = {"utils.helpers"}
        local_pkgs = set()
        stdlib = {"os"}
        assert _classify_import("utils", local_mods, local_pkgs, stdlib) == "local"

    def test_local_subpackage_prefix(self):
        local_mods = set()
        local_pkgs = {"app.core"}
        stdlib = {"os"}
        assert _classify_import("app", local_mods, local_pkgs, stdlib) == "local"

    def test_stdlib_import(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = {"os", "json", "sys"}
        assert _classify_import("os", local_mods, local_pkgs, stdlib) == "stdlib"
        assert _classify_import("json", local_mods, local_pkgs, stdlib) == "stdlib"

    def test_stdlib_submodule(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = {"os", "json"}
        assert _classify_import("os.path", local_mods, local_pkgs, stdlib) == "stdlib"

    def test_third_party_import(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = {"os", "json"}
        assert _classify_import("requests", local_mods, local_pkgs, stdlib) == "third_party"
        assert _classify_import("numpy", local_mods, local_pkgs, stdlib) == "third_party"

    def test_third_party_submodule(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = {"os"}
        assert _classify_import("requests.auth", local_mods, local_pkgs, stdlib) == "third_party"

    def test_empty_target(self):
        assert _classify_import("", set(), set(), set()) == "unknown"

    def test_unknown_when_no_stdlib_match(self):
        local_mods = {"utils"}
        local_pkgs = {"app"}
        stdlib = set()
        assert _classify_import("something", local_mods, local_pkgs, stdlib) == "third_party"


# -----------------------------------------------------------------------------
# Tests: _resolve_relative_import
# -----------------------------------------------------------------------------

class TestResolveRelativeImport:
    def test_relative_from_root_module_level_1(self):
        result = _resolve_relative_import("main", 1, None, {"main", "utils"})
        assert result == []

    def test_relative_from_nested_module_level_1(self):
        result = _resolve_relative_import("app.core.engine", 1, None, {"app.core", "app.core.engine"})
        assert result == ["app.core"]

    def test_relative_from_nested_module_level_1_with_module(self):
        result = _resolve_relative_import("app.core.engine", 1, "models", {"app.core.models"})
        assert result == ["app.core.models"]

    def test_relative_from_init_level_1(self):
        result = _resolve_relative_import("app.core.__init__", 1, None, {"app.core"})
        assert result == ["app.core"]

    def test_relative_level_2(self):
        result = _resolve_relative_import("a.b.c", 2, None, {"a"})
        assert result == ["a"]

    def test_relative_level_2_with_module(self):
        result = _resolve_relative_import("a.b.c", 2, "utils", {"a.utils"})
        assert result == ["a.utils"]

    def test_relative_too_deep_returns_empty(self):
        result = _resolve_relative_import("a", 2, None, {"a"})
        assert result == []

    def test_relative_from_root_level_1_returns_empty(self):
        result = _resolve_relative_import("main", 1, "utils", {"utils"})
        assert result == []


# -----------------------------------------------------------------------------
# Tests: _extract_imports — absolutos
# -----------------------------------------------------------------------------

class TestExtractImportsAbsolute:
    def test_import_statement(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "import os\nimport requests\n",
        })
        modules = [{"name": "main", "path": "main.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["main.py"], project, modules, packages)

        targets = {imp["target"] for imp in imports}
        assert "os" in targets
        assert "requests" in targets

        # os es stdlib, requests es third_party → ningún edge local
        assert edges == []

    def test_from_import_statement(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "from json import loads\nfrom numpy import array\n",
        })
        modules = [{"name": "main", "path": "main.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["main.py"], project, modules, packages)

        json_imp = next(imp for imp in imports if imp["target"] == "json")
        assert json_imp["classification"] == "stdlib"

        numpy_imp = next(imp for imp in imports if imp["target"] == "numpy")
        assert numpy_imp["classification"] == "third_party"

    def test_local_import_creates_edge(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "import utils\n",
            "utils.py": "pass\n",
        })
        modules = [
            {"name": "main", "path": "main.py", "package": "", "is_package_initializer": False},
            {"name": "utils", "path": "utils.py", "package": "", "is_package_initializer": False},
        ]
        packages = []
        imports, edges = _extract_imports(["main.py", "utils.py"], project, modules, packages)

        local_imp = next(imp for imp in imports if imp["target"] == "utils")
        assert local_imp["classification"] == "local"
        assert ("main", "utils") in edges


# -----------------------------------------------------------------------------
# Tests: _extract_imports — relativos
# -----------------------------------------------------------------------------

class TestExtractImportsRelative:
    def test_relative_import_from_module(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "app/__init__.py": "",
            "app/core.py": "from . import utils\n",
            "app/utils.py": "pass\n",
        })
        modules = [
            {"name": "app", "path": "app/__init__.py", "package": "app", "is_package_initializer": True},
            {"name": "app.core", "path": "app/core.py", "package": "app", "is_package_initializer": False},
            {"name": "app.utils", "path": "app/utils.py", "package": "app", "is_package_initializer": False},
        ]
        packages = [{"name": "app", "path": "app", "modules": ["app", "app.core", "app.utils"]}]
        imports, edges = _extract_imports(
            ["app/__init__.py", "app/core.py", "app/utils.py"], project, modules, packages
        )

        rel_imp = next(imp for imp in imports if imp["type"] == "relative")
        assert rel_imp["source"] == "app.core"
        assert rel_imp["classification"] == "local"
        assert ("app.core", "app") in edges

    def test_relative_import_with_module(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from .b import func\n",
            "pkg/b.py": "def func(): pass\n",
        })
        modules = [
            {"name": "pkg", "path": "pkg/__init__.py", "package": "pkg", "is_package_initializer": True},
            {"name": "pkg.a", "path": "pkg/a.py", "package": "pkg", "is_package_initializer": False},
            {"name": "pkg.b", "path": "pkg/b.py", "package": "pkg", "is_package_initializer": False},
        ]
        packages = [{"name": "pkg", "path": "pkg", "modules": ["pkg", "pkg.a", "pkg.b"]}]
        imports, edges = _extract_imports(
            ["pkg/__init__.py", "pkg/a.py", "pkg/b.py"], project, modules, packages
        )

        rel_imp = next(imp for imp in imports if imp["type"] == "relative" and imp.get("module") == "b")
        assert rel_imp["classification"] == "local"
        assert ("pkg.a", "pkg.b") in edges


# -----------------------------------------------------------------------------
# Tests: _extract_imports — robustez
# -----------------------------------------------------------------------------

class TestExtractImportsRobustness:
    def test_syntax_error_skipped_gracefully(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "broken.py": "def foo(\n",  # sintaxis inválida
            "valid.py": "import os\n",
        })
        modules = [
            {"name": "broken", "path": "broken.py", "package": "", "is_package_initializer": False},
            {"name": "valid", "path": "valid.py", "package": "", "is_package_initializer": False},
        ]
        packages = []
        imports, edges = _extract_imports(["broken.py", "valid.py"], project, modules, packages)

        assert len(imports) == 1
        assert imports[0]["source"] == "valid"

    def test_no_imports_returns_empty(self, tmp_path: Path):
        project = _make_project(tmp_path, {"empty.py": "x = 1\n"})
        modules = [{"name": "empty", "path": "empty.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["empty.py"], project, modules, packages)
        assert imports == []
        assert edges == []

    def test_import_inside_function(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "def foo():\n    import os\n",
        })
        modules = [{"name": "main", "path": "main.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["main.py"], project, modules, packages)
        assert len(imports) == 1
        assert imports[0]["target"] == "os"

    def test_multiple_imports_same_line(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "import os, sys, json\n",
        })
        modules = [{"name": "main", "path": "main.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["main.py"], project, modules, packages)
        targets = [imp["target"] for imp in imports]
        assert targets == ["os", "sys", "json"]

    def test_star_import(self, tmp_path: Path):
        project = _make_project(tmp_path, {
            "main.py": "from os import *\n",
        })
        modules = [{"name": "main", "path": "main.py", "package": "", "is_package_initializer": False}]
        packages = []
        imports, edges = _extract_imports(["main.py"], project, modules, packages)
        assert len(imports) == 1
        assert imports[0]["target"] == "os"