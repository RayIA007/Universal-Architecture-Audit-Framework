"""
Minimal audit orchestration for local UAAF plugins.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from uaaf_core.audit.audit_result import validate_audit_result
from uaaf_core.plugins.plugin_manager import PluginManager
from uaaf_core.plugins.plugin_models import PluginManifest


class AuditOrchestrator:
    """Discover a plugin, load its entrypoint, and execute its run function."""

    def __init__(self, plugins_root: Path | str) -> None:
        self.plugin_manager = PluginManager(plugins_root)

    def run(self, plugin_id: str, context: Any) -> Any:
        self.plugin_manager.discover()
        manifest = self.plugin_manager.get(plugin_id)
        module = self._load_module(manifest)

        run_function = getattr(module, "run", None)

        if not callable(run_function):
            raise AttributeError(
                f"Plugin {plugin_id!r} must expose a callable run(context)."
            )

        result = run_function(context)

        try:
            validate_audit_result(result)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Plugin {plugin_id!r} returned an invalid "
                f"Audit Result Contract: {exc}"
            ) from exc

        return result

    @staticmethod
    def _load_module(manifest: PluginManifest) -> ModuleType:
        entrypoint_path = (
            manifest.plugin_directory / manifest.entrypoint
        ).resolve()

        if not entrypoint_path.is_file():
            raise FileNotFoundError(
                f"Plugin entrypoint not found: {entrypoint_path}"
            )

        module_name = (
            "uaaf_plugin_"
            + manifest.plugin_id.replace("-", "_")
        )

        spec = importlib.util.spec_from_file_location(
            module_name,
            entrypoint_path,
        )

        if spec is None or spec.loader is None:
            raise ImportError(
                f"Unable to create module spec for: {entrypoint_path}"
            )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


__all__ = ["AuditOrchestrator"]
