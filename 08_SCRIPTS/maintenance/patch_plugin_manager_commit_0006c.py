"""
PATCH-PLUGIN-MANAGER-COMMIT-0006C

Create the minimal in-memory plugin registry.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "uaaf_core"
    / "plugins"
    / "plugin_registry.py"
)

MODULE_SOURCE = '"""\nMinimal in-memory registry for discovered UAAF plugins.\n"""\n\nfrom __future__ import annotations\n\nfrom uaaf_core.plugins.plugin_models import PluginManifest\n\n\nclass PluginRegistry:\n    """Store plugin manifests by plugin identifier."""\n\n    def __init__(self) -> None:\n        self._plugins: dict[str, PluginManifest] = {}\n\n    def register(self, manifest: PluginManifest) -> None:\n        if not isinstance(manifest, PluginManifest):\n            raise TypeError("manifest must be a PluginManifest.")\n\n        if manifest.plugin_id in self._plugins:\n            raise ValueError(\n                f"Plugin already registered: {manifest.plugin_id}"\n            )\n\n        self._plugins[manifest.plugin_id] = manifest\n\n    def get(self, plugin_id: str) -> PluginManifest:\n        if not isinstance(plugin_id, str) or not plugin_id.strip():\n            raise ValueError("plugin_id must be a non-empty string.")\n\n        try:\n            return self._plugins[plugin_id]\n        except KeyError as exc:\n            raise KeyError(f"Plugin not registered: {plugin_id}") from exc\n\n    def list(self) -> tuple[PluginManifest, ...]:\n        return tuple(\n            self._plugins[plugin_id]\n            for plugin_id in sorted(self._plugins)\n        )\n\n    def __contains__(self, plugin_id: object) -> bool:\n        return plugin_id in self._plugins\n\n    def __len__(self) -> int:\n        return len(self._plugins)\n\n\n__all__ = ["PluginRegistry"]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PluginRegistry"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one PluginRegistry class; "
            f"found {len(classes)}."
        )

    methods = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    required = {
        "__init__",
        "register",
        "get",
        "list",
        "__contains__",
        "__len__",
    }

    missing = required - methods
    if missing:
        raise RuntimeError(
            "PluginRegistry is missing methods: "
            f"{', '.join(sorted(missing))}."
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    original = (
        TARGET.read_text(encoding="utf-8")
        if TARGET.exists()
        else None
    )

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)
        print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006C already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(MODULE_SOURCE)
        TARGET.write_text(MODULE_SOURCE, encoding="utf-8", newline="")
        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))
    except Exception as exc:
        if original is None:
            if TARGET.exists():
                TARGET.unlink()
        else:
            TARGET.write_text(original, encoding="utf-8", newline="")

        print("[ROLLBACK] Original plugin registry state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006C applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")
    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")
    print("[OK] PluginRegistry created.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())