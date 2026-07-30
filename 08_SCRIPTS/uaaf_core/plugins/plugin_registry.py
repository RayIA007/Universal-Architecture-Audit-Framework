"""
Minimal in-memory registry for discovered UAAF plugins.
"""

from __future__ import annotations

from uaaf_core.plugins.plugin_models import PluginManifest


class PluginRegistry:
    """Store plugin manifests by plugin identifier."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        if not isinstance(manifest, PluginManifest):
            raise TypeError("manifest must be a PluginManifest.")

        if manifest.plugin_id in self._plugins:
            raise ValueError(
                f"Plugin already registered: {manifest.plugin_id}"
            )

        self._plugins[manifest.plugin_id] = manifest

    def get(self, plugin_id: str) -> PluginManifest:
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise ValueError("plugin_id must be a non-empty string.")

        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise KeyError(f"Plugin not registered: {plugin_id}") from exc

    def list(self) -> tuple[PluginManifest, ...]:
        return tuple(
            self._plugins[plugin_id]
            for plugin_id in sorted(self._plugins)
        )

    def __contains__(self, plugin_id: object) -> bool:
        return plugin_id in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)


__all__ = ["PluginRegistry"]
