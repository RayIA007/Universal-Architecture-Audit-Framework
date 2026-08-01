"""
Architecture Auditor MVP — Commit 0013-0019 + AuditResult Canónico.

Emite findings formales del dominio UAAF para todas las violaciones detectadas.
"""

from __future__ import annotations

import ast
import fnmatch
import os
import sys
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
PLUGIN_VERSION = "1.5.1"
AUDIT_TYPE = "architecture"

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

    local_import_count = sum(
        1 for imp in imports if imp["classification"] == "local"
    )

    # --- Build canonical findings ---
    findings = _build_findings(
        cycles=dependency_cycles,
        layer_violations=layer_violations,
        forbidden_violations=forbidden_violations,
        missing_init_violations=missing_init_violations,
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
    for v in layer_violations:
        findings.append(
            AuditFinding(
                code="ARCH-LAYER-001",
                severity=FindingSeverity.WARNING,
                path=v["source"],
                message=v["message"],
                details={
                    "source": v["source"],
                    "source_layer": v["source_layer"],
                    "target": v["target"],
                    "target_layer": v["target_layer"],
                    "rule": "layer_violation",
                },
            )
        )

    # --- Forbidden imports: ARCH-FORBIDDEN-001 (ERROR) ---
    for v in forbidden_violations:
        findings.append(
            AuditFinding(
                code="ARCH-FORBIDDEN-001",
                severity=FindingSeverity.ERROR,
                path=v["source"],
                message=v["message"],
                details={
                    "source": v["source"],
                    "target": v["target"],
                    "matched_pattern": v["matched_pattern"],
                    "scope": v["scope"],
                    "rule": "forbidden_import",
                },
            )
        )

    # --- Missing __init__.py: ARCH-INIT-001 (WARNING) ---
    for v in missing_init_violations:
        findings.append(
            AuditFinding(
                code="ARCH-INIT-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "package": v["package"],
                    "modules_in_package": v["modules"],
                    "rule": "missing_package_initializer",
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