"""
PATCH-PLUGIN-MANAGER-COMMIT-0006B

Create the minimal local plugin manifest loader.
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
    / "plugin_loader.py"
)

MODULE_SOURCE = '"""\nLoad a local UAAF plugin manifest from plugin.yaml.\n"""\n\nfrom __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Any\n\nimport yaml\n\nfrom uaaf_core.plugins.plugin_models import PluginManifest\n\n\nclass PluginLoader:\n    """Load and validate a minimal local plugin manifest."""\n\n    MANIFEST_FILENAME = "plugin.yaml"\n\n    @classmethod\n    def load_manifest(cls, plugin_directory: Path | str) -> PluginManifest:\n        directory = Path(plugin_directory).resolve()\n        manifest_path = directory / cls.MANIFEST_FILENAME\n\n        if not directory.is_dir():\n            raise FileNotFoundError(\n                f"Plugin directory not found: {directory}"\n            )\n\n        if not manifest_path.is_file():\n            raise FileNotFoundError(\n                f"Plugin manifest not found: {manifest_path}"\n            )\n\n        with manifest_path.open("r", encoding="utf-8") as stream:\n            raw_data = yaml.safe_load(stream)\n\n        if not isinstance(raw_data, dict):\n            raise ValueError(\n                f"Plugin manifest must contain a mapping: {manifest_path}"\n            )\n\n        values = {\n            field: cls._required_string(raw_data, field, manifest_path)\n            for field in (\n                "plugin_id",\n                "name",\n                "version",\n                "entrypoint",\n            )\n        }\n\n        return PluginManifest(\n            plugin_id=values["plugin_id"],\n            name=values["name"],\n            version=values["version"],\n            entrypoint=values["entrypoint"],\n            manifest_path=manifest_path,\n        )\n\n    @staticmethod\n    def _required_string(\n        data: dict[str, Any],\n        field: str,\n        manifest_path: Path,\n    ) -> str:\n        value = data.get(field)\n\n        if not isinstance(value, str) or not value.strip():\n            raise ValueError(\n                f"Plugin manifest field {field!r} must be a "\n                f"non-empty string: {manifest_path}"\n            )\n\n        return value.strip()\n\n\n__all__ = ["PluginLoader"]\n'


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
        and node.name == "PluginLoader"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one PluginLoader class; "
            f"found {len(classes)}."
        )

    methods = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    required = {
        "load_manifest",
        "_required_string",
    }

    missing = required - methods
    if missing:
        raise RuntimeError(
            "PluginLoader is missing methods: "
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
        print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006B already applied.")
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

        print("[ROLLBACK] Original plugin loader state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006B applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")
    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")
    print("[OK] PluginLoader created.")
    print("[OK] plugin.yaml loading supported.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())