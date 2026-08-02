#!/usr/bin/env python3
"""attach_parity — the gate `spec/11 §5bis.2` names: the same station, run headless
(`v3.host.runner.run_station`) and run through the ONE attach choke point
(`v3.host.attach.AttachSession.invoke`), produces the SAME pin.

    python3 -m v3.verify.checks.attach_parity                       # the gate
    V3_ATTACH_SABOTAGE=1 python3 -m v3.verify.checks.attach_parity  # the red side; must ALSO exit 0

No model anywhere on this path (`.gen/CONTRACT-v3-attach.md`'s own design decision): `AttachSession`'s
`station` dispatch is deterministic Python, and everything below runs it in tmpdirs/staged copies —
nothing in the working tree's `.proof/` ever moves.

GREEN, two levels, both required:
  1. SYNTHETIC, EXHAUSTIVE — a tmpdir line of two stations (`s0`, all green, two checks; `s1`,
     file-order successor of `s0`, one check that fails and prints to both streams), staged TWICE
     (byte-identical). Each station runs HEADLESS on copy 1 and ATTACHED (`AttachSession.invoke`) on
     copy 2; `_compare_station` asserts the written proof record (`proof_sha`, `checks`, `passed`) and
     the run log are IDENTICAL, per station.
  2. REAL, ONCE — `factories/dummy` (the cheapest real line: pure checks, no toolchain) staged into two
     tmpdirs from git's tracked files (`v3.verify.rederive.stage`, reused rather than restated); its
     first station (`s00`) runs headless and attached, same comparison. If the vehicle cannot be
     staged, the gate is RED, not N/A — the vehicle existing is part of the claim.

Also asserted, because "same pin" is necessary and not sufficient: `invoke` on a `declare` tool
(`pin`) is refused and writes nothing to `.proof/`; `invoke` on an unknown tool name is refused;
`state()` is bounded (no string value carries a newline or exceeds a one-line byte bound).

RED, `V3_ATTACH_SABOTAGE=1` — five planted defects, one per row of the contract's own table. Each is
planted on a SYNTHETIC fixture or an in-memory copy — `v3.host.attach` itself is never mutated. Per
`v3.verify.registry.Gate.red_run`'s contract (the opposite of the obvious one): this run exits **0**
when it caught all five, printing what it caught; it prints `GATE DECORATIVO` + exit **1** the moment
one slips through.

  1. a hand-authored stand-in for "the attached path honours an extra `skip` argument and drops a
     check" is run against the synthetic fixture; its proof diverges from an honest headless run of
     the SAME station — `_compare_station` catches it.
  2. a stand-in that writes `.proof/<id>.json` directly (never calling `run_station`) forges
     `passed: true` over a station whose real check is red; diverges from the honest headless proof.
  3. a stand-in that hardcodes `dial="harden"` regardless of what the session was attached at, run
     against a two-station fixture where the first station is `tier: harden`: under the REAL session's
     requested `dial="draft"` the second station runs immediately (the harden predecessor is
     transparently skipped); the hardcoded stand-in blocks it instead — the outcomes diverge.
  4. `pin` (a real `declare` row) has its `tier` flipped to `"run"` on an IN-MEMORY copy and fed
     through the SAME `authority_decision` law the real `invoke` calls: the untampered row refuses,
     the tampered one does not — proving the tier check is what prevents reachability.
  5. a stand-in `Verdict` constructor that reports exit 0 regardless of `result["status"]` is compared
     against the real `verdict_from_result` law fed the identical FAIL-status result: the real law
     reports non-zero, the stand-in reports 0 — the divergence is what a regression to this defect
     would look like.

Register in `v3.verify.suite` as `attach_parity`, witness `sabotage_env` `V3_ATTACH_SABOTAGE`, no
`na_when` — it builds its own line, so it is never vacuous.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import yaml

from ...host import runlog
from ...host.attach import (AttachSession, AttachTarget, authority_decision, find_tool,
                            verdict_from_result)
from ...kernel.report import Verdict

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_ATTACH_SABOTAGE"

_GREEN_CHECKS = [
    {"name": "c1", "kind": "command", "cmd": ["python3", "-c", "pass"]},
    {"name": "c2", "kind": "command", "cmd": ["python3", "-c", "pass"]},
]
_RED_CHECKS = [
    {"name": "boom", "kind": "command",
     "cmd": ["python3", "-c",
            "import sys; sys.stdout.write('to stdout\\n'); sys.stderr.write('to stderr\\n'); "
            "sys.exit(1)"]},
]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# synthetic fixtures — written fresh into a tmpdir, never committed, never touching the working tree
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _write_station(stations_dir: Path, station_id: str, checks: list[dict], *, tier: str | None = None) -> None:
    node = {"id": station_id, "name": station_id, "activation": "always", "builds": [], "checks": checks}
    if tier:
        node["tier"] = tier
    (stations_dir / f"{station_id}.yml").write_text(yaml.safe_dump(node, sort_keys=False), encoding="utf-8")


def _write_factory_spec(fdir: Path, slug: str) -> None:
    spec = {"factory": {"name": slug, "slug": slug, "maturity": "test"},
           "domain": {"produces": "an attach_parity fixture"}}
    (fdir / "factory.spec.yml").write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


def _stage_two_station_line(root: Path, slug: str = "synth") -> None:
    """`s0` (2 green checks), `s1` (1 red check, both streams). No explicit `requires_prev`: `s1`
    gates on `s0` through the SAME file-order fallback any two-station line resolves to
    (`v3.kernel.sequence.predecessors`) — nothing about this fixture is special-cased."""
    fdir = root / "factories" / slug
    stations_dir = fdir / "stations"
    stations_dir.mkdir(parents=True, exist_ok=True)
    _write_factory_spec(fdir, slug)
    _write_station(stations_dir, "s0", _GREEN_CHECKS)
    _write_station(stations_dir, "s1", _RED_CHECKS)


def _stage_dial_line(root: Path, slug: str = "dialtest") -> None:
    """`h0` (tier harden, 1 green check), `h1` (file-order successor, 1 green check) — the minimal
    shape that makes a station's REQUESTED dial observable: under `draft`, `h0` is inactive and `h1`'s
    predecessor resolution transparently skips it; under `harden`, `h1` is blocked until `h0` runs."""
    fdir = root / "factories" / slug
    stations_dir = fdir / "stations"
    stations_dir.mkdir(parents=True, exist_ok=True)
    _write_factory_spec(fdir, slug)
    _write_station(stations_dir, "h0", _GREEN_CHECKS[:1], tier="harden")
    _write_station(stations_dir, "h1", _GREEN_CHECKS[:1])


def _load_line(root: Path, factory: str):
    from ...spec.loader import load_spec
    from ...host.line import load_stations, resolve_line

    fdir = root / "factories" / factory
    spec = load_spec(fdir / "factory.spec.yml")
    raw = load_stations(fdir)
    return fdir, spec, resolve_line(raw, spec.subst)


def _run_headless_station(root: Path, factory: str, station_id: str):
    """The oracle side: `v3.host.runner.run_station`, called DIRECTLY — no `AttachSession` anywhere
    on this path."""
    from ...host.builds import BuildContext, apply_builds
    from ...host.runner import RunContext, run_station

    fdir, spec, line = _load_line(root, factory)
    target = next((s for s in line if str(s.get("id")) == station_id), None)
    if target is None:
        raise ValueError(f"no such station {station_id!r} in the staged line")
    ctx = RunContext(root=fdir, home=root, proof_dir=fdir / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=fdir, meta_root=root, subst=spec.subst, chassis=fdir)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    return run_station(target, line, ctx)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# comparison — the LAW both the green run and the sabotage feed data through
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _proof_record(root: Path, factory: str, station_id: str) -> dict | None:
    path = root / "factories" / factory / ".proof" / f"{station_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _runlog_shape(root: Path, station_id: str) -> dict | None:
    """The run log's CONTENT (station + per-check name/exit/bytes/first_line), minus the wall-clock
    `ts` two independent runs would never agree on — comparing that would be a flaky assertion about
    the clock, not about whether the log is the same."""
    idx = runlog.index(root, station_id)
    if idx is None:
        return None
    return {"station": idx.get("station"), "checks": idx.get("checks")}


def _compare_station(label: str, factory: str, station_id: str, headless_root: Path,
                     attached_root: Path) -> list[str]:
    problems: list[str] = []
    h = _proof_record(headless_root, factory, station_id)
    a = _proof_record(attached_root, factory, station_id)
    if h is None and a is None:
        return problems   # neither wrote a proof — nothing to diverge on (both correctly abstained)
    if h is None or a is None:
        problems.append(f"{label}/{station_id}: proof present on one side only "
                        f"(headless={h is not None}, attached={a is not None})")
        return problems
    if h.get("proof_sha") != a.get("proof_sha"):
        problems.append(f"{label}/{station_id}: proof_sha differs "
                        f"(headless={h.get('proof_sha')}, attached={a.get('proof_sha')})")
    if h.get("checks") != a.get("checks"):
        problems.append(f"{label}/{station_id}: checks array differs")
    if bool(h.get("passed")) != bool(a.get("passed")):
        problems.append(f"{label}/{station_id}: `passed` differs "
                        f"(headless={h.get('passed')}, attached={a.get('passed')})")
    if _runlog_shape(headless_root, station_id) != _runlog_shape(attached_root, station_id):
        problems.append(f"{label}/{station_id}: run log content differs between headless and attached")
    return problems


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# GREEN
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _state_bounded_problems(state: dict) -> list[str]:
    problems: list[str] = []

    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]")
        elif isinstance(value, str):
            if "\n" in value:
                problems.append(f"state(){path}: contains a newline — a log body, not a bounded line")
            encoded = value.encode("utf-8")
            if len(encoded) > 400:
                problems.append(f"state(){path}: {len(encoded)} byte(s) — exceeds a one-line bound")

    walk(state, "")
    if not isinstance(state.get("stations"), list):
        problems.append("state()['stations'] is not a list")
    return problems


def _level1_synthetic(problems: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="v3-attach-parity-syn-") as t1, \
         tempfile.TemporaryDirectory(prefix="v3-attach-parity-syn-") as t2:
        headless_root, attached_root = Path(t1), Path(t2)
        _stage_two_station_line(headless_root)
        _stage_two_station_line(attached_root)

        session = AttachSession(attached_root, AttachTarget(factory="synth"))
        for station_id in ("s0", "s1"):
            _run_headless_station(headless_root, "synth", station_id)
            verdict = session.invoke("station", {"id": station_id})
            if station_id == "s0" and verdict.exit_code != 0:
                problems.append(f"synthetic/s0: attached invoke reported non-zero for the all-green "
                                f"station: {verdict.summary}")
            if station_id == "s1" and verdict.exit_code == 0:
                problems.append(f"synthetic/s1: attached invoke reported PASS for the deliberately "
                                f"red station: {verdict.summary}")
            problems.extend(_compare_station("synthetic", "synth", station_id, headless_root, attached_root))

        # invoke on a declare tool is REFUSED and writes nothing
        proof_dir = attached_root / "factories" / "synth" / ".proof"
        before = sorted(p.name for p in proof_dir.glob("*.json"))
        refusal = session.invoke("pin", {})
        after = sorted(p.name for p in proof_dir.glob("*.json"))
        if refusal.exit_code == 0:
            problems.append("invoke('pin', ...) (a declare tool) was not refused")
        if before != after:
            problems.append("invoke('pin', ...) wrote to `.proof/` despite being a declare tool")

        # invoke on an unknown tool is refused
        if session.invoke("not_a_real_tool_xyz", {}).exit_code == 0:
            problems.append("invoke() on an unknown tool name was not refused")

        # state() is bounded and contains no log body
        problems.extend(_state_bounded_problems(session.state()))


def _level2_real(problems: list[str]) -> None:
    from ..rederive import stage

    with tempfile.TemporaryDirectory(prefix="v3-attach-parity-real-") as t1, \
         tempfile.TemporaryDirectory(prefix="v3-attach-parity-real-") as t2:
        headless_root, attached_root = Path(t1), Path(t2)
        _, copied1 = stage(_ROOT, "dummy", headless_root)
        _, copied2 = stage(_ROOT, "dummy", attached_root)
        if copied1 == 0 or copied2 == 0:
            problems.append("could not stage factories/dummy (git tracks zero files there) — the "
                            "vehicle existing is part of the claim, so this is RED, not N/A")
            return
        station_id = "s00"
        _run_headless_station(headless_root, "dummy", station_id)
        session = AttachSession(attached_root, AttachTarget(factory="dummy"))
        verdict = session.invoke("station", {"id": station_id})
        if verdict.exit_code != 0:
            problems.append(f"real/dummy/{station_id}: attached invoke did not go green: "
                            f"{verdict.summary}")
        problems.extend(_compare_station("real/dummy", "dummy", station_id, headless_root, attached_root))


def _green() -> Verdict:
    problems: list[str] = []
    _level1_synthetic(problems)
    _level2_real(problems)
    if problems:
        return Verdict("attach-parity", 1, f"{len(problems)} problem(s)", failures=tuple(problems))
    return Verdict("attach-parity", 0,
                   "a synthetic 2-station line and a staged copy of factories/dummy both reproduce an "
                   "IDENTICAL proof_sha/checks/passed and run log headless vs attached; declare and "
                   "unknown tools are refused; state() stays bounded")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RED — one stand-in per row of the contract's table; `v3.host.attach` itself is never mutated
# ══════════════════════════════════════════════════════════════════════════════════════════════════
def _wrong_drops_check(root: Path, factory: str, station_id: str, *, skip_name: str) -> None:
    """Stand-in for defect #1: an attach path that honours an extra `skip` argument."""
    from ...host.builds import BuildContext, apply_builds
    from ...host.runner import RunContext, run_station

    fdir, spec, line = _load_line(root, factory)
    target = next(s for s in line if str(s.get("id")) == station_id)
    doctored = {**target, "checks": [c for c in target["checks"] if c["name"] != skip_name]}
    doctored_line = [doctored if s is target else s for s in line]
    ctx = RunContext(root=fdir, home=root, proof_dir=fdir / ".proof", pythonpath=str(_ROOT))
    build_ctx = BuildContext(root=fdir, meta_root=root, subst=spec.subst, chassis=fdir)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    run_station(doctored, doctored_line, ctx)


def _plant_skip_drops_check() -> bool:
    with tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab1-") as t1, \
         tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab1-") as t2:
        honest_root, buggy_root = Path(t1), Path(t2)
        _stage_two_station_line(honest_root)
        _stage_two_station_line(buggy_root)
        _run_headless_station(honest_root, "synth", "s0")
        _wrong_drops_check(buggy_root, "synth", "s0", skip_name="c2")
        return bool(_compare_station("sabotage-1", "synth", "s0", honest_root, buggy_root))


def _wrong_forges_proof(root: Path, factory: str, station_id: str) -> None:
    """Stand-in for defect #2: writes `.proof/<id>.json` directly, never calling `run_station`."""
    proof_dir = root / "factories" / factory / ".proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    forged = {"station": station_id, "checks": [], "passed": True,
             "proof_sha": "forged-outside-run_station"}
    (proof_dir / f"{station_id}.json").write_text(json.dumps(forged), encoding="utf-8")


def _plant_forged_proof() -> bool:
    with tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab2-") as t1, \
         tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab2-") as t2:
        honest_root, buggy_root = Path(t1), Path(t2)
        _stage_two_station_line(honest_root)
        _stage_two_station_line(buggy_root)
        _run_headless_station(honest_root, "synth", "s1")   # genuinely red
        _wrong_forges_proof(buggy_root, "synth", "s1")
        return bool(_compare_station("sabotage-2", "synth", "s1", honest_root, buggy_root))


def _wrong_hardcoded_harden(root: Path, factory: str, station_id: str):
    """Stand-in for defect #3: ignores whatever dial the session was attached at."""
    from ...host.builds import BuildContext, apply_builds
    from ...host.runner import RunContext, run_station

    fdir, spec, line = _load_line(root, factory)
    target = next(s for s in line if str(s.get("id")) == station_id)
    ctx = RunContext(root=fdir, home=root, proof_dir=fdir / ".proof", pythonpath=str(_ROOT),
                     dial="harden")   # HARDCODED — ignores the caller's actual request
    build_ctx = BuildContext(root=fdir, meta_root=root, subst=spec.subst, chassis=fdir)
    ctx.builder = lambda st, _ctx: apply_builds(st, build_ctx)
    return run_station(target, line, ctx)


def _plant_wrong_dial() -> bool:
    with tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab3-") as t1, \
         tempfile.TemporaryDirectory(prefix="v3-attach-parity-sab3-") as t2:
        correct_root, wrong_root = Path(t1), Path(t2)
        _stage_dial_line(correct_root)
        _stage_dial_line(wrong_root)
        session = AttachSession(correct_root, AttachTarget(factory="dialtest", dial="draft"))
        correct = session.invoke("station", {"id": "h1"})
        wrong = _wrong_hardcoded_harden(wrong_root, "dialtest", "h1")
        # under draft, h0 (tier harden) is inactive so h1 runs immediately (transparent skip); the
        # hardcoded-harden stand-in demands h0's never-run proof and blocks h1 instead — the
        # divergence between the two outcomes is what a real regression to this defect would produce.
        return correct.exit_code == 0 and not wrong.ran


def _plant_declare_reachable() -> bool:
    real_pin = find_tool("pin")
    tampered_pin = replace(real_pin, tier="run")
    real_refusal = authority_decision(real_pin)
    tampered_refusal = authority_decision(tampered_pin)
    return real_refusal is not None and tampered_refusal is None


def _wrong_verdict_always_zero(tool: str, result: dict) -> Verdict:
    return Verdict(f"attach {tool}", 0, str(result.get("summary", "")))


def _plant_lying_verdict() -> bool:
    red_result = {"status": "FAIL", "summary": "s1: RED", "counts": {}, "failures": ["boom"]}
    honest = verdict_from_result("station", red_result)
    wrong = _wrong_verdict_always_zero("station", red_result)
    return honest.exit_code != 0 and wrong.exit_code == 0


def _run_sabotage() -> int:
    plants = {
        "skip-argument-drops-check": _plant_skip_drops_check,
        "second-producer-forges-proof": _plant_forged_proof,
        "wrong-dial": _plant_wrong_dial,
        "declare-tool-reachable": _plant_declare_reachable,
        "lying-verdict": _plant_lying_verdict,
    }
    caught: list[str] = []
    missed: list[str] = []
    for name, fn in plants.items():
        try:
            ok = fn()
        except Exception as exc:  # noqa: BLE001 — a plant that crashes is a MISS, not a pass
            missed.append(f"{name} (raised {exc!r})")
            continue
        (caught if ok else missed).append(name)

    if missed:
        return Verdict("attach-parity (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)} caught · {len(missed)} MISSED "
                       f"{sorted(missed)}").emit()
    return Verdict("attach-parity (SABOTAGE)", 0,
                   f"{len(caught)}/5 planted defect(s) caught: {sorted(caught)}",
                   counts={"caught": len(caught)}).emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("attach-parity", 2, f"takes no arguments; got {argv!r}").emit()
    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()
    return _green().emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
