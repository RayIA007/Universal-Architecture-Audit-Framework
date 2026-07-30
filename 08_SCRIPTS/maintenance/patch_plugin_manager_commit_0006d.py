"""
PATCH-PLUGIN-MANAGER-COMMIT-0006D

Create the minimal PluginManager orchestration component.
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
    / "plugin_manager.py"
)

MODULE_SOURCE = '"""\nMinimal Plugin Manager for local UAAF plugins.\n"""\n\nfrom __future__ import annotations\n\nfrom pathlib import Path\n\nfrom uaaf_core.plugins.plugin_loader import PluginLoader\nfrom uaaf_core.plugins.plugin_models import PluginManifest\nfrom uaaf_core.plugins.plugin_registry import PluginRegistry\n\n\nclass PluginManager:\n    """Discover and access local plugins from a plugins directory."""\n\n    def __init__(self, plugins_root: Path | str) -> None:\n        self.plugins_root = Path(plugins_root).resolve()\n        self.registry = PluginRegistry()\n\n    def discover(self) -> tuple[PluginManifest, ...]:\n        if not self.plugins_root.is_dir():\n            raise FileNotFoundError(\n                f"Plugins directory not found: {self.plugins_root}"\n            )\n\n        self.registry = PluginRegistry()\n\n        for plugin_directory in sorted(self.plugins_root.iterdir()):\n            if not plugin_directory.is_dir():\n                continue\n\n            manifest_path = (\n                plugin_directory / PluginLoader.MANIFEST_FILENAME\n            )\n\n            if not manifest_path.is_file():\n                continue\n\n            manifest = PluginLoader.load_manifest(plugin_directory)\n            self.registry.register(manifest)\n\n        return self.registry.list()\n\n    def get(self, plugin_id: str) -> PluginManifest:\n        return self.registry.get(plugin_id)\n\n\n__all__ = ["PluginManager"]\n'


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
        and node.name == "PluginManager"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one PluginManager class; "
            f"found {len(classes)}."
        )

    methods = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    required = {
        "__init__",
        "discover",
        "get",
    }

    missing = required - methods
    if missing:
        raise RuntimeError(
            "PluginManager is missing methods: "
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
        print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006D already applied.")
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

        print("[ROLLBACK] Original plugin manager state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006D applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")
    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")
    print("[OK] PluginManager created.")
    print("[OK] Local plugin discovery supported.")
    print("[OK] Existing runtime modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())