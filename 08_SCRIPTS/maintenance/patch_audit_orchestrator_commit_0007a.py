"""
PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007A

Create the minimal AuditOrchestrator.

This commit creates only:
    08_SCRIPTS/uaaf_core/audit/audit_orchestrator.py

The orchestrator discovers a plugin, loads its entrypoint, and invokes a
top-level run(context) function. Existing Runtime and Plugin Manager modules
are not modified.
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
    / "audit"
    / "audit_orchestrator.py"
)

MODULE_SOURCE = '"""\nMinimal audit orchestration for local UAAF plugins.\n"""\n\nfrom __future__ import annotations\n\nimport importlib.util\nfrom pathlib import Path\nfrom types import ModuleType\nfrom typing import Any\n\nfrom uaaf_core.plugins.plugin_manager import PluginManager\nfrom uaaf_core.plugins.plugin_models import PluginManifest\n\n\nclass AuditOrchestrator:\n    """Discover a plugin, load its entrypoint, and execute its run function."""\n\n    def __init__(self, plugins_root: Path | str) -> None:\n        self.plugin_manager = PluginManager(plugins_root)\n\n    def run(self, plugin_id: str, context: Any) -> Any:\n        self.plugin_manager.discover()\n        manifest = self.plugin_manager.get(plugin_id)\n        module = self._load_module(manifest)\n\n        run_function = getattr(module, "run", None)\n\n        if not callable(run_function):\n            raise AttributeError(\n                f"Plugin {plugin_id!r} must expose a callable run(context)."\n            )\n\n        return run_function(context)\n\n    @staticmethod\n    def _load_module(manifest: PluginManifest) -> ModuleType:\n        entrypoint_path = (\n            manifest.plugin_directory / manifest.entrypoint\n        ).resolve()\n\n        if not entrypoint_path.is_file():\n            raise FileNotFoundError(\n                f"Plugin entrypoint not found: {entrypoint_path}"\n            )\n\n        module_name = (\n            "uaaf_plugin_"\n            + manifest.plugin_id.replace("-", "_")\n        )\n\n        spec = importlib.util.spec_from_file_location(\n            module_name,\n            entrypoint_path,\n        )\n\n        if spec is None or spec.loader is None:\n            raise ImportError(\n                f"Unable to create module spec for: {entrypoint_path}"\n            )\n\n        module = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(module)\n        return module\n\n\n__all__ = ["AuditOrchestrator"]\n'


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
        and node.name == "AuditOrchestrator"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one AuditOrchestrator class; "
            f"found {len(classes)}."
        )

    methods = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    required = {
        "__init__",
        "run",
        "_load_module",
    }

    missing = required - methods

    if missing:
        raise RuntimeError(
            "AuditOrchestrator is missing methods: "
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

        print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007A already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(MODULE_SOURCE)

        TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        if original is None:
            if TARGET.exists():
                TARGET.unlink()
        else:
            TARGET.write_text(
                original,
                encoding="utf-8",
                newline="",
            )

        print("[ROLLBACK] Original Audit Orchestrator state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007A applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] AuditOrchestrator created.")
    print("[OK] Plugin entrypoint loading supported.")
    print("[OK] run(context) execution contract established.")
    print("[OK] Existing Runtime and Plugin Manager modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())