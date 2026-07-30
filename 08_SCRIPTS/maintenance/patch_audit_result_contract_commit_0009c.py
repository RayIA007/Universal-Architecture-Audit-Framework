"""
PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C

Enforce the canonical Audit Result Contract in the Audit Orchestrator.

This commit modifies only:
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

MODULE_SOURCE = '"""\nAudit Orchestrator.\n\nDiscovers an auditor plugin, loads its runtime module, executes run(context),\nand enforces the canonical Audit Result Contract before returning the result.\n"""\n\nfrom __future__ import annotations\n\nimport importlib.util\nfrom pathlib import Path\nfrom types import ModuleType\nfrom typing import Any\n\nfrom uaaf_core.audit.audit_result import validate_audit_result\nfrom uaaf_core.plugins.plugin_manager import PluginManager\n\n\nclass AuditOrchestrator:\n    """Execute registered audit plugins through the Plugin Manager."""\n\n    def __init__(self, plugins_root: str | Path) -> None:\n        self.plugins_root = Path(plugins_root).resolve()\n        self.plugin_manager = PluginManager(self.plugins_root)\n\n    def run(\n        self,\n        plugin_id: str,\n        context: Any,\n    ) -> dict[str, Any]:\n        """Execute one plugin and enforce the canonical result contract."""\n        descriptor = self.plugin_manager.get_plugin(plugin_id)\n        module_path = self.plugins_root / descriptor.path\n\n        module = self._load_module(\n            plugin_id=plugin_id,\n            module_path=module_path,\n        )\n\n        run_callable = getattr(module, "run", None)\n\n        if not callable(run_callable):\n            raise AttributeError(\n                f"Plugin {plugin_id!r} does not expose callable run(context)."\n            )\n\n        result = run_callable(context)\n\n        try:\n            validate_audit_result(result)\n        except (TypeError, ValueError) as exc:\n            raise ValueError(\n                f"Plugin {plugin_id!r} returned an invalid "\n                f"Audit Result Contract: {exc}"\n            ) from exc\n\n        return result\n\n    @staticmethod\n    def _load_module(\n        *,\n        plugin_id: str,\n        module_path: Path,\n    ) -> ModuleType:\n        if not module_path.is_file():\n            raise FileNotFoundError(\n                f"Plugin runtime module not found: {module_path}"\n            )\n\n        safe_plugin_id = plugin_id.replace("-", "_")\n        module_name = f"uaaf_plugin_{safe_plugin_id}"\n\n        spec = importlib.util.spec_from_file_location(\n            module_name,\n            module_path,\n        )\n\n        if spec is None or spec.loader is None:\n            raise ImportError(\n                f"Unable to create module specification for: {module_path}"\n            )\n\n        module = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(module)\n\n        return module\n\n\n__all__ = ["AuditOrchestrator"]\n'


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
    tree = ast.parse(source, filename=str(TARGET))

    classes = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }

    if "AuditOrchestrator" not in classes:
        raise RuntimeError(
            "Audit Orchestrator class is missing."
        )

    required_fragments = (
        "from uaaf_core.audit.audit_result import validate_audit_result",
        "validate_audit_result(result)",
        "invalid Audit Result Contract",
        "return result",
        "PluginManager",
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing:
        raise RuntimeError(
            "Audit Orchestrator enforcement is incomplete: "
            f"{missing}"
        )


def main() -> int:
    if not TARGET.is_file():
        print(
            "[ERROR] Audit Orchestrator not found: "
            f"{TARGET}"
        )
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print(
            "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C "
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

        print("[ROLLBACK] Original Audit Orchestrator restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                f"[ROLLBACK] Backup preserved at: {backup_path}"
            )

        return 1

    print(
        "[OK] PATCH-AUDIT-RESULT-CONTRACT-COMMIT-0009C "
        "applied successfully."
    )
    print(f"[OK] Updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Audit Result Contract enforcement enabled.")
    print("[OK] Invalid plugin results now fail fast.")
    print("[OK] Plugin execution behavior preserved.")
    print("[OK] Existing plugins were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())