"""
Documentation Auditor Plugin — Fase 2.2

Audita calidad y completitud de documentación:
- README.md faltantes (raíz y paquetes)
- Docstrings faltantes (módulos, clases, funciones públicas)
- Placeholders/todos en documentación (TODO, FIXME, Lorem ipsum, etc.)
"""

from __future__ import annotations

import ast
import os
import re
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

PLUGIN_ID = "documentation-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "documentation"

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

_DEFAULT_PLACEHOLDER_PATTERNS = [
    "TODO",
    "FIXME",
    "Lorem ipsum",
    "XXX",
    "HACK",
    "PLACEHOLDER",
]

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "require_readme_in_packages",
    "require_module_docstrings",
    "require_class_docstrings",
    "require_function_docstrings",
    "placeholder_patterns",
    "readme_filenames",
}


# =====================================================================
# PUBLIC API
# =====================================================================

def run(context: Any) -> dict[str, Any]:
    """Execute full documentation audit and emit canonical AuditResult."""

    started_at = _utc_now_iso()
    t0 = datetime.now(timezone.utc)

    (
        project_path,
        ignored_directories,
        require_readme_in_packages,
        require_module_docstrings,
        require_class_docstrings,
        require_function_docstrings,
        placeholder_patterns,
        readme_filenames,
    ) = _validate_context(context)

    python_files = _discover_python_files(project_path, ignored_directories)
    readme_files = _discover_readme_files(project_path, ignored_directories, readme_filenames)

    # --- README analysis ---
    missing_readme_violations = _check_missing_readmes(
        project_path=project_path,
        python_files=python_files,
        readme_files=readme_files,
        readme_filenames=readme_filenames,
        require_in_packages=require_readme_in_packages,
    )

    # --- Docstring analysis ---
    docstring_violations = _check_docstrings(
        project_path=project_path,
        python_files=python_files,
        require_module=require_module_docstrings,
        require_class=require_class_docstrings,
        require_function=require_function_docstrings,
    )

    # --- Placeholder analysis ---
    placeholder_violations = _check_placeholders(
        project_path=project_path,
        python_files=python_files,
        readme_files=readme_files,
        patterns=placeholder_patterns,
    )

    # --- Build canonical findings ---
    findings = _build_findings(
        missing_readme_violations=missing_readme_violations,
        docstring_violations=docstring_violations,
        placeholder_violations=placeholder_violations,
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
            "python_files": python_files,
            "readme_files": readme_files,
            "missing_readme_violations": missing_readme_violations,
            "docstring_violations": docstring_violations,
            "placeholder_violations": placeholder_violations,
        },
        metrics={
            "python_file_count": len(python_files),
            "readme_file_count": len(readme_files),
            "missing_readme_count": len(missing_readme_violations),
            "missing_module_docstring_count": sum(
                1 for v in docstring_violations if v["entity_type"] == "module"
            ),
            "missing_class_docstring_count": sum(
                1 for v in docstring_violations if v["entity_type"] == "class"
            ),
            "missing_function_docstring_count": sum(
                1 for v in docstring_violations if v["entity_type"] == "function"
            ),
            "placeholder_count": len(placeholder_violations),
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
    missing_readme_violations: list[dict[str, Any]],
    docstring_violations: list[dict[str, Any]],
    placeholder_violations: list[dict[str, Any]],
) -> list[AuditFinding]:
    """Convert all raw violations into canonical AuditFinding objects."""

    findings: list[AuditFinding] = []

    # --- Missing README: DOC-README-001 (WARNING) ---
    for v in missing_readme_violations:
        findings.append(
            AuditFinding(
                code="DOC-README-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "directory": v["directory"],
                    "expected_filenames": v["expected_filenames"],
                    "rule": "missing_readme",
                },
            )
        )

    # --- Missing docstring: DOC-DOCSTRING-001 (WARNING) ---
    for v in docstring_violations:
        findings.append(
            AuditFinding(
                code="DOC-DOCSTRING-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "entity_type": v["entity_type"],
                    "entity_name": v["entity_name"],
                    "line": v.get("line", 0),
                    "rule": "missing_docstring",
                },
            )
        )

    # --- Placeholder in docs: DOC-PLACEHOLDER-001 (WARNING) ---
    for v in placeholder_violations:
        findings.append(
            AuditFinding(
                code="DOC-PLACEHOLDER-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "matched_pattern": v["matched_pattern"],
                    "line": v.get("line", 0),
                    "context": v.get("context", ""),
                    "rule": "placeholder_in_documentation",
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
    bool,
    bool,
    bool,
    bool,
    list[str],
    list[str],
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

    require_readme_in_packages = bool(
        context.get("require_readme_in_packages", True)
    )
    require_module_docstrings = bool(
        context.get("require_module_docstrings", True)
    )
    require_class_docstrings = bool(
        context.get("require_class_docstrings", True)
    )
    require_function_docstrings = bool(
        context.get("require_function_docstrings", True)
    )

    placeholder_patterns = _validate_placeholder_patterns(
        context.get("placeholder_patterns", _DEFAULT_PLACEHOLDER_PATTERNS)
    )

    readme_filenames = _validate_readme_filenames(
        context.get("readme_filenames", ["README.md"])
    )

    return (
        project_path,
        ignored_directories,
        require_readme_in_packages,
        require_module_docstrings,
        require_class_docstrings,
        require_function_docstrings,
        placeholder_patterns,
        readme_filenames,
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


def _validate_placeholder_patterns(value: Any) -> list[str]:
    """Validate placeholder pattern list."""

    if not isinstance(value, (list, tuple)):
        raise ValueError("placeholder_patterns must be a list of strings.")

    patterns: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "placeholder_patterns entries must be non-empty strings."
            )
        patterns.append(item.strip())

    return patterns


def _validate_readme_filenames(value: Any) -> list[str]:
    """Validate README filename list."""

    if not isinstance(value, (list, tuple)):
        raise ValueError("readme_filenames must be a list of strings.")

    filenames: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "readme_filenames entries must be non-empty strings."
            )
        filenames.append(item.strip())

    return filenames


# =====================================================================
# DISCOVERY
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


def _discover_readme_files(
    project_path: Path,
    ignored_directories: frozenset[str],
    readme_filenames: list[str],
) -> list[str]:
    """Return deterministic POSIX paths for discoverable README files."""

    discovered: list[str] = []
    readme_set = frozenset(f.lower() for f in readme_filenames)

    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name for name in directory_names if name not in ignored_directories
        )

        root_path = Path(root)
        for file_name in sorted(file_names):
            if file_name.lower() not in readme_set:
                continue

            file_path = root_path / file_name
            discovered.append(
                _normalize_relative_path(file_path, project_path)
            )

    return sorted(discovered)


def _normalize_relative_path(file_path: Path, project_path: Path) -> str:
    """Normalize a discovered path as a relative POSIX string."""
    return file_path.relative_to(project_path).as_posix()


# =====================================================================
# README VALIDATION
# =====================================================================

def _check_missing_readmes(
    project_path: Path,
    python_files: list[str],
    readme_files: list[str],
    readme_filenames: list[str],
    require_in_packages: bool,
) -> list[dict[str, Any]]:
    """Detect directories that should have a README but don't."""

    violations: list[dict[str, Any]] = []

    readme_dirs: set[str] = set()
    for rf in readme_files:
        dir_path = str(Path(rf).parent)
        readme_dirs.add(dir_path)
        # Also mark the directory itself (normalize "." for root)
        if dir_path == ".":
            readme_dirs.add("")

    # --- Root README check ---
    if "" not in readme_dirs and "." not in readme_dirs:
        violations.append(
            {
                "type": "missing_readme",
                "directory": ".",
                "path": ".",
                "expected_filenames": readme_filenames,
                "message": (
                    f"Project root is missing a README file "
                    f"(expected one of: {readme_filenames})."
                ),
            }
        )

    if not require_in_packages:
        return violations

    # --- Package README check ---
    # A "package directory" is any directory that contains at least one .py file
    package_dirs: set[str] = set()
    for pf in python_files:
        parent = str(Path(pf).parent)
        package_dirs.add(parent)

    for pkg_dir in sorted(package_dirs):
        # Skip root — already checked above
        if pkg_dir == ".":
            continue
        if pkg_dir in readme_dirs:
            continue

        violations.append(
            {
                "type": "missing_readme",
                "directory": pkg_dir,
                "path": pkg_dir,
                "expected_filenames": readme_filenames,
                "message": (
                    f"Package directory {pkg_dir!r} is missing a README file "
                    f"(expected one of: {readme_filenames})."
                ),
            }
        )

    return violations


# =====================================================================
# DOCSTRING VALIDATION
# =====================================================================

def _check_docstrings(
    project_path: Path,
    python_files: list[str],
    require_module: bool,
    require_class: bool,
    require_function: bool,
) -> list[dict[str, Any]]:
    """Detect missing docstrings in modules, classes, and public functions."""

    violations: list[dict[str, Any]] = []

    for relative_path in sorted(python_files):
        file_path = project_path / relative_path

        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Module-level docstring
        if require_module:
            module_doc = _extract_docstring(tree)
            if module_doc is None:
                violations.append(
                    {
                        "type": "missing_docstring",
                        "entity_type": "module",
                        "entity_name": _module_name_from_path(relative_path),
                        "path": relative_path,
                        "line": 1,
                        "message": (
                            f"Module {relative_path!r} is missing a module-level docstring."
                        ),
                    }
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and require_class:
                if not node.name.startswith("_"):
                    class_doc = _extract_docstring(node)
                    if class_doc is None:
                        violations.append(
                            {
                                "type": "missing_docstring",
                                "entity_type": "class",
                                "entity_name": node.name,
                                "path": relative_path,
                                "line": getattr(node, "lineno", 0),
                                "message": (
                                    f"Public class {node.name!r} in {relative_path!r} "
                                    f"is missing a docstring."
                                ),
                            }
                        )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if require_function and _is_public_function(node):
                    func_doc = _extract_docstring(node)
                    if func_doc is None:
                        violations.append(
                            {
                                "type": "missing_docstring",
                                "entity_type": "function",
                                "entity_name": node.name,
                                "path": relative_path,
                                "line": getattr(node, "lineno", 0),
                                "message": (
                                    f"Public function {node.name!r} in {relative_path!r} "
                                    f"is missing a docstring."
                                ),
                            }
                        )

    return violations


def _extract_docstring(node: ast.AST) -> str | None:
    """Extract the docstring from a module, class, or function node."""

    if not hasattr(node, "body") or not node.body:
        return None

    first = node.body[0]
    if not isinstance(first, ast.Expr):
        return None

    value = first.value
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value

    return None


def _is_public_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the function is considered public."""

    # __init__ is special: it should have a docstring
    if node.name == "__init__":
        return True

    # Private (single underscore) or dunder (double underscore)
    if node.name.startswith("_"):
        return False

    return True


def _module_name_from_path(relative_path: str) -> str:
    """Convert a normalized Python path into its dotted module name."""
    path = Path(relative_path)
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else relative_path


# =====================================================================
# PLACEHOLDER DETECTION
# =====================================================================

def _check_placeholders(
    project_path: Path,
    python_files: list[str],
    readme_files: list[str],
    patterns: list[str],
) -> list[dict[str, Any]]:
    """Detect placeholder/todo patterns in documentation (docstrings and READMEs)."""

    violations: list[dict[str, Any]] = []
    # Store (original_pattern, compiled_regex) to preserve the raw pattern string
    compiled_patterns = [
        (p, re.compile(re.escape(p), re.IGNORECASE)) for p in patterns
    ]

    # --- Check README files ---
    for relative_path in sorted(readme_files):
        file_path = project_path / relative_path
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for original_pat, compiled in compiled_patterns:
            for match in compiled.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                context = _extract_context(content, match.start(), match.end())
                violations.append(
                    {
                        "type": "placeholder_in_documentation",
                        "path": relative_path,
                        "matched_pattern": original_pat,
                        "line": line_num,
                        "context": context,
                        "message": (
                            f"Placeholder pattern {original_pat!r} found in "
                            f"{relative_path!r} at line {line_num}."
                        ),
                    }
                )

    # --- Check Python docstrings ---
    for relative_path in sorted(python_files):
        file_path = project_path / relative_path
        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        docstrings = _collect_docstrings(tree, relative_path)
        for ds_text, line_num, entity_name, entity_type in docstrings:
            for original_pat, compiled in compiled_patterns:
                for match in compiled.finditer(ds_text):
                    ctx = _extract_context(ds_text, match.start(), match.end())
                    violations.append(
                        {
                            "type": "placeholder_in_documentation",
                            "path": relative_path,
                            "matched_pattern": original_pat,
                            "line": line_num,
                            "context": ctx,
                            "message": (
                                f"Placeholder pattern {original_pat!r} found in "
                                f"{entity_type} {entity_name!r} docstring "
                                f"({relative_path!r}, line {line_num})."
                            ),
                        }
                    )

    return violations


def _collect_docstrings(
    tree: ast.AST,
    relative_path: str,
) -> list[tuple[str, int, str, str]]:
    """Collect all docstrings from a module AST with their metadata."""

    results: list[tuple[str, int, str, str]] = []

    # Module docstring
    mod_doc = _extract_docstring(tree)
    if mod_doc is not None:
        results.append(
            (mod_doc, 1, _module_name_from_path(relative_path), "module")
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = _extract_docstring(node)
            if doc is not None:
                results.append(
                    (doc, getattr(node, "lineno", 0), node.name, "class")
                )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = _extract_docstring(node)
            if doc is not None:
                results.append(
                    (doc, getattr(node, "lineno", 0), node.name, "function")
                )

    return results


def _extract_context(text: str, start: int, end: int, radius: int = 30) -> str:
    """Extract a snippet of text around a match for context."""
    ctx_start = max(0, start - radius)
    ctx_end = min(len(text), end + radius)
    snippet = text[ctx_start:ctx_end]
    # Normalize whitespace
    snippet = " ".join(snippet.split())
    if ctx_start > 0:
        snippet = "..." + snippet
    if ctx_end < len(text):
        snippet = snippet + "..."
    return snippet


# =====================================================================
# PLUGIN WRAPPER
# =====================================================================

class DocumentationAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "DocumentationAuditorPlugin",
    "run",
]