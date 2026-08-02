"""
Configuration Auditor Plugin — Fase 2.2

Audita archivos de configuración del proyecto:
- Detectar archivos de config soportados (.json, .yaml, .yml, .toml, .ini, .env, .cfg).
- Validar sintaxis parseable de cada archivo.
- Detectar valores hardcodeados sensibles (API keys, passwords, secrets, tokens).
- Detectar configuraciones duplicadas entre archivos.
- Detectar archivos de config requeridos que faltan (configurable).
"""

from __future__ import annotations

import configparser
import json
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

PLUGIN_ID = "configuration-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "configuration"

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

_DEFAULT_CONFIG_EXTENSIONS = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".cfg"}
)

_DEFAULT_REQUIRED_CONFIG_FILES = frozenset(
    {
        "pyproject.toml",
        ".env",
        "config.yaml",
    }
)

_DEFAULT_SECRET_PATTERNS = [
    r"(?i)api[_-]?key\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)password\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)secret\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)token\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)auth\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)private[_-]?key\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?",
    r"(?i)sk-[\w]{20,}",
    r"(?i)AKIA[0-9A-Z]{16}",
    r"(?i)ghp_[\w]{30,}",
    r"(?i)glpat-[\w]{20,}",
]

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "config_extensions",
    "required_config_files",
    "secret_patterns",
}

# =====================================================================
# PUBLIC API
# =====================================================================


def run(context: Any) -> dict[str, Any]:
    """Execute full configuration audit and emit canonical AuditResult."""

    started_at = _utc_now_iso()
    t0 = datetime.now(timezone.utc)

    (
        project_path,
        ignored_directories,
        config_extensions,
        required_config_files,
        secret_patterns,
    ) = _validate_context(context)

    # --- Discover config files ---
    config_files = _discover_config_files(
        project_path, ignored_directories, config_extensions
    )

    # --- Validate syntax ---
    invalid_violations = _check_invalid_syntax(
        config_files=config_files,
        project_path=project_path,
    )

    # --- Detect secrets ---
    secret_violations = _check_secrets(
        config_files=config_files,
        project_path=project_path,
        secret_patterns=secret_patterns,
    )

    # --- Detect duplicates ---
    duplicate_violations = _check_duplicates(
        config_files=config_files,
        project_path=project_path,
        config_extensions=config_extensions,
    )

    # --- Detect missing required files ---
    missing_violations = _check_missing_required(
        project_path=project_path,
        required_config_files=required_config_files,
    )

    # --- Build canonical findings ---
    findings = _build_findings(
        missing_violations=missing_violations,
        invalid_violations=invalid_violations,
        secret_violations=secret_violations,
        duplicate_violations=duplicate_violations,
    )

    # --- Determine status ---
    has_critical = any(f.severity == FindingSeverity.CRITICAL for f in findings)
    has_error = any(f.severity == FindingSeverity.ERROR for f in findings)
    has_warning = any(f.severity == FindingSeverity.WARNING for f in findings)

    if has_critical or has_error:
        status = AuditStatus.COMPLETED_WITH_FINDINGS
    elif has_warning:
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
            "config_files": config_files,
            "missing_violations": missing_violations,
            "invalid_violations": invalid_violations,
            "secret_violations": secret_violations,
            "duplicate_violations": duplicate_violations,
        },
        metrics={
            "config_file_count": len(config_files),
            "missing_config_count": len(missing_violations),
            "invalid_config_count": len(invalid_violations),
            "secret_count": len(secret_violations),
            "duplicate_count": len(duplicate_violations),
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
    missing_violations: list[dict[str, Any]],
    invalid_violations: list[dict[str, Any]],
    secret_violations: list[dict[str, Any]],
    duplicate_violations: list[dict[str, Any]],
) -> list[AuditFinding]:
    """Convert all raw violations into canonical AuditFinding objects."""

    findings: list[AuditFinding] = []

    # --- Missing required config: CONFIG-MISSING-001 (WARNING) ---
    for v in missing_violations:
        findings.append(
            AuditFinding(
                code="CONFIG-MISSING-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "required_file": v.get("required_file", ""),
                    "rule": "missing_required_config",
                },
            )
        )

    # --- Invalid syntax: CONFIG-INVALID-001 (ERROR) ---
    for v in invalid_violations:
        findings.append(
            AuditFinding(
                code="CONFIG-INVALID-001",
                severity=FindingSeverity.ERROR,
                path=v["path"],
                message=v["message"],
                details={
                    "error": v.get("error", ""),
                    "rule": "invalid_config_syntax",
                },
            )
        )

    # --- Secret hardcoded: CONFIG-SECRET-001 (CRITICAL) ---
    for v in secret_violations:
        findings.append(
            AuditFinding(
                code="CONFIG-SECRET-001",
                severity=FindingSeverity.CRITICAL,
                path=v["path"],
                message=v["message"],
                details={
                    "key": v.get("key", ""),
                    "line": v.get("line", 0),
                    "matched_pattern": v.get("matched_pattern", ""),
                    "rule": "hardcoded_secret",
                },
            )
        )

    # --- Duplicate config: CONFIG-DUPLICATE-001 (WARNING) ---
    for v in duplicate_violations:
        findings.append(
            AuditFinding(
                code="CONFIG-DUPLICATE-001",
                severity=FindingSeverity.WARNING,
                path=v["path"],
                message=v["message"],
                details={
                    "key": v.get("key", ""),
                    "value": v.get("value", ""),
                    "other_files": v.get("other_files", []),
                    "rule": "duplicate_config",
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
    frozenset[str],
    frozenset[str],
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

    config_extensions = _validate_string_set(
        context.get("config_extensions", list(_DEFAULT_CONFIG_EXTENSIONS)),
        "config_extensions",
    )

    required_config_files = _validate_string_set(
        context.get("required_config_files", list(_DEFAULT_REQUIRED_CONFIG_FILES)),
        "required_config_files",
    )

    secret_patterns = _validate_string_list(
        context.get("secret_patterns", _DEFAULT_SECRET_PATTERNS),
        "secret_patterns",
    )

    return (
        project_path,
        ignored_directories,
        config_extensions,
        required_config_files,
        secret_patterns,
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


def _validate_string_set(value: Any, field_name: str) -> frozenset[str]:
    """Validate a collection of non-empty strings and return as frozenset."""

    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"{field_name} must be a collection of strings.")

    result: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings.")
        result.add(item.strip())

    return frozenset(result)


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    """Validate a list of non-empty strings."""

    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list of strings.")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings.")
        result.append(item.strip())

    return result


# =====================================================================
# DISCOVERY
# =====================================================================


def _discover_config_files(
    project_path: Path,
    ignored_directories: frozenset[str],
    config_extensions: frozenset[str],
) -> list[str]:
    """Return deterministic POSIX paths for discoverable config files."""

    discovered: list[str] = []

    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name for name in directory_names if name not in ignored_directories
        )

        root_path = Path(root)
        for file_name in sorted(file_names):
            suffix = Path(file_name).suffix.lower()
            if suffix not in config_extensions and file_name not in config_extensions:
                # Also check exact filenames like .env (no suffix)
                if file_name not in config_extensions:
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
# SYNTAX VALIDATION
# =====================================================================


def _check_invalid_syntax(
    config_files: list[str],
    project_path: Path,
) -> list[dict[str, Any]]:
    """Validate that each config file is parseable."""

    violations: list[dict[str, Any]] = []

    for relative_path in sorted(config_files):
        file_path = project_path / relative_path
        suffix = file_path.suffix.lower()
        file_name = file_path.name

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            violations.append(
                {
                    "type": "invalid_syntax",
                    "path": relative_path,
                    "error": str(exc),
                    "message": f"Cannot read config file {relative_path!r}: {exc}",
                }
            )
            continue

        error = _try_parse_config(file_path, raw_text, suffix, file_name)
        if error:
            violations.append(
                {
                    "type": "invalid_syntax",
                    "path": relative_path,
                    "error": error,
                    "message": f"Config file {relative_path!r} has invalid syntax: {error}",
                }
            )

    return violations


def _try_parse_config(
    file_path: Path, raw_text: str, suffix: str, file_name: str
) -> str | None:
    """Attempt to parse a config file. Return error message or None."""

    if suffix == ".json" or file_name.endswith(".json"):
        try:
            json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return str(exc)
        return None

    if suffix in (".yaml", ".yml") or file_name.endswith((".yaml", ".yml")):
        try:
            import yaml

            yaml.safe_load(raw_text)
        except ImportError:
            # yaml not installed — skip validation
            return None
        except Exception as exc:
            return str(exc)
        return None

    if suffix == ".toml" or file_name.endswith(".toml"):
        try:
            import tomllib

            tomllib.loads(raw_text)
        except ImportError:
            try:
                import toml

                toml.loads(raw_text)
            except ImportError:
                return None
            except Exception as exc:
                return str(exc)
        except Exception as exc:
            return str(exc)
        return None

    if suffix in (".ini", ".cfg") or file_name.endswith((".ini", ".cfg")):
        parser = configparser.ConfigParser()
        try:
            parser.read_string(raw_text)
        except configparser.Error as exc:
            return str(exc)
        return None

    if file_name == ".env" or suffix == ".env":
        # .env files are line-based key=value; just check basic structure
        for line_no, line in enumerate(raw_text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped and ":" not in stripped:
                return f"Line {line_no}: invalid .env syntax (missing '=' or ':')"
        return None

    return None


# =====================================================================
# SECRET DETECTION
# =====================================================================


def _check_secrets(
    config_files: list[str],
    project_path: Path,
    secret_patterns: list[str],
) -> list[dict[str, Any]]:
    """Detect hardcoded secrets in config files."""

    violations: list[dict[str, Any]] = []

    compiled_patterns = [re.compile(p) for p in secret_patterns]

    for relative_path in sorted(config_files):
        file_path = project_path / relative_path

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_no, line in enumerate(raw_text.splitlines(), start=1):
            for pattern in compiled_patterns:
                match = pattern.search(line)
                if match:
                    key = _extract_key_from_line(line, match)
                    display_key = key if key != "unknown" else match.group(0)
                    violations.append(
                        {
                            "type": "hardcoded_secret",
                            "path": relative_path,
                            "key": key,
                            "line": line_no,
                            "matched_pattern": pattern.pattern,
                            "message": (
                                f"Possible hardcoded secret in {relative_path!r} "
                                f"at line {line_no}: {display_key}"
                            ),
                        }
                    )
                    # Only report first match per line per pattern
                    break

    return violations


def _extract_key_from_line(line: str, match: re.Match) -> str:
    """Try to extract the config key associated with a secret match."""

    text_before = line[: match.start()].strip()
    key = "unknown"
    if ":" in text_before:
        key = text_before.split(":")[0].strip().rstrip("=")
    elif "=" in text_before:
        key = text_before.split("=")[0].strip().rstrip("=")
    else:
        matched = match.group(0)
        if "=" in matched:
            key = matched.split("=")[0].strip()
        elif ":" in matched:
            key = matched.split(":")[0].strip()

    # Clean common JSON/YAML wrapping chars
    key = key.strip().strip('"').strip("'").strip("{").strip("[").strip()

    # If key looks invalid (contains non-identifier chars), fall back to unknown
    if key and re.match(r"^[A-Za-z0-9_\-]+$", key):
        return key
    return "unknown"


# =====================================================================
# DUPLICATE DETECTION
# =====================================================================


def _check_duplicates(
    config_files: list[str],
    project_path: Path,
    config_extensions: frozenset[str],
) -> list[dict[str, Any]]:
    """Detect duplicate key-value pairs across config files."""

    violations: list[dict[str, Any]] = []

    # key -> {value -> [files]}
    key_value_files: dict[str, dict[str, list[str]]] = {}

    for relative_path in sorted(config_files):
        file_path = project_path / relative_path

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        kv_pairs = _extract_key_value_pairs(file_path, raw_text, config_extensions)
        for key, value in kv_pairs:
            key_value_files.setdefault(key, {}).setdefault(value, []).append(
                relative_path
            )

    # Find duplicates
    for key, value_files in key_value_files.items():
        for value, files in value_files.items():
            if len(files) > 1:
                # Report one finding per file, referencing the others
                for file_path in files:
                    other_files = [f for f in files if f != file_path]
                    violations.append(
                        {
                            "type": "duplicate_config",
                            "path": file_path,
                            "key": key,
                            "value": value,
                            "other_files": other_files,
                            "message": (
                                f"Duplicate config key {key!r} with same value "
                                f"found in {file_path!r} and {other_files!r}."
                            ),
                        }
                    )

    return violations


def _extract_key_value_pairs(
    file_path: Path, raw_text: str, config_extensions: frozenset[str]
) -> list[tuple[str, str]]:
    """Extract flat key-value pairs from a config file."""

    suffix = file_path.suffix.lower()
    file_name = file_path.name
    pairs: list[tuple[str, str]] = []

    if suffix == ".json" or file_name.endswith(".json"):
        try:
            data = json.loads(raw_text)
            pairs.extend(_flatten_dict(data))
        except json.JSONDecodeError:
            pass
        return pairs

    if suffix in (".yaml", ".yml") or file_name.endswith((".yaml", ".yml")):
        try:
            import yaml

            data = yaml.safe_load(raw_text)
            if isinstance(data, dict):
                pairs.extend(_flatten_dict(data))
        except ImportError:
            pass
        except Exception:
            pass
        return pairs

    if suffix == ".toml" or file_name.endswith(".toml"):
        try:
            import tomllib

            data = tomllib.loads(raw_text)
            pairs.extend(_flatten_dict(data))
        except ImportError:
            try:
                import toml

                data = toml.loads(raw_text)
                pairs.extend(_flatten_dict(data))
            except ImportError:
                pass
            except Exception:
                pass
        except Exception:
            pass
        return pairs

    if suffix in (".ini", ".cfg") or file_name.endswith((".ini", ".cfg")):
        parser = configparser.ConfigParser()
        try:
            parser.read_string(raw_text)
            for section_name in parser.sections():
                for key, value in parser.items(section_name):
                    pairs.append((key, value))
        except configparser.Error:
            pass
        return pairs

    if file_name == ".env" or suffix == ".env":
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                pairs.append((key.strip(), value.strip()))
        return pairs

    return pairs


def _flatten_dict(
    data: Any, prefix: str = ""
) -> list[tuple[str, str]]:
    """Flatten a nested dict into dotted key-value string pairs."""

    results: list[tuple[str, str]] = []

    if not isinstance(data, dict):
        return results

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            results.extend(_flatten_dict(value, full_key))
        elif isinstance(value, (str, int, float, bool)):
            results.append((full_key, str(value)))
        elif value is None:
            results.append((full_key, "null"))

    return results


# =====================================================================
# MISSING REQUIRED FILES
# =====================================================================


def _check_missing_required(
    project_path: Path,
    required_config_files: frozenset[str],
) -> list[dict[str, Any]]:
    """Detect required config files that are missing from the project."""

    violations: list[dict[str, Any]] = []

    for required_file in sorted(required_config_files):
        candidate = project_path / required_file
        if not candidate.exists():
            violations.append(
                {
                    "type": "missing_required_config",
                    "path": str(project_path),
                    "required_file": required_file,
                    "message": (
                        f"Required config file {required_file!r} not found "
                        f"in project {str(project_path)!r}."
                    ),
                }
            )

    return violations


# =====================================================================
# PLUGIN WRAPPER
# =====================================================================


class ConfigurationAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "ConfigurationAuditorPlugin",
    "run",
]