"""H2 deterministic gates (no network): golden loaders, protocol parity, metrics math.

The LIVE half of H2's exit gate — judge_agreement >= 0.8 over the real 760 pairs — is
`python3 -m reqcouncil eval e0` (exit code); its evidence is pinned under runs/pinned/e0/.
These tests pin everything AROUND the API call so a green live run is trustworthy.
"""

from __future__ import annotations

import pytest

from reqcouncil.attribution.judge import USER_TEMPLATE, build_messages, parse_verdict
from reqcouncil.config import load_models, load_thresholds
from reqcouncil.eval.golden import (
    EXPECTED_COUNTS,
    INTERVIEW,
    SYSTEM_DESC,
    load_pairs,
    system_prompt_path,
)
from reqcouncil.eval.metrics import Confusion, report_text

# ---------------------------------------------------------------- golden loaders


def test_golden_counts_match_measured_reality():
    """180 + 580 = 760 pairs — the corrected counts (docs/STATE), enforced by the loader."""
    for corpus, expected in EXPECTED_COUNTS.items():
        assert len(load_pairs(corpus)) == expected
    assert sum(EXPECTED_COUNTS.values()) == 760


def test_golden_interview_first_pair_spot_check():
    p = load_pairs(INTERVIEW)[0]
    assert p.story.startswith("As a fan, I want game events to be reported live")
    assert "fan portal" in p.chunk
    assert p.human == 1


def test_golden_system_desc_first_pair_spot_check():
    p = load_pairs(SYSTEM_DESC)[0]
    assert p.story.startswith("As a Travel Agent")
    assert p.chunk.startswith("Service Booking:")
    assert p.human == 1


def test_golden_labels_are_binary():
    for corpus in EXPECTED_COUNTS:
        assert {p.human for p in load_pairs(corpus)} <= {0, 1}


# ------------------------------------------------------- protocol parity (paper)


def test_user_message_is_byte_identical_to_paper_template():
    """Inter2US LLM_qwen_supervised_evaluate.py: f"User Story:\\n{story}\\n\\nChunk Text:\\n{chunk}\\n\\nAnswer:"."""
    story, chunk = "As a user, I want X.", 'Spk 0: something\nSpk 1: else'
    msgs = build_messages("SYS", story, chunk)
    assert msgs[0] == {"role": "system", "content": "SYS"}
    assert msgs[1]["content"] == f"User Story:\n{story}\n\nChunk Text:\n{chunk}\n\nAnswer:"
    assert USER_TEMPLATE.format(story=story, chunk=chunk) == msgs[1]["content"]


def test_system_prompts_exist_per_corpus_and_differ():
    interview = system_prompt_path(INTERVIEW).read_text(encoding="utf-8")
    sysdesc = system_prompt_path(SYSTEM_DESC).read_text(encoding="utf-8")
    assert "senior requirements analyst" in interview
    assert interview != sysdesc  # each corpus ships its own examples


@pytest.mark.parametrize(
    "content,expected",
    [
        ("1", 1),
        ("0", 0),
        ("  1 \n", 1),
        ("The answer is 1", 1),  # paper rule: endswith
        ("10", 1),  # paper quirk inherited: startswith("1")
        ("<think>maybe 0?</think>\n1", 1),  # thinking stripped BEFORE the rule
        ("<think>likely 1</think>0", 0),
        ("**1**", 0),  # paper rule is literal: neither starts nor ends with "1"
        ("", 0),
    ],
)
def test_parse_verdict_paper_rule(content, expected):
    assert parse_verdict(content) == expected


# ------------------------------------------------------------------ metrics math


def _labels_from_confusion(tn, fp, fn, tp):
    y_true = [0] * (tn + fp) + [1] * (fn + tp)
    y_pred = [0] * tn + [1] * fp + [0] * fn + [1] * tp
    return y_true, y_pred


def test_metrics_reproduce_published_interview_report():
    """Feed the paper's published Qwen3-32B interview confusion matrix [[92 14][18 56]]
    through OUR math; every headline number must equal Qwen3-32B_report.txt."""
    cm = Confusion.from_labels(*_labels_from_confusion(92, 14, 18, 56))
    assert (cm.tn, cm.fp, cm.fn, cm.tp) == (92, 14, 18, 56)
    assert round(cm.accuracy, 4) == 0.8222
    assert round(cm.precision(0), 3) == 0.836
    assert round(cm.recall(0), 3) == 0.868
    assert round(cm.f1(0), 3) == 0.852
    assert round(cm.precision(1), 3) == 0.800
    assert round(cm.recall(1), 3) == 0.757
    assert round(cm.f1(1), 3) == 0.778
    assert cm.support(0) == 106 and cm.support(1) == 74


def test_metrics_reproduce_published_system_desc_report():
    """Same for system-desc: [[268 10][40 262]] -> accuracy 0.9138 etc."""
    cm = Confusion.from_labels(*_labels_from_confusion(268, 10, 40, 262))
    assert round(cm.accuracy, 4) == 0.9138
    assert round(cm.precision(0), 3) == 0.870
    assert round(cm.recall(0), 3) == 0.964
    assert round(cm.precision(1), 3) == 0.963
    assert round(cm.recall(1), 3) == 0.868


def test_pooled_confusion_is_component_sum():
    a = Confusion(92, 14, 18, 56)
    b = Confusion(268, 10, 40, 262)
    pooled = a + b
    assert pooled.total == 760
    # pooled same-model paper reference: (92+56+268+262)/760
    assert round(pooled.accuracy, 4) == round(678 / 760, 4)


def test_report_text_contains_gateable_numbers():
    text = report_text(Confusion(92, 14, 18, 56))
    assert "Accuracy: 0.8222" in text
    assert "[[ 92  14]" in text


# ------------------------------------------------------------------- config wiring


def test_models_config_pins_siliconflow_dsv4flash():
    """decisions/004: foundation = V4-Flash @ SiliconFlow; qwen stays as the paper anchor."""
    cfg = load_models()
    fm = cfg["foundation_model"]
    assert fm["model"] == "deepseek-ai/DeepSeek-V4-Flash"
    assert fm["provider"] == "siliconflow"
    assert fm["api_key_env"] == "SILICONFLOW_API_KEY"
    assert fm["arm"] == "dsv4flash"  # bare `eval e0` must land on runs/e0-dsv4flash
    assert fm["extra_body"] == {"enable_thinking": False}  # the paper's exact knob
    qwen = cfg["alternates"]["qwen32b"]
    assert qwen["model"] == "qwen/qwen3-32b"
    assert qwen["provider"] == "groq"
    judge = cfg["judge"]
    assert judge["temperature"] == 0.0
    assert judge["max_completion_tokens"] == 256
    assert str(judge["reasoning_effort"]) in {"none", "None"}


def test_judge_agreement_gate_is_08():
    gates = load_thresholds()["gates"]
    assert gates["judge_agreement"]["min"] == 0.8


def test_gate_logic_two_sided():
    gate_min = load_thresholds()["gates"]["judge_agreement"]["min"]
    assert not (0.79 >= gate_min)  # red side: would block
    assert 0.80 >= gate_min  # green side: passes exactly at threshold
