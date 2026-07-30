"""
PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C-REV2

Correct the Audit Orchestrator using the real PluginManager API.

This patch restores:
    PluginManager.discover()
    PluginManager.get(plugin_id)
    PluginManifest-based entrypoint loading

It also enforces the canonical Audit Result Contract.

Modified file:
    08_SCRIPTS/uaaf_core/audit/audit_orchestrator.py
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

MODULE_SOURCE = '"""\nMinimal audit orchestration for local UAAF plugins.\n"""\n\nfrom __future__ import annotations\n\nimport importlib.util\nfrom pathlib import Path\nfrom types import ModuleType\nfrom typing import Any\n\nfrom uaaf_core.audit.audit_result import validate_audit_result\nfrom uaaf_core.plugins.plugin_manager import PluginManager\nfrom uaaf_core.plugins.plugin_models import PluginManifest\n\n\nclass AuditOrchestrator:\n    """Discover a plugin, load its entrypoint, and execute its run function."""\n\n    def __init__(self, plugins_root: Path | str) -> None:\n        self.plugin_manager = PluginManager(plugins_root)\n\n    def run(self, plugin_id: str, context: Any) -> Any:\n        self.plugin_manager.discover()\n        manifest = self.plugin_manager.get(plugin_id)\n        module = self._load_module(manifest)\n\n        run_function = getattr(module, "run", None)\n\n        if not callable(run_function):\n            raise AttributeError(\n                f"Plugin {plugin_id!r} must expose a callable run(context)."\n            )\n\n        result = run_function(context)\n\n        try:\n            validate_audit_result(result)\n        except (TypeError, ValueError) as exc:\n            raise ValueError(\n                f"Plugin {plugin_id!r} returned an invalid "\n                f"Audit Result Contract: {exc}"\n            ) from exc\n\n        return result\n\n    @staticmethod\n    def _load_module(manifest: PluginManifest) -> ModuleType:\n        entrypoint_path = (\n            manifest.plugin_directory / manifest.entrypoint\n        ).resolve()\n\n        if not entrypoint_path.is_file():\n            raise FileNotFoundError(\n                f"Plugin entrypoint not found: {entrypoint_path}"\n            )\n\n        module_name = (\n            "uaaf_plugin_"\n            + manifest.plugin_id.replace("-", "_")\n        )\n\n        spec = importlib.util.spec_from_file_location(\n            module_name,\n            entrypoint_path,\n        )\n\n        if spec is None or spec.loader is None:\n            raise ImportError(\n                f"Unable to create module spec for: {entrypoint_path}"\n            )\n\n        module = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(module)\n        return module\n\n\n__all__ = ["AuditOrchestrator"]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    ast.parse(source, filename=str(TARGET))

    required_fragments = (
        "from uaaf_core.audit.audit_result import validate_audit_result",
        "from uaaf_core.plugins.plugin_models import PluginManifest",
        "self.plugin_manager.discover()",
        "self.plugin_manager.get(plugin_id)",
        "self._load_module(manifest)",
        "result = run_function(context)",
        "validate_audit_result(result)",
        "return result",
        "manifest.plugin_directory / manifest.entrypoint",
    )

    forbidden_fragments = (
        "get_plugin(",
        "descriptor.path",
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    forbidden = [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ]

    if missing:
        raise RuntimeError(
            "Corrected Audit Orchestrator is incomplete: "
            f"{missing}"
        )

    if forbidden:
        raise RuntimeError(
            "Incompatible PluginManager API remains present: "
            f"{forbidden}"
        )


def main() -> int:
    if not TARGET.is_file():
        print(f"[ERROR] Audit Orchestrator not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print(
            "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C-REV2 "
            "already applied."
        )
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
        TARGET.write_text(
            original,
            encoding="utf-8",
            newline="",
        )

        print("[ROLLBACK] Previous Audit Orchestrator restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print(
        "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C-REV2 "
        "applied successfully."
    )
    print(f"[OK] Updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] PluginManager.discover() restored.")
    print("[OK] PluginManager.get(plugin_id) restored.")
    print("[OK] PluginManifest entrypoint loading restored.")
    print("[OK] Canonical Audit Result enforcement enabled.")
    print("[OK] Incompatible get_plugin() call removed.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())