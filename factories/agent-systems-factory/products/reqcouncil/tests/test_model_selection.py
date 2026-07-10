"""Judge-arm selection (no network): config/models.yml routing + CLI runs-dir isolation.

History (2026-07-05): Groq's rolling 500k TPD died mid-E0 → Cerebras arms (003) died of
5 req/min → SiliconFlow V4-Flash promoted to foundation (docs/decisions/004, cheapest per
token — the project's dominant constraint), qwen kept as the paper-parity alternate. These
tests pin the selection mechanics so a run can never silently judge with the wrong model
or clobber another arm's cache (per-arm runs dir; the cache key also carries model id).
"""

from __future__ import annotations

import pytest

from reqcouncil.cli import default_runs_dir
from reqcouncil.config import load_models
from reqcouncil.llm import ChatClient

# ------------------------------------------------------------- from_config routing


def _cfg_with_keys(monkeypatch) -> dict:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "test-siliconflow")
    return load_models()


def test_default_is_the_pinned_foundation_model(monkeypatch):
    client = ChatClient.from_config(_cfg_with_keys(monkeypatch))
    assert client.model == "deepseek-ai/DeepSeek-V4-Flash"
    assert client.api_base == "https://api.siliconflow.com/v1"
    # decisions/004: the paper's exact anti-thinking knob rides every request.
    assert client.extra_body == {"enable_thinking": False}


def test_alternate_qwen_is_the_paper_anchor(monkeypatch):
    client = ChatClient.from_config(_cfg_with_keys(monkeypatch), alternate="qwen32b")
    assert client.model == "qwen/qwen3-32b"
    assert client.api_base == "https://api.groq.com/openai/v1"
    assert client.extra_body == {}  # groq path unchanged: no provider extras


def test_unknown_alternate_fails_loudly_with_the_valid_names(monkeypatch):
    with pytest.raises(KeyError, match="qwen32b"):
        ChatClient.from_config(_cfg_with_keys(monkeypatch), alternate="nope")


# ------------------------------------------------------------- runs-dir isolation


def test_bare_run_lands_on_the_foundation_arm():
    """decisions/004: plain `eval e0` must land on runs/e0-dsv4flash, not legacy runs/e0."""
    arm = load_models()["foundation_model"]["arm"]
    assert default_runs_dir("runs/e0", arm) == "runs/e0-dsv4flash"


def test_each_alternate_gets_its_own_runs_dir():
    assert default_runs_dir("runs/e0", "qwen32b") == "runs/e0-qwen32b"


def test_armless_config_keeps_legacy_dir():
    assert default_runs_dir("runs/e0", None) == "runs/e0"


def test_explicit_runs_dir_always_wins():
    """The legacy qwen cache stays reachable: --model qwen32b --runs-dir runs/e0."""
    assert default_runs_dir("runs/e0-custom", "dsv4flash") == "runs/e0-custom"
