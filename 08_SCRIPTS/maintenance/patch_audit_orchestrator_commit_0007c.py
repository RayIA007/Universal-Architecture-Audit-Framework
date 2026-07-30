"""
PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007C

Create the end-to-end Audit Orchestrator smoke test.
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
    / "tests"
    / "audit_orchestrator_smoke_test.py"
)

TEST_SOURCE = '"""\nEnd-to-end smoke test for the UAAF Audit Orchestrator MVP.\n"""\n\nfrom __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\n\nSCRIPT_FILE = Path(__file__).resolve()\nPROJECT_ROOT = SCRIPT_FILE.parents[2]\nSCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"\n\nif str(SCRIPTS_ROOT) not in sys.path:\n    sys.path.insert(0, str(SCRIPTS_ROOT))\n\nfrom uaaf_core.audit.audit_orchestrator import AuditOrchestrator\n\n\ndef main() -> int:\n    context = {\n        "project_path": str(PROJECT_ROOT),\n        "audit_type": "documentation",\n    }\n\n    orchestrator = AuditOrchestrator(PROJECT_ROOT / "plugins")\n    result = orchestrator.run(\n        "documentation-auditor",\n        context,\n    )\n\n    assert isinstance(result, dict)\n    assert result["plugin_id"] == "documentation-auditor"\n    assert result["status"] == "completed"\n    assert result["context"] == context\n\n    print(result["plugin_id"])\n    print(result["status"])\n    print(result["context"]["audit_type"])\n    print("[PASS] Audit Orchestrator smoke test completed.")\n\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


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

    if "main" not in functions:
        raise RuntimeError(
            "Audit Orchestrator smoke test must define main()."
        )

    required_fragments = (
        'AuditOrchestrator(PROJECT_ROOT / "plugins")',
        'orchestrator.run(',
        '"documentation-auditor"',
        '[PASS] Audit Orchestrator smoke test completed.',
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing:
        raise RuntimeError(
            "Smoke test is missing required checks: "
            f"{missing}"
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    original = (
        TARGET.read_text(encoding="utf-8")
        if TARGET.exists()
        else None
    )

    if original == TEST_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007C already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(TEST_SOURCE)

        TARGET.write_text(
            TEST_SOURCE,
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

        print("[ROLLBACK] Original Audit Orchestrator smoke test restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-AUDIT-ORCHESTRATOR-COMMIT-0007C applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Audit Orchestrator smoke test created.")
    print("[OK] End-to-end plugin execution validation added.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())