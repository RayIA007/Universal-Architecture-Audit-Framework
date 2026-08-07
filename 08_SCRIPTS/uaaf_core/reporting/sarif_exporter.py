"""Deterministic SARIF 2.1.0 export for canonical UAAF audit results."""

from __future__ import annotations

import json
import ntpath
import posixpath
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import PureWindowsPath
from typing import Any, Final

from uaaf_core.audit.audit_result import AuditResult, validate_audit_result

SARIF_VERSION: Final[str] = "2.1.0"
SARIF_SCHEMA_URI: Final[str] = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/"
    "schemas/sarif-schema-2.1.0.json"
)
UAAF_INFORMATION_URI: Final[str] = (
    "https://github.com/RayIA007/Universal-Architecture-Audit-Framework"
)

_SEVERITY_TO_LEVEL: Final[dict[str, str]] = {
    "critical": "error",
    "error": "error",
    "warning": "warning",
    "info": "note",
}
_SEVERITY_RANK: Final[dict[str, int]] = {
    "critical": 0,
    "error": 1,
    "warning": 2,
    "info": 3,
}


class SarifExporter:
    """Convert canonical UAAF results into deterministic SARIF 2.1.0."""

    def to_dict(self, result: Any) -> dict[str, Any]:
        """Return a validated, JSON-serializable SARIF document."""
        data = self._normalize_result(result)
        findings = list(data["findings"])
        rules, rule_indexes = self._build_rules(findings, data)
        results = self._build_results(findings, data, rule_indexes)

        document: dict[str, Any] = {
            "$schema": SARIF_SCHEMA_URI,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "UAAF",
                            "version": data["plugin_version"],
                            "informationUri": UAAF_INFORMATION_URI,
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }

        # Enforce strict JSON compatibility without changing the returned object.
        json.dumps(document, ensure_ascii=False, allow_nan=False)
        return document

    def to_json(self, result: Any, *, indent: int = 2) -> str:
        """Return a UTF-8-safe deterministic SARIF JSON string."""
        if not isinstance(indent, int) or isinstance(indent, bool) or indent < 0:
            raise ValueError("indent must be a non-negative integer.")
        return json.dumps(
            self.to_dict(result),
            indent=indent,
            ensure_ascii=False,
            sort_keys=False,
            allow_nan=False,
        )

    @staticmethod
    def _normalize_result(result: Any) -> dict[str, Any]:
        if isinstance(result, AuditResult):
            data = result.to_dict()
        elif isinstance(result, Mapping):
            data = dict(result)
        else:
            raise TypeError(
                "result must be an AuditResult instance or a mapping, "
                f"got {type(result).__name__}"
            )
        validate_audit_result(data)
        return data

    def _build_rules(
        self,
        findings: Sequence[Mapping[str, Any]],
        result: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for finding in findings:
            grouped[str(finding["code"])].append(finding)

        rules: list[dict[str, Any]] = []
        for code in sorted(grouped, key=lambda value: (value.casefold(), value)):
            group = grouped[code]
            default_severity = min(
                (str(item["severity"]).casefold() for item in group),
                key=lambda value: (_SEVERITY_RANK.get(value, 99), value),
            )
            descriptor: dict[str, Any] = {
                "id": code,
                "name": code,
                "defaultConfiguration": {
                    "level": self._sarif_level(default_severity),
                },
            }

            labels = sorted(
                {
                    label
                    for item in group
                    if (label := self._rule_label(item.get("details"))) is not None
                },
                key=lambda value: (value.casefold(), value),
            )
            if labels:
                descriptor["shortDescription"] = {"text": labels[0]}

            source_plugin_ids = sorted(
                {
                    self._source_value(
                        item.get("details"),
                        key="source_plugin_id",
                        fallback=result["plugin_id"],
                    )
                    for item in group
                },
                key=lambda value: (value.casefold(), value),
            )
            source_audit_types = sorted(
                {
                    self._source_value(
                        item.get("details"),
                        key="source_audit_type",
                        fallback=result["audit_type"],
                    )
                    for item in group
                },
                key=lambda value: (value.casefold(), value),
            )
            descriptor["properties"] = {
                "sourcePluginIds": source_plugin_ids,
                "sourceAuditTypes": source_audit_types,
            }
            rules.append(descriptor)

        return rules, {rule["id"]: index for index, rule in enumerate(rules)}

    def _build_results(
        self,
        findings: Sequence[Mapping[str, Any]],
        result: Mapping[str, Any],
        rule_indexes: Mapping[str, int],
    ) -> list[dict[str, Any]]:
        project_root = self._project_root(result.get("summary"))
        built: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        for finding in findings:
            code = str(finding["code"])
            severity = str(finding["severity"]).casefold()
            message = self._sanitize_message(
                str(finding["message"]),
                project_root,
            )
            details = finding.get("details")
            source_plugin_id = self._source_value(
                details,
                key="source_plugin_id",
                fallback=result["plugin_id"],
            )
            source_audit_type = self._source_value(
                details,
                key="source_audit_type",
                fallback=result["audit_type"],
            )
            rule_label = self._rule_label(details)
            uri = self._artifact_uri(str(finding["path"]), project_root)
            line = self._valid_line(details)

            sarif_result: dict[str, Any] = {
                "ruleId": code,
                "ruleIndex": rule_indexes[code],
                "level": self._sarif_level(severity),
                "message": {"text": message},
                "properties": {
                    "sourcePluginId": source_plugin_id,
                    "sourceAuditType": source_audit_type,
                },
            }
            if rule_label is not None:
                sarif_result["properties"]["uaafRule"] = rule_label

            if uri is not None:
                physical_location: dict[str, Any] = {
                    "artifactLocation": {"uri": uri}
                }
                if line is not None:
                    physical_location["region"] = {"startLine": line}
                sarif_result["locations"] = [
                    {"physicalLocation": physical_location}
                ]

            sort_key = (
                code.casefold(),
                code,
                uri or "",
                line or 0,
                message,
                _SEVERITY_RANK.get(severity, 99),
                source_plugin_id.casefold(),
                source_plugin_id,
                source_audit_type.casefold(),
                source_audit_type,
                rule_label or "",
            )
            built.append((sort_key, sarif_result))

        built.sort(key=lambda item: item[0])
        return [item[1] for item in built]

    @classmethod
    def _sanitize_message(
        cls,
        message: str,
        project_root: str | None,
    ) -> str:
        """Redact the absolute project root from a canonical finding message."""
        if project_root is None:
            return message

        root = project_root.strip()
        if not root:
            return message

        variants = {root, root.rstrip("/\\")}
        if cls._is_windows_absolute(root):
            normalized = ntpath.normpath(root)
            raw_windows_variants = {
                root,
                root.rstrip("/\\"),
                normalized,
            }
            variants.update(raw_windows_variants)
            variants.update(
                value.replace("\\", "\\\\")
                for value in raw_windows_variants
                if value
            )
            variants.add(normalized.replace("\\", "/"))
            case_insensitive = True
        else:
            normalized = posixpath.normpath(root.replace("\\", "/"))
            variants.add(normalized)
            case_insensitive = False

        sanitized = message
        for variant in sorted(
            (item for item in variants if item),
            key=len,
            reverse=True,
        ):
            if case_insensitive:
                sanitized = re.sub(
                    re.escape(variant),
                    "<PROJECT_ROOT>",
                    sanitized,
                    flags=re.IGNORECASE,
                )
            else:
                sanitized = sanitized.replace(variant, "<PROJECT_ROOT>")
        return sanitized

    @staticmethod
    def _sarif_level(severity: str) -> str:
        # Canonical validation rejects unknown values. The fallback remains
        # conservative for direct helper use and future compatible extensions.
        return _SEVERITY_TO_LEVEL.get(severity.casefold(), "warning")

    @staticmethod
    def _rule_label(details: Any) -> str | None:
        if not isinstance(details, Mapping):
            return None
        value = details.get("rule")
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _source_value(
        details: Any,
        *,
        key: str,
        fallback: Any,
    ) -> str:
        if isinstance(details, Mapping):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(fallback).strip()

    @staticmethod
    def _project_root(summary: Any) -> str | None:
        if not isinstance(summary, Mapping):
            return None
        value = summary.get("project_path")
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    @staticmethod
    def _valid_line(details: Any) -> int | None:
        if not isinstance(details, Mapping):
            return None
        value = details.get("line")
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        return None

    @classmethod
    def _artifact_uri(
        cls,
        path_value: str,
        project_root: str | None,
    ) -> str | None:
        original = path_value.strip()
        if not original:
            return None

        if cls._is_windows_absolute(original):
            relative = cls._relative_windows_path(original, project_root)
            if relative is None:
                return None
            candidate = relative.replace("\\", "/")
        else:
            normalized_slashes = original.replace("\\", "/")
            if posixpath.isabs(normalized_slashes):
                relative = cls._relative_posix_path(
                    normalized_slashes,
                    project_root,
                )
                if relative is None:
                    return None
                candidate = relative
            else:
                candidate = normalized_slashes

        normalized = posixpath.normpath(candidate)
        if normalized in {"", ".", ".."} or normalized.startswith("../"):
            return None
        if normalized.startswith("//"):
            return None
        first_segment = normalized.split("/", 1)[0]
        if ":" in first_segment:
            return None
        return normalized

    @staticmethod
    def _is_windows_absolute(value: str) -> bool:
        return PureWindowsPath(value).is_absolute() or ntpath.isabs(value)

    @classmethod
    def _relative_windows_path(
        cls,
        path_value: str,
        project_root: str | None,
    ) -> str | None:
        if project_root is None or not cls._is_windows_absolute(project_root):
            return None
        path_normalized = ntpath.normpath(path_value)
        root_normalized = ntpath.normpath(project_root)
        try:
            common = ntpath.commonpath([root_normalized, path_normalized])
        except ValueError:
            return None
        if ntpath.normcase(common) != ntpath.normcase(root_normalized):
            return None
        relative = ntpath.relpath(path_normalized, root_normalized)
        if relative == "." or relative == ".." or relative.startswith(f"..{ntpath.sep}"):
            return None
        return relative

    @staticmethod
    def _relative_posix_path(
        path_value: str,
        project_root: str | None,
    ) -> str | None:
        if project_root is None:
            return None
        root = project_root.replace("\\", "/")
        if not posixpath.isabs(root):
            return None
        path_normalized = posixpath.normpath(path_value)
        root_normalized = posixpath.normpath(root)
        try:
            common = posixpath.commonpath([root_normalized, path_normalized])
        except ValueError:
            return None
        if common != root_normalized:
            return None
        relative = posixpath.relpath(path_normalized, root_normalized)
        if relative == "." or relative == ".." or relative.startswith("../"):
            return None
        return relative


_default_exporter = SarifExporter()


def to_sarif(result: Any, *, indent: int = 2) -> str:
    """Generate a SARIF JSON string using the default exporter."""
    return _default_exporter.to_json(result, indent=indent)


__all__ = [
    "SARIF_SCHEMA_URI",
    "SARIF_VERSION",
    "UAAF_INFORMATION_URI",
    "SarifExporter",
    "to_sarif",
]
