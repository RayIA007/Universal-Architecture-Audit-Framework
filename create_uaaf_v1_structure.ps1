$ErrorActionPreference = 'Stop'
$Root = "C:\Universal Architecture Audit Framework (UAAF)"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " UAAF v1.0 - Structure Generator" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Root: $Root"

New-Item -ItemType Directory -Force -Path $Root | Out-Null

$Directories = @(
    "00_DOCUMENTATION/01_GOVERNANCE",
    "00_DOCUMENTATION/02_ARCHITECTURE",
    "00_DOCUMENTATION/03_METHODOLOGY",
    "00_DOCUMENTATION/04_PLANNING",
    "01_CONFIG",
    "02_SCHEMAS",
    "03_RULES/architecture",
    "03_RULES/documentation",
    "03_RULES/code",
    "03_RULES/testing",
    "03_RULES/ai_systems",
    "03_RULES/governance",
    "04_AUDIT_PROFILES",
    "05_INPUTS",
    "06_WORKSPACES",
    "07_OUTPUTS/reports",
    "07_OUTPUTS/matrices",
    "07_OUTPUTS/evidence",
    "08_SCRIPTS/uaaf_core/engines",
    "08_SCRIPTS/uaaf_core/adapters",
    "08_SCRIPTS/uaaf_core/auditors",
    "08_SCRIPTS/uaaf_core/plugins",
    "08_SCRIPTS/uaaf_core/reporting",
    "08_SCRIPTS/uaaf_core/validators",
    "08_SCRIPTS/uaaf_core/utils",
    "09_TESTS/unit",
    "09_TESTS/integration",
    "09_TESTS/smoke",
    "09_TESTS/fixtures",
    "10_TEMPLATES/reports",
    "10_TEMPLATES/matrices",
    "10_TEMPLATES/manifests",
    "11_LOGS",
    "12_EXAMPLES/sample_project",
    "13_PLUGINS",
    "90_SPECIFICATIONS"
)

foreach ($Directory in $Directories) {
    $Target = Join-Path $Root $Directory
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Write-Host "[DIR ] $Directory"
}

$Files = @(
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    ".gitignore",
    ".env.example",
    "pyproject.toml",
    "run.py",

    "00_DOCUMENTATION/01_GOVERNANCE/UAAF_CORE_CONSTITUTION.md",
    "00_DOCUMENTATION/01_GOVERNANCE/UAAF_DOCUMENT_HIERARCHY.md",
    "00_DOCUMENTATION/01_GOVERNANCE/UAAF_GOVERNANCE_MODEL.md",
    "00_DOCUMENTATION/01_GOVERNANCE/UAAF_LANGUAGE_STANDARD.md",
    "00_DOCUMENTATION/01_GOVERNANCE/UAAF_ENGINEERING_STANDARD.md",

    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_CORE_ARCHITECTURE.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_ARCHITECTURE_STANDARD.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_LAYERED_ARCHITECTURE.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_RUNTIME_ARCHITECTURE.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_PIPELINE_ARCHITECTURE.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_PLUGIN_ARCHITECTURE.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_DATA_MODEL.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_COMPONENT_CATALOG.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_DATA_FLOW.md",
    "00_DOCUMENTATION/02_ARCHITECTURE/UAAF_SECURITY_MODEL.md",

    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_AUDIT_METHODOLOGY.md",
    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_SCORING_METHODOLOGY.md",
    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_FINDING_TAXONOMY.md",
    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_EVIDENCE_STANDARD.md",
    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_TRACEABILITY_STANDARD.md",
    "00_DOCUMENTATION/03_METHODOLOGY/UAAF_REPORT_STANDARD.md",

    "00_DOCUMENTATION/04_PLANNING/UAAF_IMPLEMENTATION_PLAN.md",
    "00_DOCUMENTATION/04_PLANNING/UAAF_TEST_STRATEGY.md",
    "00_DOCUMENTATION/04_PLANNING/UAAF_ACCEPTANCE_CRITERIA.md",
    "00_DOCUMENTATION/04_PLANNING/UAAF_ROADMAP.md",

    "01_CONFIG/uaaf.yaml",
    "01_CONFIG/defaults.yaml",
    "01_CONFIG/logging.yaml",
    "01_CONFIG/severity_levels.yaml",

    "02_SCHEMAS/project_manifest.schema.json",
    "02_SCHEMAS/audit_profile.schema.json",
    "02_SCHEMAS/audit_run.schema.json",
    "02_SCHEMAS/audit_rule.schema.json",
    "02_SCHEMAS/audit_finding.schema.json",
    "02_SCHEMAS/audit_evidence.schema.json",
    "02_SCHEMAS/audit_score.schema.json",
    "02_SCHEMAS/audit_report.schema.json",

    "03_RULES/architecture/core_rules.yaml",
    "03_RULES/documentation/core_rules.yaml",
    "03_RULES/code/core_rules.yaml",
    "03_RULES/testing/core_rules.yaml",
    "03_RULES/ai_systems/core_rules.yaml",
    "03_RULES/governance/core_rules.yaml",

    "04_AUDIT_PROFILES/generic_project.yaml",
    "04_AUDIT_PROFILES/documentation_only.yaml",
    "04_AUDIT_PROFILES/python_project.yaml",
    "04_AUDIT_PROFILES/ai_system.yaml",
    "04_AUDIT_PROFILES/cips.yaml",

    "05_INPUTS/.gitkeep",
    "06_WORKSPACES/.gitkeep",
    "07_OUTPUTS/reports/.gitkeep",
    "07_OUTPUTS/matrices/.gitkeep",
    "07_OUTPUTS/evidence/.gitkeep",

    "08_SCRIPTS/uaaf_core/__init__.py",
    "08_SCRIPTS/uaaf_core/kernel.py",
    "08_SCRIPTS/uaaf_core/engine.py",
    "08_SCRIPTS/uaaf_core/audit_orchestrator.py",
    "08_SCRIPTS/uaaf_core/registry.py",
    "08_SCRIPTS/uaaf_core/models.py",
    "08_SCRIPTS/uaaf_core/exceptions.py",
    "08_SCRIPTS/uaaf_core/cli.py",

    "08_SCRIPTS/uaaf_core/engines/__init__.py",
    "08_SCRIPTS/uaaf_core/engines/contract_engine.py",
    "08_SCRIPTS/uaaf_core/engines/rule_engine.py",
    "08_SCRIPTS/uaaf_core/engines/evidence_engine.py",
    "08_SCRIPTS/uaaf_core/engines/finding_engine.py",
    "08_SCRIPTS/uaaf_core/engines/scoring_engine.py",
    "08_SCRIPTS/uaaf_core/engines/metrics_engine.py",
    "08_SCRIPTS/uaaf_core/engines/traceability_engine.py",
    "08_SCRIPTS/uaaf_core/engines/report_engine.py",

    "08_SCRIPTS/uaaf_core/adapters/__init__.py",
    "08_SCRIPTS/uaaf_core/adapters/filesystem_adapter.py",
    "08_SCRIPTS/uaaf_core/adapters/markdown_adapter.py",
    "08_SCRIPTS/uaaf_core/adapters/python_ast_adapter.py",
    "08_SCRIPTS/uaaf_core/adapters/yaml_adapter.py",
    "08_SCRIPTS/uaaf_core/adapters/json_adapter.py",

    "08_SCRIPTS/uaaf_core/auditors/__init__.py",
    "08_SCRIPTS/uaaf_core/auditors/base_auditor.py",
    "08_SCRIPTS/uaaf_core/auditors/documentation_auditor.py",
    "08_SCRIPTS/uaaf_core/auditors/architecture_auditor.py",
    "08_SCRIPTS/uaaf_core/auditors/code_auditor.py",
    "08_SCRIPTS/uaaf_core/auditors/testing_auditor.py",
    "08_SCRIPTS/uaaf_core/auditors/ai_system_auditor.py",

    "08_SCRIPTS/uaaf_core/plugins/__init__.py",
    "08_SCRIPTS/uaaf_core/plugins/plugin_manager.py",
    "08_SCRIPTS/uaaf_core/plugins/plugin_loader.py",
    "08_SCRIPTS/uaaf_core/plugins/plugin_validator.py",

    "08_SCRIPTS/uaaf_core/reporting/__init__.py",
    "08_SCRIPTS/uaaf_core/reporting/report_generator.py",
    "08_SCRIPTS/uaaf_core/reporting/matrix_generator.py",
    "08_SCRIPTS/uaaf_core/reporting/markdown_renderer.py",

    "08_SCRIPTS/uaaf_core/validators/__init__.py",
    "08_SCRIPTS/uaaf_core/validators/schema_validator.py",
    "08_SCRIPTS/uaaf_core/validators/rule_validator.py",
    "08_SCRIPTS/uaaf_core/validators/evidence_validator.py",

    "08_SCRIPTS/uaaf_core/utils/__init__.py",
    "08_SCRIPTS/uaaf_core/utils/file_utils.py",
    "08_SCRIPTS/uaaf_core/utils/hash_utils.py",
    "08_SCRIPTS/uaaf_core/utils/path_utils.py",

    "09_TESTS/conftest.py",
    "09_TESTS/unit/test_models.py",
    "09_TESTS/unit/test_rule_engine.py",
    "09_TESTS/unit/test_scoring_engine.py",
    "09_TESTS/integration/test_audit_pipeline.py",
    "09_TESTS/smoke/test_uaaf_smoke.py",
    "09_TESTS/fixtures/.gitkeep",

    "10_TEMPLATES/reports/executive_report.md",
    "10_TEMPLATES/reports/technical_report.md",
    "10_TEMPLATES/matrices/master_audit_matrix.md",
    "10_TEMPLATES/manifests/project_manifest.yaml",

    "11_LOGS/.gitkeep",
    "12_EXAMPLES/sample_project/README.md",
    "13_PLUGINS/README.md",

    "90_SPECIFICATIONS/UAAF_CORE_SPECIFICATION.md",
    "90_SPECIFICATIONS/UAAF_DOMAIN_MODEL.md",
    "90_SPECIFICATIONS/UAAF_CONTRACT_CATALOG.md",
    "90_SPECIFICATIONS/UAAF_PLUGIN_CONTRACT.md",
    "90_SPECIFICATIONS/UAAF_MVP_SPECIFICATION.md"
)

foreach ($File in $Files) {
    $Target = Join-Path $Root $File
    $Parent = Split-Path -Parent $Target

    if (-not (Test-Path $Parent)) {
        New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    }

    if (-not (Test-Path $Target)) {
        New-Item -ItemType File -Path $Target | Out-Null
        Write-Host "[FILE] $File"
    }
    else {
        Write-Host "[SKIP] $File already exists" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "UAAF v1.0 structure created successfully." -ForegroundColor Green
Write-Host "Existing files were preserved." -ForegroundColor Green
Write-Host "Root: $Root"