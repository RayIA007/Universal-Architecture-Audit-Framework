"""
Test de validación de capas para Commit 0017.
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


TEST_PROJECT = _PROJECT_ROOT / "test_layer_project"


def setup() -> None:
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)
    TEST_PROJECT.mkdir()

    # Layer: infrastructure (innermost)
    (TEST_PROJECT / "database.py").write_text(
        "def connect():\n    return 'db'\n",
        encoding="utf-8",
    )

    # Layer: business — imports from infrastructure (VALID)
    (TEST_PROJECT / "services.py").write_text(
        "from database import connect\n\ndef get_data():\n    return connect()\n",
        encoding="utf-8",
    )

    # Layer: presentation — imports from business (VALID)
    (TEST_PROJECT / "controllers.py").write_text(
        "from services import get_data\n\ndef handle():\n    return get_data()\n",
        encoding="utf-8",
    )

    # VIOLATION: infrastructure imports from presentation (INVALID)
    (TEST_PROJECT / "utils.py").write_text(
        "from controllers import handle\n\ndef log():\n    return handle()\n",
        encoding="utf-8",
    )

    print("[OK] Created layered project with 1 expected violation:")
    print("     utils (infrastructure) -> controllers (presentation)")


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
            "layers": {
                "order": ["infrastructure", "business", "presentation"],
                "mapping": {
                    "infrastructure": ["database", "utils"],
                    "business": ["services"],
                    "presentation": ["controllers"],
                }
            }
        })

        print()
        print("=" * 60)
        print("LAYER VALIDATION TEST RESULTS")
        print("=" * 60)
        print(f"Python files        : {result['metrics']['python_file_count']}")
        print(f"Local imports       : {result['metrics']['local_import_count']}")
        print(f"Dependency edges    : {result['metrics']['dependency_edge_count']}")
        print(f"Layer violations    : {result['metrics']['layer_violation_count']}")
        print()

        violations = result["summary"]["layer_violations"]

        if violations:
            print("--- LAYER VIOLATIONS DETECTED ---")
            for v in violations:
                print(f"  ❌ {v['message']}")
            print()
            print("✅ TEST PASSED: Layer validation caught the violation.")
            return 0
        else:
            print("❌ TEST FAILED: Expected a layer violation but none found.")
            return 1

    finally:
        teardown()


if __name__ == "__main__":
    raise SystemExit(main())