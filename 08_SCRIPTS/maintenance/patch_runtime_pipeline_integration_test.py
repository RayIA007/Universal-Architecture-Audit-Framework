"""
Robust patch for the RuntimePipeline integration test.

This script replaces every remaining ``session.is_running`` reference with
``session.status is SessionStatus.RUNNING`` and ensures that SessionStatus is
imported from uaaf_core.models.enums.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_integration_test.py
"""

from __future__ import annotations

import ast
import py_compile
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
TEST_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "runtime_pipeline_integration_test.py"
)

ENUM_IMPORT_PATTERN = re.compile(
    r"^from uaaf_core\.models\.enums import (?P<names>.+)$",
    re.MULTILINE,
)


def create_backup(path: Path) -> Path:
    """Create a timestamped backup beside the target file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def ensure_session_status_import(source: str) -> str:
    """Add SessionStatus to the existing enums import."""
    match = ENUM_IMPORT_PATTERN.search(source)

    if match is None:
        raise RuntimeError(
            "Could not find the uaaf_core.models.enums import statement."
        )

    names = [name.strip() for name in match.group("names").split(",")]

    if "SessionStatus" in names:
        return source

    names.append("SessionStatus")
    replacement = (
        "from uaaf_core.models.enums import " + ", ".join(names)
    )

    return (
        source[: match.start()]
        + replacement
        + source[match.end() :]
    )


def validate_source(source: str) -> None:
    """Validate the final patched source."""
    if "session.is_running" in source:
        raise RuntimeError(
            "The patched file still contains session.is_running."
        )

    if "SessionStatus.RUNNING" not in source:
        raise RuntimeError(
            "The patched file does not contain SessionStatus.RUNNING."
        )

    if "SessionStatus" not in source:
        raise RuntimeError(
            "The patched file does not import SessionStatus."
        )

    ast.parse(source, filename=str(TEST_FILE))


def main() -> int:
    """Patch the integration test safely."""
    if not TEST_FILE.exists():
        print(
            f"[ERROR] Integration test not found: {TEST_FILE}",
            file=sys.stderr,
        )
        return 1

    original_bytes = TEST_FILE.read_bytes()

    try:
        source = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        print(f"[ERROR] Unable to decode test file: {error}", file=sys.stderr)
        return 1

    obsolete_count = source.count("session.is_running")

    if obsolete_count == 0:
        if (
            "SessionStatus.RUNNING" in source
            and "SessionStatus" in source
        ):
            print("[OK] RuntimePipeline integration test is already patched.")
            return 0

        print(
            "[ERROR] No session.is_running references were found, but the "
            "expected SessionStatus-based correction is also absent.",
            file=sys.stderr,
        )
        print(
            "[ERROR] The local test file differs from the uploaded version.",
            file=sys.stderr,
        )
        return 1

    patched_source = source.replace(
        "session.is_running",
        "session.status is SessionStatus.RUNNING",
    )

    try:
        patched_source = ensure_session_status_import(patched_source)
        validate_source(patched_source)
    except Exception as error:
        print(
            f"[ERROR] Patched source validation failed: {error}",
            file=sys.stderr,
        )
        return 1

    backup_path = create_backup(TEST_FILE)

    try:
        TEST_FILE.write_text(
            patched_source,
            encoding="utf-8",
            newline="",
        )
        py_compile.compile(str(TEST_FILE), doraise=True)
    except Exception as error:
        TEST_FILE.write_bytes(original_bytes)
        print(
            f"[ROLLBACK] Original test restored: {error}",
            file=sys.stderr,
        )
        print(f"[ROLLBACK] Backup retained at: {backup_path}")
        return 1

    print("[OK] RuntimePipeline integration test patched successfully.")
    print(f"[OK] Modified file: {TEST_FILE}")
    print(f"[OK] References replaced: {obsolete_count}")
    print(f"[OK] Backup created: {backup_path}")
    print("[OK] AST validation passed.")
    print("[OK] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())