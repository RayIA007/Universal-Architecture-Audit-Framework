"""
Test combinado para Commit 0018 (Forbidden Imports) y 0019 (Missing __init__.py).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from plugins.architecture.architecture_auditor import run


TEST_PROJECT = _PROJECT_ROOT / "test_forbidden_init_project"


def setup() -> None:
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)
    TEST_PROJECT.mkdir()

    # Package WITH __init__.py
    pkg_ok = TEST_PROJECT / "core"
    pkg_ok.mkdir()
    (pkg_ok / "__init__.py").write_text("", encoding="utf-8")
    (pkg_ok / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

    # Package WITHOUT __init__.py (violation 0019)
    pkg_bad = TEST_PROJECT / "api"
    pkg_bad.mkdir()
    (pkg_bad / "routes.py").write_text("def index(): pass\n", encoding="utf-8")

    # Module with forbidden import (violation 0018)
    (TEST_PROJECT / "main.py").write_text(
        "from subprocess import call\nfrom api.routes import index\n\ndef run(): pass\n",
        encoding="utf-8",
    )

    print("[OK] Created test project:")
    print("     - core/          (has __init__.py)  -> OK")
    print("     - api/           (no __init__.py)   -> VIOLATION 0019")
    print("     - main.py        (imports subprocess) -> VIOLATION 0018")


def teardown() -> None:
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)
    print("[OK] Cleaned up.")


def main() -> int:
    setup()

    try:
        result = run({
            "project_path": str(TEST_PROJECT),
            "audit_type": "architecture",
            "ignored_directories": [],
            "forbidden_imports": ["subprocess.*", "os.system"],
            "require_package_initializers": True,
        })

        print()
        print("=" * 60)
        print("COMMIT 0018 + 0019 TEST RESULTS")
        print("=" * 60)
        print(f"Python files              : {result['metrics']['python_file_count']}")
        print(f"Packages                  : {result['metrics']['package_count']}")
        print(f"Forbidden imports         : {result['metrics']['forbidden_import_count']}")
        print(f"Missing __init__.py       : {result['metrics']['missing_package_initializer_count']}")
        print()

        fb = result["summary"]["forbidden_violations"]
        mi = result["summary"]["missing_package_initializer_violations"]

        if fb:
            print("--- FORBIDDEN IMPORTS (0018) ---")
            for v in fb:
                print(f"  ❌ {v['message']}")
            print()

        if mi:
            print("--- MISSING __init__.py (0019) ---")
            for v in mi:
                print(f"  ❌ {v['message']}")
            print()

        if fb and mi:
            print("✅ TEST PASSED: Both 0018 and 0019 detected violations.")
            return 0
        else:
            print("❌ TEST FAILED: Expected violations from both checks.")
            return 1

    finally:
        teardown()


if __name__ == "__main__":
    raise SystemExit(main())