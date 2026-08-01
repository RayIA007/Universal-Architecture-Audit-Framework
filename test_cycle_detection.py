"""
Test de ciclo artificial para Commit 0016 — Cycle Detection.

Crea un micro-proyecto con 3 módulos que forman un ciclo:
  a.py -> b.py -> c.py -> a.py

Luego ejecuta el Architecture Auditor y verifica que detecta el ciclo.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Bootstrap
_PROJECT_ROOT = Path(__file__).resolve().parent
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from plugins.architecture.architecture_auditor import run


TEST_PROJECT = _PROJECT_ROOT / "test_cycle_project"


def setup() -> None:
    """Create the artificial cyclic project."""
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)

    TEST_PROJECT.mkdir()

    (TEST_PROJECT / "a.py").write_text(
        "from b import b_func\n\ndef a_func():\n    return b_func()\n",
        encoding="utf-8",
    )
    (TEST_PROJECT / "b.py").write_text(
        "from c import c_func\n\ndef b_func():\n    return c_func()\n",
        encoding="utf-8",
    )
    (TEST_PROJECT / "c.py").write_text(
        "from a import a_func\n\ndef c_func():\n    return a_func()\n",
        encoding="utf-8",
    )

    print(f"[OK] Created cyclic project at: {TEST_PROJECT}")
    print("     a.py -> b.py -> c.py -> a.py")


def teardown() -> None:
    """Remove the test project."""
    if TEST_PROJECT.exists():
        shutil.rmtree(TEST_PROJECT)
    print(f"[OK] Cleaned up: {TEST_PROJECT}")


def main() -> int:
    setup()

    try:
        result = run({
            "project_path": str(TEST_PROJECT),
            "audit_type": "architecture",
            "ignored_directories": [],
        })

        print()
        print("=" * 60)
        print("CYCLE DETECTION TEST RESULTS")
        print("=" * 60)
        print(f"Python files           : {result['metrics']['python_file_count']}")
        print(f"Modules                : {result['metrics']['module_count']}")
        print(f"Local imports          : {result['metrics']['local_import_count']}")
        print(f"Dependency edges       : {result['metrics']['dependency_edge_count']}")
        print(f"Circular dependencies  : {result['metrics']['circular_dependency_count']}")
        print()

        cycles = result["summary"]["dependency_cycles"]

        if cycles:
            print("--- CYCLES DETECTED ---")
            for cycle in cycles:
                arrow = " -> ".join(cycle)
                print(f"  {arrow} -> {cycle[0]}")
            print()
            print("✅ TEST PASSED: Cycle detection is working correctly.")
            return 0
        else:
            print("--- NO CYCLES DETECTED ---")
            print("❌ TEST FAILED: Expected a cycle but none was found.")
            return 1

    finally:
        teardown()


if __name__ == "__main__":
    raise SystemExit(main())