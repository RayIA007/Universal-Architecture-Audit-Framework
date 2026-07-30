"""
PATCH-RUNTIME-PIPELINE-COMMIT-0001B

Remove obsolete RuntimePipeline._stable_topological_order implementation.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0001b.py
"""
from __future__ import annotations
import ast, py_compile, shutil
from datetime import datetime
from pathlib import Path

SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
TARGET = PROJECT_ROOT/"08_SCRIPTS"/"uaaf_core"/"runtime"/"pipeline.py"

START = "    @staticmethod\n    def _stable_topological_order("
END = "    @staticmethod\n    def _normalize_identifier("

def backup(path: Path)->Path:
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    dst=path.with_name(f"{path.name}.{ts}.bak")
    shutil.copy2(path,dst)
    return dst

def main()->int:
    if not TARGET.exists():
        print(f"[ERROR] File not found: {TARGET}")
        return 1
    original=TARGET.read_text(encoding="utf-8")
    if START not in original:
        print("[OK] Patch already applied.")
        return 0
    s=original.find(START)
    e=original.find(END,s)
    if s==-1 or e==-1:
        print("[ERROR] Unable to locate method boundaries.")
        return 1
    patched=original[:s]+original[e:]
    ast.parse(patched)
    bak=backup(TARGET)
    try:
        TARGET.write_text(patched,encoding="utf-8",newline="")
        py_compile.compile(str(TARGET),doraise=True)
    except Exception as exc:
        TARGET.write_text(original,encoding="utf-8",newline="")
        print(f"[ROLLBACK] {exc}")
        print(f"[ROLLBACK] Backup: {bak}")
        return 1
    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0001B applied successfully.")
    print(f"[OK] Backup: {bak}")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())