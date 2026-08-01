from plugins.architecture.architecture_auditor import run

result = run({
    "project_path": ".",
    "audit_type": "architecture",
    "ignored_directories": [".git", "__pycache__", ".venv", "venv", "node_modules"],
    "forbidden_imports": ["subprocess.*"],
    "require_package_initializers": True,
})

print("=== PASO 1.1 — AUDITRESULT CANÓNICO ===")
print(f"Status           : {result['status']}")
print(f"Findings count   : {result['metrics']['findings_count']}")
print(f"Execution start  : {result['execution']['started_at']}")
print(f"Execution end    : {result['execution']['completed_at']}")
print(f"Duration ms      : {result['execution']['duration_ms']}")
print()

print("--- Findings (first 5) ---")
for f in result["findings"][:5]:
    print(f"  [{f['severity']:8}] {f['code']} | {f['path']}")
    print(f"           {f['message'][:80]}...")