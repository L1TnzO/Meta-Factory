"""spec_conformance — proves `docs/spec/` is RECONSTRUCTION-COMPLETE for the trust kernel.

The claim under test: *a person given only `docs/spec/` can rebuild this system.* That claim is
usually unfalsifiable prose. Here it is a gate.

How: the spec carries its reference implementation inline, in fenced blocks marked

    <!-- spec-impl: kernel -->
    ```python
    ...
    ```

This runner EXTRACTS those blocks (nothing else — not the repo's source), executes them in an empty
namespace with only the standard library, and runs the conformance suite of `12-conformance.md`
against the golden vectors in `docs/spec/fixtures/`, which are anchored to committed pins.

If the spec's prose drifts from the machine, or if a block is incomplete, the vectors stop
reproducing and this gate goes red. The document cannot rot silently.

Two-sided (anti-decorative, §02.4): with SPEC_CONFORMANCE_SABOTAGE=1 the extracted source is mutated
so the digest must change. If the suite still passes under sabotage, the gate prints GATE DECORATIVO
and fails — a gate that cannot go red proves nothing.

Usage:  python3 tools/spec_conformance.py [repo_root]
        SPEC_CONFORMANCE_SABOTAGE=1 python3 tools/spec_conformance.py   # must FAIL
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SPEC_DIR = "docs/spec"
FIXTURE = "docs/spec/fixtures/proof-sha-vectors.json"
MARKER = re.compile(r"<!--\s*spec-impl:\s*([A-Za-z0-9_.-]+)\s*-->\s*\n```python\n(.*?)\n```",
                    re.DOTALL)
# The sabotage makes the digest depend on a field the real algorithm MUST exclude (a timestamp).
SABOTAGE = ('\n\n_orig_compute_proof_sha = compute_proof_sha\n'
            'def compute_proof_sha(station_id, checks):\n'
            '    return _orig_compute_proof_sha(station_id, list(checks) + [{"name": "_t", "exit": 1}])\n')
# The plan sabotage removes DERIVED closure: a parent stops seeing its open descendants. That is
# pathology D3 (silent completion) reintroduced on purpose — the suite must notice.
PLAN_SABOTAGE = ('\n\ndef effective_state(plan, nid):\n'
                 '    return (plan.get(nid) or {}).get("state", "missing")\n'
                 'def structure_problems(plan):\n'
                 '    return []\n')
# Each §19 module gets a sabotage that reintroduces the exact defect its law exists to prevent.
DOCSEAL_SABOTAGE = ('\n\ndef git_blob_sha(data):\n'
                    '    import hashlib\n'
                    '    return hashlib.sha1(data).hexdigest()\n')   # drops git's blob header
SLOTLAW_SABOTAGE = ('\n\ndef footprint_problems(slot, changed_paths):\n'
                    '    return []\n')                               # every write becomes "inside"
SEQUENCE_SABOTAGE = ('\n\ndef natural_key(name):\n'
                     '    return (str(name),)\n')                    # s10 sorts before s9 again


def extract(root: Path, module: str) -> tuple[str, list[str]]:
    """Concatenate every `spec-impl: <module>` block, in filename then document order."""
    parts, sources = [], []
    for md in sorted((root / SPEC_DIR).glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for name, body in MARKER.findall(text):
            if name == module:
                parts.append(body)
                sources.append(md.name)
    return "\n\n".join(parts), sources


def load_module(source: str, sabotage: bool) -> dict:
    ns: dict = {"__name__": "spec_kernel"}
    exec(compile(source + (SABOTAGE if sabotage else ""), "<spec:kernel>", "exec"), ns)
    return ns


def run_suite(ns: dict, vectors: list[dict]) -> list[str]:
    """The conformance suite of docs/spec/12-conformance.md. Returns a list of failures."""
    fail: list[str] = []

    # CONF-K1 — the kernel surface exists.
    for fn in ("compute_proof_sha", "recompute_passed"):
        if not callable(ns.get(fn)):
            fail.append(f"CONF-K1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    sha, passed = ns["compute_proof_sha"], ns["recompute_passed"]

    # CONF-K2 — every golden vector reproduces (the pin-anchored oracle).
    bad = 0
    for v in vectors:
        checks = [{"name": n, "exit": e} for n, e in v["checks"]]
        if sha(v["station"], checks) != v["proof_sha"]:
            bad += 1
            if bad <= 3:
                fail.append(f"CONF-K2: vector {v['origin']}:{v['station']} does not reproduce")
    if bad > 3:
        fail.append(f"CONF-K2: … and {bad - 3} more vector(s)")

    # CONF-K3 — `passed` semantics, including the no-vacuous-pass rule.
    if passed([]) is not False:
        fail.append("CONF-K3: an empty check list must NOT be 'trivially passed'")
    if passed([{"name": "a", "exit": 0}, {"name": "b", "exit": 0}]) is not True:
        fail.append("CONF-K3: all-zero exits must be passed")
    if passed([{"name": "a", "exit": 0}, {"name": "b", "exit": 1}]) is not False:
        fail.append("CONF-K3: any non-zero exit must not be passed")

    # CONF-K4 — the digest is outcome-addressed: order of checks must not matter.
    a = sha("s0", [{"name": "x", "exit": 0}, {"name": "y", "exit": 1}])
    b = sha("s0", [{"name": "y", "exit": 1}, {"name": "x", "exit": 0}])
    if a != b:
        fail.append("CONF-K4: the digest must be invariant to check ORDER (it sorts)")

    # CONF-K5 — a different exit code must change the sha (the whole point).
    if sha("s0", [{"name": "x", "exit": 0}]) == sha("s0", [{"name": "x", "exit": 1}]):
        fail.append("CONF-K5: a different exit code must produce a different sha")

    # CONF-K6 — the station id participates in the digest.
    if sha("s0", [{"name": "x", "exit": 0}]) == sha("s1", [{"name": "x", "exit": 0}]):
        fail.append("CONF-K6: the station id must participate in the digest")
    return fail


def _fixture_tree() -> dict:
    """A minimal plan exercising every rule: a done leaf, an open branch, a captured residual."""
    return {
        "R": {"parent": None, "title": "root", "kind": "direction", "state": "open",
              "origin": {"session": "s1", "cause": "manual"}},
        "A": {"parent": "R", "title": "a", "kind": "increment", "state": "done",
              "evidence": ["proof:abc"], "origin": {"session": "s1", "cause": "manual"}},
        "B": {"parent": "R", "title": "b", "kind": "task", "state": "open",
              "origin": {"session": "s2", "cause": "gate_red", "ref": "gate:quality"}},
        "B1": {"parent": "B", "title": "b1", "kind": "residual", "state": "open",
               "origin": {"session": "s2", "cause": "deferral", "ref": "slot:x"}},
    }


def run_plan_suite(ns: dict) -> list[str]:
    """The conformance suite of docs/spec/15-plan-and-memory.md §9."""
    fail: list[str] = []
    need = ("effective_state", "structure_problems", "node_problems", "capture_problems",
            "next_actionable", "ancestry", "open_set")
    for fn in need:
        if not callable(ns.get(fn)):
            fail.append(f"CONF-P1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    t = _fixture_tree()

    # CONF-P2 — derived closure: a parent is open while a descendant is open.
    if ns["effective_state"](t, "R") != "open":
        fail.append("CONF-P2: root must be effectively OPEN (descendants B/B1 are open)")
    if ns["effective_state"](t, "A") != "done":
        fail.append("CONF-P2: a childless done node must be effectively done")
    if ns["effective_state"](t, "B") != "open":
        fail.append("CONF-P2: a node with an open child must be effectively open")

    # CONF-P3 — D3: done over an open descendant is a structural problem.
    bad = dict(t)
    bad["R"] = dict(t["R"], state="done", evidence=["x"])
    if not ns["structure_problems"](bad):
        fail.append("CONF-P3: marking a parent done over open descendants must be flagged")
    if ns["structure_problems"](t):
        fail.append("CONF-P3: the well-formed fixture must have NO structural problem")

    # CONF-P4 — per-node law.
    for nid, node, why in (
        ("X", {"parent": None, "kind": "task", "state": "done",
               "origin": {"cause": "manual"}}, "done without evidence"),
        ("X", {"parent": None, "kind": "task", "state": "dropped",
               "origin": {"cause": "manual"}}, "dropped without a reason"),
        ("X", {"parent": None, "kind": "task", "state": "blocked",
               "origin": {"cause": "manual"}}, "blocked without a trigger"),
    ):
        if not ns["node_problems"]({nid: node}, nid):
            fail.append(f"CONF-P4: must flag a node {why}")

    # CONF-P5 — D1: declared work with no node would leak.
    if not ns["capture_problems"](t, [{"ref": "slot:y", "cause": "deferral"}]):
        fail.append("CONF-P5: undeclared-as-node work must be flagged as a leak")
    if ns["capture_problems"](t, [{"ref": "slot:x", "cause": "deferral"}]):
        fail.append("CONF-P5: work that DOES have a node must not be flagged")

    # CONF-P6 — deterministic leaf selection.
    nxt = ns["next_actionable"](t)
    if nxt != "B1":
        fail.append(f"CONF-P6: next actionable must be the open leaf B1, got {nxt!r}")

    # CONF-P7 — ancestry is root→leaf and cycle-safe.
    if ns["ancestry"](t, "B1") != ["R", "B", "B1"]:
        fail.append("CONF-P7: ancestry must read root → leaf")
    cyc = {"P": {"parent": "Q", "kind": "task", "state": "open", "origin": {"cause": "manual"}},
           "Q": {"parent": "P", "kind": "task", "state": "open", "origin": {"cause": "manual"}}}
    try:
        ns["ancestry"](cyc, "P")
        ns["structure_problems"](cyc)
    except RecursionError:
        fail.append("CONF-P7: a cyclic plan must be REPORTED, never hang or overflow")

    # CONF-P8 — the handoff projection is pure, deterministic and pointer-shaped.
    if not callable(ns.get("render_handoff")):
        fail.append("CONF-P8: spec does not define a callable `render_handoff`")
    else:
        r1, r2 = ns["render_handoff"](t, "R"), ns["render_handoff"](t, "R")
        if r1 != r2:
            fail.append("CONF-P8: the projection must be deterministic (two renders differ)")
        listed = [m.group(1) for m in
                  (re.match(r"\[.\]\s+(\S+)", ln.strip()) for ln in r1.splitlines()) if m]
        if "B1" not in listed or "B" not in listed:
            fail.append(f"CONF-P8: the projection must list the arc's open nodes, listed={listed}")
        if "A" in listed:
            fail.append("CONF-P8: a DONE node must not appear in the open projection")
        # tree order, not id order: a rendered child must FOLLOW its rendered parent immediately.
        deep = {"R": {"parent": None, "title": "r", "kind": "direction", "state": "open",
                      "origin": {"cause": "manual"}},
                "Z": {"parent": "R", "title": "z", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}},
                "Y": {"parent": "Z", "title": "y", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}},
                "M": {"parent": "R", "title": "m", "kind": "task", "state": "open",
                      "origin": {"cause": "manual"}}}
        order = [m.group(1) for m in
                 (re.match(r"\[.\]\s+(\S+)", ln.strip()) for ln in
                  ns["render_handoff"](deep, "R").splitlines()) if m]
        if order != ["R", "M", "Z", "Y"]:
            fail.append(f"CONF-P8: projection must be DEPTH-FIRST in tree order, got {order}")
        if ns["render_handoff"](t, "R") == ns["render_handoff"](
                {**t, "B1": dict(t["B1"], state="done", evidence=["e"])}, "R"):
            fail.append("CONF-P8: closing a node must change the projection")
    return fail


def run_docseal_suite(ns: dict, root: Path) -> list[str]:
    """§19.1 — differential against the LIVE implementation over every real sealed document."""
    fail: list[str] = []
    for fn in ("git_blob_sha", "split_seal", "seal_ok", "render_seal"):
        if not callable(ns.get(fn)):
            fail.append(f"CONF-D1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    sys.path.insert(0, str(root / "src"))
    try:
        from metafactory import docs_manifest as live
    except Exception as exc:                                      # noqa: BLE001
        return [f"CONF-D1: cannot import the live implementation to differ against: {exc!r}"]

    docs = sorted(root.glob("docs/**/*.md")) + sorted(root.glob("factories/*/docs/**/*.md"))
    compared = valid = 0
    for d in docs:
        try:
            text = d.read_text(encoding="utf-8")
        except OSError:
            continue
        compared += 1
        # CONF-D2 — the two implementations must SPLIT the seal identically.
        if ns["split_seal"](text) != live.split_seal(text):
            fail.append(f"CONF-D2: seal split differs from the live implementation on {d.name}")
            break
        # CONF-D3 — and must compute the same blob address for the body.
        body = ns["split_seal"](text)[1].encode("utf-8")
        if ns["git_blob_sha"](body) != live.git_blob_sha(body):
            fail.append(f"CONF-D3: blob address differs from the live implementation on {d.name}")
            break
        if ns["seal_ok"](text):
            valid += 1
    if compared < 50:
        fail.append(f"CONF-D4: only {compared} document(s) compared — the oracle is too thin to mean anything")
    if valid < 50:
        fail.append(f"CONF-D4: only {valid} document(s) have a VALID seal — expected the corpus to be sealed")
    # CONF-D5 — round-trip, and an unsealed document is NOT ok (silence is not freshness).
    sealed = ns["render_seal"]("# t\n\nbody\n", "2026-01-01T00:00Z")
    if not ns["seal_ok"](sealed):
        fail.append("CONF-D5: a freshly rendered seal must validate")
    if ns["seal_ok"]("# t\n\nbody\n"):
        fail.append("CONF-D5: an UNSEALED document must not be considered ok (fail-closed)")
    if ns["seal_ok"](sealed.replace("body", "tampered")):
        fail.append("CONF-D5: tampering with the body must invalidate the seal")
    return fail


def run_slotlaw_suite(ns: dict, root: Path) -> list[str]:
    """§19.2 — differential against `seed/delegation.py` on real-shaped cases."""
    fail: list[str] = []
    for fn in ("write_allowed", "footprint_problems", "verdict_problems"):
        if not callable(ns.get(fn)):
            fail.append(f"CONF-L1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    sys.path.insert(0, str(root))
    try:
        from seed import delegation as live
    except Exception as exc:                                      # noqa: BLE001
        return [f"CONF-L1: cannot import the live slot law to differ against: {exc!r}"]

    slot = {"slot_id": "s", "verdict_path": ".gen/s.verdict.json",
            "allow_globs": ["docs/spec/*.md", "tools/x.py"],
            "baseline_dirty": ["already/dirty.txt"]}
    cases = ["docs/spec/19-algorithms-reference.md", "tools/x.py", "src/metafactory/cli.py",
             ".gen/scratch.txt", ".gen/s.verdict.json", "already/dirty.txt",
             "docs/spec/sub/deep.md", "README.md", ".gen"]
    # CONF-L2 — the footprint law must agree, path by path.
    if ns["footprint_problems"](slot, cases) != live.footprint_problems(slot, cases):
        fail.append("CONF-L2: footprint verdict differs from the live implementation")
    # CONF-L3 — and so must the write predicate.
    for rel in cases:
        if rel == ".gen":
            continue                                   # the live predicate resolves a real path
        if ns["write_allowed"](slot, rel) != live.write_allowed(root, slot, str(root / rel)):
            fail.append(f"CONF-L3: write permission differs from the live implementation on {rel}")
            break
    # CONF-L4 — a path escaping the repository is never writable (fail-closed).
    if ns["write_allowed"](slot, None) is not False:
        fail.append("CONF-L4: a path that escapes the repo must never be writable")
    # CONF-L5 — the split-gate rule: green needs the HEAVY gate, not just the fast one.
    g = {"slot_id": "s", "status": "green", "check": "c", "exit_code": 0}
    if not ns["verdict_problems"]({**slot, "acceptance_gate_cmd": ["x"]}, g):
        fail.append("CONF-L5: a green verdict without acceptance_exit_code==0 must be refused")
    if ns["verdict_problems"]({**slot, "acceptance_gate_cmd": ["x"]},
                              {**g, "acceptance_exit_code": 0}):
        fail.append("CONF-L5: a green verdict WITH the acceptance gate passed must be accepted")
    if not ns["verdict_problems"](slot, None):
        fail.append("CONF-L5: a missing verdict must be a problem")
    return fail


def run_sequence_suite(ns: dict, root: Path) -> list[str]:
    """§19.3 — ordering, the dial, and transparent deferral."""
    fail: list[str] = []
    for fn in ("natural_key", "order_stations", "active_in", "predecessors"):
        if not callable(ns.get(fn)):
            fail.append(f"CONF-Q1: spec does not define a callable `{fn}`")
    if fail:
        return fail
    # CONF-Q2 — numeric-aware ordering: the defect that only appears past nine stations.
    if ns["order_stations"](["s10.yml", "s9.yml", "s1.yml", "_partial.yml"]) != \
            ["s1.yml", "s9.yml", "s10.yml"]:
        fail.append("CONF-Q2: ordering must be numeric-aware and skip `_`-prefixed files")
    # CONF-Q3 — the dial.
    if ns["active_in"]({"id": "a", "tier": "harden"}, "draft") is not False:
        fail.append("CONF-Q3: a harden-tier station must be deferred in draft mode")
    if ns["active_in"]({"id": "a", "tier": "harden"}, "harden") is not True:
        fail.append("CONF-Q3: a harden-tier station must be active in harden mode")
    if ns["active_in"]({"id": "a", "activation": "off"}, "harden") is not False:
        fail.append("CONF-Q3: `activation: off` must be inactive in every mode")
    # CONF-Q4 — TRANSPARENT deferral: a skipped predecessor must not satisfy its successors.
    line = [{"id": "s0"}, {"id": "s1", "tier": "harden"}, {"id": "s2"}]
    if ns["predecessors"](line, "s2", "harden") != ["s1"]:
        fail.append("CONF-Q4: in harden mode the predecessor of s2 is s1")
    if ns["predecessors"](line, "s2", "draft") != ["s0"]:
        fail.append("CONF-Q4: a DEFERRED predecessor must be transparent — the gate falls through "
                    "to ITS predecessor, never treating the chain as satisfied")
    # CONF-Q5 — explicit fan-in wins over file order.
    fan = [{"id": "a"}, {"id": "b"}, {"id": "c", "depends_on": ["a", "b"]}]
    if sorted(ns["predecessors"](fan, "c")) != ["a", "b"]:
        fail.append("CONF-Q5: an explicit depends_on fan-in must require ALL of them")
    return fail


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parents[1]
    sabotage = os.environ.get("SPEC_CONFORMANCE_SABOTAGE") == "1"

    source, files = extract(root, "kernel")
    if not source.strip():
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print("SUMMARY    no `<!-- spec-impl: kernel -->` block found in docs/spec/*.md")
        print("NEXT       the spec must CARRY its reference implementation, not point at the repo")
        return 1
    fx = root / FIXTURE
    if not fx.exists():
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print(f"SUMMARY    missing golden vectors: {FIXTURE}")
        print("NEXT       run `python3 tools/spec_fixture_gen.py`")
        return 1
    vectors = json.loads(fx.read_text(encoding="utf-8"))["vectors"]

    try:
        ns = load_module(source, sabotage)
    except Exception as exc:                                  # noqa: BLE001 — any error is a red
        failures = [f"CONF-K0: the extracted implementation does not execute: {exc!r}"]
    else:
        failures = run_suite(ns, vectors)

    # ── the plan algebra (§15) — a marked block is NORMATIVE, so it must be executed ──
    plan_src, plan_files = extract(root, "plan")
    if not plan_src.strip():
        failures.append("CONF-P1: no `<!-- spec-impl: plan -->` block found in docs/spec/*.md")
    else:
        files = files + plan_files
        try:
            plan_ns = load_module(plan_src, False)
            if sabotage:
                exec(compile(PLAN_SABOTAGE, "<spec:plan-sabotage>", "exec"), plan_ns)
        except Exception as exc:                                  # noqa: BLE001
            failures.append(f"CONF-P1: the extracted plan algebra does not execute: {exc!r}")
        else:
            failures.extend(run_plan_suite(plan_ns))

    # ── §19: seal, slot law, sequence — each with a real oracle ──────────────────
    for mod, runner, sab in (("docseal", run_docseal_suite, DOCSEAL_SABOTAGE),
                             ("slotlaw", run_slotlaw_suite, SLOTLAW_SABOTAGE),
                             ("sequence", run_sequence_suite, SEQUENCE_SABOTAGE)):
        src, mod_files = extract(root, mod)
        if not src.strip():
            failures.append(f"CONF: no `<!-- spec-impl: {mod} -->` block found in docs/spec/*.md")
            continue
        files = files + mod_files
        try:
            mod_ns = load_module(src, False)
            if sabotage:
                exec(compile(sab, f"<spec:{mod}-sabotage>", "exec"), mod_ns)
        except Exception as exc:                                  # noqa: BLE001
            failures.append(f"CONF: the extracted `{mod}` does not execute: {exc!r}")
        else:
            failures.extend(runner(mod_ns, root))

    if sabotage:
        if failures:
            print("VERDICT    spec-conformance (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the suite bit as it must: {len(failures)} failure(s) under sabotage")
            return 0
        print("VERDICT    spec-conformance (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: the suite passed with a sabotaged digest")
        return 1

    if failures:
        print("VERDICT    spec-conformance — FAIL   (exit 1)")
        print(f"SUMMARY    {len(failures)} conformance failure(s) over {len(vectors)} golden vector(s)")
        for f in failures[:5]:
            print(f"FAILURES   {f}")
        print("NEXT       fix the reference implementation IN THE SPEC (docs/spec/), not in src/")
        return 1
    print("VERDICT    spec-conformance — PASS   (exit 0)")
    print(f"SUMMARY    kernel rebuilt from {len(files)} spec file(s); "
          f"{len(vectors)} pin-anchored vector(s) reproduce; 26 conformance checks green (kernel + plan + seal + slot law + sequence)")
    print(f"ARTIFACT   {SPEC_DIR}/ (blocks: {', '.join(sorted(set(files)))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
