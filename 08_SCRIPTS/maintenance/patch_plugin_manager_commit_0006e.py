"""
PATCH-PLUGIN-MANAGER-COMMIT-0006E

Create the first official UAAF plugin fixture:

    plugins/documentation/plugin.yaml
    plugins/documentation/plugin.py

The plugin intentionally performs no audit yet. Its purpose is to provide a
real local plugin for Plugin Manager discovery and loading validation.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

PLUGIN_DIRECTORY = PROJECT_ROOT / "plugins" / "documentation"
MANIFEST_TARGET = PLUGIN_DIRECTORY / "plugin.yaml"
MODULE_TARGET = PLUGIN_DIRECTORY / "plugin.py"

MANIFEST_SOURCE = 'plugin_id: documentation-auditor\nname: Documentation Auditor\nversion: 1.0.0\nentrypoint: plugin.py\n'
MODULE_SOURCE = '"""\nMinimal Documentation Auditor plugin used to validate plugin discovery.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\n\nclass DocumentationAuditorPlugin:\n    """First executable plugin for the UAAF Plugin Manager MVP."""\n\n    def execute(self, context: Any) -> None:\n        print("Documentation Auditor loaded successfully.")\n\n\n__all__ = ["DocumentationAuditorPlugin"]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_manifest(source: str) -> None:
    expected_lines = {
        "plugin_id": "documentation-auditor",
        "name": "Documentation Auditor",
        "version": "1.0.0",
        "entrypoint": "plugin.py",
    }

    parsed: dict[str, str] = {}

    for raw_line in source.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise RuntimeError(
                f"Invalid plugin manifest line: {raw_line!r}"
            )

        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()

    if parsed != expected_lines:
        raise RuntimeError(
            "Documentation plugin manifest is invalid. "
            f"Expected {expected_lines}, received {parsed}."
        )


def validate_module(source: str) -> None:
    tree = ast.parse(source, filename=str(MODULE_TARGET))

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "DocumentationAuditorPlugin"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one DocumentationAuditorPlugin class; "
            f"found {len(classes)}."
        )

    methods = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    if "execute" not in methods:
        raise RuntimeError(
            "DocumentationAuditorPlugin must define execute()."
        )


def restore_file(path: Path, original: str | None) -> None:
    if original is None:
        if path.exists():
            path.unlink()
        return

    path.write_text(original, encoding="utf-8", newline="")


def main() -> int:
    PLUGIN_DIRECTORY.mkdir(parents=True, exist_ok=True)

    original_manifest = (
        MANIFEST_TARGET.read_text(encoding="utf-8")
        if MANIFEST_TARGET.exists()
        else None
    )
    original_module = (
        MODULE_TARGET.read_text(encoding="utf-8")
        if MODULE_TARGET.exists()
        else None
    )

    if (
        original_manifest == MANIFEST_SOURCE
        and original_module == MODULE_SOURCE
    ):
        validate_manifest(original_manifest)
        validate_module(original_module)
        py_compile.compile(str(MODULE_TARGET), doraise=True)

        print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006E already applied.")
        print("[OK] Documentation Auditor plugin is present.")
        print("[OK] Manifest validation passed.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    manifest_backup = create_backup(MANIFEST_TARGET)
    module_backup = create_backup(MODULE_TARGET)

    try:
        validate_manifest(MANIFEST_SOURCE)
        validate_module(MODULE_SOURCE)

        MANIFEST_TARGET.write_text(
            MANIFEST_SOURCE,
            encoding="utf-8",
            newline="",
        )
        MODULE_TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        validate_manifest(
            MANIFEST_TARGET.read_text(encoding="utf-8")
        )
        validate_module(
            MODULE_TARGET.read_text(encoding="utf-8")
        )
        py_compile.compile(str(MODULE_TARGET), doraise=True)

    except Exception as exc:
        restore_file(MANIFEST_TARGET, original_manifest)
        restore_file(MODULE_TARGET, original_module)

        print("[ROLLBACK] Original documentation plugin state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if manifest_backup is not None:
            print(
                "[ROLLBACK] Manifest backup preserved at: "
                f"{manifest_backup}"
            )

        if module_backup is not None:
            print(
                "[ROLLBACK] Module backup preserved at: "
                f"{module_backup}"
            )

        return 1

    print("[OK] PATCH-PLUGIN-MANAGER-COMMIT-0006E applied successfully.")
    print(f"[OK] Created or updated: {MANIFEST_TARGET}")
    print(f"[OK] Created or updated: {MODULE_TARGET}")

    if manifest_backup is not None:
        print(f"[OK] Manifest backup: {manifest_backup}")

    if module_backup is not None:
        print(f"[OK] Module backup: {module_backup}")

    print("[OK] Documentation Auditor plugin created.")
    print("[OK] Plugin manifest validation passed.")
    print("[OK] Plugin module AST validation passed.")
    print("[OK] Plugin module compilation validation passed.")
    print("[OK] Existing Runtime and Plugin Manager modules were not modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())