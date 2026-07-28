"""plan_capture — the anti-leak tooth (§15.4): declared work that has no node would leak.

Pathology D1: a session declares work — a deferral, a red gate, a failed slot — and the declaration
dies with the session. The handoff names it once; the next handoff does not.

This tool HARVESTS declarations from real artifacts and compares them against the plan tree using
`capture_problems`, the normative function in `docs/spec/15-plan-and-memory.md`. Harvesting is I/O,
so it lives here; the comparison is law, so it lives in the spec (§12 rule 2).

Modes:
    (default)  GATE   — exit 1 if any declared work has no node
    --fix      CAPTURE — create the missing nodes (this is what makes capture MACHINERY, not memory)
    --report   observe only, never fail

Two-sided (anti-decorative): PLAN_CAPTURE_SABOTAGE=1 injects a phantom declaration that has no node;
the gate MUST go red. If it passes, it prints GATE DECORATIVO and fails.

Honest scope, stated because it bounds the claim: this harvests STRUCTURED declarations only —
`deferral: {trigger, since}` mappings, slot verdicts, and non-zero check exits in proofs. Work
declared in PROSE (a sentence inside a `tech:` string saying something is deferred) is counted and
reported, but cannot be tracked by identity: prose has no stable ref. That gap is the argument for
moving prose deferrals to the structured form, and the number is printed so the argument is measured
rather than asserted.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PHANTOM = "deferral:zz-phantom#zz"
PROSE = re.compile(r"=\s*declared-deferred", re.IGNORECASE)


def _yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None


def harvest(root: Path) -> tuple[list[dict], dict[str, int]]:
    """Collect every STRUCTURED declaration of outstanding work, each with a stable `ref`."""
    declared: list[dict] = []
    stats = {"spec_deferrals": 0, "station_deferrals": 0, "red_verdicts": 0,
             "verdict_defers": 0, "red_checks": 0, "prose_deferrals": 0}

    # (a) structured `deferral: {trigger, since}` inside a spec's station entries
    for fs in list(root.glob("factories/*/factory.spec.yml")) + \
              list(root.glob("factories/*/products/*/factory.spec.yml")) + \
              list(root.glob("specs/*.yml")):
        spec = _yaml(fs)
        if not isinstance(spec, dict):
            continue
        rel = fs.relative_to(root).as_posix()
        for st in ((spec.get("domain") or {}).get("station_sequence") or []):
            if isinstance(st, dict) and isinstance(st.get("deferral"), dict):
                declared.append({"ref": f"deferral:{rel}#{st.get('id')}",
                                 "cause": "deferral",
                                 "title": f"Deferral in {rel} station {st.get('id')}: "
                                          f"{st['deferral'].get('trigger', '(no trigger)')}"})
                stats["spec_deferrals"] += 1

    # (b) structured deferrals inside materialized station YAMLs
    for sy in root.glob("factories/*/stations/*.yml"):
        st = _yaml(sy)
        if isinstance(st, dict) and isinstance(st.get("deferral"), dict):
            rel = sy.relative_to(root).as_posix()
            declared.append({"ref": f"deferral:{rel}", "cause": "deferral",
                             "title": f"Deferral in {rel}: "
                                      f"{st['deferral'].get('trigger', '(no trigger)')}"})
            stats["station_deferrals"] += 1

    # (c) slot verdicts: a red slot, or an explicit `defers` list
    for vf in sorted(root.glob(".gen/*.verdict.json")):
        try:
            v = json.loads(vf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(v, dict):
            continue
        sid = v.get("slot_id") or vf.stem
        if v.get("status") == "red":
            declared.append({"ref": f"slot:{sid}", "cause": "escalation",
                             "title": f"Red slot {sid}: {str(v.get('summary'))[:120]}"})
            stats["red_verdicts"] += 1
        for i, d in enumerate(v.get("defers") or []):
            declared.append({"ref": f"slot:{sid}#{i}", "cause": "deferral",
                             "title": f"Deferred by slot {sid}: {str(d)[:120]}"})
            stats["verdict_defers"] += 1

    # (d) a check that exited non-zero inside a proof
    for pf in sorted(root.glob("factories/*/.proof/*.json")):
        if pf.name in {"active.json", "ledger.json"}:
            continue
        try:
            proof = json.loads(pf.read_text(encoding="utf-8"))
            checks = proof.get("checks") or []
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        for c in checks:
            try:
                if int(c.get("exit", 0)) != 0:
                    origin = pf.parent.parent.name
                    declared.append({"ref": f"gate_red:{origin}#{proof.get('station')}:{c.get('name')}",
                                     "cause": "gate_red",
                                     "title": f"Red check {c.get('name')} in {origin} "
                                              f"{proof.get('station')}"})
                    stats["red_checks"] += 1
            except (TypeError, ValueError):
                continue

    # (e) PROSE declarations — counted, never tracked (they have no stable identity)
    for fs in list(root.glob("factories/*/factory.spec.yml")) + \
              list(root.glob("factories/*/products/*/factory.spec.yml")):
        try:
            stats["prose_deferrals"] += len(PROSE.findall(fs.read_text(encoding="utf-8")))
        except OSError:
            continue

    return declared, stats


def main(argv: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    import plan as plan_tool

    ns = plan_tool.algebra()
    nodes = plan_tool.load()
    declared, stats = harvest(ROOT)
    sabotage = os.environ.get("PLAN_CAPTURE_SABOTAGE") == "1"
    if sabotage:
        declared = declared + [{"ref": PHANTOM, "cause": "deferral", "title": "phantom"}]

    problems = ns["capture_problems"](nodes, declared)
    missing = [d for d in declared if any(d["ref"] in p for p in problems)]

    if sabotage:
        if any(PHANTOM in p for p in problems):
            print("VERDICT    plan-capture (SABOTAGE) — PASS   (exit 0)")
            print("SUMMARY    the phantom declaration was detected as unnodeed, as it must be")
            return 0
        print("VERDICT    plan-capture (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a declaration with no node passed")
        return 1

    if "--fix" in argv and missing:
        parent = None
        if "--parent" in argv:
            parent = argv[argv.index("--parent") + 1]
        for d in missing:
            nid = plan_tool._new_id(nodes)
            nodes[nid] = {
                "parent": parent, "title": d["title"], "kind": "residual", "state": "open",
                "evidence": [], "opened_at": plan_tool._now(),
                "origin": {"session": plan_tool._session(), "cause": d["cause"], "ref": d["ref"]},
            }
        plan_tool.save(nodes)
        print(f"VERDICT    plan-capture --fix — PASS   (exit 0)")
        print(f"SUMMARY    captured {len(missing)} declaration(s) that would have leaked")
        print(f"COUNTS     {stats}")
        return 0

    print(f"COUNTS     harvested {len(declared)} structured declaration(s): {stats}")
    if stats["prose_deferrals"]:
        print(f"NOTE       {stats['prose_deferrals']} deferral(s) declared in PROSE — counted, "
              f"NOT trackable (no stable ref); move them to the structured form")
    if problems and "--report" not in argv:
        print(f"VERDICT    plan-capture — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} declared item(s) have no node — they would leak")
        for p in problems[:5]:
            print(f"FAILURES   {p}")
        print("NEXT       python3 tools/plan_capture.py --fix --parent <NODE-ID>")
        return 1
    print("VERDICT    plan-capture — PASS   (exit 0)")
    print(f"SUMMARY    every structured declaration has a node ({len(declared)} checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
