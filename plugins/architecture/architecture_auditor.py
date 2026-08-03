"""
Architecture Auditor MVP — Commit 0013-0019 + AuditResult Canónico.

Emite findings formales del dominio UAAF para todas las violaciones detectadas.
"""

from __future__ import annotations

import ast
import fnmatch
import io
import os
import re
import sys
import tokenize
import uuid
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


PLUGIN_ID = "architecture-auditor"
PLUGIN_VERSION = "1.6.0"
AUDIT_TYPE = "architecture"
_DEFAULT_MAX_CYCLOMATIC_COMPLEXITY = 10

_KNOWN_ENTRY_POINT_NAMES = frozenset(
    {
        "cli",
        "execute",
        "handler",
        "lambda_handler",
        "run",
    }
)

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

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "forbidden_imports",
    "layers",
    "require_package_initializers",
    "max_cyclomatic_complexity",
}

_FALLBACK_STDLIB_MODULES: frozenset[str] = frozenset(
    {
        "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
        "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
        "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
        "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
        "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes",
        "curses", "dataclasses", "datetime", "dbm", "decimal", "difflib",
        "dis", "distutils", "doctest", "email", "encodings", "enum", "errno",
        "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
        "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq",
        "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
        "importlib", "inspect", "io", "ipaddress", "itertools", "json",
        "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
        "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
        "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
        "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
        "queue", "quopri", "random", "re", "readline", "reprlib",
        "resource", "rlcompleter", "runpy", "sched", "secrets",
        "select", "selectors", "shelve", "shlex", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver",
        "spwd", "sqlite3", "ssl", "stat", "statistics", "string",
        "stringprep", "struct", "subprocess", "sunau", "symtable",
        "sys", "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib",
        "tempfile", "termios", "test", "textwrap", "threading", "time",
        "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
        "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "winreg",
        "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
        "zipfile", "zipimport", "zlib", "_thread", "__future__",
    }
)


# =====================================================================
# PUBLIC API
# =====================================================================

def run(context: Any) -> dict[str, Any]:
    """Execute full architecture audit and emit canonical AuditResult."""

    started_at = _utc_now_iso()
    t0 = datetime.now(timezone.utc)

    project_path, ignored_directories = _validate_context(context)
    max_cyclomatic_complexity = _validate_max_cyclomatic_complexity(
        context.get(
            "max_cyclomatic_complexity",
            _DEFAULT_MAX_CYCLOMATIC_COMPLEXITY,
        )
    )
    python_files = _discover_python_files(project_path, ignored_directories)
    modules, packages = _build_module_index(python_files)

    imports, dependency_edges = _extract_imports(
        python_files=python_files,
        project_path=project_path,
        modules=modules,
        packages=packages,
    )

    dependency_cycles = _detect_cycles(dependency_edges)

    # --- Rule evaluation ---
    layers_config = context.get("layers")
    layer_violations: list[dict[str, Any]] = []
    if layers_config is not None:
        layer_violations = _validate_layers(
            dependency_edges=dependency_edges,
            modules=modules,
            layers_config=layers_config,
        )

    forbidden_imports_config = context.get("forbidden_imports")
    forbidden_violations: list[dict[str, Any]] = []
    if forbidden_imports_config is not None:
        forbidden_violations = _validate_forbidden_imports(
            imports=imports,
            forbidden_config=forbidden_imports_config,
        )

    require_init = context.get("require_package_initializers", False)
    missing_init_violations: list[dict[str, Any]] = []
    if require_init:
        missing_init_violations = _validate_package_initializers(
            packages=packages,
            modules=modules,
        )

    module_metrics, complexity_violations, dead_code_violations = (
        _analyze_semantics(
            python_files=python_files,
            project_path=project_path,
            modules=modules,
            packages=packages,
            dependency_edges=dependency_edges,
            max_cyclomatic_complexity=max_cyclomatic_complexity,
        )
    )
    semantic_metrics = _aggregate_semantic_metrics(
        module_metrics=module_metrics,
        complexity_violations=complexity_violations,
        dead_code_violations=dead_code_violations,
        threshold=max_cyclomatic_complexity,
    )

    local_import_count = sum(
        1 for imp in imports if imp["classification"] == "local"
    )

    # --- Build canonical findings ---
    findings = _build_findings(
        cycles=dependency_cycles,
        layer_violations=layer_violations,
        forbidden_violations=forbidden_violations,
        missing_init_violations=missing_init_violations,
        complexity_violations=complexity_violations,
        dead_code_violations=dead_code_violations,
    )

    # --- Determine status ---
    if findings:
        status = AuditStatus.COMPLETED_WITH_FINDINGS
    else:
        status = AuditStatus.COMPLETED

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
            "modules": modules,
            "packages": packages,
            "dependency_cycles": dependency_cycles,
            "imports": imports,
            "dependency_edges": dependency_edges,
            "layer_violations": layer_violations,
            "forbidden_violations": forbidden_violations,
            "missing_package_initializer_violations": missing_init_violations,
            "module_metrics": module_metrics,
            "complexity_violations": complexity_violations,
            "dead_code_violations": dead_code_violations,
            "semantic_analysis": {
                "max_cyclomatic_complexity": max_cyclomatic_complexity,
                "complexity_base": 1,
                "boolean_operator_increment": "operands_minus_one",
                "nested_function_bodies_excluded_from_parent": True,
            },
        },
        metrics={
            "python_file_count": len(python_files),
            "module_count": len(modules),
            "package_count": len(packages),
            "local_import_count": local_import_count,
            "dependency_edge_count": len(dependency_edges),
            "circular_dependency_count": len(dependency_cycles),
            "forbidden_import_count": len(forbidden_violations),
            "layer_violation_count": len(layer_violations),
            "missing_package_initializer_count": len(missing_init_violations),
            **semantic_metrics,
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
    cycles: list[list[str]],
    layer_violations: list[dict[str, Any]],
    forbidden_violations: list[dict[str, Any]],
    missing_init_violations: list[dict[str, Any]],
    complexity_violations: list[dict[str, Any]] | None = None,
    dead_code_violations: list[dict[str, Any]] | None = None,
) -> list[AuditFinding]:
    """Convert all raw violations into canonical AuditFinding objects."""

    findings: list[AuditFinding] = []

    # --- Cycles: ARCH-CYCLE-001 (ERROR) ---
    for cycle in cycles:
        cycle_str = " -> ".join(cycle) + " -> " + cycle[0]
        findings.append(
            AuditFinding(
                code="ARCH-CYCLE-001",
                severity=FindingSeverity.ERROR,
                path=cycle[0],
                message=f"Circular dependency detected: {cycle_str}",
                details={
                    "cycle_nodes": cycle,
                    "cycle_display": cycle_str,
                    "rule": "dependency_cycle",
                },
            )
        )

    # --- Layer violations: ARCH-LAYER-001 (WARNING) ---
    for violation in layer_violations:
        findings.append(
            AuditFinding(
                code="ARCH-LAYER-001",
                severity=FindingSeverity.WARNING,
                path=violation["source"],
                message=violation["message"],
                details={
                    "source": violation["source"],
                    "source_layer": violation["source_layer"],
                    "target": violation["target"],
                    "target_layer": violation["target_layer"],
                    "rule": "layer_violation",
                },
            )
        )

    # --- Forbidden imports: ARCH-FORBIDDEN-001 (ERROR) ---
    for violation in forbidden_violations:
        findings.append(
            AuditFinding(
                code="ARCH-FORBIDDEN-001",
                severity=FindingSeverity.ERROR,
                path=violation["source"],
                message=violation["message"],
                details={
                    "source": violation["source"],
                    "target": violation["target"],
                    "matched_pattern": violation["matched_pattern"],
                    "scope": violation["scope"],
                    "rule": "forbidden_import",
                },
            )
        )

    # --- Missing __init__.py: ARCH-INIT-001 (WARNING) ---
    for violation in missing_init_violations:
        findings.append(
            AuditFinding(
                code="ARCH-INIT-001",
                severity=FindingSeverity.WARNING,
                path=violation["path"],
                message=violation["message"],
                details={
                    "package": violation["package"],
                    "modules_in_package": violation["modules"],
                    "rule": "missing_package_initializer",
                },
            )
        )

    # --- Cyclomatic complexity: ARCH-COMPLEX-001 (WARNING) ---
    for violation in sorted(
        complexity_violations or [],
        key=lambda item: (
            item["path"],
            item["line"],
            item["qualified_name"],
        ),
    ):
        findings.append(
            AuditFinding(
                code="ARCH-COMPLEX-001",
                severity=FindingSeverity.WARNING,
                path=violation["path"],
                message=(
                    f"{violation['symbol_type'].replace('_', ' ').title()} "
                    f"{violation['qualified_name']!r} has cyclomatic complexity "
                    f"{violation['complexity']}, exceeding the configured "
                    f"threshold {violation['threshold']}."
                ),
                details={
                    "module": violation["module"],
                    "qualified_name": violation["qualified_name"],
                    "line": violation["line"],
                    "complexity": violation["complexity"],
                    "threshold": violation["threshold"],
                    "symbol_type": violation["symbol_type"],
                    "rule": violation["rule"],
                },
            )
        )

    # --- Conservative dead code: ARCH-DEAD-001 (WARNING) ---
    for violation in sorted(
        dead_code_violations or [],
        key=_dead_code_sort_key,
    ):
        if violation["kind"] == "unused_import":
            message = (
                f"Import binding {violation['binding']!r} is not statically "
                f"referenced in module {violation['module']!r}."
            )
            details = {
                "kind": "unused_import",
                "module": violation["module"],
                "symbol": violation["symbol"],
                "qualified_name": violation["qualified_name"],
                "line": violation["line"],
                "binding": violation["binding"],
                "imported": violation["imported"],
                "classification": violation["classification"],
                "import_type": violation["import_type"],
                "symbol_type": violation["symbol_type"],
                "rule": violation["rule"],
            }
        else:
            message = (
                f"Module-level function {violation['qualified_name']!r} has "
                "no statically demonstrable project reference."
            )
            details = {
                "kind": "unused_function",
                "module": violation["module"],
                "symbol": violation["symbol"],
                "qualified_name": violation["qualified_name"],
                "line": violation["line"],
                "symbol_type": violation["symbol_type"],
                "rule": violation["rule"],
            }

        findings.append(
            AuditFinding(
                code="ARCH-DEAD-001",
                severity=FindingSeverity.WARNING,
                path=violation["path"],
                message=message,
                details=details,
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
) -> tuple[Path, frozenset[str]]:
    """Validate context and return the project path and exclusions."""

    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary.")

    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS
    if unknown_fields:
        raise ValueError(
            "context contains unknown fields: "
            f"{sorted(unknown_fields)}"
        )

    raw_project_path = context.get("project_path")
    if not isinstance(raw_project_path, (str, Path)):
        raise ValueError(
            "context must contain a valid project_path."
        )

    project_path = Path(raw_project_path).expanduser().resolve()
    if not project_path.is_dir():
        raise ValueError(
            f"project_path must reference an existing directory: "
            f"{project_path}"
        )

    audit_type = context.get("audit_type")
    if audit_type is not None and audit_type != AUDIT_TYPE:
        raise ValueError(
            f"audit_type must be {AUDIT_TYPE!r}."
        )

    ignored_directories = _validate_ignored_directories(
        context.get("ignored_directories", [])
    )

    return project_path, ignored_directories


def _validate_ignored_directories(
    value: Any,
) -> frozenset[str]:
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


# =====================================================================
# DISCOVERY & INDEX (Commits 0013-0014)
# =====================================================================

def _discover_python_files(
    project_path: Path,
    ignored_directories: frozenset[str],
) -> list[str]:
    """Return deterministic POSIX paths for discoverable Python files."""

    discovered: list[str] = []

    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in ignored_directories
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


def _normalize_relative_path(
    file_path: Path,
    project_path: Path,
) -> str:
    """Normalize a discovered path as a relative POSIX string."""

    return file_path.relative_to(project_path).as_posix()


def _build_module_index(
    python_files: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build deterministic module and package records from Python paths."""

    module_records: list[dict[str, Any]] = []
    package_modules: dict[str, list[str]] = {}
    package_paths: dict[str, str] = {}

    for relative_path in sorted(python_files):
        module_name = _module_name_from_path(relative_path)
        package_name = _package_name_from_path(relative_path)
        is_package_initializer = relative_path.endswith("/__init__.py")

        module_records.append(
            {
                "name": module_name,
                "path": relative_path,
                "package": package_name,
                "is_package_initializer": is_package_initializer,
            }
        )

        if package_name:
            package_modules.setdefault(package_name, []).append(module_name)
            package_paths.setdefault(
                package_name,
                package_name.replace(".", "/"),
            )

    package_records = [
        {
            "name": package_name,
            "path": package_paths[package_name],
            "modules": sorted(package_modules[package_name]),
        }
        for package_name in sorted(package_modules)
    ]

    return module_records, package_records


def _module_name_from_path(relative_path: str) -> str:
    """Convert a normalized Python path into its dotted module name."""

    path = Path(relative_path)
    parts = list(path.with_suffix("").parts)

    if parts and parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def _package_name_from_path(relative_path: str) -> str:
    """Return the dotted package that owns a normalized Python path."""

    path = Path(relative_path)
    module_parts = list(path.with_suffix("").parts)

    if module_parts and module_parts[-1] == "__init__":
        module_parts.pop()
        return ".".join(module_parts)

    return ".".join(module_parts[:-1])


# =====================================================================
# AST IMPORT EXTRACTION (Commit 0015)
# =====================================================================

def _extract_imports(
    python_files: list[str],
    project_path: Path,
    modules: list[dict[str, Any]],
    packages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Extract and classify import statements from all Python files via AST."""

    local_module_names: set[str] = {m["name"] for m in modules}
    local_package_names: set[str] = {p["name"] for p in packages}

    try:
        stdlib_modules: set[str] = set(sys.stdlib_module_names)
    except AttributeError:
        stdlib_modules = set(_FALLBACK_STDLIB_MODULES)

    imports: list[dict[str, Any]] = []
    edges: list[tuple[str, str]] = []

    for relative_path in sorted(python_files):
        source_module = _module_name_from_path(relative_path)
        file_path = project_path / relative_path

        try:
            source_text = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    classification = _classify_import(
                        target, local_module_names, local_package_names, stdlib_modules
                    )
                    imports.append(
                        {
                            "source": source_module,
                            "target": target,
                            "type": "absolute",
                            "classification": classification,
                            "line": getattr(node, "lineno", 0),
                        }
                    )
                    if classification == "local":
                        edges.append((source_module, target))

            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    target = node.module or ""
                    classification = _classify_import(
                        target, local_module_names, local_package_names, stdlib_modules
                    )
                    imports.append(
                        {
                            "source": source_module,
                            "target": target,
                            "type": "absolute",
                            "classification": classification,
                            "line": getattr(node, "lineno", 0),
                        }
                    )
                    if classification == "local":
                        edges.append((source_module, target))

                else:
                    resolved_targets = _resolve_relative_import(
                        source_module, node.level, node.module, local_module_names
                    )
                    for target in resolved_targets:
                        classification = _classify_import(
                            target, local_module_names, local_package_names, stdlib_modules
                        )
                        imports.append(
                            {
                                "source": source_module,
                                "target": target,
                                "type": "relative",
                                "level": node.level,
                                "module": node.module,
                                "classification": classification,
                                "line": getattr(node, "lineno", 0),
                            }
                        )
                        if classification == "local":
                            edges.append((source_module, target))

    return imports, edges


def _resolve_relative_import(
    source_module: str,
    level: int,
    module: str | None,
    local_module_names: set[str],
) -> list[str]:
    """Resolve relative imports to absolute dotted module names."""

    parts = source_module.split(".")

    if parts[-1] == "__init__":
        base_parts = parts[:-1]
        levels_to_remove = level - 1
    else:
        base_parts = parts[:-1]
        levels_to_remove = level - 1

    if levels_to_remove > 0:
        if len(base_parts) < levels_to_remove:
            return []
        base_parts = base_parts[:-levels_to_remove]

    if not base_parts:
        return []

    if module:
        resolved = ".".join(base_parts) + "." + module
        return [resolved]

    base = ".".join(base_parts)
    return [base]


def _classify_import(
    target: str,
    local_modules: set[str],
    local_packages: set[str],
    stdlib_modules: set[str],
) -> str:
    """Classify an import target as local, stdlib, third_party, or unknown."""

    if not target:
        return "unknown"

    if target in local_modules or target in local_packages:
        return "local"

    for mod in local_modules:
        if mod.startswith(target + "."):
            return "local"
    for pkg in local_packages:
        if pkg.startswith(target + "."):
            return "local"

    root = target.split(".")[0]
    if root in stdlib_modules:
        return "stdlib"

    return "third_party"


# =====================================================================
# SEMANTIC ANALYSIS — CYCLOMATIC COMPLEXITY, DEAD CODE, METRICS
# =====================================================================

def _validate_max_cyclomatic_complexity(value: Any) -> int:
    """Validate and normalize the configured complexity threshold."""

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(
            "max_cyclomatic_complexity must be a positive integer."
        )

    return value


def _analyze_semantics(
    python_files: list[str],
    project_path: Path,
    modules: list[dict[str, Any]],
    packages: list[dict[str, Any]],
    dependency_edges: list[tuple[str, str]],
    max_cyclomatic_complexity: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Run deterministic, conservative AST semantic analysis."""

    local_module_names = {module["name"] for module in modules}
    local_package_names = {package["name"] for package in packages}

    try:
        stdlib_modules: set[str] = set(sys.stdlib_module_names)
    except AttributeError:
        stdlib_modules = set(_FALLBACK_STDLIB_MODULES)

    dependencies_by_module: dict[str, set[str]] = {}
    for source, target in dependency_edges:
        dependencies_by_module.setdefault(source, set()).add(target)

    semantic_modules: list[dict[str, Any]] = []
    parsed_modules: list[dict[str, Any]] = []

    for relative_path in sorted(python_files):
        module_name = _module_name_from_path(relative_path)
        file_path = project_path / relative_path
        local_dependencies = sorted(
            dependencies_by_module.get(module_name, set())
        )

        try:
            source_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            semantic_modules.append(
                _empty_semantic_module_record(
                    module_name=module_name,
                    relative_path=relative_path,
                    parse_status="decode_error",
                    local_dependencies=local_dependencies,
                )
            )
            continue

        physical_lines = _count_physical_lines(source_text)
        lines_of_code = _count_lines_of_code(source_text)

        try:
            tree = ast.parse(source_text, filename=str(file_path))
        except SyntaxError:
            record = _empty_semantic_module_record(
                module_name=module_name,
                relative_path=relative_path,
                parse_status="syntax_error",
                local_dependencies=local_dependencies,
            )
            record["physical_lines"] = physical_lines
            record["lines_of_code"] = lines_of_code
            semantic_modules.append(record)
            continue

        parent_map = _build_parent_map(tree)
        function_records = _collect_function_records(
            tree=tree,
            module_name=module_name,
            relative_path=relative_path,
        )
        import_bindings = _collect_import_bindings(
            tree=tree,
            source_text=source_text,
            source_module=module_name,
            relative_path=relative_path,
            local_module_names=local_module_names,
            local_package_names=local_package_names,
            stdlib_modules=stdlib_modules,
            parent_map=parent_map,
        )
        exports, dynamic_exports = _extract_static_all(tree)
        loaded_names = _collect_loaded_names(tree)
        loaded_names.update(_collect_annotation_string_names(tree))
        dynamic_usage = _uses_dynamic_symbol_access(tree)
        has_substantive_code = _module_has_substantive_code(tree)
        has_module_getattr = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in {"__getattr__", "__dir__"}
            for node in tree.body
        )

        total_complexity = sum(
            function["complexity"] for function in function_records
        )
        maximum_complexity = max(
            (function["complexity"] for function in function_records),
            default=0,
        )
        average_complexity = _safe_average(
            total_complexity,
            len(function_records),
        )

        record = {
            "module": module_name,
            "path": relative_path,
            "parse_status": "parsed",
            "physical_lines": physical_lines,
            "lines_of_code": lines_of_code,
            "function_count": len(function_records),
            "async_function_count": sum(
                1 for function in function_records if function["is_async"]
            ),
            "module_level_function_count": sum(
                1
                for function in function_records
                if function["scope"] == "module"
            ),
            "class_count": sum(
                1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ),
            "complexity_total": total_complexity,
            "complexity_average": average_complexity,
            "complexity_max": maximum_complexity,
            "import_count": len(import_bindings),
            "import_statement_count": sum(
                1
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ),
            "local_dependencies": local_dependencies,
            "local_dependency_count": len(local_dependencies),
            "potentially_unused_imports": [],
            "potentially_unused_import_count": 0,
            "potentially_unused_functions": [],
            "potentially_unused_function_count": 0,
            "complexity_finding_count": 0,
            "dead_code_finding_count": 0,
            "functions": function_records,
        }

        semantic_modules.append(record)
        parsed_modules.append(
            {
                "module": module_name,
                "path": relative_path,
                "source_text": source_text,
                "tree": tree,
                "parent_map": parent_map,
                "functions": function_records,
                "imports": import_bindings,
                "exports": exports,
                "dynamic_exports": dynamic_exports,
                "loaded_names": loaded_names,
                "dynamic_usage": dynamic_usage,
                "has_substantive_code": has_substantive_code,
                "has_module_getattr": has_module_getattr,
                "record": record,
            }
        )

    symbol_references, wildcard_imported_modules = (
        _collect_project_symbol_references(
            parsed_modules=parsed_modules,
            local_module_names=local_module_names,
            local_package_names=local_package_names,
        )
    )

    complexity_violations: list[dict[str, Any]] = []
    dead_code_violations: list[dict[str, Any]] = []

    for module_data in parsed_modules:
        module_complexity_violations = [
            {
                "path": module_data["path"],
                "module": module_data["module"],
                "qualified_name": function["qualified_name"],
                "line": function["line"],
                "complexity": function["complexity"],
                "threshold": max_cyclomatic_complexity,
                "symbol_type": function["symbol_type"],
                "rule": "cyclomatic_complexity",
            }
            for function in module_data["functions"]
            if function["complexity"] > max_cyclomatic_complexity
        ]

        unused_imports = _find_unused_imports(module_data)
        unused_functions = _find_unused_functions(
            module_data=module_data,
            symbol_references=symbol_references,
            wildcard_imported_modules=wildcard_imported_modules,
        )

        module_dead_code_violations = sorted(
            [*unused_imports, *unused_functions],
            key=_dead_code_sort_key,
        )

        module_data["record"]["potentially_unused_imports"] = [
            _public_unused_import_record(violation)
            for violation in unused_imports
        ]
        module_data["record"]["potentially_unused_import_count"] = len(
            unused_imports
        )
        module_data["record"]["potentially_unused_functions"] = [
            _public_unused_function_record(violation)
            for violation in unused_functions
        ]
        module_data["record"]["potentially_unused_function_count"] = len(
            unused_functions
        )
        module_data["record"]["complexity_finding_count"] = len(
            module_complexity_violations
        )
        module_data["record"]["dead_code_finding_count"] = len(
            module_dead_code_violations
        )

        complexity_violations.extend(module_complexity_violations)
        dead_code_violations.extend(module_dead_code_violations)

    complexity_violations.sort(
        key=lambda violation: (
            violation["path"],
            violation["line"],
            violation["qualified_name"],
        )
    )
    dead_code_violations.sort(key=_dead_code_sort_key)
    semantic_modules.sort(key=lambda record: record["path"])

    return semantic_modules, complexity_violations, dead_code_violations


def _empty_semantic_module_record(
    module_name: str,
    relative_path: str,
    parse_status: str,
    local_dependencies: list[str],
) -> dict[str, Any]:
    """Return a serializable zeroed semantic record for an unparsed file."""

    return {
        "module": module_name,
        "path": relative_path,
        "parse_status": parse_status,
        "physical_lines": 0,
        "lines_of_code": 0,
        "function_count": 0,
        "async_function_count": 0,
        "module_level_function_count": 0,
        "class_count": 0,
        "complexity_total": 0,
        "complexity_average": 0.0,
        "complexity_max": 0,
        "import_count": 0,
        "import_statement_count": 0,
        "local_dependencies": list(local_dependencies),
        "local_dependency_count": len(local_dependencies),
        "potentially_unused_imports": [],
        "potentially_unused_import_count": 0,
        "potentially_unused_functions": [],
        "potentially_unused_function_count": 0,
        "complexity_finding_count": 0,
        "dead_code_finding_count": 0,
        "functions": [],
    }


def _count_physical_lines(source_text: str) -> int:
    """Count physical source lines without creating a trailing phantom line."""

    return len(source_text.splitlines())


def _count_lines_of_code(source_text: str) -> int:
    """Count lines containing non-comment Python tokens."""

    significant_lines: set[int] = set()
    ignored_token_types = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source_text).readline)
        for token in tokens:
            if token.type in ignored_token_types:
                continue
            start_line = token.start[0]
            end_line = token.end[0]
            significant_lines.update(range(start_line, end_line + 1))
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return sum(
            1
            for line in source_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )

    return len(significant_lines)


def _safe_average(total: int, count: int) -> float:
    """Return a deterministic four-decimal average."""

    if count == 0:
        return 0.0
    return round(total / count, 4)


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Build a deterministic parent lookup for AST safeguards."""

    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


class _CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Count documented decision points inside one function body."""

    _BREAKDOWN_KEYS = (
        "if",
        "for",
        "async_for",
        "while",
        "except",
        "and",
        "or",
        "ternary",
        "match_case",
        "comprehension_if",
    )

    def __init__(self) -> None:
        self.increment = 0
        self.breakdown = {key: 0 for key in self._BREAKDOWN_KEYS}

    def _add(self, key: str, amount: int = 1) -> None:
        self.increment += amount
        self.breakdown[key] += amount

    def visit_If(self, node: ast.If) -> None:
        self._add("if")
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._add("for")
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._add("async_for")
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._add("while")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._add("except")
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        amount = max(0, len(node.values) - 1)
        if isinstance(node.op, ast.And):
            self._add("and", amount)
        elif isinstance(node.op, ast.Or):
            self._add("or", amount)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._add("ternary")
        self.generic_visit(node)

    def visit_match_case(self, node: ast.match_case) -> None:
        self._add("match_case")
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._add("comprehension_if", len(node.ifs))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return None


def _calculate_cyclomatic_complexity(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[int, dict[str, int]]:
    """Calculate complexity starting at one for a single function."""

    visitor = _CyclomaticComplexityVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return 1 + visitor.increment, dict(visitor.breakdown)


class _FunctionCollector(ast.NodeVisitor):
    """Collect functions, methods, and nested functions with stable names."""

    def __init__(self, module_name: str, relative_path: str) -> None:
        self.module_name = module_name
        self.relative_path = relative_path
        self.scope_stack: list[tuple[str, str]] = []
        self.records: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope_stack.append(("class", node.name))
        for statement in node.body:
            self.visit(statement)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        qualified_name = self._qualified_name(node.name)
        function_scope_present = any(
            kind == "function" for kind, _name in self.scope_stack
        )
        class_scope_present = any(
            kind == "class" for kind, _name in self.scope_stack
        )

        if function_scope_present:
            scope = "nested"
            symbol_type = (
                "nested_async_function" if is_async else "nested_function"
            )
        elif class_scope_present:
            scope = "class"
            symbol_type = "async_method" if is_async else "method"
        else:
            scope = "module"
            symbol_type = "async_function" if is_async else "function"

        complexity, breakdown = _calculate_cyclomatic_complexity(node)
        decorator_names = sorted(_decorator_names(node.decorator_list))

        self.records.append(
            {
                "name": node.name,
                "qualified_name": qualified_name,
                "module": self.module_name,
                "path": self.relative_path,
                "line": getattr(node, "lineno", 0),
                "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                "symbol_type": symbol_type,
                "scope": scope,
                "is_async": is_async,
                "is_method": scope == "class",
                "is_nested": scope == "nested",
                "is_decorated": bool(node.decorator_list),
                "decorators": decorator_names,
                "complexity": complexity,
                "complexity_breakdown": breakdown,
            }
        )

        self.scope_stack.append(("function", node.name))
        for statement in node.body:
            self.visit(statement)
        self.scope_stack.pop()

    def _qualified_name(self, name: str) -> str:
        parts: list[str] = []
        for kind, scope_name in self.scope_stack:
            parts.append(scope_name)
            if kind == "function":
                parts.append("<locals>")
        parts.append(name)
        return ".".join(parts)


def _collect_function_records(
    tree: ast.AST,
    module_name: str,
    relative_path: str,
) -> list[dict[str, Any]]:
    """Return ordered semantic records for every function-like symbol."""

    collector = _FunctionCollector(module_name, relative_path)
    collector.visit(tree)
    return sorted(
        collector.records,
        key=lambda record: (record["line"], record["qualified_name"]),
    )


def _decorator_names(decorators: list[ast.expr]) -> set[str]:
    """Extract stable dotted decorator names where statically available."""

    names: set[str] = set()
    for decorator in decorators:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        chain = _attribute_chain(target)
        if chain:
            names.add(".".join(chain))
    return names


def _collect_import_bindings(
    tree: ast.AST,
    source_text: str,
    source_module: str,
    relative_path: str,
    local_module_names: set[str],
    local_package_names: set[str],
    stdlib_modules: set[str],
    parent_map: dict[ast.AST, ast.AST],
) -> list[dict[str, Any]]:
    """Collect individual import bindings for conservative usage analysis."""

    lines = source_text.splitlines()
    bindings: list[dict[str, Any]] = []
    import_nodes = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ),
        key=lambda node: (
            getattr(node, "lineno", 0),
            getattr(node, "col_offset", 0),
        ),
    )

    for node in import_nodes:
        is_top_level = parent_map.get(node) is tree
        in_try = _has_ancestor_type(node, parent_map, (ast.Try, ast.TryStar))
        in_type_checking = _has_type_checking_ancestor(node, parent_map)
        suppressed = _line_has_unused_import_suppression(
            lines,
            getattr(node, "lineno", 0),
            getattr(node, "end_lineno", getattr(node, "lineno", 0)),
        )

        if isinstance(node, ast.Import):
            for alias in node.names:
                binding = alias.asname or alias.name.split(".")[0]
                target_module = alias.name
                classification = _classify_import(
                    target_module,
                    local_module_names,
                    local_package_names,
                    stdlib_modules,
                )
                bindings.append(
                    {
                        "path": relative_path,
                        "module": source_module,
                        "line": getattr(node, "lineno", 0),
                        "column": getattr(node, "col_offset", 0),
                        "binding": binding,
                        "imported": target_module,
                        "target_module": target_module,
                        "imported_name": None,
                        "import_type": "import",
                        "classification": classification,
                        "is_top_level": is_top_level,
                        "in_try": in_try,
                        "in_type_checking": in_type_checking,
                        "suppressed": suppressed,
                        "is_star": False,
                        "explicit_reexport": (
                            is_top_level
                            and alias.asname is not None
                            and alias.asname == alias.name.split(".")[-1]
                        ),
                    }
                )
            continue

        base_module = _resolve_import_from_base(
            source_module=source_module,
            relative_path=relative_path,
            level=node.level,
            module=node.module,
        )
        classification = _classify_import(
            base_module,
            local_module_names,
            local_package_names,
            stdlib_modules,
        )

        for alias in node.names:
            is_star = alias.name == "*"
            binding = alias.asname or alias.name
            imported = (
                f"{base_module}.{alias.name}"
                if base_module and not is_star
                else base_module or alias.name
            )
            bindings.append(
                {
                    "path": relative_path,
                    "module": source_module,
                    "line": getattr(node, "lineno", 0),
                    "column": getattr(node, "col_offset", 0),
                    "binding": binding,
                    "imported": imported,
                    "target_module": base_module,
                    "imported_name": alias.name,
                    "import_type": "from",
                    "classification": classification,
                    "is_top_level": is_top_level,
                    "in_try": in_try,
                    "in_type_checking": in_type_checking,
                    "suppressed": suppressed,
                    "is_star": is_star,
                    "explicit_reexport": (
                        is_top_level
                        and (
                            relative_path.endswith("/__init__.py")
                            or relative_path == "__init__.py"
                            or (
                                alias.asname is not None
                                and alias.asname == alias.name
                            )
                        )
                    ),
                }
            )

    return sorted(
        bindings,
        key=lambda binding: (
            binding["line"],
            binding["column"],
            binding["binding"],
            binding["imported"],
        ),
    )


def _resolve_import_from_base(
    source_module: str,
    relative_path: str,
    level: int,
    module: str | None,
) -> str:
    """Resolve the module portion of ImportFrom for semantic references."""

    if level == 0:
        return module or ""

    if relative_path.endswith("/__init__.py") or relative_path == "__init__.py":
        package_parts = source_module.split(".") if source_module else []
    else:
        package_parts = source_module.split(".")[:-1] if source_module else []

    levels_to_remove = level - 1
    if levels_to_remove > len(package_parts):
        return ""
    if levels_to_remove:
        package_parts = package_parts[:-levels_to_remove]
    if module:
        package_parts.extend(module.split("."))
    return ".".join(part for part in package_parts if part)


def _has_ancestor_type(
    node: ast.AST,
    parent_map: dict[ast.AST, ast.AST],
    ancestor_types: tuple[type[ast.AST], ...],
) -> bool:
    current = parent_map.get(node)
    while current is not None:
        if isinstance(current, ancestor_types):
            return True
        current = parent_map.get(current)
    return False


def _has_type_checking_ancestor(
    node: ast.AST,
    parent_map: dict[ast.AST, ast.AST],
) -> bool:
    current = parent_map.get(node)
    while current is not None:
        if isinstance(current, ast.If) and _is_type_checking_guard(current.test):
            return True
        current = parent_map.get(current)
    return False


def _is_type_checking_guard(node: ast.AST) -> bool:
    chain = _attribute_chain(node)
    return bool(chain and chain[-1] == "TYPE_CHECKING")


def _line_has_unused_import_suppression(
    lines: list[str],
    start_line: int,
    end_line: int,
) -> bool:
    markers = ("# noqa", "# type: ignore", "# nosec")
    for line_number in range(max(start_line, 1), min(end_line, len(lines)) + 1):
        line = lines[line_number - 1].lower()
        if any(marker in line for marker in markers):
            return True
    return False


def _collect_loaded_names(tree: ast.AST) -> set[str]:
    """Collect every statically loaded identifier in a module."""

    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _collect_annotation_string_names(tree: ast.AST) -> set[str]:
    """Collect identifiers from string forward references in annotations."""

    names: set[str] = set()
    annotation_nodes: list[ast.AST] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.AnnAssign, ast.arg)) and node.annotation:
            annotation_nodes.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns:
                annotation_nodes.append(node.returns)

    for annotation in annotation_nodes:
        for child in ast.walk(annotation):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                names.update(re.findall(r"[A-Za-z_]\w*", child.value))

    return names


def _extract_static_all(tree: ast.Module) -> tuple[set[str], bool]:
    """Extract static __all__ exports and report unresolved dynamic updates."""

    exports: set[str] = set()
    dynamic = False

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = []
            value: ast.expr | None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value = node.value
            else:
                targets = [node.target]
                value = node.value

            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
                literal = _literal_string_collection(value)
                if literal is None:
                    dynamic = True
                else:
                    exports.update(literal)

        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                literal = _literal_string_collection(node.value)
                if literal is None:
                    dynamic = True
                else:
                    exports.update(literal)

        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                owner = call.func.value
                if isinstance(owner, ast.Name) and owner.id == "__all__":
                    if call.func.attr == "append" and len(call.args) == 1:
                        literal = _literal_string(call.args[0])
                        if literal is None:
                            dynamic = True
                        else:
                            exports.add(literal)
                    elif call.func.attr == "extend" and len(call.args) == 1:
                        literal_collection = _literal_string_collection(call.args[0])
                        if literal_collection is None:
                            dynamic = True
                        else:
                            exports.update(literal_collection)
                    else:
                        dynamic = True

    return exports, dynamic


def _literal_string_collection(node: ast.AST | None) -> set[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return None
    values: set[str] = set()
    for element in node.elts:
        literal = _literal_string(element)
        if literal is None:
            return None
        values.add(literal)
    return values


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _uses_dynamic_symbol_access(tree: ast.AST) -> bool:
    """Detect constructs that make static unused-symbol proof unsafe."""

    dynamic_call_names = {
        "eval",
        "exec",
        "globals",
        "locals",
        "vars",
        "__import__",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        chain = _attribute_chain(node.func)
        if chain and chain[-1] in dynamic_call_names:
            return True
    return False


def _module_has_substantive_code(tree: ast.Module) -> bool:
    """Distinguish executable modules from import-only aggregators."""

    for index, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if index == 0 and _is_docstring_statement(node):
            continue
        if _is_dunder_all_update(node):
            continue
        if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
            continue
        return True
    return False


def _is_docstring_statement(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_dunder_all_update(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    if isinstance(node, ast.AugAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        return (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "__all__"
        )
    return False


def _collect_project_symbol_references(
    parsed_modules: list[dict[str, Any]],
    local_module_names: set[str],
    local_package_names: set[str],
) -> tuple[set[tuple[str, str]], set[str]]:
    """Collect exact static references to module-level project symbols."""

    references: set[tuple[str, str]] = set()
    wildcard_modules: set[str] = set()

    for module_data in parsed_modules:
        module_name = module_data["module"]
        tree = module_data["tree"]
        import_aliases: dict[str, str] = {}

        for binding in module_data["imports"]:
            if binding["is_star"]:
                if binding["target_module"]:
                    wildcard_modules.add(binding["target_module"])
                continue

            if binding["import_type"] == "from":
                target_module = binding["target_module"]
                imported_name = binding["imported_name"]
                if target_module and imported_name:
                    references.add((target_module, imported_name))
                    possible_module = f"{target_module}.{imported_name}"
                    if (
                        possible_module in local_module_names
                        or possible_module in local_package_names
                    ):
                        import_aliases[binding["binding"]] = possible_module
                continue

            target_module = binding["target_module"]
            if not target_module:
                continue
            if "." in target_module and binding["binding"] == target_module.split(".")[0]:
                import_aliases[binding["binding"]] = target_module.split(".")[0]
            else:
                import_aliases[binding["binding"]] = target_module

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                references.add((module_name, node.id))

            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                chain = _attribute_chain(node)
                if not chain:
                    continue
                root = chain[0]
                if root in import_aliases and len(chain) >= 2:
                    absolute_parts = import_aliases[root].split(".") + chain[1:]
                    if len(absolute_parts) >= 2:
                        references.add(
                            (".".join(absolute_parts[:-1]), absolute_parts[-1])
                        )

            if isinstance(node, ast.Call):
                chain = _attribute_chain(node.func)
                if chain and chain[-1] == "getattr" and len(node.args) >= 2:
                    owner_chain = _attribute_chain(node.args[0])
                    member = _literal_string(node.args[1])
                    if owner_chain and member:
                        root = owner_chain[0]
                        if root in import_aliases:
                            absolute_module = ".".join(
                                import_aliases[root].split(".") + owner_chain[1:]
                            )
                            references.add((absolute_module, member))

    return references, wildcard_modules


def _attribute_chain(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        owner = _attribute_chain(node.value)
        if owner is None:
            return None
        return [*owner, node.attr]
    return None


def _find_unused_imports(module_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return imports that are provably unused under conservative safeguards."""

    if (
        module_data["dynamic_usage"]
        or module_data["dynamic_exports"]
        or not module_data["has_substantive_code"]
    ):
        return []

    loaded_names = module_data["loaded_names"]
    exports = module_data["exports"]
    violations: list[dict[str, Any]] = []

    for binding in module_data["imports"]:
        name = binding["binding"]
        if (
            binding["is_star"]
            or binding["suppressed"]
            or binding["in_try"]
            or binding["in_type_checking"]
            or binding["explicit_reexport"]
            or name in loaded_names
            or name in exports
            or name == "_"
            or name.startswith("_")
            or binding["target_module"] == "__future__"
        ):
            continue

        violations.append(
            {
                "kind": "unused_import",
                "path": binding["path"],
                "module": binding["module"],
                "symbol": name,
                "qualified_name": f"{binding['module']}:{name}",
                "line": binding["line"],
                "binding": name,
                "imported": binding["imported"],
                "classification": binding["classification"],
                "import_type": binding["import_type"],
                "symbol_type": "import",
                "rule": "dead_code",
            }
        )

    return sorted(violations, key=_dead_code_sort_key)


def _find_unused_functions(
    module_data: dict[str, Any],
    symbol_references: set[tuple[str, str]],
    wildcard_imported_modules: set[str],
) -> list[dict[str, Any]]:
    """Return conservatively unreferenced module-level functions."""

    if (
        module_data["dynamic_usage"]
        or module_data["dynamic_exports"]
        or module_data["has_module_getattr"]
        or module_data["module"] in wildcard_imported_modules
    ):
        return []

    violations: list[dict[str, Any]] = []
    exports = module_data["exports"]
    path = module_data["path"]
    module_name = module_data["module"]

    for function in module_data["functions"]:
        if function["scope"] != "module":
            continue

        name = function["name"]
        if _is_protected_module_function(
            function=function,
            module_name=module_name,
            relative_path=path,
            exports=exports,
            symbol_references=symbol_references,
        ):
            continue

        violations.append(
            {
                "kind": "unused_function",
                "path": path,
                "module": module_name,
                "symbol": name,
                "qualified_name": function["qualified_name"],
                "line": function["line"],
                "symbol_type": function["symbol_type"],
                "rule": "dead_code",
            }
        )

    return sorted(violations, key=_dead_code_sort_key)


def _is_protected_module_function(
    function: dict[str, Any],
    module_name: str,
    relative_path: str,
    exports: set[str],
    symbol_references: set[tuple[str, str]],
) -> bool:
    name = function["name"]
    path_name = Path(relative_path).name
    path_parts = {part.lower() for part in Path(relative_path).parts}
    decorator_leaves = {
        decorator.split(".")[-1] for decorator in function["decorators"]
    }

    if function["is_decorated"]:
        return True
    if name in exports:
        return True
    if name == "main":
        return True
    if name.startswith("__") and name.endswith("__"):
        return True
    if name in _KNOWN_ENTRY_POINT_NAMES:
        return True
    if name.startswith("pytest_"):
        return True
    if "fixture" in decorator_leaves:
        return True
    if (
        name.startswith("test_")
        and (path_name.startswith("test_") or "tests" in path_parts or "09_tests" in path_parts)
    ):
        return True
    if path_name == "conftest.py":
        return True
    if relative_path.endswith("/__init__.py") or relative_path == "__init__.py":
        return True
    if (module_name, name) in symbol_references:
        return True
    return False


def _dead_code_sort_key(violation: dict[str, Any]) -> tuple[Any, ...]:
    kind_rank = {"unused_import": 0, "unused_function": 1}
    return (
        violation["path"],
        violation["line"],
        kind_rank.get(violation["kind"], 99),
        violation["qualified_name"],
    )


def _public_unused_import_record(
    violation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "binding": violation["binding"],
        "imported": violation["imported"],
        "line": violation["line"],
        "classification": violation["classification"],
    }


def _public_unused_function_record(
    violation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "qualified_name": violation["qualified_name"],
        "line": violation["line"],
        "symbol_type": violation["symbol_type"],
    }


def _aggregate_semantic_metrics(
    module_metrics: list[dict[str, Any]],
    complexity_violations: list[dict[str, Any]],
    dead_code_violations: list[dict[str, Any]],
    threshold: int,
) -> dict[str, Any]:
    """Aggregate deterministic maintainability metrics across modules."""

    physical_lines = sum(record["physical_lines"] for record in module_metrics)
    lines_of_code = sum(record["lines_of_code"] for record in module_metrics)
    function_count = sum(record["function_count"] for record in module_metrics)
    async_function_count = sum(
        record["async_function_count"] for record in module_metrics
    )
    class_count = sum(record["class_count"] for record in module_metrics)
    total_complexity = sum(
        record["complexity_total"] for record in module_metrics
    )
    maximum_complexity = max(
        (record["complexity_max"] for record in module_metrics),
        default=0,
    )
    import_count = sum(record["import_count"] for record in module_metrics)
    import_statement_count = sum(
        record["import_statement_count"] for record in module_metrics
    )
    local_dependency_count = sum(
        record["local_dependency_count"] for record in module_metrics
    )
    unused_import_count = sum(
        record["potentially_unused_import_count"] for record in module_metrics
    )
    unused_function_count = sum(
        record["potentially_unused_function_count"] for record in module_metrics
    )
    dead_code_finding_count = len(dead_code_violations)

    return {
        "physical_line_count": physical_lines,
        "physical_lines": physical_lines,
        "lines_of_code": lines_of_code,
        "function_count": function_count,
        "async_function_count": async_function_count,
        "class_count": class_count,
        "total_cyclomatic_complexity": total_complexity,
        "total_complexity": total_complexity,
        "average_cyclomatic_complexity": _safe_average(
            total_complexity,
            function_count,
        ),
        "average_complexity": _safe_average(total_complexity, function_count),
        "max_cyclomatic_complexity": maximum_complexity,
        "maximum_cyclomatic_complexity": maximum_complexity,
        "cyclomatic_complexity_threshold": threshold,
        "import_count": import_count,
        "import_statement_count": import_statement_count,
        "local_dependency_count": local_dependency_count,
        "potentially_unused_import_count": unused_import_count,
        "potentially_unused_function_count": unused_function_count,
        "complexity_finding_count": len(complexity_violations),
        "dead_code_finding_count": dead_code_finding_count,
    }


# =====================================================================
# CYCLE DETECTION (Commit 0016)
# =====================================================================

def _detect_cycles(
    edges: list[tuple[str, str]],
    max_depth: int = 20,
) -> list[list[str]]:
    """Detect simple circular dependency cycles in the local module graph."""

    graph: dict[str, list[str]] = {}
    nodes: set[str] = set()

    for src, dst in edges:
        nodes.add(src)
        nodes.add(dst)
        graph.setdefault(src, []).append(dst)

    for node in nodes:
        graph.setdefault(node, [])

    found_cycles: set[tuple[str, ...]] = set()

    for start_node in sorted(nodes):
        stack: list[tuple[str, list[str], set[str]]] = [
            (start_node, [start_node], {start_node})
        ]

        while stack:
            current, path, path_set = stack.pop()

            if len(path) >= max_depth:
                continue

            for neighbor in sorted(graph.get(current, [])):
                if neighbor == start_node and len(path) > 1:
                    cycle = path.copy()
                    canonical = _canonicalize_cycle(cycle)
                    if canonical not in found_cycles:
                        found_cycles.add(canonical)

                elif neighbor not in path_set and neighbor >= start_node:
                    new_path = path + [neighbor]
                    new_set = set(path_set)
                    new_set.add(neighbor)
                    stack.append((neighbor, new_path, new_set))

    return [list(cycle) for cycle in sorted(found_cycles)]


def _canonicalize_cycle(cycle: list[str]) -> tuple[str, ...]:
    """Canonicalize a cycle by rotating it so the smallest node is first."""

    if not cycle:
        return ()

    best_rotation = min(
        tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))
    )
    return best_rotation


# =====================================================================
# LAYER VALIDATION (Commit 0017)
# =====================================================================

def _validate_layers(
    dependency_edges: list[tuple[str, str]],
    modules: list[dict[str, Any]],
    layers_config: Any,
) -> list[dict[str, Any]]:
    """Validate that local dependency edges respect the declared layer hierarchy."""

    if not isinstance(layers_config, dict):
        raise ValueError("layers must be a dictionary.")

    order = layers_config.get("order")
    mapping = layers_config.get("mapping")

    if not isinstance(order, list) or not order:
        raise ValueError("layers.order must be a non-empty list of layer names.")

    if not isinstance(mapping, dict):
        raise ValueError("layers.mapping must be a dictionary.")

    layer_rank: dict[str, int] = {
        name: idx for idx, name in enumerate(order)
    }

    for layer_name in mapping:
        if layer_name not in layer_rank:
            raise ValueError(
                f"Layer {layer_name!r} in mapping is not declared in order."
            )

    module_names: set[str] = {m["name"] for m in modules}
    module_layer: dict[str, str] = {}

    for layer_name, patterns in mapping.items():
        if not isinstance(patterns, (list, tuple)):
            raise ValueError(
                f"layers.mapping[{layer_name!r}] must be a list of patterns."
            )

        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError("Layer patterns must be non-empty strings.")

            for mod_name in module_names:
                if fnmatch.fnmatch(mod_name, pattern):
                    module_layer[mod_name] = layer_name

    violations: list[dict[str, Any]] = []

    for source, target in dependency_edges:
        source_layer = module_layer.get(source)
        target_layer = module_layer.get(target)

        if source_layer is None or target_layer is None:
            continue

        source_rank = layer_rank[source_layer]
        target_rank = layer_rank[target_layer]

        if target_rank > source_rank:
            violations.append(
                {
                    "type": "layer_violation",
                    "source": source,
                    "source_layer": source_layer,
                    "target": target,
                    "target_layer": target_layer,
                    "message": (
                        f"Module {source!r} (layer: {source_layer}) imports "
                        f"module {target!r} (layer: {target_layer}), violating "
                        f"the layer hierarchy: {source_layer} -> {target_layer}."
                    ),
                }
            )

    return violations


# =====================================================================
# FORBIDDEN IMPORTS (Commit 0018)
# =====================================================================

def _validate_forbidden_imports(
    imports: list[dict[str, Any]],
    forbidden_config: Any,
) -> list[dict[str, Any]]:
    """Detect imports that match forbidden patterns."""

    if forbidden_config is None:
        return []

    global_patterns: list[str] = []
    per_source_patterns: dict[str, list[str]] = {}

    if isinstance(forbidden_config, (list, tuple)):
        global_patterns = list(forbidden_config)

    elif isinstance(forbidden_config, dict):
        global_cfg = forbidden_config.get("global")
        if global_cfg is not None:
            if not isinstance(global_cfg, (list, tuple)):
                raise ValueError("forbidden_imports.global must be a list.")
            global_patterns = list(global_cfg)

        per_cfg = forbidden_config.get("per_source")
        if per_cfg is not None:
            if not isinstance(per_cfg, dict):
                raise ValueError("forbidden_imports.per_source must be a dict.")
            for source_pattern, target_list in per_cfg.items():
                if not isinstance(target_list, (list, tuple)):
                    raise ValueError(
                        f"forbidden_imports.per_source[{source_pattern!r}] "
                        f"must be a list."
                    )
                per_source_patterns[source_pattern] = list(target_list)

    else:
        raise ValueError(
            "forbidden_imports must be a list of patterns or a dict."
        )

    def _matches_forbidden(target: str, pattern: str) -> bool:
        if fnmatch.fnmatch(target, pattern):
            return True
        if pattern.endswith(".*"):
            root_module = pattern[:-2]
            if target == root_module:
                return True
        return False

    violations: list[dict[str, Any]] = []

    for imp in imports:
        source = imp["source"]
        target = imp["target"]

        for pattern in global_patterns:
            if _matches_forbidden(target, pattern):
                violations.append(
                    {
                        "type": "forbidden_import",
                        "source": source,
                        "target": target,
                        "matched_pattern": pattern,
                        "scope": "global",
                        "message": (
                            f"Module {source!r} imports forbidden target "
                            f"{target!r} (matched pattern: {pattern!r})."
                        ),
                    }
                )
                break

        for source_pattern, target_patterns in per_source_patterns.items():
            if fnmatch.fnmatch(source, source_pattern):
                for pattern in target_patterns:
                    if _matches_forbidden(target, pattern):
                        violations.append(
                            {
                                "type": "forbidden_import",
                                "source": source,
                                "target": target,
                                "matched_pattern": pattern,
                                "scope": f"per_source:{source_pattern}",
                                "message": (
                                    f"Module {source!r} (matching "
                                    f"{source_pattern!r}) imports forbidden "
                                    f"target {target!r} (matched pattern: "
                                    f"{pattern!r})."
                                ),
                            }
                        )
                        break

    return violations


# =====================================================================
# MISSING __init__.py VALIDATION (Commit 0019)
# =====================================================================

def _validate_package_initializers(
    packages: list[dict[str, Any]],
    modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect packages that lack an __init__.py initializer."""

    module_names: set[str] = {m["name"] for m in modules}
    violations: list[dict[str, Any]] = []

    for package in packages:
        pkg_name = package["name"]
        if pkg_name not in module_names:
            violations.append(
                {
                    "type": "missing_package_initializer",
                    "package": pkg_name,
                    "path": package.get("path", ""),
                    "modules": package.get("modules", []),
                    "message": (
                        f"Package {pkg_name!r} is missing __init__.py. "
                        f"It contains {len(package.get('modules', []))} module(s) "
                        f"but no package initializer."
                    ),
                }
            )

    return violations


# =====================================================================
# PLUGIN WRAPPER
# =====================================================================

class ArchitectureAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "ArchitectureAuditorPlugin",
    "run",
]

# =====================================================================
# OPTIONAL OBJECT-ORIENTED WRAPPER
# =====================================================================

class ArchitectureAuditor:
    """Compatibility wrapper around the canonical functional API."""

    plugin_id = PLUGIN_ID
    plugin_version = PLUGIN_VERSION
    audit_type = AUDIT_TYPE

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        self._context = context

    def execute(
        self,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        active_context = context if context is not None else self._context
        if active_context is None:
            raise ValueError(
                "ArchitectureAuditor.execute() requires an audit context."
            )
        return run(active_context)