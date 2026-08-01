"""
Test Suite D — Las 4 reglas del Architecture Auditor.

Pruebas deterministas para:
1. Ciclos de dependencia      (ARCH-CYCLE-001)
2. Violaciones de capa       (ARCH-LAYER-001)
3. Imports prohibidos        (ARCH-FORBIDDEN-001)
4. __init__.py faltante      (ARCH-INIT-001)
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
    _detect_cycles,
    _validate_layers,
    _validate_forbidden_imports,
    _validate_package_initializers,
    _build_findings,
)

from uaaf_core.audit.audit_result import FindingSeverity


# -----------------------------------------------------------------------------
# Rule 1: Cycles (ARCH-CYCLE-001)
# -----------------------------------------------------------------------------

class TestCycleDetection:
    def test_no_cycles(self):
        edges = [("a", "b"), ("b", "c")]
        cycles = _detect_cycles(edges)
        assert cycles == []

    def test_simple_cycle(self):
        edges = [("a", "b"), ("b", "a")]
        cycles = _detect_cycles(edges)
        assert cycles == [["a", "b"]]

    def test_triangle_cycle(self):
        edges = [("a", "b"), ("b", "c"), ("c", "a")]
        cycles = _detect_cycles(edges)
        assert cycles == [["a", "b", "c"]]

    def test_cycle_with_extra_edges(self):
        edges = [("a", "b"), ("b", "c"), ("c", "a"), ("a", "d")]
        cycles = _detect_cycles(edges)
        assert cycles == [["a", "b", "c"]]

    def test_self_cycle_not_detected(self):
        """Self-cycles (a -> a) are not detected by the current DFS implementation."""
        edges = [("a", "a")]
        cycles = _detect_cycles(edges)
        assert cycles == []

    def test_multiple_cycles(self):
        edges = [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")]
        cycles = _detect_cycles(edges)
        assert cycles == [["a", "b"], ["c", "d"]]

    def test_canonicalization_avoids_duplicates(self):
        edges = [("a", "b"), ("b", "c"), ("c", "a")]
        cycles = _detect_cycles(edges)
        assert len(cycles) == 1

    def test_max_depth_limits(self):
        edges = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a")]
        cycles = _detect_cycles(edges, max_depth=3)
        assert cycles == []  # cycle length 5 > max_depth 3

    def test_no_edges(self):
        assert _detect_cycles([]) == []


# -----------------------------------------------------------------------------
# Rule 2: Layer violations (ARCH-LAYER-001)
# -----------------------------------------------------------------------------

class TestLayerValidation:
    def test_no_violation_same_layer(self):
        edges = [("domain.user", "domain.order")]
        modules = [
            {"name": "domain.user", "path": "domain/user.py", "package": "domain", "is_package_initializer": False},
            {"name": "domain.order", "path": "domain/order.py", "package": "domain", "is_package_initializer": False},
        ]
        config = {
            "order": ["domain", "infra"],
            "mapping": {
                "domain": ["domain.*"],
            },
        }
        violations = _validate_layers(edges, modules, config)
        assert violations == []

    def test_no_violation_lower_to_higher(self):
        edges = [("infra.db", "domain.user")]
        modules = [
            {"name": "infra.db", "path": "infra/db.py", "package": "infra", "is_package_initializer": False},
            {"name": "domain.user", "path": "domain/user.py", "package": "domain", "is_package_initializer": False},
        ]
        config = {
            "order": ["domain", "infra"],
            "mapping": {
                "domain": ["domain.*"],
                "infra": ["infra.*"],
            },
        }
        violations = _validate_layers(edges, modules, config)
        assert violations == []

    def test_violation_higher_imports_lower(self):
        edges = [("domain.user", "infra.db")]
        modules = [
            {"name": "domain.user", "path": "domain/user.py", "package": "domain", "is_package_initializer": False},
            {"name": "infra.db", "path": "infra/db.py", "package": "infra", "is_package_initializer": False},
        ]
        config = {
            "order": ["domain", "infra"],
            "mapping": {
                "domain": ["domain.*"],
                "infra": ["infra.*"],
            },
        }
        violations = _validate_layers(edges, modules, config)
        assert len(violations) == 1
        assert violations[0]["source"] == "domain.user"
        assert violations[0]["target"] == "infra.db"
        assert "layer" in violations[0]["message"].lower()

    def test_unmapped_modules_ignored(self):
        edges = [("unknown.module", "domain.user")]
        modules = [
            {"name": "unknown.module", "path": "unknown/module.py", "package": "unknown", "is_package_initializer": False},
            {"name": "domain.user", "path": "domain/user.py", "package": "domain", "is_package_initializer": False},
        ]
        config = {
            "order": ["domain"],
            "mapping": {"domain": ["domain.*"]},
        }
        violations = _validate_layers(edges, modules, config)
        assert violations == []

    def test_invalid_layers_not_dict(self):
        with pytest.raises(ValueError, match="layers must be a dictionary"):
            _validate_layers([], [], [])

    def test_invalid_order_empty(self):
        with pytest.raises(ValueError, match="layers.order must be a non-empty list"):
            _validate_layers([], [], {"order": [], "mapping": {}})

    def test_invalid_mapping_not_dict(self):
        with pytest.raises(ValueError, match="layers.mapping must be a dictionary"):
            _validate_layers([], [], {"order": ["a"], "mapping": "bad"})

    def test_layer_not_in_order(self):
        with pytest.raises(ValueError, match="not declared in order"):
            _validate_layers([], [], {"order": ["a"], "mapping": {"b": ["*"]}})

    def test_pattern_not_list(self):
        modules = [{"name": "a", "path": "a.py", "package": "", "is_package_initializer": False}]
        with pytest.raises(ValueError, match="must be a list of patterns"):
            _validate_layers([], modules, {"order": ["x"], "mapping": {"x": "not_list"}})


# -----------------------------------------------------------------------------
# Rule 3: Forbidden imports (ARCH-FORBIDDEN-001)
# -----------------------------------------------------------------------------

class TestForbiddenImports:
    def test_global_forbidden_pattern(self):
        imports = [
            {"source": "main", "target": "requests", "classification": "third_party"},
        ]
        violations = _validate_forbidden_imports(imports, ["requests"])
        assert len(violations) == 1
        assert violations[0]["source"] == "main"
        assert violations[0]["target"] == "requests"
        assert violations[0]["scope"] == "global"

    def test_wildcard_pattern(self):
        imports = [
            {"source": "main", "target": "requests.auth", "classification": "third_party"},
        ]
        violations = _validate_forbidden_imports(imports, ["requests.*"])
        assert len(violations) == 1
        assert violations[0]["matched_pattern"] == "requests.*"

    def test_no_match(self):
        imports = [
            {"source": "main", "target": "os", "classification": "stdlib"},
        ]
        violations = _validate_forbidden_imports(imports, ["requests"])
        assert violations == []

    def test_per_source_pattern(self):
        imports = [
            {"source": "api.routes", "target": "sqlalchemy", "classification": "third_party"},
            {"source": "domain.model", "target": "sqlalchemy", "classification": "third_party"},
        ]
        config = {
            "global": [],
            "per_source": {"api.*": ["sqlalchemy"]},
        }
        violations = _validate_forbidden_imports(imports, config)
        assert len(violations) == 1
        assert violations[0]["source"] == "api.routes"
        assert "per_source:api.*" in violations[0]["scope"]

    def test_none_config_returns_empty(self):
        assert _validate_forbidden_imports([], None) == []

    def test_invalid_config_type(self):
        with pytest.raises(ValueError, match="must be a list of patterns or a dict"):
            _validate_forbidden_imports([], 42)

    def test_invalid_global_type(self):
        with pytest.raises(ValueError, match="forbidden_imports.global must be a list"):
            _validate_forbidden_imports([], {"global": "bad"})

    def test_invalid_per_source_type(self):
        with pytest.raises(ValueError, match="forbidden_imports.per_source must be a dict"):
            _validate_forbidden_imports([], {"per_source": "bad"})


# -----------------------------------------------------------------------------
# Rule 4: Missing __init__.py (ARCH-INIT-001)
# -----------------------------------------------------------------------------

class TestPackageInitializers:
    def test_no_missing_init(self):
        packages = [
            {"name": "utils", "path": "utils", "modules": ["utils.helpers"]},
        ]
        modules = [
            {"name": "utils", "path": "utils/__init__.py", "package": "utils", "is_package_initializer": True},
            {"name": "utils.helpers", "path": "utils/helpers.py", "package": "utils", "is_package_initializer": False},
        ]
        violations = _validate_package_initializers(packages, modules)
        assert violations == []

    def test_missing_init_detected(self):
        packages = [
            {"name": "utils", "path": "utils", "modules": ["utils.helpers"]},
        ]
        modules = [
            {"name": "utils.helpers", "path": "utils/helpers.py", "package": "utils", "is_package_initializer": False},
        ]
        violations = _validate_package_initializers(packages, modules)
        assert len(violations) == 1
        assert violations[0]["package"] == "utils"
        assert "__init__.py" in violations[0]["message"]

    def test_multiple_missing(self):
        packages = [
            {"name": "a", "path": "a", "modules": ["a.x"]},
            {"name": "b", "path": "b", "modules": ["b.y"]},
        ]
        modules = [
            {"name": "a.x", "path": "a/x.py", "package": "a", "is_package_initializer": False},
            {"name": "b.y", "path": "b/y.py", "package": "b", "is_package_initializer": False},
        ]
        violations = _validate_package_initializers(packages, modules)
        assert len(violations) == 2

    def test_empty_packages(self):
        assert _validate_package_initializers([], []) == []


# -----------------------------------------------------------------------------
# Tests: _build_findings canonical output
# -----------------------------------------------------------------------------

class TestBuildFindings:
    def test_cycle_finding(self):
        findings = _build_findings(
            cycles=[["a", "b", "c"]],
            layer_violations=[],
            forbidden_violations=[],
            missing_init_violations=[],
        )
        assert len(findings) == 1
        assert findings[0].code == "ARCH-CYCLE-001"
        assert findings[0].severity == FindingSeverity.ERROR
        assert "a -> b -> c -> a" in findings[0].message

    def test_layer_violation_finding(self):
        findings = _build_findings(
            cycles=[],
            layer_violations=[{
                "source": "domain.x",
                "source_layer": "domain",
                "target": "infra.y",
                "target_layer": "infra",
                "message": "Layer violation msg",
            }],
            forbidden_violations=[],
            missing_init_violations=[],
        )
        assert len(findings) == 1
        assert findings[0].code == "ARCH-LAYER-001"
        assert findings[0].severity == FindingSeverity.WARNING
        assert findings[0].path == "domain.x"

    def test_forbidden_import_finding(self):
        findings = _build_findings(
            cycles=[],
            layer_violations=[],
            forbidden_violations=[{
                "source": "main",
                "target": "requests",
                "matched_pattern": "requests",
                "scope": "global",
                "message": "Forbidden msg",
            }],
            missing_init_violations=[],
        )
        assert len(findings) == 1
        assert findings[0].code == "ARCH-FORBIDDEN-001"
        assert findings[0].severity == FindingSeverity.ERROR

    def test_missing_init_finding(self):
        findings = _build_findings(
            cycles=[],
            layer_violations=[],
            forbidden_violations=[],
            missing_init_violations=[{
                "package": "utils",
                "path": "utils",
                "modules": ["utils.helpers"],
                "message": "Missing init msg",
            }],
        )
        assert len(findings) == 1
        assert findings[0].code == "ARCH-INIT-001"
        assert findings[0].severity == FindingSeverity.WARNING