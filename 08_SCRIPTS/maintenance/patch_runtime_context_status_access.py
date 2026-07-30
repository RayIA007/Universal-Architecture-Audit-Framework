"""
PATCH-0003

Correct invalid direct access to Audit and AuditSession from UAAFRuntime in the
RuntimePipeline integration test.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_runtime_context_status_access.py
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
TARGET_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "runtime_pipeline_integration_test.py"
)

CANONICAL_AUDIT_LINE = "print(context.audit.status.value)"
CANONICAL_SESSION_LINE = "print(context.session.status.value)"

AUDIT_VARIANTS = (
    "print(runtime.audit.status.value)",
    "print(runtime.session.audit.status.value)",
    "print(runtime.context.audit.status.value)",
)

SESSION_VARIANTS = (
    "print(runtime.session.status.value)",
    "print(runtime.context.session.status.value)",
)


def create_backup(path: Path) -> Path:
    """Create a timestamped backup beside the target file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def replace_exactly_one_variant(
    source: str,
    *,
    variants: tuple[str, ...],
    canonical: str,
    label: str,
) -> tuple[str, str | None]:
    """Replace exactly one known obsolete variant."""
    canonical_count = source.count(canonical)

    if canonical_count > 1:
        raise RuntimeError(
            f"Expected at most one canonical {label} line, "
            f"but found {canonical_count}."
        )

    matched_variants = [
        variant
        for variant in variants
        if variant != canonical and variant in source
    ]

    if canonical_count == 1:
        if matched_variants:
            raise RuntimeError(
                f"Canonical {label} access already exists, but obsolete "
                f"variants remain: {matched_variants!r}."
            )
        return source, None

    if len(matched_variants) != 1:
        raise RuntimeError(
            f"Expected exactly one known obsolete {label} access variant, "
            f"but found {len(matched_variants)}: {matched_variants!r}."
        )

    obsolete = matched_variants[0]

    if source.count(obsolete) != 1:
        raise RuntimeError(
            f"Expected exactly one occurrence of {obsolete!r}, "
            f"but found {source.count(obsolete)}."
        )

    return source.replace(obsolete, canonical, 1), obsolete


def validate_final_source(source: str) -> None:
    """Validate semantic expectations and Python syntax."""
    if source.count("context = runtime.context") != 1:
        raise RuntimeError(
            "Expected exactly one 'context = runtime.context' assignment."
        )

    if source.count(CANONICAL_AUDIT_LINE) != 1:
        raise RuntimeError(
            "Expected exactly one canonical context.audit status line."
        )

    if source.count(CANONICAL_SESSION_LINE) != 1:
        raise RuntimeError(
            "Expected exactly one canonical context.session status line."
        )

    forbidden_fragments = (
        "runtime.audit.status",
        "runtime.session.audit.status",
        "runtime.session.status",
        "runtime.context.audit.status",
        "runtime.context.session.status",
    )

    remaining = [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ]

    if remaining:
        raise RuntimeError(
            f"Obsolete runtime status access remains: {remaining!r}."
        )

    ast.parse(source, filename=str(TARGET_FILE))


def main() -> int:
    """Apply PATCH-0003 safely and idempotently."""
    if not TARGET_FILE.exists():
        print(
            f"[ERROR] Integration test not found: {TARGET_FILE}",
            file=sys.stderr,
        )
        return 1

    original_bytes = TARGET_FILE.read_bytes()

    try:
        original_source = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        print(
            f"[ERROR] Unable to decode integration test: {error}",
            file=sys.stderr,
        )
        return 1

    try:
        patched_source, replaced_audit = replace_exactly_one_variant(
            original_source,
            variants=AUDIT_VARIANTS,
            canonical=CANONICAL_AUDIT_LINE,
            label="audit",
        )

        patched_source, replaced_session = replace_exactly_one_variant(
            patched_source,
            variants=SESSION_VARIANTS,
            canonical=CANONICAL_SESSION_LINE,
            label="session",
        )

        validate_final_source(patched_source)

    except Exception as error:
        print(f"[ERROR] Patch validation failed: {error}", file=sys.stderr)
        return 1

    if replaced_audit is None and replaced_session is None:
        print("[OK] PATCH-0003 is already applied.")
        print(f"[OK] Target file: {TARGET_FILE}")
        print("[OK] AST validation passed.")
        return 0

    backup_path = create_backup(TARGET_FILE)

    try:
        TARGET_FILE.write_text(
            patched_source,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(
            str(TARGET_FILE),
            doraise=True,
        )

    except Exception as error:
        TARGET_FILE.write_bytes(original_bytes)

        print(
            f"[ROLLBACK] Original integration test restored: {error}",
            file=sys.stderr,
        )
        print(f"[ROLLBACK] Backup retained: {backup_path}")
        return 1

    print("[OK] PATCH-0003 applied successfully.")
    print(f"[OK] Modified file: {TARGET_FILE}")

    if replaced_audit is not None:
        print(
            f"[OK] Replaced: {replaced_audit!r} -> "
            f"{CANONICAL_AUDIT_LINE!r}"
        )

    if replaced_session is not None:
        print(
            f"[OK] Replaced: {replaced_session!r} -> "
            f"{CANONICAL_SESSION_LINE!r}"
        )

    print(f"[OK] Backup created: {backup_path}")
    print("[OK] AST validation passed.")
    print("[OK] Python compilation validation passed.")
    print("[OK] Production runtime code was not modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())