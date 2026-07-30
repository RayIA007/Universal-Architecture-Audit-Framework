"""
PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008G

Create a deterministic fixture-based functional test for the Documentation
Auditor.

This commit creates:
    08_SCRIPTS/tests/documentation_auditor_functional_test.py

Production modules are not modified.
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
    / "documentation_auditor_functional_test.py"
)

TEST_SOURCE = '"""\nDeterministic functional test for the Documentation Auditor.\n\nThe test builds an isolated temporary project so every supported finding can\nbe validated without depending on the contents of the UAAF repository.\n"""\n\nfrom __future__ import annotations\n\nimport sys\nimport tempfile\nfrom pathlib import Path\n\n\nSCRIPT_FILE = Path(__file__).resolve()\nPROJECT_ROOT = SCRIPT_FILE.parents[2]\nSCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"\n\nif str(SCRIPTS_ROOT) not in sys.path:\n    sys.path.insert(0, str(SCRIPTS_ROOT))\n\nfrom uaaf_core.audit.audit_orchestrator import AuditOrchestrator\n\n\ndef main() -> int:\n    with tempfile.TemporaryDirectory(\n        prefix="uaaf_documentation_auditor_"\n    ) as temporary_directory:\n        fixture_root = Path(temporary_directory)\n\n        _create_fixture(fixture_root)\n\n        orchestrator = AuditOrchestrator(\n            PROJECT_ROOT / "plugins"\n        )\n        result = orchestrator.run(\n            "documentation-auditor",\n            {\n                "project_path": str(fixture_root),\n                "audit_type": "documentation",\n            },\n        )\n\n        _assert_result(result, fixture_root)\n\n    print("documentation-auditor")\n    print("completed_with_findings")\n    print("4")\n    print("3")\n    print("1")\n    print("1")\n    print("2")\n    print("[PASS] Documentation Auditor functional test completed.")\n\n    return 0\n\n\ndef _create_fixture(fixture_root: Path) -> None:\n    (fixture_root / "docs").mkdir(parents=True)\n    (fixture_root / "node_modules").mkdir()\n\n    (fixture_root / "README.md").write_text(\n        "# Fixture Project\\n\\nValid documentation file.\\n",\n        encoding="utf-8",\n    )\n\n    (fixture_root / "docs" / "empty.md").write_text(\n        "",\n        encoding="utf-8",\n    )\n\n    (fixture_root / "docs" / "missing-h1.markdown").write_text(\n        "Documentation without a level-one heading.\\n",\n        encoding="utf-8",\n    )\n\n    (fixture_root / "application.py").write_text(\n        "print(\'fixture\')\\n",\n        encoding="utf-8",\n    )\n\n    (fixture_root / "node_modules" / "ignored.md").write_text(\n        "",\n        encoding="utf-8",\n    )\n\n\ndef _assert_result(\n    result: dict[str, object],\n    fixture_root: Path,\n) -> None:\n    assert result["plugin_id"] == "documentation-auditor"\n    assert result["status"] == "completed_with_findings"\n    assert result["project_path"] == str(fixture_root.resolve())\n\n    assert result["files_scanned"] == 4\n    assert result["markdown_file_count"] == 3\n    assert result["empty_markdown_file_count"] == 1\n    assert result["markdown_files_without_h1_count"] == 1\n    assert result["findings_count"] == 2\n    assert result["errors"] == []\n\n    findings = result["findings"]\n    assert isinstance(findings, list)\n\n    findings_by_code = {\n        finding["code"]: finding\n        for finding in findings\n    }\n\n    assert set(findings_by_code) == {\n        "DOC_EMPTY_FILE",\n        "DOC_MISSING_H1",\n    }\n\n    assert findings_by_code["DOC_EMPTY_FILE"] == {\n        "code": "DOC_EMPTY_FILE",\n        "severity": "warning",\n        "path": "docs/empty.md",\n        "message": "Markdown file is empty.",\n    }\n\n    assert findings_by_code["DOC_MISSING_H1"] == {\n        "code": "DOC_MISSING_H1",\n        "severity": "warning",\n        "path": "docs/missing-h1.markdown",\n        "message": (\n            "Markdown file does not contain a level-one heading."\n        ),\n    }\n\n    assert "node_modules/ignored.md" not in result["markdown_files"]\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


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

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_functions = {
        "main",
        "_create_fixture",
        "_assert_result",
    }

    missing_functions = required_functions - functions

    if missing_functions:
        raise RuntimeError(
            "Functional test is missing functions: "
            f"{', '.join(sorted(missing_functions))}."
        )

    required_fragments = (
        "TemporaryDirectory",
        '"DOC_EMPTY_FILE"',
        '"DOC_MISSING_H1"',
        '"node_modules/ignored.md"',
        '"files_scanned"] == 4',
        '"markdown_file_count"] == 3',
        "[PASS] Documentation Auditor functional test completed.",
    )

    missing_fragments = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing_fragments:
        raise RuntimeError(
            "Functional test is missing deterministic checks: "
            f"{missing_fragments}"
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

        print(
            "[OK] PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008G "
            "already applied."
        )
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

        print(
            "[ROLLBACK] Original Documentation Auditor "
            "functional test restored."
        )
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                f"[ROLLBACK] Backup preserved at: {backup_path}"
            )

        return 1

    print(
        "[OK] PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008G "
        "applied successfully."
    )
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Isolated temporary project fixture created.")
    print("[OK] DOC_EMPTY_FILE behavior covered.")
    print("[OK] DOC_MISSING_H1 behavior covered.")
    print("[OK] Ignored-directory behavior covered.")
    print("[OK] Exact finding payloads validated.")
    print("[OK] Existing production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())