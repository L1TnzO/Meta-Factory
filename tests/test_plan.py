"""test_plan — the CONTRACT for the plan LAW (`metafactory.plan`, COST-DOWN INC-4).

Written and reviewed by the orchestrator with its own eyes: `plan_problems` becomes the `plan` tooth of
`meta check` (trust-chain — SELF-IMPROVEMENT §3), so it is not delegated. The tests pin BOTH sides of every
tooth (a well-formed plan passes; each specific defect is caught) and the ordering/selection logic that the
S2 executor drives (`toposort`/`next_slot`/`status_summary`).

The per-WorkOrder contract is validated by REUSING the slot law (`delegation.manifest_problems`) — so a slot
with no gate is rejected here without this module re-implementing the slot vocab.
"""
from __future__ import annotations

import json

from metafactory import plan


def _wo(sid: str, **over) -> dict:
    """A minimal VALID WorkOrder: a well-formed slot manifest (both gates) + execution metadata."""
    base = {
        "slot_id": sid,
        "single_responsibility": f"do {sid}",
        "allow_globs": [f"src/pkg/{sid}.py"],
        "iteration_gate_cmd": ["python3", "-c", "pass"],
        "acceptance_gate_cmd": ["python3", "-m", "pytest", "-q"],
        "verdict_path": f".gen/{sid}.verdict.json",
        "commit": f"feat({sid}): do it",
    }
    base.update(over)
    return base


def _plan(*wos: dict, **over) -> dict:
    p = {"increment": "DEMO", "work_orders": list(wos)}
    p.update(over)
    return p


# ── well-formed plan ──────────────────────────────────────────────────────────
def test_valid_plan_has_no_problems():
    p = _plan(_wo("a"), _wo("b", deps=["a"]), _wo("c", deps=["a", "b"]))
    assert plan.plan_problems(p) == []


def test_empty_work_orders_is_a_problem():
    assert plan.plan_problems(_plan()) == ["`work_orders` must be a non-empty list"]
    assert plan.plan_problems({}) == ["`work_orders` must be a non-empty list"]


# ── the split-gate tooth is inherited from the slot law ────────────────────────
def test_work_order_without_a_gate_is_rejected():
    bad = _wo("a")
    del bad["acceptance_gate_cmd"]  # a slot with no acceptance gate — the 79-min-slot class
    probs = plan.plan_problems(_plan(bad))
    assert any("acceptance_gate_cmd" in x and x.startswith("a:") for x in probs)


def test_work_order_missing_iteration_gate_is_rejected():
    bad = _wo("a")
    del bad["iteration_gate_cmd"]
    probs = plan.plan_problems(_plan(bad))
    assert any("iteration_gate_cmd" in x for x in probs)


def test_bad_pwf_vocab_in_work_order_is_rejected():
    probs = plan.plan_problems(_plan(_wo("a", cost_class="luxury")))  # not in COST_CLASSES
    assert any("cost_class" in x for x in probs)


# ── plan-shape teeth ───────────────────────────────────────────────────────────
def test_duplicate_slot_ids():
    probs = plan.plan_problems(_plan(_wo("a"), _wo("a")))
    assert any("duplicate slot_id" in x for x in probs)


def test_dangling_dependency():
    probs = plan.plan_problems(_plan(_wo("a", deps=["ghost"])))
    assert any("unknown slot_id 'ghost'" in x for x in probs)


def test_self_dependency():
    probs = plan.plan_problems(_plan(_wo("a", deps=["a"])))
    assert any("depends on itself" in x for x in probs)


def test_cycle_is_rejected():
    p = _plan(_wo("a", deps=["b"]), _wo("b", deps=["a"]))
    probs = plan.plan_problems(p)
    assert any("cycle" in x for x in probs)
    assert plan.toposort(p) is None


def test_bad_status():
    probs = plan.plan_problems(_plan(_wo("a", status="halfway")))
    assert any("`status` invalid" in x for x in probs)


def test_deferred_needs_reason():
    probs = plan.plan_problems(_plan(_wo("a", status="deferred")))
    assert any("defer_reason" in x for x in probs)
    # with a reason it is honest → no defer problem
    ok = plan.plan_problems(_plan(_wo("a", status="deferred", defer_reason="blocked on INC-5")))
    assert not any("defer_reason" in x for x in ok)


def test_empty_commit_is_rejected():
    probs = plan.plan_problems(_plan(_wo("a", commit="   ")))
    assert any("`commit`" in x for x in probs)


def test_bad_deps_type():
    probs = plan.plan_problems(_plan(_wo("a", deps="b")))  # must be a list
    assert any("`deps` must be a list" in x for x in probs)


# ── ordering ───────────────────────────────────────────────────────────────────
def test_toposort_deps_precede_dependents():
    p = _plan(_wo("c", deps=["a", "b"]), _wo("b", deps=["a"]), _wo("a"))
    order = plan.toposort(p)
    assert order is not None
    assert order.index("a") < order.index("b") < order.index("c")


def test_toposort_stable_declaration_order_on_ties():
    p = _plan(_wo("a"), _wo("b"), _wo("c"))  # no deps → declaration order
    assert plan.toposort(p) == ["a", "b", "c"]


# ── next_slot ──────────────────────────────────────────────────────────────────
def test_next_slot_picks_first_ready():
    p = _plan(_wo("a"), _wo("b", deps=["a"]))
    assert plan.next_slot(p)["slot_id"] == "a"


def test_next_slot_respects_deps():
    # a not done → b is blocked; next must be a
    p = _plan(_wo("a"), _wo("b", deps=["a"]))
    assert plan.next_slot(p)["slot_id"] == "a"
    # a done → next is b
    p2 = _plan(_wo("a", status="done"), _wo("b", deps=["a"]))
    assert plan.next_slot(p2)["slot_id"] == "b"


def test_next_slot_skips_done_and_deferred():
    p = _plan(_wo("a", status="done"), _wo("b", status="deferred", defer_reason="later"), _wo("c"))
    assert plan.next_slot(p)["slot_id"] == "c"


def test_next_slot_none_when_complete():
    p = _plan(_wo("a", status="done"), _wo("b", status="done"))
    assert plan.next_slot(p) is None


def test_next_slot_none_when_frontier_blocked_by_deferred_dep():
    # a deferred dep is NOT done → b can never become ready (surfaced as blocked, not picked)
    p = _plan(_wo("a", status="deferred", defer_reason="skip"), _wo("b", deps=["a"]))
    assert plan.next_slot(p) is None


# ── status_summary ─────────────────────────────────────────────────────────────
def test_status_summary_counts_and_blocked():
    p = _plan(_wo("a", status="done"), _wo("b", deps=["c"]), _wo("c"),
              _wo("d", status="deferred", defer_reason="later"))
    s = plan.status_summary(p)
    assert s["total"] == 4
    assert s["done"] == ["a"]
    assert s["deferred"] == ["d"]
    assert set(s["pending"]) == {"b", "c"}
    assert s["blocked"] == ["b"]      # b depends on c which isn't done
    assert s["next"] == "c"
    assert s["complete"] is False


def test_status_summary_complete():
    s = plan.status_summary(_plan(_wo("a", status="done")))
    assert s["complete"] is True and s["next"] is None


# ── load/write round-trip ──────────────────────────────────────────────────────
def test_write_and_load_roundtrip(tmp_path):
    p = _plan(_wo("a"))
    plan.write_plan(tmp_path, p)
    assert plan.load_plan(tmp_path) == p


def test_load_plan_none_when_absent(tmp_path):
    assert plan.load_plan(tmp_path) is None


def test_load_plan_none_when_malformed(tmp_path):
    plan.plan_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    plan.plan_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert plan.load_plan(tmp_path) is None


# ── escalations ────────────────────────────────────────────────────────────────
def test_escalation_shape():
    ok = {"slot_id": "a", "failure": "acceptance red x2", "attempts": 2, "hypothesis": "missing import"}
    assert plan.escalation_problems(ok) == []
    assert plan.escalation_problems({"slot_id": "a"})  # missing keys
    assert any("attempts" in x for x in plan.escalation_problems({**ok, "attempts": -1}))


def test_load_escalations(tmp_path):
    d = plan.escalations_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "a.json").write_text(json.dumps({"slot_id": "a", "failure": "x", "attempts": 2, "hypothesis": "y"}),
                              encoding="utf-8")
    (d / "bad.json").write_text("{broken", encoding="utf-8")
    got = dict(plan.load_escalations(tmp_path))
    assert got["a.json"]["slot_id"] == "a"
    assert "_error" in got["bad.json"]


def test_load_escalations_empty_when_no_dir(tmp_path):
    assert plan.load_escalations(tmp_path) == []
