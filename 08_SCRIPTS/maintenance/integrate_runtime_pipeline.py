"""
Integrate RuntimePipeline into UAAFRuntime automatically.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/integrate_runtime_pipeline.py

The script:
- patches uaaf_core/runtime/runtime.py;
- adds the RuntimePipeline import when missing;
- replaces only UAAFRuntime.execute_profile_processors();
- preserves the existing public method signature;
- creates a timestamped backup;
- validates the modified module with ast and py_compile;
- restores the original file if validation fails;
- is idempotent.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "uaaf_core"
    / "runtime"
    / "runtime.py"
)

PIPELINE_IMPORT = (
    "from uaaf_core.runtime.pipeline import RuntimePipeline\n"
)

INTEGRATION_MARKER = "RuntimePipeline.from_context(self.context)"


class IntegrationError(RuntimeError):
    """Raised when runtime.py cannot be patched safely."""


def create_backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, destination)
    return destination


def find_class(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise IntegrationError(f"Class {name!r} was not found.")


def find_method(
    class_node: ast.ClassDef,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in class_node.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise IntegrationError(
        f"Method {class_node.name}.{name}() was not found."
    )


def offset_at_line(source: str, line_number: int) -> int:
    lines = source.splitlines(keepends=True)
    return sum(len(line) for line in lines[: line_number - 1])


def offset_after_line(source: str, line_number: int) -> int:
    lines = source.splitlines(keepends=True)
    return sum(len(line) for line in lines[:line_number])


def method_indentation(
    source: str,
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    line = source.splitlines()[method.lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def build_replacement_body(
    indent: str,
    newline: str,
) -> str:
    body = indent + "    "
    return (
        f'{body}"""Execute the active profile through RuntimePipeline."""'
        f"{newline}"
        f"{body}pipeline = RuntimePipeline.from_context(self.context)"
        f"{newline}"
        f"{body}pipeline.execute(self.context)"
        f"{newline}"
        f"{body}return self.context.list_processor_results()"
        f"{newline}"
    )


def replace_method_body(
    source: str,
    method: ast.FunctionDef | ast.AsyncFunctionDef,
    newline: str,
) -> str:
    if not method.body:
        raise IntegrationError(
            "execute_profile_processors() has no method body."
        )

    first_statement = method.body[0]
    last_statement = method.body[-1]

    start = offset_at_line(source, first_statement.lineno)
    end = offset_after_line(source, last_statement.end_lineno)

    indent = method_indentation(source, method)
    replacement = build_replacement_body(indent, newline)

    return source[:start] + replacement + source[end:]


def import_insertion_offset(
    source: str,
    tree: ast.Module,
) -> int:
    """
    Insert after module docstring and import block.

    This keeps imports grouped without reformatting the entire module.
    """
    import_nodes: list[ast.AST] = []

    for index, node in enumerate(tree.body):
        if (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)
            continue

        break

    if import_nodes:
        return offset_after_line(
            source,
            import_nodes[-1].end_lineno,
        )

    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        return offset_after_line(
            source,
            tree.body[0].end_lineno,
        )

    return 0


def ensure_import(source: str, newline: str) -> str:
    if (
        "from uaaf_core.runtime.pipeline import RuntimePipeline"
        in source
    ):
        return source

    tree = ast.parse(source, filename=str(RUNTIME_FILE))
    insertion = import_insertion_offset(source, tree)

    prefix = ""
    if insertion and not source[:insertion].endswith(
        (newline, "\n", "\r")
    ):
        prefix = newline

    return (
        source[:insertion]
        + prefix
        + PIPELINE_IMPORT.replace("\n", newline)
        + source[insertion:]
    )


def validate_integration(source: str) -> None:
    tree = ast.parse(source, filename=str(RUNTIME_FILE))
    runtime_class = find_class(tree, "UAAFRuntime")
    method = find_method(
        runtime_class,
        "execute_profile_processors",
    )

    method_source = ast.get_source_segment(source, method) or ""

    if "RuntimePipeline.from_context" not in method_source:
        raise IntegrationError(
            "RuntimePipeline integration marker was not found "
            "inside execute_profile_processors()."
        )

    if "pipeline.execute" not in method_source:
        raise IntegrationError(
            "Pipeline execution call was not generated."
        )


def main() -> int:
    if not RUNTIME_FILE.exists():
        print(
            f"[ERROR] Target file does not exist: {RUNTIME_FILE}",
            file=sys.stderr,
        )
        return 1

    original_bytes = RUNTIME_FILE.read_bytes()

    try:
        source = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1

    newline = "\r\n" if "\r\n" in source else "\n"

    if INTEGRATION_MARKER in source:
        print(
            "[OK] RuntimePipeline is already integrated. "
            "No changes were made."
        )
        return 0

    try:
        tree = ast.parse(source, filename=str(RUNTIME_FILE))
        runtime_class = find_class(tree, "UAAFRuntime")
        method = find_method(
            runtime_class,
            "execute_profile_processors",
        )

        patched = replace_method_body(
            source,
            method,
            newline,
        )
        patched = ensure_import(patched, newline)

        validate_integration(patched)
    except (SyntaxError, IntegrationError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1

    backup = create_backup(RUNTIME_FILE)

    try:
        RUNTIME_FILE.write_text(
            patched,
            encoding="utf-8",
            newline="",
        )
        py_compile.compile(
            str(RUNTIME_FILE),
            doraise=True,
        )
    except Exception as error:
        RUNTIME_FILE.write_bytes(original_bytes)
        print(
            f"[ROLLBACK] Original runtime.py restored: {error}",
            file=sys.stderr,
        )
        print(f"[ROLLBACK] Backup retained at: {backup}")
        return 1

    print("[OK] RuntimePipeline integrated into UAAFRuntime.")
    print(f"[OK] Modified file: {RUNTIME_FILE}")
    print(f"[OK] Backup created: {backup}")
    print("[OK] Existing public method signature preserved.")
    print("[OK] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())