"""
Automated patch for UAAF Audit metadata API.

Adds Audit.get_metadata() to:
    08_SCRIPTS/uaaf_core/models/audit.py

Properties:
- Idempotent: does nothing if get_metadata() already exists.
- Creates a timestamped backup before changing the file.
- Reuses the key-normalization expression from set_metadata() when possible.
- Validates the modified module with py_compile.
- Restores the original file automatically if validation fails.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_audit_get_metadata.py
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = PROJECT_ROOT / "08_SCRIPTS" / "uaaf_core" / "models" / "audit.py"


class PatchError(RuntimeError):
    """Raised when the source file cannot be patched safely."""


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def find_audit_class(tree: ast.Module) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Audit":
            return node
    raise PatchError("The class 'Audit' was not found in audit.py.")


def find_method(class_node: ast.ClassDef, name: str):
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def get_normalization_expression(source: str, set_metadata_method: ast.FunctionDef):
    for statement in set_metadata_method.body:
        if not isinstance(statement, ast.Assign):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id == "normalized_key":
                segment = ast.get_source_segment(source, statement.value)
                if segment:
                    return segment.strip()
    return None


def build_method_source(class_indent: str, body_indent: str, normalization_expression, newline: str) -> str:
    if normalization_expression:
        expression_lines = normalization_expression.splitlines()
        normalized_expression = newline.join(
            body_indent + line if index > 0 else line
            for index, line in enumerate(expression_lines)
        )
        normalization_block = f"{body_indent}normalized_key = {normalized_expression}{newline}"
    else:
        normalization_block = (
            f"{body_indent}if not isinstance(key, str):{newline}"
            f"{body_indent}    raise TypeError({newline}"
            f'{body_indent}        "Audit metadata key must be a string, "{newline}'
            f"{body_indent}        f\"received {{type(key).__name__}}.\"{newline}"
            f"{body_indent}    ){newline}"
            f"{body_indent}normalized_key = key.strip(){newline}"
            f"{body_indent}if not normalized_key:{newline}"
            f"{body_indent}    raise ValueError({newline}"
            f'{body_indent}        "Audit metadata key cannot be empty."{newline}'
            f"{body_indent}    ){newline}"
        )

    return (
        f"{newline}"
        f"{class_indent}def get_metadata({newline}"
        f"{body_indent}self,{newline}"
        f"{body_indent}key: str,{newline}"
        f"{body_indent}default: Any = None,{newline}"
        f"{class_indent}) -> Any:{newline}"
        f'{body_indent}"""Return one audit metadata value."""{newline}'
        f"{normalization_block}"
        f"{body_indent}return self.metadata.get(normalized_key, default){newline}"
    )


def line_end_offset(text: str, node: ast.AST) -> int:
    if not hasattr(node, "end_lineno") or node.end_lineno is None:
        raise PatchError("Python could not determine the end of set_metadata().")
    lines = text.splitlines(keepends=True)
    return sum(len(line) for line in lines[: node.end_lineno])


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup)
    return backup


def validate_python(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)


def patch() -> int:
    if not AUDIT_FILE.exists():
        raise PatchError(f"Target file does not exist: {AUDIT_FILE}")

    source = AUDIT_FILE.read_text(encoding="utf-8")
    newline = detect_newline(source)

    try:
        tree = ast.parse(source, filename=str(AUDIT_FILE))
    except SyntaxError as error:
        raise PatchError(f"audit.py already contains a syntax error: {error}") from error

    audit_class = find_audit_class(tree)

    if find_method(audit_class, "get_metadata") is not None:
        print("[OK] Audit.get_metadata() already exists. No changes were made.")
        return 0

    set_metadata_method = find_method(audit_class, "set_metadata")
    if set_metadata_method is None:
        raise PatchError("Audit.set_metadata() was not found; the patch was not applied.")

    source_lines = source.splitlines()
    method_line = source_lines[set_metadata_method.lineno - 1]
    class_indent = method_line[: len(method_line) - len(method_line.lstrip())]
    body_indent = class_indent + "    "

    normalization_expression = get_normalization_expression(source, set_metadata_method)
    method_source = build_method_source(
        class_indent,
        body_indent,
        normalization_expression,
        newline,
    )

    insertion_offset = line_end_offset(source, set_metadata_method)
    patched_source = source[:insertion_offset] + method_source + source[insertion_offset:]

    try:
        ast.parse(patched_source, filename=str(AUDIT_FILE))
    except SyntaxError as error:
        raise PatchError(f"The generated patch is not syntactically valid: {error}") from error

    backup = create_backup(AUDIT_FILE)

    try:
        AUDIT_FILE.write_text(patched_source, encoding="utf-8", newline="")
        validate_python(AUDIT_FILE)
    except Exception:
        shutil.copy2(backup, AUDIT_FILE)
        print(f"[ROLLBACK] Original file restored from: {backup}")
        raise

    print("[OK] Audit.get_metadata() was added successfully.")
    print(f"[OK] Modified file: {AUDIT_FILE}")
    print(f"[OK] Backup created: {backup}")
    print("[OK] Python compilation validation passed.")
    return 0


def main() -> int:
    try:
        return patch()
    except (PatchError, OSError, UnicodeError, py_compile.PyCompileError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())