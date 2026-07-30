"""
Minimal Plugin Manager for local UAAF plugins.
"""

from __future__ import annotations

from pathlib import Path

from uaaf_core.plugins.plugin_loader import PluginLoader
from uaaf_core.plugins.plugin_models import PluginManifest
from uaaf_core.plugins.plugin_registry import PluginRegistry


class PluginManager:
    """Discover and access local plugins from a plugins directory."""

    def __init__(self, plugins_root: Path | str) -> None:
        self.plugins_root = Path(plugins_root).resolve()
        self.registry = PluginRegistry()

    def discover(self) -> tuple[PluginManifest, ...]:
        if not self.plugins_root.is_dir():
            raise FileNotFoundError(
                f"Plugins directory not found: {self.plugins_root}"
            )

        self.registry = PluginRegistry()

        for plugin_directory in sorted(self.plugins_root.iterdir()):
            if not plugin_directory.is_dir():
                continue

            manifest_path = (
                plugin_directory / PluginLoader.MANIFEST_FILENAME
            )

            if not manifest_path.is_file():
                continue

            manifest = PluginLoader.load_manifest(plugin_directory)
            self.registry.register(manifest)

        return self.registry.list()

    def get(self, plugin_id: str) -> PluginManifest:
        return self.registry.get(plugin_id)


__all__ = ["PluginManager"]
