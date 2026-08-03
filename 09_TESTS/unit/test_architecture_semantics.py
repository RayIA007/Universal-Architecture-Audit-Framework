"""
Test Suite K — Features semánticas avanzadas del Architecture Auditor.

Pruebas deterministas para complejidad ciclomática, dead code conservador,
métricas por módulo, métricas agregadas, orden y contrato canónico.
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
_PLUGINS_DIR = _PROJECT_ROOT / "plugins"

for import_root in (_SCRIPTS_DIR, _PLUGINS_DIR):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)


from architecture.architecture_auditor import (  # noqa: E402
    ArchitectureAuditor,
    PLUGIN_VERSION,
    _DEFAULT_MAX_CYCLOMATIC_COMPLEXITY,
    run,
)
from uaaf_core.audit.audit_result import validate_audit_result  # noqa: E402


@contextmanager
def _temporary_project(
    files: dict[str, str | bytes],
) -> Iterator[Path]:
    """Create a deterministic temporary project using TemporaryDirectory."""

    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        for relative_path, content in files.items():
            file_path = root / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content, encoding="utf-8")
        yield root


def _audit(
    files: dict[str, str | bytes],
    **options: Any,
) -> dict[str, Any]:
    with _temporary_project(files) as project_path:
        context = {
            "project_path": str(project_path),
            "audit_type": "architecture",
            **options,
        }
        result = run(context)
        validate_audit_result(result)
        return result


def _module_record(
    result: dict[str, Any],
    path: str,
) -> dict[str, Any]:
    return next(
        record
        for record in result["summary"]["module_metrics"]
        if record["path"] == path
    )


def _function_record(
    result: dict[str, Any],
    qualified_name: str,
) -> dict[str, Any]:
    for module in result["summary"]["module_metrics"]:
        for function in module["functions"]:
            if function["qualified_name"] == qualified_name:
                return function
    raise AssertionError(f"Function record not found: {qualified_name}")


def _findings(
    result: dict[str, Any],
    code: str,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    selected = [
        finding
        for finding in result["findings"]
        if finding["code"] == code
    ]
    if kind is not None:
        selected = [
            finding
            for finding in selected
            if finding["details"].get("kind") == kind
        ]
    return selected


def _referenced_function(body: str, name: str = "target") -> str:
    return f"def {name}(value=None):\n{body}\n\nUSED = {name}\n"


class TestSemanticContext:
    def test_default_threshold_is_backward_compatible(self) -> None:
        result = _audit({"main.py": "pass\n"})
        assert (
            result["summary"]["semantic_analysis"][
                "max_cyclomatic_complexity"
            ]
            == _DEFAULT_MAX_CYCLOMATIC_COMPLEXITY
            == 10
        )

    def test_positive_threshold_is_accepted(self) -> None:
        result = _audit(
            {"main.py": "pass\n"},
            max_cyclomatic_complexity=7,
        )
        assert result["metrics"]["cyclomatic_complexity_threshold"] == 7

    @pytest.mark.parametrize(
        "invalid_value",
        [0, -1, True, False, 1.5, "10", None],
        ids=["zero", "negative", "true", "false", "float", "string", "none"],
    )
    def test_invalid_threshold_is_rejected(self, invalid_value: Any) -> None:
        with _temporary_project({"main.py": "pass\n"}) as project_path:
            with pytest.raises(
                ValueError,
                match="max_cyclomatic_complexity must be a positive integer",
            ):
                run(
                    {
                        "project_path": str(project_path),
                        "max_cyclomatic_complexity": invalid_value,
                    }
                )

    def test_plugin_version_is_incremented_compatibly(self) -> None:
        assert PLUGIN_VERSION == "1.6.0"

    def test_object_wrapper_execute_preserves_public_run_contract(self) -> None:
        with _temporary_project({"main.py": "pass\n"}) as project_path:
            auditor = ArchitectureAuditor(
                {
                    "project_path": str(project_path),
                    "audit_type": "architecture",
                }
            )
            result = auditor.execute()
            validate_audit_result(result)
            assert result["plugin_version"] == PLUGIN_VERSION


class TestFunctionDiscoveryAndNames:
    def test_sync_function_starts_at_one(self) -> None:
        result = _audit(
            {"module.py": "def target():\n    return 1\n\nUSED = target\n"}
        )
        function = _function_record(result, "target")
        assert function["complexity"] == 1
        assert function["symbol_type"] == "function"

    def test_async_function_starts_at_one(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "async def target():\n"
                    "    return 1\n\n"
                    "USED = target\n"
                )
            }
        )
        function = _function_record(result, "target")
        assert function["complexity"] == 1
        assert function["symbol_type"] == "async_function"
        assert function["is_async"] is True

    def test_method_has_stable_qualified_name(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "class Service:\n"
                    "    def execute(self):\n"
                    "        return 1\n"
                )
            }
        )
        function = _function_record(result, "Service.execute")
        assert function["symbol_type"] == "method"
        assert function["is_method"] is True

    def test_async_method_has_stable_qualified_name(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "class Service:\n"
                    "    async def execute(self):\n"
                    "        return 1\n"
                )
            }
        )
        function = _function_record(result, "Service.execute")
        assert function["symbol_type"] == "async_method"
        assert function["is_async"] is True

    def test_nested_function_uses_python_style_qualified_name(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def outer():\n"
                    "    def inner():\n"
                    "        return 1\n"
                    "    return inner\n\n"
                    "USED = outer\n"
                )
            }
        )
        nested = _function_record(result, "outer.<locals>.inner")
        assert nested["symbol_type"] == "nested_function"
        assert nested["is_nested"] is True

    def test_nested_async_function_uses_stable_qualified_name(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def outer():\n"
                    "    async def inner():\n"
                    "        return 1\n"
                    "    return inner\n\n"
                    "USED = outer\n"
                )
            }
        )
        nested = _function_record(result, "outer.<locals>.inner")
        assert nested["symbol_type"] == "nested_async_function"
        assert nested["is_async"] is True

    def test_nested_body_is_excluded_from_parent_complexity(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def outer():\n"
                    "    def inner(value):\n"
                    "        if value:\n"
                    "            return 1\n"
                    "        return 0\n"
                    "    return inner\n\n"
                    "USED = outer\n"
                )
            }
        )
        assert _function_record(result, "outer")["complexity"] == 1
        assert (
            _function_record(result, "outer.<locals>.inner")["complexity"]
            == 2
        )


_COMPLEXITY_CASES = [
    (
        "if",
        "    if value:\n        return 1\n    return 0",
        2,
        "if",
        1,
    ),
    (
        "for",
        "    for item in value:\n        print(item)\n    return None",
        2,
        "for",
        1,
    ),
    (
        "while",
        "    while value:\n        value -= 1\n    return value",
        2,
        "while",
        1,
    ),
    (
        "except",
        "    try:\n        return value()\n    except ValueError:\n        return None",
        2,
        "except",
        1,
    ),
    (
        "and",
        "    return value and True and 1",
        3,
        "and",
        2,
    ),
    (
        "or",
        "    return value or False or None",
        3,
        "or",
        2,
    ),
    (
        "ternary",
        "    return 1 if value else 0",
        2,
        "ternary",
        1,
    ),
    (
        "match",
        (
            "    match value:\n"
            "        case 0:\n"
            "            return 0\n"
            "        case 1:\n"
            "            return 1\n"
            "        case _:\n"
            "            return 2"
        ),
        4,
        "match_case",
        3,
    ),
    (
        "comprehension-one-filter",
        "    return [item for item in value if item]",
        2,
        "comprehension_if",
        1,
    ),
    (
        "comprehension-two-filters",
        "    return [item for item in value if item if item > 1]",
        3,
        "comprehension_if",
        2,
    ),
]


class TestComplexityDecisionPoints:
    @pytest.mark.parametrize(
        ("case_name", "body", "expected", "breakdown_key", "increment"),
        _COMPLEXITY_CASES,
        ids=[case[0] for case in _COMPLEXITY_CASES],
    )
    def test_exact_complexity_for_decision_point(
        self,
        case_name: str,
        body: str,
        expected: int,
        breakdown_key: str,
        increment: int,
    ) -> None:
        del case_name
        result = _audit({"module.py": _referenced_function(body)})
        function = _function_record(result, "target")
        assert function["complexity"] == expected
        assert function["complexity_breakdown"][breakdown_key] == increment

    def test_async_for_increments_complexity(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "async def target(values):\n"
                    "    async for value in values:\n"
                    "        print(value)\n"
                    "    return None\n\n"
                    "USED = target\n"
                )
            }
        )
        function = _function_record(result, "target")
        assert function["complexity"] == 2
        assert function["complexity_breakdown"]["async_for"] == 1

    def test_multiple_except_handlers_increment_individually(self) -> None:
        result = _audit(
            {
                "module.py": _referenced_function(
                    "    try:\n"
                    "        return value()\n"
                    "    except ValueError:\n"
                    "        return 1\n"
                    "    except TypeError:\n"
                    "        return 2"
                )
            }
        )
        function = _function_record(result, "target")
        assert function["complexity"] == 3
        assert function["complexity_breakdown"]["except"] == 2

    def test_combined_complexity_is_exact(self) -> None:
        result = _audit(
            {
                "module.py": _referenced_function(
                    "    if value and value > 0:\n"
                    "        for item in range(value):\n"
                    "            if item % 2:\n"
                    "                return item\n"
                    "    return 0"
                )
            }
        )
        assert _function_record(result, "target")["complexity"] == 5


_THRESHOLD_CASES = [
    (
        "threshold-minus-one",
        "    if value:\n        return 1\n    return 0",
        2,
        False,
    ),
    (
        "threshold-exact",
        "    if value:\n        return 1\n    if value is None:\n        return 2\n    return 0",
        3,
        False,
    ),
    (
        "threshold-plus-one",
        (
            "    if value:\n"
            "        return 1\n"
            "    if value is None:\n"
            "        return 2\n"
            "    if value == 0:\n"
            "        return 3\n"
            "    return 0"
        ),
        4,
        True,
    ),
]


class TestComplexityThresholdAndFinding:
    @pytest.mark.parametrize(
        ("case_name", "body", "expected_complexity", "expected_finding"),
        _THRESHOLD_CASES,
        ids=[case[0] for case in _THRESHOLD_CASES],
    )
    def test_threshold_boundaries(
        self,
        case_name: str,
        body: str,
        expected_complexity: int,
        expected_finding: bool,
    ) -> None:
        del case_name
        result = _audit(
            {"module.py": _referenced_function(body)},
            max_cyclomatic_complexity=3,
        )
        assert _function_record(result, "target")["complexity"] == expected_complexity
        assert bool(_findings(result, "ARCH-COMPLEX-001")) is expected_finding

    def test_complexity_finding_has_complete_structure(self) -> None:
        result = _audit(
            {
                "pkg/module.py": _referenced_function(
                    "    if value:\n        return 1\n    return 0"
                )
            },
            max_cyclomatic_complexity=1,
        )
        finding = _findings(result, "ARCH-COMPLEX-001")[0]
        assert finding == {
            "code": "ARCH-COMPLEX-001",
            "severity": "warning",
            "path": "pkg/module.py",
            "message": (
                "Function 'target' has cyclomatic complexity 2, exceeding "
                "the configured threshold 1."
            ),
            "details": {
                "module": "pkg.module",
                "qualified_name": "target",
                "line": 1,
                "complexity": 2,
                "threshold": 1,
                "symbol_type": "function",
                "rule": "cyclomatic_complexity",
            },
        }


class TestUnusedImports:
    def test_unused_plain_import_is_reported(self) -> None:
        result = _audit(
            {"module.py": "import os\n\nVALUE = 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_import")[0]
        assert finding["details"]["binding"] == "os"
        assert finding["details"]["imported"] == "os"

    def test_used_plain_import_is_not_reported(self) -> None:
        result = _audit(
            {"module.py": "import os\n\nVALUE = os.name\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_unused_alias_is_reported_by_binding(self) -> None:
        result = _audit(
            {"module.py": "import json as serializer\n\nVALUE = 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_import")[0]
        assert finding["details"]["binding"] == "serializer"
        assert finding["details"]["imported"] == "json"

    def test_used_alias_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "import json as serializer\n\n"
                    "VALUE = serializer.dumps({})\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_unused_from_import_is_reported(self) -> None:
        result = _audit(
            {"module.py": "from pathlib import Path\n\nVALUE = 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_import")[0]
        assert finding["details"]["binding"] == "Path"
        assert finding["details"]["import_type"] == "from"

    def test_used_from_import_is_not_reported(self) -> None:
        result = _audit(
            {"module.py": "from pathlib import Path\n\nVALUE = Path('.')\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_only_unused_binding_from_multi_import_is_reported(self) -> None:
        result = _audit(
            {"module.py": "import os, json\n\nVALUE = os.name\n"}
        )
        findings = _findings(result, "ARCH-DEAD-001", "unused_import")
        assert [finding["details"]["binding"] for finding in findings] == ["json"]

    def test_noqa_suppression_is_respected(self) -> None:
        result = _audit(
            {"module.py": "import os  # noqa: F401\n\nVALUE = 1\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_optional_import_in_try_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "try:\n"
                    "    import optional_dependency\n"
                    "except ImportError:\n"
                    "    optional_dependency = None\n\n"
                    "VALUE = 1\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_import_only_module_is_treated_as_conservative_aggregator(self) -> None:
        result = _audit({"module.py": "import os\n"})
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_import_listed_in_all_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "from pathlib import Path\n\n"
                    "__all__ = ['Path']\n"
                    "VALUE = 1\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_package_initializer_reexport_is_not_reported(self) -> None:
        result = _audit(
            {
                "pkg/__init__.py": "from .service import Service\n",
                "pkg/service.py": "class Service:\n    pass\n",
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_star_import_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": "from helpers import *\n\nVALUE = 1\n",
                "helpers.py": "VALUE = 1\n",
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_forward_reference_annotation_marks_import_used(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "from pathlib import Path\n\n"
                    "def convert(value: 'Path'):\n"
                    "    return value\n\n"
                    "USED = convert\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_import") == []

    def test_unused_import_finding_has_complete_structure(self) -> None:
        result = _audit(
            {"pkg/module.py": "import os\n\nVALUE = 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_import")[0]
        assert finding["code"] == "ARCH-DEAD-001"
        assert finding["severity"] == "warning"
        assert finding["path"] == "pkg/module.py"
        assert finding["details"] == {
            "kind": "unused_import",
            "module": "pkg.module",
            "symbol": "os",
            "qualified_name": "pkg.module:os",
            "line": 1,
            "binding": "os",
            "imported": "os",
            "classification": "stdlib",
            "import_type": "import",
            "symbol_type": "import",
            "rule": "dead_code",
        }


class TestUnusedFunctions:
    def test_unreferenced_module_function_is_reported(self) -> None:
        result = _audit(
            {"module.py": "def orphan():\n    return 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_function")[0]
        assert finding["details"]["qualified_name"] == "orphan"

    def test_same_module_reference_prevents_finding(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def active():\n"
                    "    return 1\n\n"
                    "REGISTERED = active\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_from_import_in_other_module_prevents_finding(self) -> None:
        result = _audit(
            {
                "service.py": "def build():\n    return 1\n",
                "consumer.py": "from service import build\n",
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_module_attribute_reference_prevents_finding(self) -> None:
        result = _audit(
            {
                "service.py": "def build():\n    return 1\n",
                "consumer.py": "import service\n\nVALUE = service.build\n",
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_function_in_all_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "__all__ = ['public_api']\n\n"
                    "def public_api():\n"
                    "    return 1\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_decorated_function_is_not_reported(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def register(function):\n"
                    "    return function\n\n"
                    "@register\n"
                    "def plugin():\n"
                    "    return 1\n\n"
                    "USED = register\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_pytest_fixture_is_not_reported(self) -> None:
        result = _audit(
            {
                "test_module.py": (
                    "import pytest\n\n"
                    "@pytest.fixture\n"
                    "def sample_fixture():\n"
                    "    return 1\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_main_function_is_not_reported(self) -> None:
        result = _audit(
            {"module.py": "def main():\n    return 0\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_dunder_function_is_not_reported(self) -> None:
        result = _audit(
            {"module.py": "def __custom__():\n    return 0\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_test_entry_point_is_not_reported(self) -> None:
        result = _audit(
            {"test_module.py": "def test_behavior():\n    assert True\n"}
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_public_methods_are_never_module_dead_code_candidates(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "class Service:\n"
                    "    def public_method(self):\n"
                    "        return 1\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_explicit_reexport_prevents_source_function_finding(self) -> None:
        result = _audit(
            {
                "service.py": "def build():\n    return 1\n",
                "api.py": "from service import build as build\n",
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_dynamic_globals_access_suppresses_uncertain_dead_code(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "def dynamic_target():\n"
                    "    return 1\n\n"
                    "REGISTRY = globals()\n"
                )
            }
        )
        assert _findings(result, "ARCH-DEAD-001", "unused_function") == []

    def test_unused_function_finding_has_complete_structure(self) -> None:
        result = _audit(
            {"pkg/module.py": "def orphan():\n    return 1\n"}
        )
        finding = _findings(result, "ARCH-DEAD-001", "unused_function")[0]
        assert finding["path"] == "pkg/module.py"
        assert finding["details"] == {
            "kind": "unused_function",
            "module": "pkg.module",
            "symbol": "orphan",
            "qualified_name": "orphan",
            "line": 1,
            "symbol_type": "function",
            "rule": "dead_code",
        }


class TestSemanticMetricsAndDeterminism:
    def test_module_metrics_include_required_maintainability_fields(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "import os\n\n"
                    "class Service:\n"
                    "    async def execute(self, value):\n"
                    "        if value:\n"
                    "            return os.name\n"
                    "        return ''\n"
                )
            }
        )
        module = _module_record(result, "module.py")
        assert module["physical_lines"] == 7
        assert module["lines_of_code"] == 6
        assert module["function_count"] == 1
        assert module["async_function_count"] == 1
        assert module["class_count"] == 1
        assert module["complexity_total"] == 2
        assert module["complexity_average"] == 2.0
        assert module["complexity_max"] == 2
        assert module["import_count"] == 1

    def test_aggregate_metrics_cover_multiple_modules(self) -> None:
        result = _audit(
            {
                "a.py": "def first():\n    return 1\n\nUSED = first\n",
                "b.py": (
                    "async def second(value):\n"
                    "    if value:\n"
                    "        return 1\n"
                    "    return 0\n\n"
                    "USED = second\n"
                ),
            }
        )
        metrics = result["metrics"]
        assert metrics["function_count"] == 2
        assert metrics["async_function_count"] == 1
        assert metrics["total_cyclomatic_complexity"] == 3
        assert metrics["average_cyclomatic_complexity"] == 1.5
        assert metrics["max_cyclomatic_complexity"] == 2

    def test_local_dependencies_are_recorded_per_module(self) -> None:
        result = _audit(
            {
                "pkg/__init__.py": "",
                "pkg/a.py": "from pkg import b\n",
                "pkg/b.py": "VALUE = 1\n",
            }
        )
        module = _module_record(result, "pkg/a.py")
        assert module["local_dependencies"] == ["pkg"]
        assert module["local_dependency_count"] == 1

    def test_unused_counts_and_finding_counts_are_aggregated(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "import os\n\n"
                    "def orphan():\n"
                    "    return 1\n"
                )
            }
        )
        metrics = result["metrics"]
        assert metrics["potentially_unused_import_count"] == 1
        assert metrics["potentially_unused_function_count"] == 1
        assert metrics["dead_code_finding_count"] == 2
        assert metrics["findings_count"] == 2

    def test_syntax_error_has_deterministic_module_record(self) -> None:
        result = _audit({"broken.py": "def broken(\n    pass\n"})
        module = _module_record(result, "broken.py")
        assert module["parse_status"] == "syntax_error"
        assert module["function_count"] == 0
        assert module["functions"] == []

    def test_decode_error_has_deterministic_module_record(self) -> None:
        result = _audit({"broken.py": b"\xff\xfe\x80"})
        module = _module_record(result, "broken.py")
        assert module["parse_status"] == "decode_error"
        assert module["physical_lines"] == 0

    def test_all_semantic_paths_are_relative_posix(self) -> None:
        result = _audit(
            {
                "pkg/nested/module.py": (
                    "import os\n\n"
                    "def orphan():\n"
                    "    return 1\n"
                )
            }
        )
        assert _module_record(result, "pkg/nested/module.py")["path"] == (
            "pkg/nested/module.py"
        )
        for finding in result["findings"]:
            if finding["code"] in {"ARCH-COMPLEX-001", "ARCH-DEAD-001"}:
                assert "\\" not in finding["path"]
                assert not Path(finding["path"]).is_absolute()

    def test_findings_have_deterministic_order(self) -> None:
        result = _audit(
            {
                "z.py": "import sys\n\ndef zebra():\n    return 1\n",
                "a.py": "import os\n\ndef alpha():\n    return 1\n",
            }
        )
        dead_findings = _findings(result, "ARCH-DEAD-001")
        ordered = [
            (
                finding["path"],
                finding["details"]["line"],
                finding["details"]["kind"],
            )
            for finding in dead_findings
        ]
        assert ordered == [
            ("a.py", 1, "unused_import"),
            ("a.py", 3, "unused_function"),
            ("z.py", 1, "unused_import"),
            ("z.py", 3, "unused_function"),
        ]

    def test_result_is_deterministic_excluding_execution_metadata(self) -> None:
        files = {
            "module.py": (
                "import os\n\n"
                "def orphan(value):\n"
                "    if value:\n"
                "        return 1\n"
                "    return 0\n"
            )
        }
        with _temporary_project(files) as project_path:
            context = {
                "project_path": str(project_path),
                "max_cyclomatic_complexity": 1,
            }
            first = run(context)
            second = run(context)
            validate_audit_result(first)
            validate_audit_result(second)
            for result in (first, second):
                result.pop("execution")
            assert json.dumps(first, sort_keys=True) == json.dumps(
                second,
                sort_keys=True,
            )

    def test_complexity_findings_precede_dead_code_findings(self) -> None:
        result = _audit(
            {
                "module.py": (
                    "import os\n\n"
                    "def orphan(value):\n"
                    "    if value:\n"
                    "        return 1\n"
                    "    return 0\n"
                )
            },
            max_cyclomatic_complexity=1,
        )
        semantic_codes = [
            finding["code"]
            for finding in result["findings"]
            if finding["code"] in {"ARCH-COMPLEX-001", "ARCH-DEAD-001"}
        ]
        assert semantic_codes == [
            "ARCH-COMPLEX-001",
            "ARCH-DEAD-001",
            "ARCH-DEAD-001",
        ]