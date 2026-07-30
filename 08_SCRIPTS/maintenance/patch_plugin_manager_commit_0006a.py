"""
PATCH-PLUGIN-MANAGER-COMMIT-0006A

Create the minimal Plugin Manager data model.
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
    / "plugin_models.py"
)

MODULE_SOURCE = '"""\nMinimal data model for UAAF plugins.\n"""\n\nfrom __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom pathlib import Path\n\n\n@dataclass(frozen=True, slots=True)\nclass PluginManifest:\n    """Metadata required to identify and load a local UAAF plugin."""\n\n    plugin_id: str\n    name: str\n    version: str\n    entrypoint: str\n    manifest_path: Path\n\n    @property\n    def plugin_directory(self) -> Path:\n        return self.manifest_path.parent\n\n\n__all__ = ["PluginManifest"]\n'


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
        and node.name == "PluginManifest"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one PluginManifest class; "
            f"found {len(classes)}."
        )

    fields = {
        node.target.id
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
    }

    expected = {
        "plugin_id",
        "name",
        "version",
        "entrypoint",
        "manifest_path",
    }

    if fields != expected:
        raise RuntimeError(
            "PluginManifest fields are invalid. "
            f"Expected {sorted(expected)}, received {sorted(fields)}."
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
        print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006A already applied.")
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

        print("[ROLLBACK] Original plugin model state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006A applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")
    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")
    print("[OK] PluginManifest created.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())