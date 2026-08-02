"""
Testing Auditor Plugin — Fase 2.2

Audita cobertura y calidad de tests:
- Detectar módulos Python sin archivo de test correspondiente.
- Verificar que funciones/clases públicas tengan al menos un test asociado.
- Detectar tests vacíos o con solo pass/... (placeholders).
"""

from __future__ import annotations

import ast
import fnmatch
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bootstrap
_PLUGIN_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _PLUGIN_FILE.parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
)

PLUGIN_ID = "testing-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "testing"

_DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
    }
)

_DEFAULT_TEST_FILE_PATTERNS = ["test_*.py", "*_test.py"]
_DEFAULT_TEST_DIRECTORIES = ["tests", "test", "09_TESTS"]
_DEFAULT_SOURCE_DIRECTORIES = ["."]
_DEFAULT_REQUIRE_TEST_FOR_PUBLIC_API = True

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "test_file_patterns",
    "test_directories",
    "source_directories",
    "require_test_for_public_api",
}


# =====================================================================
# PUBLIC API
# =====================================================================

def run(context: Any) -> dict[str, Any]:
    """Execute full testing audit and emit canonical AuditResult."""

    started_at = _utc_now_iso()
    t0 = datetime.now(timezone.utc)

    (
        project_path,
        ignored_directories,
        test_file_patterns,
        test_directories,
        source_directories,
        require_test_for_public_api,
    ) = _validate_context(context)

    all_python_files = _discover_python_files(project_path, ignored_directories)
    test_files = _filter_test_files(all_python_files, test_file_patterns, test_directories)
    source_files = _filter_source_files(
        all_python_files, test_file_patterns, test_directories, source_directories
    )

    # --- Missing test file analysis ---
    missing_test_violations = _check_missing_test_files(
        source_files=source_files,
        test_files=test_files,
    )

    # --- Empty test analysis ---
    empty_test_violations = _check_empty_tests(
        test_files=test_files,
        project_path=project_path,
    )

    # --- Public API without test analysis ---
    public_api_violations: list[dict[str, Any]] = []
    if require_test_for_public_api:
        public_api_violations = _check_public_api_coverage(
            source_files=source_files,
            test_files=test_files,
            project_path=project_path,
        )

    # --- Build canonical findings ---
    findings = _build_findings(
        missing_test_violations=missing_test_violations,
        empty_test_violations=empty_test_violations,
        public_api_violations=public_api_violations,
    )

    # --- Determine status ---
    status = AuditStatus.COMPLETED_WITH_FINDINGS if findings else AuditStatus.COMPLETED

    # --- Execution metadata ---
    completed_at = _utc_now_iso()
    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    result = AuditResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        audit_type=AUDIT_TYPE,
        status=status,
        summary={
            "project_path": str(project_path),
            "source_files": source_files,
            "test_files": test_files,
            "missing_test_violations": missing_test_violations,
            "empty_test_violations": empty_test_violations,
            "public_api_violations": public_api_violations,
        },
        metrics={
            "source_file_count": len(source_files),
            "test_file_count": len(test_files),
            "missing_test_file_count": len(missing_test_violations),
            "empty_test_count": len(empty_test_violations),
            "public_api_without_test_count": len(public_api_violations),
            "findings_count": len(findings),
        },
        findings=tuple(findings),
        errors=(),
        execution=AuditExecution(
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        ),
    )

    return result.to_dict()


# =====================================================================
# FINDINGS BUILDER (Canonical)
# =====================================================================

def _build_findings(
    missing_test_violations: list[dict[str, Any]],
    empty_test_violations: list[dict[str, Any]],
    public_api_violations: list[dict[str, Any]],
) -> list[AuditFinding]:
    """Convert all raw violations into canonical AuditFinding objects."""

    findings: list[AuditFinding] = []

    # --- Missing test file: TEST-MISSING-001 (WARNING) ---
    for v in missing_test_violations:
        findings.append(
            AuditFinding(
                code="TEST-MISSING-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "source_module": v.get("source_module", ""),
                    "expected_test_patterns": v.get("expected_test_patterns", []),
                    "rule": "missing_test_file",
                },
            )
        )

    # --- Empty test: TEST-EMPTY-001 (ERROR) ---
    for v in empty_test_violations:
        findings.append(
            AuditFinding(
                code="TEST-EMPTY-001",
                severity=FindingSeverity.ERROR,
                path=v["path"],
                message=v["message"],
                details={
                    "test_function": v.get("test_function", ""),
                    "line": v.get("line", 0),
                    "body_nodes": v.get("body_nodes", 0),
                    "rule": "empty_test",
                },
            )
        )

    # --- Public API without test: TEST-OUTDATED-001 (WARNING) ---
    for v in public_api_violations:
        findings.append(
            AuditFinding(
                code="TEST-OUTDATED-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "entity_type": v.get("entity_type", ""),
                    "entity_name": v.get("entity_name", ""),
                    "line": v.get("line", 0),
                    "rule": "public_api_without_test",
                },
            )
        )

    return findings


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# CONTEXT VALIDATION
# =====================================================================

def _validate_context(
    context: Any,
) -> tuple[
    Path,
    frozenset[str],
    list[str],
    list[str],
    list[str],
    bool,
]:
    """Validate context and return parsed configuration."""

    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary.")

    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS
    if unknown_fields:
        raise ValueError(
            "context contains unknown fields: " f"{sorted(unknown_fields)}"
        )

    raw_project_path = context.get("project_path")
    if not isinstance(raw_project_path, (str, Path)):
        raise ValueError("context must contain a valid project_path.")

    project_path = Path(raw_project_path).expanduser().resolve()
    if not project_path.is_dir():
        raise ValueError(
            f"project_path must reference an existing directory: {project_path}"
        )

    audit_type = context.get("audit_type")
    if audit_type is not None and audit_type != AUDIT_TYPE:
        raise ValueError(f"audit_type must be {AUDIT_TYPE!r}.")

    ignored_directories = _validate_ignored_directories(
        context.get("ignored_directories", [])
    )

    test_file_patterns = _validate_string_list(
        context.get("test_file_patterns", _DEFAULT_TEST_FILE_PATTERNS),
        "test_file_patterns",
    )

    test_directories = _validate_string_list(
        context.get("test_directories", _DEFAULT_TEST_DIRECTORIES),
        "test_directories",
    )

    source_directories = _validate_string_list(
        context.get("source_directories", _DEFAULT_SOURCE_DIRECTORIES),
        "source_directories",
    )

    require_test_for_public_api = bool(
        context.get("require_test_for_public_api", _DEFAULT_REQUIRE_TEST_FOR_PUBLIC_API)
    )

    return (
        project_path,
        ignored_directories,
        test_file_patterns,
        test_directories,
        source_directories,
        require_test_for_public_api,
    )


def _validate_ignored_directories(value: Any) -> frozenset[str]:
    """Validate user exclusions and merge them with the defaults."""

    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(
            "ignored_directories must be a collection of directory names."
        )

    normalized: set[str] = set(_DEFAULT_IGNORED_DIRECTORIES)

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "ignored_directories entries must be non-empty strings."
            )

        directory_name = item.strip()
        if Path(directory_name).name != directory_name:
            raise ValueError(
                "ignored_directories entries must be directory names, "
                f"not paths: {directory_name!r}."
            )

        normalized.add(directory_name)

    return frozenset(normalized)


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    """Validate a list of non-empty strings."""

    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list of strings.")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{field_name} entries must be non-empty strings."
            )
        result.append(item.strip())

    return result


# =====================================================================
# DISCOVERY & FILTERING
# =====================================================================

def _discover_python_files(
    project_path: Path,
    ignored_directories: frozenset[str],
) -> list[str]:
    """Return deterministic POSIX paths for discoverable Python files."""

    discovered: list[str] = []

    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name for name in directory_names if name not in ignored_directories
        )

        root_path = Path(root)
        for file_name in sorted(file_names):
            if not file_name.endswith(".py"):
                continue

            file_path = root_path / file_name
            discovered.append(
                _normalize_relative_path(file_path, project_path)
            )

    return sorted(discovered)


def _normalize_relative_path(file_path: Path, project_path: Path) -> str:
    """Normalize a discovered path as a relative POSIX string."""
    return file_path.relative_to(project_path).as_posix()


def _filter_test_files(
    python_files: list[str],
    test_file_patterns: list[str],
    test_directories: list[str],
) -> list[str]:
    """Return only the paths that match test file conventions."""

    test_files: list[str] = []
    for path in python_files:
        path_obj = Path(path)
        file_name = path_obj.name

        # Match by directory
        in_test_dir = any(
            part in test_directories for part in path_obj.parts[:-1]
        )

        # Match by pattern
        matches_pattern = any(
            fnmatch.fnmatch(file_name, pattern)
            for pattern in test_file_patterns
        )

        if in_test_dir or matches_pattern:
            test_files.append(path)

    return sorted(test_files)


def _filter_source_files(
    python_files: list[str],
    test_file_patterns: list[str],
    test_directories: list[str],
    source_directories: list[str],
) -> list[str]:
    """Return source files excluding tests and non-source directories."""

    source_files: list[str] = []
    for path in python_files:
        path_obj = Path(path)
        file_name = path_obj.name

        # Exclude test files by pattern
        is_test_by_pattern = any(
            fnmatch.fnmatch(file_name, pattern)
            for pattern in test_file_patterns
        )

        # Exclude files inside test directories
        in_test_dir = any(
            part in test_directories for part in path_obj.parts[:-1]
        )

        if is_test_by_pattern or in_test_dir:
            continue

        # If source_directories is specified, filter by it
        if source_directories != ["."]:
            in_source_dir = any(
                path.startswith(sd + "/") or path == sd
                for sd in source_directories
            )
            if not in_source_dir:
                continue

        source_files.append(path)

    return sorted(source_files)


# =====================================================================
# MISSING TEST FILE DETECTION
# =====================================================================

def _check_missing_test_files(
    source_files: list[str],
    test_files: list[str],
) -> list[dict[str, Any]]:
    """Detect source modules that lack a corresponding test file."""

    violations: list[dict[str, Any]] = []

    # Build a set of test file stems for quick lookup
    test_stems: set[str] = set()
    for tf in test_files:
        stem = Path(tf).stem
        # Remove common test prefixes/suffixes to get the module name
        for prefix in ("test_",):
            if stem.startswith(prefix):
                test_stems.add(stem[len(prefix):])
                break
        for suffix in ("_test",):
            if stem.endswith(suffix):
                test_stems.add(stem[: -len(suffix)])
                break
        # Also keep the raw stem
        test_stems.add(stem)

    for src_path in source_files:
        src_name = Path(src_path).stem
        # Skip __init__.py
        if src_name == "__init__":
            continue

        # Expected test names
        expected_patterns = [f"test_{src_name}.py", f"{src_name}_test.py"]

        has_test = False
        for pattern in expected_patterns:
            # Check if any test file matches this pattern
            for tf in test_files:
                if Path(tf).name == pattern:
                    has_test = True
                    break
            if has_test:
                break

        # Also check by stem mapping
        if not has_test:
            if src_name in test_stems:
                has_test = True

        if not has_test:
            violations.append(
                {
                    "type": "missing_test_file",
                    "path": src_path,
                    "source_module": src_name,
                    "expected_test_patterns": expected_patterns,
                    "message": (
                        f"Source module {src_path!r} has no corresponding "
                        f"test file (expected: {expected_patterns})."
                    ),
                }
            )

    return violations


# =====================================================================
# EMPTY TEST DETECTION
# =====================================================================

def _check_empty_tests(
    test_files: list[str],
    project_path: Path,
) -> list[dict[str, Any]]:
    """Detect test functions whose body is empty or contains only pass/...."""

    violations: list[dict[str, Any]] = []

    for relative_path in sorted(test_files):
        file_path = project_path / relative_path

        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if not node.name.startswith("test_"):
                continue

            body = node.body
            # Remove docstring from body check
            effective_body = _strip_docstring(body)

            if _is_empty_or_placeholder_body(effective_body):
                violations.append(
                    {
                        "type": "empty_test",
                        "path": relative_path,
                        "test_function": node.name,
                        "line": getattr(node, "lineno", 0),
                        "body_nodes": len(effective_body),
                        "message": (
                            f"Test function {node.name!r} in {relative_path!r} "
                            f"is empty or contains only placeholder statements."
                        ),
                    }
                )

    return violations


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Remove the leading docstring from a function body if present."""

    if not body:
        return body

    first = body[0]
    if isinstance(first, ast.Expr):
        value = first.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return body[1:]
        # Python < 3.8 compatibility — guarded for 3.14+
        if hasattr(ast, "Str") and isinstance(value, ast.Str):  # type: ignore[attr-defined]
            return body[1:]

    return body


def _is_empty_or_placeholder_body(body: list[ast.stmt]) -> bool:
    """Return True if the body is empty or contains only Pass/Ellipsis/Expr(Ellipsis)."""

    if not body:
        return True

    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr):
            value = stmt.value
            if isinstance(value, ast.Constant) and value.value is ...:
                continue
            # Python < 3.8 compatibility — guarded for 3.14+
            if (
                hasattr(ast, "NameConstant")
                and isinstance(value, ast.NameConstant)  # type: ignore[attr-defined]
                and value.value is ...  # type: ignore[attr-defined]
            ):
                continue
        return False

    return True


# =====================================================================
# PUBLIC API COVERAGE DETECTION
# =====================================================================

def _check_public_api_coverage(
    source_files: list[str],
    test_files: list[str],
    project_path: Path,
) -> list[dict[str, Any]]:
    """
    Detect public functions/classes in source files that are not
    referenced in any test file.
    """

    violations: list[dict[str, Any]] = []

    # Collect public API from source files
    source_api: dict[str, list[dict[str, Any]]] = {}
    for src_path in sorted(source_files):
        file_path = project_path / src_path
        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        module_name = _module_name_from_path(src_path)
        public_entities = _extract_public_entities(tree, src_path)
        if public_entities:
            source_api[module_name] = public_entities

    # Collect all referenced names from test files
    test_references: set[str] = set()
    for test_path in sorted(test_files):
        file_path = project_path / test_path
        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        refs = _extract_referenced_names(tree)
        test_references.update(refs)

    # Check coverage
    for module_name, entities in source_api.items():
        for entity in entities:
            entity_name = entity["name"]
            # Check if referenced directly or via module prefix
            referenced = (
                entity_name in test_references
                or f"{module_name}.{entity_name}" in test_references
            )

            if not referenced:
                violations.append(
                    {
                        "type": "public_api_without_test",
                        "path": entity["path"],
                        "entity_type": entity["entity_type"],
                        "entity_name": entity_name,
                        "line": entity["line"],
                        "message": (
                            f"Public {entity['entity_type']} {entity_name!r} "
                            f"in {entity['path']!r} has no associated test."
                        ),
                    }
                )

    return violations


def _extract_public_entities(
    tree: ast.AST,
    relative_path: str,
) -> list[dict[str, Any]]:
    """Extract public classes and functions from a module AST."""

    entities: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                entities.append(
                    {
                        "name": node.name,
                        "entity_type": "class",
                        "path": relative_path,
                        "line": getattr(node, "lineno", 0),
                    }
                )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_function(node):
                entities.append(
                    {
                        "name": node.name,
                        "entity_type": "function",
                        "path": relative_path,
                        "line": getattr(node, "lineno", 0),
                    }
                )

    return entities


def _is_public_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the function is considered public."""

    if node.name == "__init__":
        return True
    if node.name.startswith("_"):
        return False
    return True


def _extract_referenced_names(tree: ast.AST) -> set[str]:
    """Extract all names referenced in an AST (imports, attributes, calls)."""

    refs: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)

        elif isinstance(node, ast.Attribute):
            # Build dotted reference like module.Class.method
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                refs.add(".".join(reversed(parts)))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                refs.add(name)
                # Also add the root module
                refs.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                refs.add(name)
                if module:
                    refs.add(f"{module}.{alias.name}")
                    refs.add(module.split(".")[0])

    return refs


def _module_name_from_path(relative_path: str) -> str:
    """Convert a normalized Python path into its dotted module name."""
    path = Path(relative_path)
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else relative_path


# =====================================================================
# PLUGIN WRAPPER
# =====================================================================

class TestingAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "TestingAuditorPlugin",
    "run",
]