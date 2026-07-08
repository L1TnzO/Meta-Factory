"""CHECK-WHEN-GUARD: the per-check `when:` guard makes a check opt-in WITHOUT perturbing the pin.

Proves the trust-chain invariant behind ADR-024's byte-neutral opt-in: a guarded check that does not match
the effective substitution is SKIPPED — it never enters the proof, so a non-adopter re-derives an IDENTICAL
`proof_sha` (the pin law, `seed/verifier.compute_proof_sha`, counts only the `(name, exit)` pairs of checks
that RAN). The guard is the per-CHECK analogue of `station_activation` (station level, in the loader)."""
from __future__ import annotations

from metafactory._seed import load_seed_verifier
from metafactory.engine.runner import _check_active

_V = load_seed_verifier()  # the REAL seed verifier (trust root): computes proof_sha exactly like the line

CHECK_A = {"name": "always_a", "kind": "command"}
CHECK_B = {"name": "design_floor", "kind": "infra_up", "when": {"frontend_surface": "model-native"}}


def _filter(checks: list[dict], subst: dict) -> list[dict]:
    """Mirror run_station's filter (runner.py:80) exactly — the same predicate the line uses."""
    return [c for c in checks if _check_active(c, subst)]


def _proof_sha(sid: str, ran: list[dict]) -> str:
    """proof_sha over the checks that RAN, all green — the pin's semantic digest."""
    return _V.compute_proof_sha(sid, [{"name": c["name"], "exit": 0} for c in ran])


# ── _check_active truth table ────────────────────────────────────────────────

def test_unguarded_check_always_runs():
    assert _check_active(CHECK_A, {}) is True
    assert _check_active(CHECK_A, {"frontend_surface": "model-native"}) is True


def test_guarded_check_runs_only_on_exact_match():
    assert _check_active(CHECK_B, {"frontend_surface": "model-native"}) is True
    assert _check_active(CHECK_B, {}) is False                          # flag absent
    assert _check_active(CHECK_B, {"frontend_surface": "template"}) is False  # flag present, wrong value


def test_multikey_when_needs_all_keys():
    c = {"name": "x", "when": {"a": "1", "b": "2"}}
    assert _check_active(c, {"a": "1", "b": "2"}) is True
    assert _check_active(c, {"a": "1"}) is False                        # one key missing => skip


# ── the pin invariant: skip ⇒ byte-identical proof_sha ───────────────────────

def test_nonadopter_pin_is_byte_identical():
    """A product without the flag re-derives an IDENTICAL proof_sha to a station that never had the
    guarded check — so adding an opt-in check to a shared station never re-pins the non-adopters (assets)."""
    ran = _filter([CHECK_A, CHECK_B], {})
    assert [c["name"] for c in ran] == ["always_a"]                     # guarded check filtered out
    assert _proof_sha("s9", ran) == _proof_sha("s9", [CHECK_A])         # pin untouched, not just absent


def test_adopter_includes_guarded_check_and_shifts_its_own_pin():
    """The opt-in product DOES run the guarded check — it is part of ITS verdict (a distinct pin, by design)."""
    ran = _filter([CHECK_A, CHECK_B], {"frontend_surface": "model-native"})
    assert [c["name"] for c in ran] == ["always_a", "design_floor"]
    assert _proof_sha("s9", ran) != _proof_sha("s9", [CHECK_A])
