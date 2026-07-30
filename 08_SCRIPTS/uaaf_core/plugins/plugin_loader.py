"""
Load a local UAAF plugin manifest from plugin.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from uaaf_core.plugins.plugin_models import PluginManifest


class PluginLoader:
    """Load and validate a minimal local plugin manifest."""

    MANIFEST_FILENAME = "plugin.yaml"

    @classmethod
    def load_manifest(cls, plugin_directory: Path | str) -> PluginManifest:
        directory = Path(plugin_directory).resolve()
        manifest_path = directory / cls.MANIFEST_FILENAME

        if not directory.is_dir():
            raise FileNotFoundError(
                f"Plugin directory not found: {directory}"
            )

        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Plugin manifest not found: {manifest_path}"
            )

        with manifest_path.open("r", encoding="utf-8") as stream:
            raw_data = yaml.safe_load(stream)

        if not isinstance(raw_data, dict):
            raise ValueError(
                f"Plugin manifest must contain a mapping: {manifest_path}"
            )

        values = {
            field: cls._required_string(raw_data, field, manifest_path)
            for field in (
                "plugin_id",
                "name",
                "version",
                "entrypoint",
            )
        }

        return PluginManifest(
            plugin_id=values["plugin_id"],
            name=values["name"],
            version=values["version"],
            entrypoint=values["entrypoint"],
            manifest_path=manifest_path,
        )

    @staticmethod
    def _required_string(
        data: dict[str, Any],
        field: str,
        manifest_path: Path,
    ) -> str:
        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Plugin manifest field {field!r} must be a "
                f"non-empty string: {manifest_path}"
            )

        return value.strip()


__all__ = ["PluginLoader"]
