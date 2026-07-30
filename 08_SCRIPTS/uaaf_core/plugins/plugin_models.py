"""
Minimal data model for UAAF plugins.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Metadata required to identify and load a local UAAF plugin."""

    plugin_id: str
    name: str
    version: str
    entrypoint: str
    manifest_path: Path

    @property
    def plugin_directory(self) -> Path:
        return self.manifest_path.parent


__all__ = ["PluginManifest"]
