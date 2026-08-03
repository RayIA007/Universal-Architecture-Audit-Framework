"""
Test Suite K: AI Systems Auditor — deterministic unit tests.
"""

from __future__ import annotations

import ast
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
_PLUGINS_DIR = _PROJECT_ROOT / "plugins"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

from uaaf_core.audit.audit_result import (
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from plugins.ai_systems.ai_systems_auditor import (
    AUDIT_TYPE,
    PLUGIN_ID,
    PLUGIN_VERSION,
    AISystemsAuditorPlugin,
    _DEFAULT_AI_LIBRARIES,
    _DEFAULT_DEPRECATED_MODELS,
    _DEFAULT_SECRET_PATTERNS,
    _build_findings,
    _build_module_analysis,
    _compile_patterns,
    _detect_ai_imports,
    _detect_autonomous_agents,
    _detect_deprecated_models,
    _detect_hardcoded_prompts,
    _detect_hardcoded_secrets,
    _detect_llm_eval_usage,
    _detect_unprotected_ai_calls,
    _detect_unvalidated_rag,
    _detect_unsafe_generation_config,
    _discover_python_files,
    _redact_secret,
    _validate_context,
    _validate_ignored_directories,
    _validate_positive_int,
    _validate_string_list,
    _validate_string_set,
    run,
)


@pytest.fixture
def temp_project() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def plugin() -> AISystemsAuditorPlugin:
    return AISystemsAuditorPlugin()


def _write_file(project_path: Path, relative_path: str, content: str) -> None:
    file_path = project_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def _analysis(source: str, path: str = "sample.py"):
    tree = ast.parse(source)
    return _build_module_analysis(
        relative_path=path,
        source=source,
        tree=tree,
        ai_libraries=_DEFAULT_AI_LIBRARIES,
    )


def _codes(result: dict) -> set[str]:
    return {finding["code"] for finding in result["findings"]}


# =====================================================================
# Context validation (1-10)
# =====================================================================


class TestContextValidation:
    def test_context_must_be_dict(self):
        with pytest.raises(TypeError, match="dictionary"):
            _validate_context("bad")

    def test_context_requires_project_path(self):
        with pytest.raises(ValueError, match="project_path"):
            _validate_context({})

    def test_context_rejects_missing_directory(self):
        with pytest.raises(ValueError, match="existing directory"):
            _validate_context({"project_path": "/path/that/does/not/exist"})

    def test_context_rejects_unknown_fields(self, temp_project):
        with pytest.raises(ValueError, match="unknown fields"):
            _validate_context({"project_path": temp_project, "unknown": True})

    def test_context_rejects_wrong_audit_type(self, temp_project):
        with pytest.raises(ValueError, match="audit_type"):
            _validate_context(
                {"project_path": temp_project, "audit_type": "architecture"}
            )

    def test_ignored_directories_rejects_paths(self):
        with pytest.raises(ValueError, match="directory names"):
            _validate_ignored_directories(["nested/path"])

    def test_string_set_rejects_empty_entry(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_string_set(["openai", ""], "ai_libraries")

    def test_string_list_rejects_non_list(self):
        with pytest.raises(ValueError, match="list of strings"):
            _validate_string_list({"pattern"}, "secret_patterns")

    def test_positive_int_rejects_bool(self):
        with pytest.raises(ValueError, match="positive integer"):
            _validate_positive_int(True, "prompt_min_chars")

    def test_invalid_secret_regex_rejected(self, temp_project):
        with pytest.raises(ValueError, match="Invalid secret pattern"):
            _validate_context(
                {
                    "project_path": temp_project,
                    "secret_patterns": ["("],
                }
            )


# =====================================================================
# Discovery (11-15)
# =====================================================================


class TestDiscovery:
    def test_discovers_python_files(self, temp_project):
        _write_file(temp_project, "a.py", "x = 1\n")
        assert _discover_python_files(temp_project, frozenset()) == ["a.py"]

    def test_ignores_non_python_files(self, temp_project):
        _write_file(temp_project, "a.txt", "text")
        assert _discover_python_files(temp_project, frozenset()) == []

    def test_uses_posix_relative_paths(self, temp_project):
        _write_file(temp_project, "pkg/module.py", "x = 1\n")
        assert _discover_python_files(temp_project, frozenset()) == [
            "pkg/module.py"
        ]

    def test_ignores_configured_directories(self, temp_project):
        _write_file(temp_project, "vendor/ai.py", "import openai\n")
        assert _discover_python_files(
            temp_project, frozenset({"vendor"})
        ) == []

    def test_discovery_is_sorted(self, temp_project):
        _write_file(temp_project, "z.py", "")
        _write_file(temp_project, "a.py", "")
        assert _discover_python_files(temp_project, frozenset()) == [
            "a.py",
            "z.py",
        ]


# =====================================================================
# AI import detection (16-22)
# =====================================================================


class TestAIImports:
    @pytest.mark.parametrize(
        "source,expected",
        [
            ("import openai\n", "openai"),
            ("import anthropic as ant\n", "anthropic"),
            ("from langchain_core.messages import HumanMessage\n", "langchain_core"),
            ("import google.generativeai as genai\n", "google.generativeai"),
            ("from llama_index.core import VectorStoreIndex\n", "llama_index"),
            ("import transformers\n", "transformers"),
            ("from google import generativeai\n", "google.generativeai"),
        ],
    )
    def test_detects_supported_imports(self, source, expected):
        violations = _detect_ai_imports(_analysis(source), _DEFAULT_AI_LIBRARIES)
        assert len(violations) == 1
        assert violations[0]["library"] == expected

    def test_does_not_flag_standard_library(self):
        violations = _detect_ai_imports(
            _analysis("import json\nfrom pathlib import Path\n"),
            _DEFAULT_AI_LIBRARIES,
        )
        assert violations == []


# =====================================================================
# Secret detection (23-31)
# =====================================================================


class TestSecrets:
    @pytest.mark.parametrize(
        "source,secret_type",
        [
            ('OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', "OpenAI"),
            ('ANTHROPIC_API_KEY = "anthropic-secret-value-123"\n', "Anthropic"),
            ('COHERE_API_KEY = "cohere-secret-value-123456"\n', "Cohere"),
            ('TOKEN = "hf_abcdefghijklmnopqrstuvwxyz123456"\n', "Hugging Face"),
            ('AWS_KEY = "AKIA1234567890ABCDEF"\n', "AWS"),
            ('GITHUB = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"\n', "GitHub"),
        ],
    )
    def test_detects_secret_patterns(self, source, secret_type):
        violations = _detect_hardcoded_secrets(
            source,
            "keys.py",
            _compile_patterns(_DEFAULT_SECRET_PATTERNS),
        )
        assert len(violations) == 1
        assert secret_type in violations[0]["secret_type"]
        assert "abcdefghijklmnopqrstuvwxyz" not in violations[0]["message"]

    def test_ignores_environment_lookup(self):
        source = 'OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")\n'
        violations = _detect_hardcoded_secrets(
            source,
            "safe.py",
            _compile_patterns(_DEFAULT_SECRET_PATTERNS),
        )
        assert violations == []

    def test_detects_secret_leaked_in_comment(self):
        source = '# OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n'
        violations = _detect_hardcoded_secrets(
            source,
            "leak.py",
            _compile_patterns(_DEFAULT_SECRET_PATTERNS),
        )
        assert len(violations) == 1

    def test_redaction_hides_middle(self):
        redacted = _redact_secret("sk-abcdefghijklmnopqrstuvwxyz123456")
        assert "..." in redacted
        assert "abcdefghijklmnopqrstuvwxyz" not in redacted


# =====================================================================
# Prompt detection (32-37)
# =====================================================================


class TestPrompts:
    def test_detects_long_prompt_assignment(self):
        prompt = "You are a senior auditor. " + "Analyze the project carefully. " * 10
        source = f"SYSTEM_PROMPT = {prompt!r}\n"
        violations = _detect_hardcoded_prompts(_analysis(source), 200)
        assert len(violations) == 1
        assert violations[0]["char_count"] > 200

    def test_detects_long_f_string_prompt(self):
        static = "You are an assistant. " + "Follow every instruction. " * 10
        source = f'name = "Ray"\nprompt = f"{static} {{name}}"\n'
        violations = _detect_hardcoded_prompts(_analysis(source), 200)
        assert len(violations) == 1
        assert violations[0]["string_kind"] == "f-string"

    def test_detects_triple_quoted_prompt(self):
        body = "Act as a secure coding reviewer. " + "Review all code paths. " * 10
        source = 'prompt = """' + body + '"""\n'
        violations = _detect_hardcoded_prompts(_analysis(source), 200)
        assert len(violations) == 1
        assert violations[0]["triple_quoted"] is True

    def test_ignores_short_prompt(self):
        source = 'prompt = "You are helpful."\n'
        assert _detect_hardcoded_prompts(_analysis(source), 200) == []

    def test_ignores_module_docstring(self):
        doc = "You are documentation only. " + "Explain this module. " * 20
        source = f'{doc!r}\nx = 1\n'
        assert _detect_hardcoded_prompts(_analysis(source), 200) == []

    def test_custom_threshold_is_honored(self):
        source = 'prompt = "You are helpful and must answer clearly."\n'
        assert len(_detect_hardcoded_prompts(_analysis(source), 20)) == 1


# =====================================================================
# Error handling and retry detection (38-43)
# =====================================================================


class TestErrorHandling:
    def test_flags_call_without_try_or_retry(self):
        source = """
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", max_tokens=100)
"""
        violations = _detect_unprotected_ai_calls(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["missing_exception_handling"] is True
        assert violations[0]["missing_retry_logic"] is True

    def test_try_only_still_flags_missing_retry(self):
        source = """
from openai import OpenAI
client = OpenAI()
try:
    response = client.responses.create(model="gpt-4o", max_tokens=100)
except Exception:
    response = None
"""
        violations = _detect_unprotected_ai_calls(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["missing_exception_handling"] is False
        assert violations[0]["missing_retry_logic"] is True

    def test_retry_only_still_flags_missing_try(self):
        source = """
from openai import OpenAI
client = OpenAI(max_retries=3)
response = client.responses.create(model="gpt-4o", max_tokens=100)
"""
        violations = _detect_unprotected_ai_calls(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["missing_exception_handling"] is True
        assert violations[0]["missing_retry_logic"] is False

    def test_try_and_client_retry_are_safe(self):
        source = """
from openai import OpenAI
client = OpenAI(max_retries=3)
try:
    response = client.responses.create(model="gpt-4o", max_tokens=100)
except Exception:
    response = None
"""
        assert _detect_unprotected_ai_calls(_analysis(source)) == []

    def test_retry_decorator_is_recognized(self):
        source = """
from openai import OpenAI
from tenacity import retry
client = OpenAI()
@retry()
def ask():
    try:
        return client.responses.create(model="gpt-4o", max_tokens=100)
    except Exception:
        return None
"""
        assert _detect_unprotected_ai_calls(_analysis(source)) == []

    def test_non_ai_create_call_is_ignored(self):
        source = "repository.create(name='x')\n"
        assert _detect_unprotected_ai_calls(_analysis(source)) == []


# =====================================================================
# eval/exec detection (44-48)
# =====================================================================


class TestEvalRisks:
    @pytest.mark.parametrize("evaluator", ["eval", "exec", "ast.literal_eval"])
    def test_detects_evaluator_with_llm_output(self, evaluator):
        source = f"""
import ast
from openai import OpenAI
client = OpenAI()
llm_output = client.responses.create(model="gpt-4o", max_tokens=100)
result = {evaluator}(llm_output)
"""
        violations = _detect_llm_eval_usage(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["evaluator"] == evaluator

    def test_detects_derived_llm_content(self):
        source = """
from openai import OpenAI
client = OpenAI()
response = client.responses.create(model="gpt-4o", max_tokens=100)
generated_code = response.output_text
exec(generated_code)
"""
        assert len(_detect_llm_eval_usage(_analysis(source))) == 1

    def test_ignores_eval_of_static_literal(self):
        assert _detect_llm_eval_usage(_analysis("value = eval('1 + 1')\n")) == []


# =====================================================================
# Generation configuration (49-54)
# =====================================================================


class TestGenerationConfiguration:
    def test_flags_temperature_above_threshold(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", temperature=0.95, max_tokens=100)
"""
        violations = _detect_unsafe_generation_config(_analysis(source), 32768)
        assert "temperature_above_0_9" in violations[0]["reasons"]

    def test_flags_missing_max_tokens(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", temperature=0.2)
"""
        violations = _detect_unsafe_generation_config(_analysis(source), 32768)
        assert "missing_max_tokens_limit" in violations[0]["reasons"]

    def test_flags_unbounded_none(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", max_tokens=None)
"""
        violations = _detect_unsafe_generation_config(_analysis(source), 32768)
        assert "unbounded_max_tokens" in violations[0]["reasons"]

    def test_flags_excessive_token_limit(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", max_tokens=50000)
"""
        violations = _detect_unsafe_generation_config(_analysis(source), 32768)
        assert "unreasonable_max_tokens" in violations[0]["reasons"]

    def test_safe_generation_config_passes(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", temperature=0.2, max_tokens=1000)
"""
        assert _detect_unsafe_generation_config(_analysis(source), 32768) == []


    def test_flags_high_temperature_on_model_constructor(self):
        source = """
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(temperature=1.1, max_tokens=100)
"""
        violations = _detect_unsafe_generation_config(_analysis(source), 32768)
        assert "temperature_above_0_9" in violations[0]["reasons"]

    def test_embedding_call_not_treated_as_generation(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.embeddings.create(model="text-embedding-3-small", input="hello")
"""
        assert _detect_unsafe_generation_config(_analysis(source), 32768) == []


# =====================================================================
# Deprecated models (55-58)
# =====================================================================


class TestDeprecatedModels:
    def test_detects_model_keyword(self):
        source = """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-3.5-turbo", max_tokens=100)
"""
        violations = _detect_deprecated_models(
            _analysis(source), _DEFAULT_DEPRECATED_MODELS
        )
        assert len(violations) == 1
        assert violations[0]["model"] == "gpt-3.5-turbo"

    def test_detects_model_assignment(self):
        source = 'MODEL_NAME = "text-davinci-003"\n'
        assert len(
            _detect_deprecated_models(
                _analysis(source), _DEFAULT_DEPRECATED_MODELS
            )
        ) == 1

    def test_ignores_recommended_model(self):
        source = 'MODEL_NAME = "gpt-4o"\n'
        assert _detect_deprecated_models(
            _analysis(source), _DEFAULT_DEPRECATED_MODELS
        ) == []


    def test_detects_model_in_configuration_dict(self):
        source = 'settings = {"model": "gpt-3.5-turbo"}\n'
        violations = _detect_deprecated_models(
            _analysis(source), _DEFAULT_DEPRECATED_MODELS
        )
        assert len(violations) == 1

    def test_custom_deprecated_model(self):
        source = 'model = "internal-old-model"\n'
        violations = _detect_deprecated_models(
            _analysis(source), frozenset({"internal-old-model"})
        )
        assert len(violations) == 1


# =====================================================================
# Agent and RAG safety (59-65)
# =====================================================================


class TestSafety:
    def test_flags_while_true_ai_loop(self):
        source = """
from openai import OpenAI
client = OpenAI()
def agent():
    while True:
        client.responses.create(model="gpt-4o", max_tokens=100)
"""
        violations = _detect_autonomous_agents(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["function"] == "agent"

    def test_loop_with_break_is_safe(self):
        source = """
from openai import OpenAI
client = OpenAI()
def agent():
    while True:
        client.responses.create(model="gpt-4o", max_tokens=100)
        break
"""
        assert _detect_autonomous_agents(_analysis(source)) == []

    def test_loop_with_human_approval_is_safe(self):
        source = """
from openai import OpenAI
client = OpenAI()
def agent():
    while True:
        input("Approve next step?")
        client.responses.create(model="gpt-4o", max_tokens=100)
"""
        assert _detect_autonomous_agents(_analysis(source)) == []

    def test_bounded_condition_is_safe(self):
        source = """
from openai import OpenAI
client = OpenAI()
def agent():
    iterations = 0
    while iterations < 3:
        client.responses.create(model="gpt-4o", max_tokens=100)
        iterations += 1
"""
        assert _detect_autonomous_agents(_analysis(source)) == []

    def test_flags_rag_without_validation(self):
        source = """
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
embeddings = OpenAIEmbeddings()
retriever = vectorstore.as_retriever()
docs = retriever.get_relevant_documents("question")
llm = ChatOpenAI()
answer = llm.invoke(docs)
"""
        violations = _detect_unvalidated_rag(_analysis(source))
        assert len(violations) == 1
        assert violations[0]["type"] == "rag_without_source_validation"

    def test_rag_with_validation_marker_is_safe(self):
        source = """
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
embeddings = OpenAIEmbeddings()
retriever = vectorstore.as_retriever()
docs = retriever.get_relevant_documents("question")
docs = validate_sources(docs)
llm = ChatOpenAI()
answer = llm.invoke(docs)
"""
        assert _detect_unvalidated_rag(_analysis(source)) == []

    def test_retrieval_only_is_not_rag_generation(self):
        source = """
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()
docs = vectorstore.similarity_search("question")
"""
        assert _detect_unvalidated_rag(_analysis(source)) == []


# =====================================================================
# Findings and end-to-end contract (66-76)
# =====================================================================


class TestEndToEnd:
    def test_empty_project_completes(self, temp_project):
        result = run({"project_path": temp_project})
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["python_file_count"] == 0
        validate_audit_result(result)

    def test_run_emits_all_requested_codes(self, temp_project):
        long_prompt = "You are a secure AI agent. " + "Follow instructions. " * 15
        source = f"""
import ast
from openai import OpenAI
OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"
SYSTEM_PROMPT = {long_prompt!r}
client = OpenAI()
MODEL_NAME = "gpt-3.5-turbo"
def agent():
    while True:
        response = client.responses.create(model=MODEL_NAME, temperature=1.0)
        generated_code = response.output_text
        exec(generated_code)
"""
        _write_file(temp_project, "app.py", source)
        result = run({"project_path": temp_project})
        expected = {
            "AI-IMPORT-001",
            "AI-SECRET-001",
            "AI-PROMPT-001",
            "AI-ERROR-001",
            "AI-EVAL-001",
            "AI-TEMP-001",
            "AI-MODEL-001",
            "AI-SAFETY-001",
        }
        assert expected <= _codes(result)
        validate_audit_result(result)

    def test_severities_are_canonical(self, temp_project):
        _write_file(
            temp_project,
            "app.py",
            'import openai\nOPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n',
        )
        result = run({"project_path": temp_project})
        severities = {finding["code"]: finding["severity"] for finding in result["findings"]}
        assert severities["AI-IMPORT-001"] == FindingSeverity.INFO.value
        assert severities["AI-SECRET-001"] == FindingSeverity.CRITICAL.value

    def test_summary_paths_are_deterministic(self, temp_project):
        _write_file(temp_project, "z.py", "")
        _write_file(temp_project, "pkg/a.py", "")
        result = run({"project_path": temp_project})
        assert result["summary"]["python_files"] == ["pkg/a.py", "z.py"]

    def test_syntax_error_sets_completed_with_errors(self, temp_project):
        _write_file(temp_project, "bad.py", "def broken(:\n")
        result = run({"project_path": temp_project})
        assert result["status"] == AuditStatus.COMPLETED_WITH_ERRORS.value
        assert result["metrics"]["parse_error_count"] == 1
        assert len(result["errors"]) == 1
        validate_audit_result(result)

    def test_plugin_wrapper_returns_canonical_result(self, plugin, temp_project):
        result = plugin.execute({"project_path": temp_project})
        assert result["plugin_id"] == PLUGIN_ID
        assert result["plugin_version"] == PLUGIN_VERSION
        assert result["audit_type"] == AUDIT_TYPE
        validate_audit_result(result)

    def test_custom_ai_library_is_supported(self, temp_project):
        _write_file(temp_project, "app.py", "import my_ai_sdk\n")
        result = run(
            {
                "project_path": temp_project,
                "ai_libraries": ["my_ai_sdk"],
            }
        )
        assert "AI-IMPORT-001" in _codes(result)

    def test_custom_prompt_threshold_is_supported(self, temp_project):
        _write_file(
            temp_project,
            "app.py",
            'prompt = "You are helpful and must answer clearly."\n',
        )
        result = run(
            {
                "project_path": temp_project,
                "prompt_min_chars": 20,
            }
        )
        assert "AI-PROMPT-001" in _codes(result)

    def test_custom_max_tokens_threshold_is_supported(self, temp_project):
        _write_file(
            temp_project,
            "app.py",
            """
from openai import OpenAI
client = OpenAI()
client.responses.create(model="gpt-4o", max_tokens=101)
""",
        )
        result = run(
            {
                "project_path": temp_project,
                "max_reasonable_tokens": 100,
            }
        )
        assert "AI-TEMP-001" in _codes(result)

    def test_findings_builder_uses_rag_safety_subtype(self):
        findings = _build_findings(
            import_violations=[],
            secret_violations=[],
            prompt_violations=[],
            error_handling_violations=[],
            eval_violations=[],
            generation_config_violations=[],
            model_violations=[],
            safety_violations=[
                {
                    "type": "rag_without_source_validation",
                    "path": "rag.py",
                    "line": 4,
                    "message": "RAG lacks validation.",
                }
            ],
        )
        assert len(findings) == 1
        assert findings[0].code == "AI-SAFETY-001"
        assert findings[0].details["rule"] == "rag_without_source_validation"

    def test_metrics_are_integers(self, temp_project):
        result = run({"project_path": temp_project})
        assert all(isinstance(value, int) for value in result["metrics"].values())