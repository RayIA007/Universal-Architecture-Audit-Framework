"""
Creates the initial Patch Engine project structure.

Safe to execute multiple times.

Author:
    UAAF

Version:
    1.0.0
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DIRECTORIES = [
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine",
    PROJECT_ROOT / "08_SCRIPTS" / "tests",
    PROJECT_ROOT / "08_SCRIPTS" / "docs",
]

FILES = [
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "__init__.py",

    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "__init__.py",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "engine.py",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "models.py",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "operations.py",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "exceptions.py",
    PROJECT_ROOT / "08_SCRIPTS" / "uaaf_tools" / "patch_engine" / "version.py",

    PROJECT_ROOT / "08_SCRIPTS" / "tests" / "__init__.py",
    PROJECT_ROOT / "08_SCRIPTS" / "tests" / "patch_engine_functional_test.py",

    PROJECT_ROOT / "08_SCRIPTS" / "docs" / "PATCH_ENGINE_ARCHITECTURE_V1.md",
]


def touch(path: Path) -> None:
    """
    Creates an empty file if it does not exist.
    """
    if not path.exists():
        path.touch()


def main() -> int:

    print("=" * 60)
    print("Patch Engine Structure Builder")
    print("=" * 60)

    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Directory: {directory}")

    for file in FILES:
        touch(file)
        print(f"[OK] File: {file}")

    print("-" * 60)
    print("Structure created successfully.")
    print("-" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())