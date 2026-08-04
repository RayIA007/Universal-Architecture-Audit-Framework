"""
Test Suite H: Documentation Auditor — Deterministic unit tests.

Coverage:
- Context validation (fields, types, project_path)
- README discovery and missing README detection
- Docstring detection (module, class, function)
- Placeholder detection in README and docstrings
- AuditResult contract compliance
- Metrics accuracy
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path

# Bootstrap: ensure 08_SCRIPTS is on sys.path
_TEST_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _TEST_FILE.parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pytest

from uaaf_core.audit.audit_result import (
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)

from plugins.documentation.documentation_auditor import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    AUDIT_TYPE,
    DocumentationAuditorPlugin,
    run,
    _validate_context,
    _discover_python_files,
    _discover_readme_files,
    _check_missing_readmes,
    _check_docstrings,
    _check_placeholders,
    _extract_docstring,
    _is_public_function,
    _extract_context,
    _DEFAULT_PLACEHOLDER_PATTERNS,
)


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture
def temp_project():
    """Yield a temporary project directory path."""

    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =====================================================================
# TEST H.1: Context Validation
# =====================================================================

class TestContextValidation:
    """Tests for _validate_context and run() entry-point guards."""

    def test_context_must_be_dict(self, temp_project: Path):
        with pytest.raises(TypeError, match="context must be a dictionary"):
            run("not a dict")

    def test_project_path_required(self):
        with pytest.raises(ValueError, match="project_path"):
            run({})

    def test_project_path_must_exist(self, temp_project: Path):
        nonexistent = temp_project / "does_not_exist"
        with pytest.raises(ValueError, match="existing directory"):
            run({"project_path": str(nonexistent)})

    def test_unknown_fields_rejected(self, temp_project: Path):
        with pytest.raises(ValueError, match="unknown fields"):
            run(
                {
                    "project_path": str(temp_project),
                    "bogus_field": 123,
                }
            )

    def test_audit_type_mismatch(self, temp_project: Path):
        with pytest.raises(ValueError, match="audit_type must be"):
            run(
                {
                    "project_path": str(temp_project),
                    "audit_type": "architecture",
                }
            )

    def test_ignored_directories_must_be_collection(self, temp_project: Path):
        with pytest.raises(ValueError, match="collection"):
            run(
                {
                    "project_path": str(temp_project),
                    "ignored_directories": "not_a_list",
                }
            )

    def test_ignored_directories_entry_must_be_string(self, temp_project: Path):
        with pytest.raises(ValueError, match="non-empty strings"):
            run(
                {
                    "project_path": str(temp_project),
                    "ignored_directories": [123],
                }
            )

    def test_ignored_directories_entry_must_be_dir_name(self, temp_project: Path):
        with pytest.raises(ValueError, match="directory names"):
            run(
                {
                    "project_path": str(temp_project),
                    "ignored_directories": ["some/path"],
                }
            )

    def test_default_context_values(self, temp_project: Path):
        (
            project_path,
            ignored_dirs,
            require_readme,
            require_module,
            require_class,
            require_function,
            placeholder_patterns,
            readme_filenames,
        ) = _validate_context({"project_path": str(temp_project)})

        assert project_path == temp_project.resolve()
        assert ".git" in ignored_dirs
        assert require_readme is True
        assert require_module is True
        assert require_class is True
        assert require_function is True
        assert placeholder_patterns == _DEFAULT_PLACEHOLDER_PATTERNS
        assert readme_filenames == ["README.md"]

    def test_custom_context_values(self, temp_project: Path):
        (
            project_path,
            ignored_dirs,
            require_readme,
            require_module,
            require_class,
            require_function,
            placeholder_patterns,
            readme_filenames,
        ) = _validate_context(
            {
                "project_path": str(temp_project),
                "require_readme_in_packages": False,
                "require_module_docstrings": False,
                "require_class_docstrings": False,
                "require_function_docstrings": False,
                "placeholder_patterns": ["CUSTOM"],
                "readme_filenames": ["README.rst", "README.md"],
            }
        )

        assert require_readme is False
        assert require_module is False
        assert require_class is False
        assert require_function is False
        assert placeholder_patterns == ["CUSTOM"]
        assert readme_filenames == ["README.rst", "README.md"]


# =====================================================================
# TEST H.2: Discovery
# =====================================================================

class TestDiscovery:
    """Tests for file discovery functions."""

    def test_discover_python_files(self, temp_project: Path):
        (temp_project / "a.py").write_text("pass", encoding="utf-8")
        (temp_project / "sub").mkdir()
        (temp_project / "sub" / "b.py").write_text("pass", encoding="utf-8")
        (temp_project / "ignored").mkdir()
        (temp_project / "ignored" / "c.py").write_text("pass", encoding="utf-8")

        files = _discover_python_files(
            temp_project, frozenset({"ignored"})
        )
        assert files == ["a.py", "sub/b.py"]

    def test_discover_python_files_ignores_non_py(self, temp_project: Path):
        (temp_project / "a.txt").write_text("hello", encoding="utf-8")
        files = _discover_python_files(temp_project, frozenset())
        assert files == []

    def test_discover_readme_files(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "sub").mkdir()
        (temp_project / "sub" / "README.rst").write_text("# Sub", encoding="utf-8")

        files = _discover_readme_files(
            temp_project, frozenset(), ["README.md", "README.rst"]
        )
        assert files == ["README.md", "sub/README.rst"]

    def test_discover_readme_case_insensitive(self, temp_project: Path):
        (temp_project / "readme.md").write_text("# Root", encoding="utf-8")
        files = _discover_readme_files(
            temp_project, frozenset(), ["README.md"]
        )
        assert files == ["readme.md"]


# =====================================================================
# TEST H.3: Missing README Detection
# =====================================================================

class TestMissingReadme:
    """Tests for DOC-README-001."""

    def test_missing_root_readme(self, temp_project: Path):
        (temp_project / "a.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        readme_findings = [
            f for f in result["findings"] if f["code"] == "DOC-README-001"
        ]
        assert len(readme_findings) == 1
        assert readme_findings[0]["path"] == "."
        assert "Project root is missing" in readme_findings[0]["message"]

    def test_root_readme_present(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Project", encoding="utf-8")
        (temp_project / "a.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        readme_findings = [
            f for f in result["findings"] if f["code"] == "DOC-README-001"
        ]
        assert len(readme_findings) == 0

    def test_missing_package_readme(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "pkg").mkdir()
        (temp_project / "pkg" / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        readme_findings = [
            f for f in result["findings"] if f["code"] == "DOC-README-001"
        ]
        assert len(readme_findings) == 1
        assert readme_findings[0]["path"] == "pkg"
        assert "pkg" in readme_findings[0]["message"]

    def test_package_readme_present(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "pkg").mkdir()
        (temp_project / "pkg" / "README.md").write_text("# Pkg", encoding="utf-8")
        (temp_project / "pkg" / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        readme_findings = [
            f for f in result["findings"] if f["code"] == "DOC-README-001"
        ]
        assert len(readme_findings) == 0

    def test_require_readme_in_packages_false(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "pkg").mkdir()
        (temp_project / "pkg" / "module.py").write_text("pass", encoding="utf-8")
        result = run(
            {
                "project_path": str(temp_project),
                "require_readme_in_packages": False,
            }
        )

        readme_findings = [
            f for f in result["findings"] if f["code"] == "DOC-README-001"
        ]
        assert len(readme_findings) == 0


# =====================================================================
# TEST H.4: Docstring Detection
# =====================================================================

class TestDocstrings:
    """Tests for DOC-DOCSTRING-001."""

    def test_missing_module_docstring(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("x = 1\n", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["entity_type"] == "module"
        assert findings[0]["details"]["entity_name"] == "module"

    def test_module_docstring_present(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"This is a module.\"\"\"\nx = 1\n', encoding="utf-8"
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0

    def test_missing_class_docstring(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        class_findings = [f for f in findings if f["details"]["entity_type"] == "class"]
        assert len(class_findings) == 1
        assert class_findings[0]["details"]["entity_name"] == "MyClass"

    def test_class_docstring_present(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"Class doc.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0

    def test_private_class_ignored(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass _PrivateClass:\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0

    def test_missing_function_docstring(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\ndef public_func():\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        func_findings = [
            f for f in findings if f["details"]["entity_type"] == "function"
        ]
        assert len(func_findings) == 1
        assert func_findings[0]["details"]["entity_name"] == "public_func"

    def test_function_docstring_present(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\ndef public_func():\n    \"\"\"Func doc.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        func_findings = [
            f for f in findings if f["details"]["entity_type"] == "function"
        ]
        assert len(func_findings) == 0

    def test_private_function_ignored(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\ndef _private_func():\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        func_findings = [
            f for f in findings if f["details"]["entity_type"] == "function"
        ]
        assert len(func_findings) == 0

    def test_dunder_methods_ignored(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"Class doc.\"\"\"\n'
            '    def __str__(self):\n        return "x"\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        func_findings = [
            f for f in findings if f["details"]["entity_type"] == "function"
        ]
        assert len(func_findings) == 0

    def test_require_module_docstrings_false(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("x = 1\n", encoding="utf-8")
        result = run(
            {
                "project_path": str(temp_project),
                "require_module_docstrings": False,
            }
        )

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0

    def test_require_class_docstrings_false(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    pass\n',
            encoding="utf-8",
        )
        result = run(
            {
                "project_path": str(temp_project),
                "require_class_docstrings": False,
            }
        )

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0

    def test_require_function_docstrings_false(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\ndef public_func():\n    pass\n',
            encoding="utf-8",
        )
        result = run(
            {
                "project_path": str(temp_project),
                "require_function_docstrings": False,
            }
        )

        findings = [f for f in result["findings"] if f["code"] == "DOC-DOCSTRING-001"]
        assert len(findings) == 0


# =====================================================================
# TEST H.5: Placeholder Detection
# =====================================================================

class TestPlaceholders:
    """Tests for DOC-PLACEHOLDER-001."""

    def test_placeholder_in_readme(self, temp_project: Path):
        (temp_project / "README.md").write_text(
            "# Project\n\nTODO: write docs\n", encoding="utf-8"
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["matched_pattern"] == "TODO"
        assert "README.md" in findings[0]["message"]

    def test_placeholder_in_module_docstring(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"FIXME: this module needs docs.\"\"\"\nx = 1\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["matched_pattern"] == "FIXME"
        assert "module" in findings[0]["message"]

    def test_placeholder_in_class_docstring(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"Lorem ipsum dolor.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["matched_pattern"] == "Lorem ipsum"

    def test_placeholder_case_insensitive(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"todo: fix me.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["matched_pattern"] == "TODO"

    def test_no_placeholder_no_findings(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root\n\nGood docs.", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"Class doc.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 0

    def test_custom_placeholder_patterns(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"CUSTOM placeholder.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run(
            {
                "project_path": str(temp_project),
                "placeholder_patterns": ["CUSTOM"],
            }
        )

        findings = [f for f in result["findings"] if f["code"] == "DOC-PLACEHOLDER-001"]
        assert len(findings) == 1
        assert findings[0]["details"]["matched_pattern"] == "CUSTOM"


# =====================================================================
# TEST H.6: AuditResult Contract
# =====================================================================

class TestAuditResultContract:
    """Tests that the emitted AuditResult complies with the canonical contract."""

    def test_result_has_required_fields(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        assert result["plugin_id"] == PLUGIN_ID
        assert result["plugin_version"] == PLUGIN_VERSION
        assert result["audit_type"] == AUDIT_TYPE
        assert "status" in result
        assert "summary" in result
        assert "metrics" in result
        assert "findings" in result
        assert "errors" in result
        assert "execution" in result
        assert "started_at" in result["execution"]
        assert "completed_at" in result["execution"]
        assert "duration_ms" in result["execution"]

    def test_result_passes_validate_audit_result(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        # Should not raise
        validate_audit_result(result)

    def test_findings_are_list_in_dict(self, temp_project: Path):
        """AuditResult.to_dict() serializes tuples as lists via dataclasses.asdict()."""
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        assert isinstance(result["findings"], list)
        assert isinstance(result["errors"], list)

    def test_finding_has_required_fields(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        for finding in result["findings"]:
            assert "code" in finding
            assert "severity" in finding
            assert "path" in finding
            assert "message" in finding
            assert "details" in finding

    def test_completed_status_when_no_findings(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text(
            '\"\"\"Mod doc.\"\"\"\nclass MyClass:\n    \"\"\"Class doc.\"\"\"\n    pass\n',
            encoding="utf-8",
        )
        result = run({"project_path": str(temp_project)})

        assert result["status"] == AuditStatus.COMPLETED.value
        assert len(result["findings"]) == 0

    def test_completed_with_findings_status(self, temp_project: Path):
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        assert len(result["findings"]) > 0

    def test_metrics_are_integers(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")
        result = run({"project_path": str(temp_project)})

        metrics = result["metrics"]
        for key, value in metrics.items():
            assert isinstance(value, int), f"metrics.{key} is not an int: {value!r}"


# =====================================================================
# TEST H.7: Plugin Wrapper
# =====================================================================

class TestPluginWrapper:
    """Tests for the DocumentationAuditorPlugin class."""

    def test_plugin_execute_returns_dict(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "module.py").write_text("pass", encoding="utf-8")

        plugin = DocumentationAuditorPlugin()
        result = plugin.execute({"project_path": str(temp_project)})

        assert isinstance(result, dict)
        assert result["plugin_id"] == PLUGIN_ID


# =====================================================================
# TEST H.8: Utility Functions
# =====================================================================

class TestUtilityFunctions:
    """Tests for small helper functions."""

    def test_extract_docstring_module(self):
        tree = ast.parse('\"\"\"Module doc.\"\"\"\nx = 1\n')
        assert _extract_docstring(tree) == "Module doc."

    def test_extract_docstring_none(self):
        tree = ast.parse("x = 1\n")
        assert _extract_docstring(tree) is None

    def test_extract_docstring_non_string_expression_python_314_safe(self):
        """Non-string expressions must not access removed AST aliases."""
        tree = ast.parse("...\n")
        assert _extract_docstring(tree) is None

    def test_extract_docstring_class(self):
        tree = ast.parse(
            'class MyClass:\n    \"\"\"Class doc.\"\"\"\n    pass\n'
        )
        cls_node = tree.body[0]
        assert _extract_docstring(cls_node) == "Class doc."

    def test_is_public_function_public(self):
        tree = ast.parse("def public(): pass\n")
        func = tree.body[0]
        assert _is_public_function(func) is True

    def test_is_public_function_private(self):
        tree = ast.parse("def _private(): pass\n")
        func = tree.body[0]
        assert _is_public_function(func) is False

    def test_is_public_function_dunder(self):
        tree = ast.parse("def __str__(self): pass\n")
        func = tree.body[0]
        assert _is_public_function(func) is False

    def test_is_public_function_init(self):
        tree = ast.parse("def __init__(self): pass\n")
        func = tree.body[0]
        assert _is_public_function(func) is True

    def test_extract_context(self):
        text = "This is a long sentence with a TODO marker in the middle."
        ctx = _extract_context(text, 27, 31)
        assert "TODO" in ctx
        assert "..." in ctx or len(ctx) <= 70


# =====================================================================
# TEST H.9: Integration / End-to-End
# =====================================================================

class TestIntegration:
    """End-to-end tests with realistic project structures."""

    def test_realistic_project_all_clean(self, temp_project: Path):
        (temp_project / "README.md").write_text("# My Project\n\nGreat docs.", encoding="utf-8")
        (temp_project / "src").mkdir()
        (temp_project / "src" / "README.md").write_text("# Source", encoding="utf-8")
        (temp_project / "src" / "__init__.py").write_text(
            '\"\"\"Source package.\"\"\"\n', encoding="utf-8"
        )
        (temp_project / "src" / "core.py").write_text(
            '\"\"\"Core module.\"\"\"\n\n'
            'class Engine:\n    \"\"\"The main engine.\"\"\"\n'
            "    def run(self):\n        \"\"\"Run the engine.\"\"\"\n        pass\n",
            encoding="utf-8",
        )

        result = run({"project_path": str(temp_project)})

        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["findings_count"] == 0
        assert result["metrics"]["python_file_count"] == 2

    def test_realistic_project_multiple_issues(self, temp_project: Path):
        (temp_project / "src").mkdir()
        (temp_project / "src" / "core.py").write_text(
            "class Engine:\n    def run(self):\n        pass\n",
            encoding="utf-8",
        )
        (temp_project / "src" / "utils.py").write_text(
            '\"\"\"Utils module.\"\"\"\n# FIXME: optimize this\n',
            encoding="utf-8",
        )

        result = run({"project_path": str(temp_project)})

        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        assert result["metrics"]["findings_count"] > 0

        codes = {f["code"] for f in result["findings"]}
        assert "DOC-README-001" in codes
        assert "DOC-DOCSTRING-001" in codes

    def test_metrics_accuracy(self, temp_project: Path):
        (temp_project / "README.md").write_text("# Root", encoding="utf-8")
        (temp_project / "a.py").write_text("pass", encoding="utf-8")
        (temp_project / "b.py").write_text("pass", encoding="utf-8")

        result = run({"project_path": str(temp_project)})

        assert result["metrics"]["python_file_count"] == 2
        assert result["metrics"]["readme_file_count"] == 1
        assert result["metrics"]["missing_readme_count"] == 0
        assert result["metrics"]["missing_module_docstring_count"] == 2
        assert result["metrics"]["findings_count"] == 2