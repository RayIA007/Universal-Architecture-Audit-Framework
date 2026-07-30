"""
PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007B

Adapt the Documentation Auditor plugin to the minimal orchestration contract.

This commit modifies only:
    plugins/documentation/plugin.py

The plugin exposes:
    run(context)

The existing class-based execute(context) entrypoint remains available as a
small compatibility wrapper.
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
    / "plugins"
    / "documentation"
    / "plugin.py"
)

MODULE_SOURCE = '"""\nMinimal Documentation Auditor plugin for end-to-end orchestration.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\n\ndef run(context: Any) -> dict[str, Any]:\n    """Execute the minimal documentation audit contract."""\n    print("Documentation Auditor loaded successfully.")\n\n    return {\n        "plugin_id": "documentation-auditor",\n        "status": "completed",\n        "context": context,\n    }\n\n\nclass DocumentationAuditorPlugin:\n    """Compatibility wrapper around the functional plugin contract."""\n\n    def execute(self, context: Any) -> dict[str, Any]:\n        return run(context)\n\n\n__all__ = [\n    "DocumentationAuditorPlugin",\n    "run",\n]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    if "run" not in functions:
        raise RuntimeError(
            "Documentation Auditor plugin must define run(context)."
        )

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
            "DocumentationAuditorPlugin must preserve execute(context)."
        )


def main() -> int:
    if not TARGET.parent.is_dir():
        print(
            "[ERROR] Documentation plugin directory not found: "
            f"{TARGET.parent}"
        )
        return 1

    original = (
        TARGET.read_text(encoding="utf-8")
        if TARGET.exists()
        else None
    )

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007B already applied.")
        print("[OK] run(context) contract is present.")
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

        print("[ROLLBACK] Original Documentation Auditor plugin restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007B applied successfully.")
    print(f"[OK] Updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Documentation Auditor now exposes run(context).")
    print("[OK] execute(context) compatibility preserved.")
    print("[OK] Existing Runtime, Plugin Manager, and Orchestrator modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())