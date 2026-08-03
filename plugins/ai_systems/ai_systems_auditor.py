"""
AI Systems Auditor Plugin — Fase 2.2

Audita el uso de sistemas de IA/LLMs en código Python:
- Imports de librerías de IA.
- Secretos y API keys hardcodeados.
- Prompts largos hardcodeados.
- Llamadas a APIs de IA sin manejo de errores o retry.
- eval/exec/ast.literal_eval con outputs de LLM.
- Configuraciones de generación inseguras.
- Modelos deprecated o no recomendados.
- Agentes autónomos y patrones RAG sin safeguards.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

# Bootstrap
_PLUGIN_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _PLUGIN_FILE.parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
)

PLUGIN_ID = "ai-systems-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "ai_systems"

_DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "build",
        "dist",
        "site-packages",
    }
)

_DEFAULT_AI_LIBRARIES = frozenset(
    {
        "openai",
        "anthropic",
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langchain_anthropic",
        "llama_index",
        "transformers",
        "torch",
        "tensorflow",
        "keras",
        "google.generativeai",
        "google.genai",
        "vertexai",
        "cohere",
        "mistralai",
        "ollama",
        "huggingface_hub",
        "sentence_transformers",
        "semantic_kernel",
        "autogen",
        "crewai",
        "haystack",
        "pydantic_ai",
    }
)

_DEFAULT_SECRET_PATTERNS = (
    r"\bsk-[A-Za-z0-9_-]{16,}\b",
    r"\bsk-proj-[A-Za-z0-9_-]{12,}\b",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bghp_[A-Za-z0-9]{30,}\b",
    r"\bglpat-[A-Za-z0-9_-]{20,}\b",
    r"\bhf_[A-Za-z0-9]{20,}\b",
    r"\b(?:OPENAI|ANTHROPIC|COHERE|MISTRAL|GOOGLE|GEMINI|HUGGINGFACE|HF)_API_KEY\b\s*[:=]\s*[rubfRUBF]*['\"][^'\"\r\n]{8,}['\"]",
)

_DEFAULT_DEPRECATED_MODELS = frozenset(
    {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k",
        "text-davinci-003",
        "text-davinci-002",
        "code-davinci-002",
        "code-cushman-001",
        "davinci",
        "curie",
        "babbage",
        "ada",
        "claude-1",
        "claude-2",
        "claude-instant-1",
    }
)

_DEFAULT_PROMPT_MIN_CHARS = 200
_DEFAULT_MAX_REASONABLE_TOKENS = 32768

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "ai_libraries",
    "secret_patterns",
    "prompt_min_chars",
    "max_reasonable_tokens",
    "deprecated_models",
}

_PROMPT_NAME_MARKERS = (
    "prompt",
    "system_message",
    "system_instruction",
    "instructions",
    "instruction",
    "message_template",
)

_PROMPT_TEXT_PATTERN = re.compile(
    r"(?is)\b(you are|act as|system prompt|system message|instructions?|"
    r"respond|answer|generate|summari[sz]e|classify|analy[sz]e|do not|must|"
    r"eres un|act[uú]a como|instrucciones?|responde|genera|resume|clasifica|"
    r"analiza|no debes|debes)\b"
)

_GENERATION_CALL_SUFFIXES = (
    "chat.completions.create",
    "ChatCompletion.create",
    "chat_completion.create",
    "Completion.create",
    "completions.create",
    "responses.create",
    "messages.create",
    "generate_content",
    "generate",
    "invoke",
    "ainvoke",
    "predict",
    "apredict",
    "complete",
    "acomplete",
    "chat",
    "run",
    "arun",
    "stream",
    "astream",
)

_RETRIEVAL_CALL_MARKERS = (
    "similarity_search",
    "similarity_search_with_score",
    "as_retriever",
    "retrieve",
    "aretrieve",
    "get_relevant_documents",
    "query_engine.query",
    "vector_store.query",
    "vectorstore.query",
)

_EMBEDDING_MARKERS = (
    "embedding",
    "embeddings",
    "embed_query",
    "embed_documents",
    "sentence_transformer",
    "vectorstore",
    "vector_store",
    "faiss",
    "chromadb",
    "pinecone",
    "weaviate",
    "qdrant",
)

_SOURCE_VALIDATION_MARKERS = (
    "validate_source",
    "validate_sources",
    "verify_source",
    "verify_sources",
    "verify_context",
    "validate_context",
    "check_citation",
    "check_citations",
    "source_validation",
    "citation_validation",
    "rerank",
    "relevance_score",
    "similarity_threshold",
    "score_threshold",
    "metadata_filter",
    "trusted_source",
    "allowed_source",
)

_HUMAN_SAFEGUARD_MARKERS = (
    "input",
    "human_approval",
    "human_input",
    "human_in_the_loop",
    "request_approval",
    "approve",
    "confirm",
    "human_review",
    "manual_review",
    "review_by_human",
    "interrupt",
)

_RETRY_DECORATOR_MARKERS = (
    "retry",
    "tenacity.retry",
    "backoff.on_exception",
    "backoff.on_predicate",
)

_DANGEROUS_EVALUATORS = {"eval", "exec", "ast.literal_eval"}
_LLM_OUTPUT_NAME_PATTERN = re.compile(
    r"(?i)(llm|model|ai|assistant|completion|generation|generated).*(output|response|text|code|result)|"
    r"(output|response|text|code|result).*(llm|model|ai|assistant|completion|generation|generated)"
)


@dataclass(frozen=True, slots=True)
class _ModuleAnalysis:
    path: str
    source: str
    tree: ast.Module
    parents: dict[ast.AST, ast.AST]
    ai_aliases: frozenset[str]
    ai_objects: frozenset[str]
    retry_configured_objects: frozenset[str]


# =====================================================================
# PUBLIC API
# =====================================================================


def run(context: Any) -> dict[str, Any]:
    """Execute the AI systems audit and emit a canonical AuditResult."""

    started_at = _utc_now_iso()
    t0 = datetime.now(timezone.utc)
    (
        project_path,
        ignored_directories,
        ai_libraries,
        secret_patterns,
        prompt_min_chars,
        max_reasonable_tokens,
        deprecated_models,
    ) = _validate_context(context)

    python_files = _discover_python_files(project_path, ignored_directories)

    imports: list[dict[str, Any]] = []
    secrets: list[dict[str, Any]] = []
    prompts: list[dict[str, Any]] = []
    api_errors: list[dict[str, Any]] = []
    eval_risks: list[dict[str, Any]] = []
    unsafe_configs: list[dict[str, Any]] = []
    deprecated: list[dict[str, Any]] = []
    safety: list[dict[str, Any]] = []
    parse_errors: list[str] = []

    compiled_secret_patterns = _compile_patterns(secret_patterns)

    for relative_path in python_files:
        file_path = project_path / relative_path
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            parse_errors.append(f"Cannot read {relative_path!r}: {exc}")
            continue

        secrets.extend(
            _detect_hardcoded_secrets(
                source=source,
                relative_path=relative_path,
                compiled_patterns=compiled_secret_patterns,
            )
        )

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            parse_errors.append(
                f"Cannot parse {relative_path!r} at line {exc.lineno or 0}: {exc.msg}"
            )
            continue

        analysis = _build_module_analysis(
            relative_path=relative_path,
            source=source,
            tree=tree,
            ai_libraries=ai_libraries,
        )

        imports.extend(_detect_ai_imports(analysis, ai_libraries))
        prompts.extend(_detect_hardcoded_prompts(analysis, prompt_min_chars))
        api_errors.extend(_detect_unprotected_ai_calls(analysis))
        eval_risks.extend(_detect_llm_eval_usage(analysis))
        unsafe_configs.extend(
            _detect_unsafe_generation_config(
                analysis,
                max_reasonable_tokens=max_reasonable_tokens,
            )
        )
        deprecated.extend(_detect_deprecated_models(analysis, deprecated_models))
        safety.extend(_detect_autonomous_agents(analysis))
        safety.extend(_detect_unvalidated_rag(analysis))

    raw_groups = {
        "import_violations": _sort_violations(imports),
        "secret_violations": _sort_violations(secrets),
        "prompt_violations": _sort_violations(prompts),
        "error_handling_violations": _sort_violations(api_errors),
        "eval_violations": _sort_violations(eval_risks),
        "generation_config_violations": _sort_violations(unsafe_configs),
        "model_violations": _sort_violations(deprecated),
        "safety_violations": _sort_violations(safety),
    }

    findings = _build_findings(**raw_groups)

    if parse_errors:
        status = AuditStatus.COMPLETED_WITH_ERRORS
    elif findings:
        status = AuditStatus.COMPLETED_WITH_FINDINGS
    else:
        status = AuditStatus.COMPLETED

    completed_at = _utc_now_iso()
    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    result = AuditResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        audit_type=AUDIT_TYPE,
        status=status,
        summary={
            "project_path": str(project_path),
            "python_files": python_files,
            **raw_groups,
        },
        metrics={
            "python_file_count": len(python_files),
            "ai_import_count": len(raw_groups["import_violations"]),
            "secret_count": len(raw_groups["secret_violations"]),
            "hardcoded_prompt_count": len(raw_groups["prompt_violations"]),
            "unprotected_api_call_count": len(
                raw_groups["error_handling_violations"]
            ),
            "llm_eval_count": len(raw_groups["eval_violations"]),
            "unsafe_generation_config_count": len(
                raw_groups["generation_config_violations"]
            ),
            "deprecated_model_count": len(raw_groups["model_violations"]),
            "safety_violation_count": len(raw_groups["safety_violations"]),
            "parse_error_count": len(parse_errors),
            "findings_count": len(findings),
        },
        findings=tuple(findings),
        errors=tuple(parse_errors),
        execution=AuditExecution(
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        ),
    )
    return result.to_dict()


# =====================================================================
# CONTEXT VALIDATION
# =====================================================================


def _validate_context(
    context: Any,
) -> tuple[
    Path,
    frozenset[str],
    frozenset[str],
    tuple[str, ...],
    int,
    int,
    frozenset[str],
]:
    """Validate context and return normalized plugin configuration."""

    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary.")

    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS
    if unknown_fields:
        raise ValueError(
            "context contains unknown fields: " f"{sorted(unknown_fields)}"
        )

    raw_project_path = context.get("project_path")
    if not isinstance(raw_project_path, (str, Path)):
        raise ValueError("context must contain a valid project_path.")

    project_path = Path(raw_project_path).expanduser().resolve()
    if not project_path.is_dir():
        raise ValueError(
            f"project_path must reference an existing directory: {project_path}"
        )

    audit_type = context.get("audit_type")
    if audit_type is not None and audit_type != AUDIT_TYPE:
        raise ValueError(f"audit_type must be {AUDIT_TYPE!r}.")

    ignored_directories = _validate_ignored_directories(
        context.get("ignored_directories", [])
    )
    ai_libraries = _validate_string_set(
        context.get("ai_libraries", list(_DEFAULT_AI_LIBRARIES)),
        "ai_libraries",
    )
    secret_patterns = tuple(
        _validate_string_list(
            context.get("secret_patterns", list(_DEFAULT_SECRET_PATTERNS)),
            "secret_patterns",
        )
    )
    _compile_patterns(secret_patterns)

    prompt_min_chars = _validate_positive_int(
        context.get("prompt_min_chars", _DEFAULT_PROMPT_MIN_CHARS),
        "prompt_min_chars",
    )
    max_reasonable_tokens = _validate_positive_int(
        context.get("max_reasonable_tokens", _DEFAULT_MAX_REASONABLE_TOKENS),
        "max_reasonable_tokens",
    )
    deprecated_models = _validate_string_set(
        context.get("deprecated_models", list(_DEFAULT_DEPRECATED_MODELS)),
        "deprecated_models",
    )

    return (
        project_path,
        ignored_directories,
        ai_libraries,
        secret_patterns,
        prompt_min_chars,
        max_reasonable_tokens,
        deprecated_models,
    )


def _validate_ignored_directories(value: Any) -> frozenset[str]:
    """Validate user exclusions and merge them with defaults."""

    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(
            "ignored_directories must be a collection of directory names."
        )

    normalized = set(_DEFAULT_IGNORED_DIRECTORIES)
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "ignored_directories entries must be non-empty strings."
            )
        directory_name = item.strip()
        if Path(directory_name).name != directory_name:
            raise ValueError(
                "ignored_directories entries must be directory names, "
                f"not paths: {directory_name!r}."
            )
        normalized.add(directory_name)

    return frozenset(normalized)


def _validate_string_set(value: Any, field_name: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"{field_name} must be a collection of strings.")

    result: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings.")
        result.add(item.strip())
    return frozenset(result)


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list of strings.")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings.")
        result.append(item.strip())
    return result


def _validate_positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _compile_patterns(patterns: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise ValueError(f"Invalid secret pattern {pattern!r}: {exc}") from exc
    return tuple(compiled)


# =====================================================================
# DISCOVERY AND MODULE ANALYSIS
# =====================================================================


def _discover_python_files(
    project_path: Path,
    ignored_directories: frozenset[str],
) -> list[str]:
    """Return deterministic relative POSIX paths for Python source files."""

    discovered: list[str] = []
    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name for name in directory_names if name not in ignored_directories
        )
        root_path = Path(root)
        for file_name in sorted(file_names):
            if Path(file_name).suffix.lower() != ".py":
                continue
            discovered.append(
                (root_path / file_name).relative_to(project_path).as_posix()
            )
    return sorted(discovered)


def _build_module_analysis(
    relative_path: str,
    source: str,
    tree: ast.Module,
    ai_libraries: frozenset[str],
) -> _ModuleAnalysis:
    parents = _build_parent_map(tree)
    ai_aliases = _collect_ai_aliases(tree, ai_libraries)
    ai_objects, retry_objects = _collect_ai_objects(
        tree=tree,
        ai_aliases=ai_aliases,
        ai_libraries=ai_libraries,
    )
    return _ModuleAnalysis(
        path=relative_path,
        source=source,
        tree=tree,
        parents=parents,
        ai_aliases=frozenset(ai_aliases),
        ai_objects=frozenset(ai_objects),
        retry_configured_objects=frozenset(retry_objects),
    )


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _collect_ai_aliases(
    tree: ast.AST,
    ai_libraries: frozenset[str],
) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _match_ai_library(alias.name, ai_libraries):
                    aliases.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_match = _match_ai_library(module, ai_libraries)
            if module_match:
                if module:
                    aliases.add(module.split(".")[0])
                for alias in node.names:
                    aliases.add(alias.asname or alias.name)
                continue

            for alias in node.names:
                combined = f"{module}.{alias.name}" if module else alias.name
                if _match_ai_library(combined, ai_libraries):
                    aliases.add(alias.asname or alias.name)
                    if module:
                        aliases.add(module.split(".")[0])
    return aliases


def _collect_ai_objects(
    tree: ast.Module,
    ai_aliases: set[str],
    ai_libraries: frozenset[str],
) -> tuple[set[str], set[str]]:
    objects: set[str] = set()
    retry_objects: set[str] = set()

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                continue
            value = _assignment_value(node)
            targets = _assignment_target_names(node)
            if value is None or not targets:
                continue

            is_ai_value = False
            has_retry = False
            if isinstance(value, ast.Call):
                call_name = _dotted_name(value.func)
                root = call_name.split(".")[0] if call_name else ""
                is_ai_value = (
                    root in ai_aliases
                    or root in objects
                    or _name_matches_ai_library(call_name, ai_libraries)
                )
                has_retry = _keyword_positive(value, "max_retries")
            else:
                referenced = _referenced_names(value)
                is_ai_value = bool(referenced & objects)
                has_retry = bool(referenced & retry_objects)

            if is_ai_value:
                before = len(objects)
                objects.update(targets)
                retry_objects.update(targets if has_retry else set())
                if len(objects) != before:
                    changed = True

    return objects, retry_objects


# =====================================================================
# RULE: AI IMPORTS
# =====================================================================


def _detect_ai_imports(
    analysis: _ModuleAnalysis,
    ai_libraries: frozenset[str],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    for node in ast.walk(analysis.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                library = _match_ai_library(alias.name, ai_libraries)
                if library:
                    violations.append(
                        {
                            "type": "ai_import",
                            "path": analysis.path,
                            "line": getattr(node, "lineno", 0),
                            "library": library,
                            "imported_module": alias.name,
                            "message": (
                                f"AI library {library!r} imported in "
                                f"{analysis.path!r} at line {getattr(node, 'lineno', 0)}."
                            ),
                        }
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            library = _match_ai_library(module, ai_libraries)
            imported_module = module
            if library:
                violations.append(
                    {
                        "type": "ai_import",
                        "path": analysis.path,
                        "line": getattr(node, "lineno", 0),
                        "library": library,
                        "imported_module": imported_module,
                        "message": (
                            f"AI library {library!r} imported in "
                            f"{analysis.path!r} at line {getattr(node, 'lineno', 0)}."
                        ),
                    }
                )
                continue

            for alias in node.names:
                imported_module = (
                    f"{module}.{alias.name}" if module else alias.name
                )
                library = _match_ai_library(imported_module, ai_libraries)
                if not library:
                    continue
                violations.append(
                    {
                        "type": "ai_import",
                        "path": analysis.path,
                        "line": getattr(node, "lineno", 0),
                        "library": library,
                        "imported_module": imported_module,
                        "message": (
                            f"AI library {library!r} imported in "
                            f"{analysis.path!r} at line {getattr(node, 'lineno', 0)}."
                        ),
                    }
                )

    return _deduplicate_violations(violations, ("path", "line", "library"))


# =====================================================================
# RULE: HARDCODED SECRETS
# =====================================================================


def _detect_hardcoded_secrets(
    source: str,
    relative_path: str,
    compiled_patterns: Iterable[re.Pattern[str]],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    for line_no, line in enumerate(source.splitlines(), start=1):
        for pattern in compiled_patterns:
            match = pattern.search(line)
            if not match:
                continue
            matched_text = match.group(0)
            if _looks_like_placeholder_secret(matched_text):
                continue
            secret_type = _classify_secret(matched_text)
            violations.append(
                {
                    "type": "hardcoded_ai_secret",
                    "path": relative_path,
                    "line": line_no,
                    "secret_type": secret_type,
                    "matched_pattern": pattern.pattern,
                    "redacted": _redact_secret(matched_text),
                    "message": (
                        f"Possible hardcoded {secret_type} secret in "
                        f"{relative_path!r} at line {line_no}."
                    ),
                }
            )
            break

    return violations


# =====================================================================
# RULE: HARDCODED PROMPTS
# =====================================================================


def _detect_hardcoded_prompts(
    analysis: _ModuleAnalysis,
    prompt_min_chars: int,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    docstrings = _docstring_nodes(analysis.tree)

    for node in ast.walk(analysis.tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node in docstrings:
                continue
            parent = analysis.parents.get(node)
            if isinstance(parent, ast.JoinedStr):
                continue
            text = node.value
            kind = "string"
        elif isinstance(node, ast.JoinedStr):
            text = _joined_string_static_text(node)
            kind = "f-string"
        else:
            continue

        if len(text.strip()) <= prompt_min_chars:
            continue
        if not _looks_like_prompt(node, text, analysis):
            continue

        segment = ast.get_source_segment(analysis.source, node) or ""
        if _is_external_file_reference(node, analysis.parents):
            continue

        violations.append(
            {
                "type": "hardcoded_prompt",
                "path": analysis.path,
                "line": getattr(node, "lineno", 0),
                "char_count": len(text),
                "string_kind": kind,
                "triple_quoted": _is_triple_quoted(segment),
                "message": (
                    f"Long hardcoded prompt detected in {analysis.path!r} "
                    f"at line {getattr(node, 'lineno', 0)} ({len(text)} chars)."
                ),
            }
        )

    return _deduplicate_violations(violations, ("path", "line", "char_count"))


# =====================================================================
# RULE: UNPROTECTED AI API CALLS
# =====================================================================


def _detect_unprotected_ai_calls(
    analysis: _ModuleAnalysis,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    for call in _iter_ai_generation_calls(analysis):
        exception_protected = _has_try_ancestor(call, analysis.parents)
        retry_protected = _has_retry_safeguard(call, analysis)
        if exception_protected and retry_protected:
            continue

        call_name = _dotted_name(call.func) or "<dynamic-call>"
        missing: list[str] = []
        if not exception_protected:
            missing.append("exception_handling")
        if not retry_protected:
            missing.append("retry_logic")

        violations.append(
            {
                "type": "unprotected_ai_call",
                "path": analysis.path,
                "line": getattr(call, "lineno", 0),
                "call": call_name,
                "missing_exception_handling": not exception_protected,
                "missing_retry_logic": not retry_protected,
                "message": (
                    f"AI API call {call_name!r} in {analysis.path!r} at line "
                    f"{getattr(call, 'lineno', 0)} lacks {', '.join(missing)}."
                ),
            }
        )

    return violations


# =====================================================================
# RULE: EVAL/EXEC WITH LLM OUTPUT
# =====================================================================


def _detect_llm_eval_usage(
    analysis: _ModuleAnalysis,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    tainted_names = _collect_llm_output_names(analysis)

    for node in ast.walk(analysis.tree):
        if not isinstance(node, ast.Call):
            continue
        evaluator = _dotted_name(node.func)
        if evaluator not in _DANGEROUS_EVALUATORS or not node.args:
            continue

        argument = node.args[0]
        referenced = _referenced_names(argument)
        has_direct_ai_call = any(
            _is_ai_generation_call(candidate, analysis)
            for candidate in ast.walk(argument)
            if isinstance(candidate, ast.Call)
        )
        suspicious_name = any(
            _LLM_OUTPUT_NAME_PATTERN.search(name) for name in referenced
        )

        if not (referenced & tainted_names or has_direct_ai_call or suspicious_name):
            continue

        violations.append(
            {
                "type": "llm_output_evaluation",
                "path": analysis.path,
                "line": getattr(node, "lineno", 0),
                "evaluator": evaluator,
                "tainted_names": sorted(referenced & tainted_names),
                "message": (
                    f"{evaluator!r} evaluates possible LLM output in "
                    f"{analysis.path!r} at line {getattr(node, 'lineno', 0)}."
                ),
            }
        )

    return violations


# =====================================================================
# RULE: UNSAFE GENERATION CONFIG
# =====================================================================


def _detect_unsafe_generation_config(
    analysis: _ModuleAnalysis,
    max_reasonable_tokens: int,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    candidate_calls = [
        node
        for node in ast.walk(analysis.tree)
        if isinstance(node, ast.Call)
        and (
            _is_ai_generation_call(node, analysis)
            or _is_ai_configuration_call(node, analysis)
        )
    ]

    for call in candidate_calls:
        reasons: list[str] = []
        is_generation_call = _is_ai_generation_call(call, analysis)
        temperature = _numeric_keyword(call, ("temperature",))
        max_tokens_keyword = _find_keyword(
            call,
            ("max_tokens", "max_output_tokens", "max_new_tokens"),
        )
        max_tokens = (
            _numeric_literal(max_tokens_keyword.value)
            if max_tokens_keyword is not None
            else None
        )

        if temperature is not None and temperature > 0.9:
            reasons.append("temperature_above_0_9")

        if is_generation_call and max_tokens_keyword is None:
            reasons.append("missing_max_tokens_limit")
        elif max_tokens_keyword is not None and max_tokens is None:
            if _is_none_literal(max_tokens_keyword.value):
                reasons.append("unbounded_max_tokens")
        elif max_tokens is not None and (
            max_tokens <= 0 or max_tokens > max_reasonable_tokens
        ):
            reasons.append("unreasonable_max_tokens")

        if not reasons:
            continue

        call_name = _dotted_name(call.func) or "<dynamic-call>"
        violations.append(
            {
                "type": "unsafe_generation_config",
                "path": analysis.path,
                "line": getattr(call, "lineno", 0),
                "call": call_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "max_reasonable_tokens": max_reasonable_tokens,
                "reasons": reasons,
                "message": (
                    f"Unsafe generation configuration for {call_name!r} in "
                    f"{analysis.path!r} at line {getattr(call, 'lineno', 0)}: "
                    f"{', '.join(reasons)}."
                ),
            }
        )

    return violations


# =====================================================================
# RULE: DEPRECATED MODELS
# =====================================================================


def _detect_deprecated_models(
    analysis: _ModuleAnalysis,
    deprecated_models: frozenset[str],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    normalized_models = {model.lower(): model for model in deprecated_models}

    for node in ast.walk(analysis.tree):
        candidates: list[tuple[str, str]] = []

        if isinstance(node, ast.keyword) and node.arg in {
            "model",
            "model_name",
            "model_id",
            "deployment_name",
        }:
            value = _string_literal(node.value)
            if value is not None:
                candidates.append((value, node.arg))

        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            target_names = _assignment_target_names(node)
            if any("model" in name.lower() for name in target_names):
                value_node = _assignment_value(node)
                value = _string_literal(value_node) if value_node is not None else None
                if value is not None:
                    candidates.append((value, ",".join(sorted(target_names))))

        elif isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                key = _string_literal(key_node)
                value = _string_literal(value_node)
                if key and value and "model" in key.lower():
                    candidates.append((value, f"dict:{key}"))

        elif isinstance(node, ast.Call) and _is_ai_generation_call(node, analysis):
            if node.args:
                value = _string_literal(node.args[0])
                if value is not None:
                    candidates.append((value, "positional_model"))

        for model_value, context in candidates:
            matched = _match_deprecated_model(model_value, normalized_models)
            if matched is None:
                continue
            violations.append(
                {
                    "type": "deprecated_model",
                    "path": analysis.path,
                    "line": getattr(node, "lineno", 0),
                    "model": matched,
                    "context": context,
                    "message": (
                        f"Deprecated or non-recommended model {matched!r} used in "
                        f"{analysis.path!r} at line {getattr(node, 'lineno', 0)}."
                    ),
                }
            )

    return _deduplicate_violations(violations, ("path", "line", "model"))


# =====================================================================
# RULE: AUTONOMOUS AGENTS WITHOUT SAFEGUARDS
# =====================================================================


def _detect_autonomous_agents(
    analysis: _ModuleAnalysis,
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    for node in ast.walk(analysis.tree):
        if not isinstance(node, ast.While):
            continue
        ai_calls = [
            call
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            and _is_ai_generation_call(call, analysis)
        ]
        if not ai_calls:
            continue
        if _loop_has_clear_safeguard(node):
            continue

        function = _nearest_ancestor(
            node,
            analysis.parents,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        function_name = function.name if function is not None else "<module>"
        violations.append(
            {
                "type": "autonomous_agent_without_safeguards",
                "path": analysis.path,
                "line": getattr(node, "lineno", 0),
                "function": function_name,
                "ai_call_count": len(ai_calls),
                "message": (
                    f"Autonomous AI loop without a clear stop condition or "
                    f"human safeguard detected in {analysis.path!r} at line "
                    f"{getattr(node, 'lineno', 0)}."
                ),
            }
        )

    return violations


# =====================================================================
# RULE: RAG WITHOUT SOURCE VALIDATION
# =====================================================================


def _detect_unvalidated_rag(
    analysis: _ModuleAnalysis,
) -> list[dict[str, Any]]:
    names = [_dotted_name(node.func).lower() for node in ast.walk(analysis.tree) if isinstance(node, ast.Call)]
    source_lower = analysis.source.lower()

    has_embedding = any(
        marker in source_lower or any(marker in name for name in names)
        for marker in _EMBEDDING_MARKERS
    )
    has_retrieval = any(
        any(marker in name for name in names)
        for marker in _RETRIEVAL_CALL_MARKERS
    )
    has_generation = any(True for _ in _iter_ai_generation_calls(analysis))

    if not (has_embedding and has_retrieval and has_generation):
        return []

    has_validation = any(marker in source_lower for marker in _SOURCE_VALIDATION_MARKERS)
    if has_validation:
        return []

    retrieval_line = 0
    for node in ast.walk(analysis.tree):
        if isinstance(node, ast.Call):
            call_name = _dotted_name(node.func).lower()
            if any(marker in call_name for marker in _RETRIEVAL_CALL_MARKERS):
                retrieval_line = getattr(node, "lineno", 0)
                break

    return [
        {
            "type": "rag_without_source_validation",
            "path": analysis.path,
            "line": retrieval_line,
            "message": (
                f"RAG pipeline in {analysis.path!r} combines embeddings, retrieval, "
                "and generation without explicit source/context validation."
            ),
        }
    ]


# =====================================================================
# FINDINGS BUILDER
# =====================================================================


def _build_findings(
    import_violations: list[dict[str, Any]],
    secret_violations: list[dict[str, Any]],
    prompt_violations: list[dict[str, Any]],
    error_handling_violations: list[dict[str, Any]],
    eval_violations: list[dict[str, Any]],
    generation_config_violations: list[dict[str, Any]],
    model_violations: list[dict[str, Any]],
    safety_violations: list[dict[str, Any]],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    for violation in import_violations:
        findings.append(
            _finding(
                violation,
                code="AI-IMPORT-001",
                severity=FindingSeverity.INFO,
                rule="ai_library_import",
                detail_keys=("line", "library", "imported_module"),
            )
        )

    for violation in secret_violations:
        findings.append(
            _finding(
                violation,
                code="AI-SECRET-001",
                severity=FindingSeverity.CRITICAL,
                rule="hardcoded_ai_secret",
                detail_keys=(
                    "line",
                    "secret_type",
                    "matched_pattern",
                    "redacted",
                ),
            )
        )

    for violation in prompt_violations:
        findings.append(
            _finding(
                violation,
                code="AI-PROMPT-001",
                severity=FindingSeverity.WARNING,
                rule="hardcoded_prompt",
                detail_keys=(
                    "line",
                    "char_count",
                    "string_kind",
                    "triple_quoted",
                ),
            )
        )

    for violation in error_handling_violations:
        findings.append(
            _finding(
                violation,
                code="AI-ERROR-001",
                severity=FindingSeverity.ERROR,
                rule="unprotected_ai_api_call",
                detail_keys=(
                    "line",
                    "call",
                    "missing_exception_handling",
                    "missing_retry_logic",
                ),
            )
        )

    for violation in eval_violations:
        findings.append(
            _finding(
                violation,
                code="AI-EVAL-001",
                severity=FindingSeverity.CRITICAL,
                rule="llm_output_code_evaluation",
                detail_keys=("line", "evaluator", "tainted_names"),
            )
        )

    for violation in generation_config_violations:
        findings.append(
            _finding(
                violation,
                code="AI-TEMP-001",
                severity=FindingSeverity.WARNING,
                rule="unsafe_generation_configuration",
                detail_keys=(
                    "line",
                    "call",
                    "temperature",
                    "max_tokens",
                    "max_reasonable_tokens",
                    "reasons",
                ),
            )
        )

    for violation in model_violations:
        findings.append(
            _finding(
                violation,
                code="AI-MODEL-001",
                severity=FindingSeverity.WARNING,
                rule="deprecated_model",
                detail_keys=("line", "model", "context"),
            )
        )

    for violation in safety_violations:
        findings.append(
            _finding(
                violation,
                code="AI-SAFETY-001",
                severity=FindingSeverity.WARNING,
                rule=violation["type"],
                detail_keys=("line", "function", "ai_call_count"),
            )
        )

    return findings


def _finding(
    violation: dict[str, Any],
    code: str,
    severity: FindingSeverity,
    rule: str,
    detail_keys: tuple[str, ...],
) -> AuditFinding:
    details = {key: violation[key] for key in detail_keys if key in violation}
    details["rule"] = rule
    return AuditFinding(
        code=code,
        severity=severity,
        path=violation["path"],
        message=violation["message"],
        details=details,
    )


# =====================================================================
# AST HELPERS
# =====================================================================


def _iter_ai_generation_calls(
    analysis: _ModuleAnalysis,
) -> Iterator[ast.Call]:
    for node in ast.walk(analysis.tree):
        if isinstance(node, ast.Call) and _is_ai_generation_call(node, analysis):
            yield node


def _is_ai_generation_call(call: ast.Call, analysis: _ModuleAnalysis) -> bool:
    call_name = _dotted_name(call.func)
    if not call_name:
        return False

    lowered = call_name.lower()
    if any(marker in lowered for marker in _RETRIEVAL_CALL_MARKERS):
        return False
    if any(marker in lowered for marker in ("embedding", "embed_query", "embed_documents")):
        return False

    root = call_name.split(".")[0]
    suffix_match = any(
        call_name == suffix or call_name.endswith(f".{suffix}")
        for suffix in _GENERATION_CALL_SUFFIXES
    )
    if not suffix_match:
        return False

    return (
        root in analysis.ai_aliases
        or root in analysis.ai_objects
        or any(
            library in lowered
            for library in (
                "openai",
                "anthropic",
                "cohere",
                "mistral",
                "ollama",
                "generativeai",
                "vertexai",
                "langchain",
                "llama_index",
            )
        )
    )


def _is_ai_configuration_call(
    call: ast.Call,
    analysis: _ModuleAnalysis,
) -> bool:
    relevant_keywords = {
        "temperature",
        "max_tokens",
        "max_output_tokens",
        "max_new_tokens",
    }
    if not any(keyword.arg in relevant_keywords for keyword in call.keywords):
        return False

    call_name = _dotted_name(call.func)
    if not call_name:
        return False
    root = call_name.split(".")[0]
    lowered = call_name.lower()
    return (
        root in analysis.ai_aliases
        or root in analysis.ai_objects
        or any(
            marker in lowered
            for marker in (
                "openai",
                "anthropic",
                "cohere",
                "mistral",
                "ollama",
                "generativeai",
                "vertexai",
                "langchain",
                "llama_index",
            )
        )
    )


def _has_try_ancestor(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.Try) and _node_is_in_statements(node, current.body, parents):
            return bool(current.handlers)
        current = parents.get(current)
    return False


def _has_retry_safeguard(
    call: ast.Call,
    analysis: _ModuleAnalysis,
) -> bool:
    if _keyword_positive(call, "max_retries"):
        return True

    root = _dotted_name(call.func).split(".")[0]
    if root in analysis.retry_configured_objects:
        return True

    function = _nearest_ancestor(
        call,
        analysis.parents,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    )
    if function is not None:
        for decorator in function.decorator_list:
            name = _dotted_name(decorator.func if isinstance(decorator, ast.Call) else decorator)
            if any(
                name == marker or name.endswith(f".{marker}")
                for marker in _RETRY_DECORATOR_MARKERS
            ):
                return True

    current = call
    while current in analysis.parents:
        current = analysis.parents[current]
        if isinstance(current, ast.Call):
            wrapper = _dotted_name(current.func).lower()
            if "retry" in wrapper or "backoff" in wrapper:
                return True

    return False


def _collect_llm_output_names(analysis: _ModuleAnalysis) -> set[str]:
    tainted: set[str] = set()
    assignments = [
        node
        for node in ast.walk(analysis.tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    ]

    changed = True
    while changed:
        changed = False
        for node in assignments:
            value = _assignment_value(node)
            targets = _assignment_target_names(node)
            if value is None or not targets:
                continue

            contains_ai_call = any(
                _is_ai_generation_call(candidate, analysis)
                for candidate in ast.walk(value)
                if isinstance(candidate, ast.Call)
            )
            references_tainted = bool(_referenced_names(value) & tainted)
            if contains_ai_call or references_tainted:
                before = len(tainted)
                tainted.update(targets)
                if len(tainted) != before:
                    changed = True

    return tainted


def _loop_has_clear_safeguard(loop: ast.While) -> bool:
    if not _is_true_literal(loop.test):
        if isinstance(loop.test, (ast.Compare, ast.BoolOp)):
            return True
        names = {name.lower() for name in _referenced_names(loop.test)}
        if any(
            marker in name
            for name in names
            for marker in ("max", "limit", "stop", "done", "finished", "iterations")
        ):
            return True

    for node in ast.walk(loop):
        if isinstance(node, ast.Break):
            return True
        if isinstance(node, ast.Call):
            call_name = _dotted_name(node.func).lower()
            if any(
                call_name == marker or call_name.endswith(f".{marker}")
                for marker in _HUMAN_SAFEGUARD_MARKERS
            ):
                return True
    return False


def _looks_like_prompt(
    node: ast.AST,
    text: str,
    analysis: _ModuleAnalysis,
) -> bool:
    if _PROMPT_TEXT_PATTERN.search(text):
        return True

    parent = analysis.parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.keyword) and parent.arg:
            lowered = parent.arg.lower()
            if any(marker in lowered for marker in _PROMPT_NAME_MARKERS):
                return True
        if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            names = _assignment_target_names(parent)
            if any(
                marker in name.lower()
                for name in names
                for marker in _PROMPT_NAME_MARKERS
            ):
                return True
        if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        parent = analysis.parents.get(parent)
    return False


def _is_external_file_reference(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    if isinstance(parent, ast.Call):
        name = _dotted_name(parent.func).lower()
        if name.endswith(("read_text", "open", "load", "loads")):
            return True
    return False


def _docstring_nodes(tree: ast.AST) -> set[ast.Constant]:
    nodes: set[ast.Constant] = set()
    for container in ast.walk(tree):
        if not isinstance(
            container,
            (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            continue
        if not container.body:
            continue
        first = container.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            nodes.add(first.value)
    return nodes


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _dotted_name(node.func)
    if isinstance(node, ast.Subscript):
        return _dotted_name(node.value)
    return ""


def _assignment_value(
    node: ast.Assign | ast.AnnAssign | ast.NamedExpr,
) -> ast.expr | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return node.value


def _assignment_target_names(
    node: ast.Assign | ast.AnnAssign | ast.NamedExpr,
) -> set[str]:
    if isinstance(node, ast.Assign):
        targets = node.targets
    else:
        targets = [node.target]

    names: set[str] = set()
    for target in targets:
        for child in ast.walk(target):
            if isinstance(child, ast.Name):
                names.add(child.id)
    return names


def _referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names


def _nearest_ancestor(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    types: tuple[type[ast.AST], ...],
) -> Any:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, types):
            return current
        current = parents.get(current)
    return None


def _node_is_in_statements(
    node: ast.AST,
    statements: list[ast.stmt],
    parents: dict[ast.AST, ast.AST],
) -> bool:
    statement_ids = {id(statement) for statement in statements}
    current: ast.AST | None = node
    while current is not None:
        if id(current) in statement_ids:
            return True
        current = parents.get(current)
    return False


def _find_keyword(
    call: ast.Call,
    names: tuple[str, ...],
) -> ast.keyword | None:
    for keyword in call.keywords:
        if keyword.arg in names:
            return keyword
    return None


def _numeric_keyword(
    call: ast.Call,
    names: tuple[str, ...],
) -> float | None:
    keyword = _find_keyword(call, names)
    if keyword is None:
        return None
    return _numeric_literal(keyword.value)


def _numeric_literal(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _numeric_literal(node.operand)
        if operand is None:
            return None
        return -operand if isinstance(node.op, ast.USub) else operand
    return None


def _keyword_positive(call: ast.Call, name: str) -> bool:
    keyword = _find_keyword(call, (name,))
    if keyword is None:
        return False
    value = _numeric_literal(keyword.value)
    return value is not None and value > 0


def _string_literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _joined_string_static_text(node: ast.JoinedStr) -> str:
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append("{value}")
    return "".join(parts)


def _is_none_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _is_true_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


# =====================================================================
# STRING / MATCH HELPERS
# =====================================================================


def _match_ai_library(
    module_name: str,
    ai_libraries: frozenset[str],
) -> str | None:
    matches = [
        library
        for library in ai_libraries
        if module_name == library or module_name.startswith(f"{library}.")
    ]
    return max(matches, key=len) if matches else None


def _name_matches_ai_library(
    dotted_name: str,
    ai_libraries: frozenset[str],
) -> bool:
    return _match_ai_library(dotted_name, ai_libraries) is not None


def _match_deprecated_model(
    model_value: str,
    normalized_models: dict[str, str],
) -> str | None:
    lowered = model_value.lower()
    for normalized, original in sorted(
        normalized_models.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if lowered == normalized or lowered.startswith(f"{normalized}-"):
            return original
    return None


def _is_triple_quoted(segment: str) -> bool:
    stripped = segment.lstrip()
    stripped = re.sub(r"(?i)^[rubf]+", "", stripped)
    return stripped.startswith("'''" ) or stripped.startswith('"""')


def _looks_like_placeholder_secret(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "your_api_key",
            "your-key",
            "replace_me",
            "changeme",
            "example",
            "dummy",
            "placeholder",
            "<api_key>",
            "${",
        )
    )


def _classify_secret(text: str) -> str:
    upper = text.upper()
    lower = text.lower()
    if "OPENAI" in upper or lower.startswith("sk-"):
        return "OpenAI API key"
    if "ANTHROPIC" in upper:
        return "Anthropic API key"
    if "COHERE" in upper:
        return "Cohere API key"
    if "MISTRAL" in upper:
        return "Mistral API key"
    if "HUGGINGFACE" in upper or upper.startswith("HF_") or lower.startswith("hf_"):
        return "Hugging Face token"
    if upper.startswith("AKIA"):
        return "AWS access key"
    if lower.startswith("ghp_"):
        return "GitHub token"
    if lower.startswith("glpat-"):
        return "GitLab token"
    return "AI service credential"


def _redact_secret(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    if len(compact) <= 8:
        return "***"
    return f"{compact[:4]}...{compact[-4:]}"


def _sort_violations(
    violations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        violations,
        key=lambda violation: (
            str(violation.get("path", "")),
            int(violation.get("line", 0) or 0),
            str(violation.get("type", "")),
            str(violation.get("message", "")),
        ),
    )


def _deduplicate_violations(
    violations: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for violation in _sort_violations(violations):
        identity = tuple(violation.get(key) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(violation)
    return result


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# PLUGIN WRAPPER
# =====================================================================


class AISystemsAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "AISystemsAuditorPlugin",
    "run",
]