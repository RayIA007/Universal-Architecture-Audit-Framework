"""
Test Suite I: Testing Auditor — Fase 2.2

Tests deterministas para el Testing Auditor Plugin.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Bootstrap para importar uaaf_core y el plugin
# test_testing_auditor.py está en: 09_TESTS/unit/
# Project root está 2 niveles arriba (parents[2])
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

from uaaf_core.audit.audit_result import (
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from plugins.testing.testing_auditor import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    AUDIT_TYPE,
    run,
    _discover_python_files,
    _filter_test_files,
    _filter_source_files,
    _check_missing_test_files,
    _check_empty_tests,
    _check_public_api_coverage,
    _is_empty_or_placeholder_body,
    _strip_docstring,
    _extract_public_entities,
    _extract_referenced_names,
    _validate_context,
    _validate_ignored_directories,
)


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture
def temp_project():
    """Create a temporary project directory for deterministic tests."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        yield project_path


def _write_file(project_path: Path, relative_path: str, content: str) -> None:
    """Helper to write a file in the temp project."""

    file_path = project_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# =====================================================================
# SUITE I-A: Context Validation
# =====================================================================

class TestContextValidation:
    """Tests for context parsing and validation."""

    def test_valid_context_minimal(self, temp_project):
        """A minimal valid context should not raise."""

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
        }
        result = _validate_context(context)
        assert result[0] == temp_project.resolve()

    def test_valid_context_full(self, temp_project):
        """A full valid context with all optional fields."""

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
            "ignored_directories": [".git", "node_modules"],
            "test_file_patterns": ["test_*.py"],
            "test_directories": ["tests"],
            "source_directories": ["src"],
            "require_test_for_public_api": False,
        }
        result = _validate_context(context)
        assert result[0] == temp_project.resolve()
        assert result[5] is False

    def test_invalid_context_type(self):
        """Non-dict context must raise TypeError."""

        with pytest.raises(TypeError, match="context must be a dictionary"):
            _validate_context("not a dict")

    def test_missing_project_path(self):
        """Context without project_path must raise ValueError."""

        with pytest.raises(ValueError, match="project_path"):
            _validate_context({})

    def test_invalid_project_path(self):
        """Non-existent project_path must raise ValueError."""

        with pytest.raises(ValueError, match="existing directory"):
            _validate_context({"project_path": "/nonexistent/path/12345"})

    def test_unknown_fields(self, temp_project):
        """Unknown fields must raise ValueError."""

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
            "unknown_field": True,
        }
        with pytest.raises(ValueError, match="unknown fields"):
            _validate_context(context)

    def test_wrong_audit_type(self, temp_project):
        """Mismatched audit_type must raise ValueError."""

        context = {
            "project_path": str(temp_project),
            "audit_type": "architecture",
        }
        with pytest.raises(ValueError, match="audit_type must be"):
            _validate_context(context)

    def test_ignored_directories_validation(self):
        """ignored_directories must be a collection of directory names."""

        with pytest.raises(ValueError, match="collection"):
            _validate_ignored_directories("not a list")

        with pytest.raises(ValueError, match="non-empty strings"):
            _validate_ignored_directories([""])

        with pytest.raises(ValueError, match="directory names"):
            _validate_ignored_directories(["path/to/dir"])


# =====================================================================
# SUITE I-B: File Discovery & Filtering
# =====================================================================

class TestDiscoveryAndFiltering:
    """Tests for discovering and categorizing Python files."""

    def test_discover_python_files(self, temp_project):
        """Should discover all .py files deterministically."""

        _write_file(temp_project, "src/module_a.py", "")
        _write_file(temp_project, "src/module_b.py", "")
        _write_file(temp_project, "tests/test_a.py", "")
        _write_file(temp_project, "README.md", "")

        files = _discover_python_files(temp_project, frozenset())
        assert files == ["src/module_a.py", "src/module_b.py", "tests/test_a.py"]

    def test_discover_ignores_excluded_dirs(self, temp_project):
        """Should skip ignored directories."""

        _write_file(temp_project, "src/module.py", "")
        _write_file(temp_project, ".venv/lib/pkg.py", "")

        files = _discover_python_files(temp_project, frozenset({".venv"}))
        assert files == ["src/module.py"]

    def test_filter_test_files_by_pattern(self):
        """Should identify test files by naming pattern."""

        all_files = [
            "src/module.py",
            "tests/test_module.py",
            "tests/module_test.py",
            "src/helper.py",
        ]
        test_files = _filter_test_files(
            all_files, ["test_*.py", "*_test.py"], ["tests"]
        )
        assert test_files == ["tests/module_test.py", "tests/test_module.py"]

    def test_filter_test_files_by_directory(self):
        """Should identify test files by directory."""

        all_files = [
            "src/module.py",
            "09_TESTS/unit/test_x.py",
            "tests/integration/test_y.py",
        ]
        test_files = _filter_test_files(
            all_files, ["test_*.py"], ["tests", "09_TESTS"]
        )
        assert test_files == [
            "09_TESTS/unit/test_x.py",
            "tests/integration/test_y.py",
        ]

    def test_filter_source_files(self):
        """Should exclude test files from source files."""

        all_files = [
            "src/module.py",
            "tests/test_module.py",
            "src/helper.py",
        ]
        source_files = _filter_source_files(
            all_files, ["test_*.py"], ["tests"], ["."]
        )
        assert source_files == ["src/helper.py", "src/module.py"]


# =====================================================================
# SUITE I-C: Missing Test File Detection
# =====================================================================

class TestMissingTestFiles:
    """Tests for TEST-MISSING-001."""

    def test_detects_missing_test_file(self):
        """Should flag source files without corresponding tests."""

        source_files = ["src/calculator.py", "src/utils.py"]
        test_files = ["tests/test_calculator.py"]

        violations = _check_missing_test_files(source_files, test_files)
        assert len(violations) == 1
        assert violations[0]["source_module"] == "utils"
        assert "utils.py" in violations[0]["message"]

    def test_skips_init_files(self):
        """Should not flag __init__.py as missing tests."""

        source_files = ["src/__init__.py"]
        test_files = []

        violations = _check_missing_test_files(source_files, test_files)
        assert len(violations) == 0

    def test_matches_by_stem(self):
        """Should recognize test files by stem mapping."""

        source_files = ["src/parser.py"]
        test_files = ["tests/parser_test.py"]

        violations = _check_missing_test_files(source_files, test_files)
        assert len(violations) == 0

    def test_no_violations_when_all_covered(self):
        """Should return empty when every source has a test."""

        source_files = ["src/a.py", "src/b.py"]
        test_files = ["tests/test_a.py", "tests/b_test.py"]

        violations = _check_missing_test_files(source_files, test_files)
        assert len(violations) == 0


# =====================================================================
# SUITE I-D: Empty Test Detection
# =====================================================================

class TestEmptyTests:
    """Tests for TEST-EMPTY-001."""

    def test_detects_pass_only_test(self, temp_project):
        """Should flag test with only pass."""

        _write_file(
            temp_project,
            "tests/test_sample.py",
            "def test_something():\n    pass\n",
        )
        violations = _check_empty_tests(["tests/test_sample.py"], temp_project)
        assert len(violations) == 1
        assert violations[0]["test_function"] == "test_something"

    def test_detects_ellipsis_test(self, temp_project):
        """Should flag test with only ellipsis."""

        _write_file(
            temp_project,
            "tests/test_sample.py",
            "def test_something():\n    ...\n",
        )
        violations = _check_empty_tests(["tests/test_sample.py"], temp_project)
        assert len(violations) == 1

    def test_detects_empty_body_test(self, temp_project):
        """Should flag test with completely empty body."""

        _write_file(
            temp_project,
            "tests/test_sample.py",
            "def test_something():\n    \"\"\"docstring\"\"\"\n",
        )
        violations = _check_empty_tests(["tests/test_sample.py"], temp_project)
        assert len(violations) == 1

    def test_ignores_nonempty_test(self, temp_project):
        """Should not flag test with actual assertions."""

        _write_file(
            temp_project,
            "tests/test_sample.py",
            "def test_something():\n    assert 1 + 1 == 2\n",
        )
        violations = _check_empty_tests(["tests/test_sample.py"], temp_project)
        assert len(violations) == 0

    def test_ignores_non_test_functions(self, temp_project):
        """Should only inspect functions starting with test_."""

        _write_file(
            temp_project,
            "tests/test_sample.py",
            "def helper():\n    pass\n\ndef test_real():\n    assert True\n",
        )
        violations = _check_empty_tests(["tests/test_sample.py"], temp_project)
        assert len(violations) == 0

    def test_handles_syntax_error_gracefully(self, temp_project):
        """Should skip files with syntax errors."""

        _write_file(
            temp_project,
            "tests/test_broken.py",
            "def test_something(\n",  # syntax error
        )
        violations = _check_empty_tests(["tests/test_broken.py"], temp_project)
        assert len(violations) == 0


# =====================================================================
# SUITE I-E: Public API Coverage
# =====================================================================

class TestPublicApiCoverage:
    """Tests for TEST-OUTDATED-001."""

    def test_detects_untested_public_function(self, temp_project):
        """Should flag public function not referenced in tests."""

        _write_file(
            temp_project,
            "src/math.py",
            "def add(a, b):\n    return a + b\n",
        )
        _write_file(
            temp_project,
            "tests/test_math.py",
            "def test_dummy():\n    assert True\n",
        )

        violations = _check_public_api_coverage(
            ["src/math.py"], ["tests/test_math.py"], temp_project
        )
        assert len(violations) == 1
        assert violations[0]["entity_name"] == "add"
        assert violations[0]["entity_type"] == "function"

    def test_detects_untested_public_class(self, temp_project):
        """Should flag public class not referenced in tests."""

        _write_file(
            temp_project,
            "src/shapes.py",
            "class Circle:\n    pass\n",
        )
        _write_file(
            temp_project,
            "tests/test_shapes.py",
            "def test_dummy():\n    pass\n",
        )

        violations = _check_public_api_coverage(
            ["src/shapes.py"], ["tests/test_shapes.py"], temp_project
        )
        assert len(violations) == 1
        assert violations[0]["entity_name"] == "Circle"
        assert violations[0]["entity_type"] == "class"

    def test_skips_private_functions(self, temp_project):
        """Should not flag private functions."""

        _write_file(
            temp_project,
            "src/utils.py",
            "def _internal():\n    pass\n\ndef public():\n    pass\n",
        )
        _write_file(
            temp_project,
            "tests/test_utils.py",
            "def test_public():\n    public()\n",
        )

        violations = _check_public_api_coverage(
            ["src/utils.py"], ["tests/test_utils.py"], temp_project
        )
        assert len(violations) == 0

    def test_recognizes_import_reference(self, temp_project):
        """Should recognize when entity is imported in test."""

        _write_file(
            temp_project,
            "src/calc.py",
            "def multiply(a, b):\n    return a * b\n",
        )
        _write_file(
            temp_project,
            "tests/test_calc.py",
            "from src.calc import multiply\n\ndef test_multiply():\n    assert multiply(2, 3) == 6\n",
        )

        violations = _check_public_api_coverage(
            ["src/calc.py"], ["tests/test_calc.py"], temp_project
        )
        assert len(violations) == 0

    def test_recognizes_attribute_reference(self, temp_project):
        """Should recognize module.Class style references."""

        _write_file(
            temp_project,
            "src/api.py",
            "class Client:\n    pass\n",
        )
        _write_file(
            temp_project,
            "tests/test_api.py",
            "import src.api\n\ndef test_client():\n    c = src.api.Client()\n",
        )

        violations = _check_public_api_coverage(
            ["src/api.py"], ["tests/test_api.py"], temp_project
        )
        assert len(violations) == 0


# =====================================================================
# SUITE I-F: AST Helpers
# =====================================================================

class TestAstHelpers:
    """Tests for internal AST utility functions."""

    def test_strip_docstring_removes_it(self):
        """_strip_docstring should remove leading docstring."""

        import ast

        code = 'def f():\n    """doc"""\n    pass\n'
        tree = ast.parse(code)
        func = tree.body[0]
        body = _strip_docstring(func.body)
        assert len(body) == 1
        assert isinstance(body[0], ast.Pass)

    def test_is_empty_or_placeholder_body(self):
        """Should correctly identify empty/placeholder bodies."""

        import ast

        # Empty
        assert _is_empty_or_placeholder_body([]) is True

        # Only pass
        tree = ast.parse("def f():\n    pass\n")
        body = tree.body[0].body
        assert _is_empty_or_placeholder_body(body) is True

        # Only ellipsis
        tree = ast.parse("def f():\n    ...\n")
        body = tree.body[0].body
        assert _is_empty_or_placeholder_body(body) is True

        # With assertion
        tree = ast.parse("def f():\n    assert True\n")
        body = tree.body[0].body
        assert _is_empty_or_placeholder_body(body) is False

    def test_extract_public_entities(self):
        """Should extract only public classes and functions."""

        import ast

        code = """
class PublicClass:
    pass

class _PrivateClass:
    pass

def public_func():
    pass

def _private_func():
    pass

def __init__():
    pass
"""
        tree = ast.parse(code)
        entities = _extract_public_entities(tree, "test.py")
        names = [e["name"] for e in entities]
        assert "PublicClass" in names
        assert "public_func" in names
        assert "__init__" in names
        assert "_PrivateClass" not in names
        assert "_private_func" not in names

    def test_extract_referenced_names(self):
        """Should collect all names referenced in code."""

        import ast

        code = """
import os
from pathlib import Path
x = SomeClass()
y = module.sub.func()
"""
        tree = ast.parse(code)
        refs = _extract_referenced_names(tree)
        assert "os" in refs
        assert "Path" in refs
        assert "SomeClass" in refs
        assert "module.sub.func" in refs


# =====================================================================
# SUITE I-G: Integration — Full Plugin Run
# =====================================================================

class TestPluginIntegration:
    """End-to-end tests for the testing auditor plugin."""

    def test_full_run_no_findings(self, temp_project):
        """A well-tested project should return COMPLETED with no findings."""

        _write_file(
            temp_project,
            "src/calc.py",
            "def add(a, b):\n    return a + b\n",
        )
        _write_file(
            temp_project,
            "tests/test_calc.py",
            "from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        )

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
            "test_directories": ["tests"],
            "test_file_patterns": ["test_*.py"],
        }
        result = run(context)

        assert result["plugin_id"] == PLUGIN_ID
        assert result["plugin_version"] == PLUGIN_VERSION
        assert result["audit_type"] == AUDIT_TYPE
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["findings_count"] == 0
        assert result["metrics"]["source_file_count"] == 1
        assert result["metrics"]["test_file_count"] == 1

        validate_audit_result(result)

    def test_full_run_with_all_findings(self, temp_project):
        """A poorly tested project should emit all three finding types."""

        _write_file(
            temp_project,
            "src/legacy.py",
            "def old_func():\n    pass\n\nclass OldClass:\n    pass\n",
        )
        _write_file(
            temp_project,
            "tests/test_empty.py",
            "def test_nothing():\n    pass\n",
        )

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
            "test_directories": ["tests"],
            "test_file_patterns": ["test_*.py"],
            "require_test_for_public_api": True,
        }
        result = run(context)

        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        assert result["metrics"]["findings_count"] >= 3

        codes = {f["code"] for f in result["findings"]}
        assert "TEST-MISSING-001" in codes
        assert "TEST-EMPTY-001" in codes
        assert "TEST-OUTDATED-001" in codes

        # Verify severities
        for finding in result["findings"]:
            if finding["code"] == "TEST-EMPTY-001":
                assert finding["severity"] == FindingSeverity.ERROR.value
            else:
                assert finding["severity"] == FindingSeverity.WARNING.value

        validate_audit_result(result)

    def test_full_run_skips_public_api_when_disabled(self, temp_project):
        """Should not emit TEST-OUTDATED-001 when disabled."""

        _write_file(
            temp_project,
            "src/lib.py",
            "def unused():\n    pass\n",
        )
        _write_file(
            temp_project,
            "tests/test_lib.py",
            "def test_something():\n    assert True\n",
        )

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
            "test_directories": ["tests"],
            "test_file_patterns": ["test_*.py"],
            "require_test_for_public_api": False,
        }
        result = run(context)

        codes = {f["code"] for f in result["findings"]}
        assert "TEST-OUTDATED-001" not in codes
        validate_audit_result(result)

    def test_execution_metadata_present(self, temp_project):
        """Result should contain valid execution metadata."""

        _write_file(temp_project, "src/x.py", "")
        _write_file(temp_project, "tests/test_x.py", "def test_x(): pass")

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
        }
        result = run(context)

        execution = result["execution"]
        assert execution["started_at"] is not None
        assert execution["completed_at"] is not None
        assert execution["duration_ms"] is not None
        assert isinstance(execution["duration_ms"], int)
        assert execution["duration_ms"] >= 0

    def test_summary_contains_expected_keys(self, temp_project):
        """Summary should contain all audit artifacts."""

        _write_file(temp_project, "src/x.py", "")
        _write_file(temp_project, "tests/test_x.py", "def test_x(): pass")

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
        }
        result = run(context)

        summary = result["summary"]
        assert "project_path" in summary
        assert "source_files" in summary
        assert "test_files" in summary
        assert "missing_test_violations" in summary
        assert "empty_test_violations" in summary
        assert "public_api_violations" in summary

    def test_metrics_are_non_negative(self, temp_project):
        """All metric values should be non-negative integers."""

        _write_file(temp_project, "src/x.py", "")
        _write_file(temp_project, "tests/test_x.py", "def test_x(): pass")

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
        }
        result = run(context)

        metrics = result["metrics"]
        for key, value in metrics.items():
            assert isinstance(value, int), f"{key} is not an int"
            assert value >= 0, f"{key} is negative"


# =====================================================================
# SUITE I-H: Plugin Wrapper
# =====================================================================

class TestPluginWrapper:
    """Tests for the class-based wrapper."""

    def test_wrapper_delegates_to_run(self, temp_project):
        """TestingAuditorPlugin.execute should return same as run()."""

        from plugins.testing.testing_auditor import TestingAuditorPlugin

        _write_file(temp_project, "src/x.py", "")
        # Use a real assertion so the test is NOT flagged as empty
        _write_file(temp_project, "tests/test_x.py", "def test_x():\n    assert True\n")

        context = {
            "project_path": str(temp_project),
            "audit_type": "testing",
        }

        plugin = TestingAuditorPlugin()
        result = plugin.execute(context)

        assert result["plugin_id"] == PLUGIN_ID
        assert result["status"] == AuditStatus.COMPLETED.value