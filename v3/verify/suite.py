#!/usr/bin/env python3
"""suite — the registry WIRED.

INC-6 ADDS SIX GATES THAT ARE NOT PORTS. Everything below this paragraph describes the port of v2's
23 gates; `telemetry_liveness`, `ledger`, `escape_threshold`, `iteration`, `compaction` and
`economy_census` have no v2 original, which is why they are absent from `gate_census`'s dispositions
(that census answers "where did each of v2's gates go", and paperwork for a gate that never existed
in v2 is exactly what it refuses). They are the economy's teeth: §07.5 states the structural problem
in one line — the engine's targets are GATED and green, the economy's are OBSERVED and red — and a
number with no tooth drifts. `telemetry_liveness` is the central one and it is red on landing, on
purpose and against measured fact: the capture layer wrote nothing between 2026-07-13 and
2026-07-28 while the project ran five increments, and a gate that went green over that would be the
fabricated green this repo refuses.

    ORIGINAL DOCSTRING (the port), unchanged below:

`build_registry` registers all 15 of v2's 23 gates ported to v3
(`compile`, `isolation`, `quality`, `pbt`, `security`, `roles`, `kinds`, `deferred`, `design_eval`,
`generality`, `plan`, `dial`, `benchmark`, `codegen_freeze`, `suite`), and `main` is the runner that
plays v2's `cmd_check` role — run every registered gate's declared argv once, fold the results through
`v3.verify.registry.summarize` (green / red / N/A counted apart, R-12), and print ONE verdict.

    python3 -m v3.verify.suite

Exit 0 iff no gate is red AND at least one is green (`summarize`'s own law — an all-N/A or empty
suite is never green, R-12 / Lock #1's shape one level up). This module is what `v3.verify.gate_census`
imports to answer "which gates has the registry actually accepted" — so `build_registry` MUST be
import-time safe: it only constructs `Gate` objects and calls `Registry.register` (a witness check
against the filesystem, not a subprocess and not a tree scan), and it runs no process and reads no
directory tree at IMPORT time. All subprocess/tree work happens inside `main`, called explicitly.

THE FIFTEEN GATES, and why each is shaped the way it is:
  `compile`     — `python3 -m compileall -q v3 seed`; no new check module (a syntax gate IS the
                  argv). One-sided: `ONE_SIDED["compile"]`.
  `isolation`   — `v3.verify.checks.isolation`; ports v2's "the platform never imports its products".
                  One-sided: `ONE_SIDED["isolation"]`.
  `quality`     — `v3.verify.checks.quality`; the PORTED `v3.graph` (build+quality) over v3/+seed/,
                  with an EMBEDDED `fixture` witness (`tests/fixtures/quality/monolith_shaped.py`)
                  asserted inside its own green run.
  `pbt`         — `v3.verify.checks.pbt`; the graph property suite (P2 serde round-trip), with a
                  `sabotage_env` witness (`V3_PBT_SABOTAGE`) — NOT embedded, re-run by `suite`.
  `security`    — `v3.verify.checks.security`; heritable secret/supply-chain scan over v3's own
                  substrate (re-pointed from v2's own platform package), with an EMBEDDED `fixture`
                  witness (`tests/fixtures/security/planted_secrets.txt`).
  `roles`       — `v3.verify.checks.roles`; agents specialize by ROLE, never by domain (subject
                  unchanged: `.claude/agents/*.md`, meta + every factory), with a `sabotage_env`
                  witness (`V3_ROLES_SABOTAGE`) — a planted domain-named agent, NOT embedded.
  `kinds`       — `v3.verify.checks.kind_hygiene`; freezes the check-kind vocabulary against
                  `v3.verify.kinds.KINDS` (subject: factories' own station YAML + specs — v2's
                  platform-side station YAMLs have no v3 analogue, see that module's own CUT note),
                  with a `sabotage_env` witness (`V3_KIND_HYGIENE_SABOTAGE`) — a planted unknown kind.
  `deferred`    — `v3.verify.checks.deferred`; `declared-deferred` with teeth + accumulation measured
                  (subject unchanged: `factories/*/factory.spec.yml`), with an EMBEDDED `fixture`
                  witness (`tests/fixtures/governance/strict_untracked.factory.spec.yml`).
  `design_eval` — `v3.verify.checks.design_eval`; criteria-as-DATA + PINNED critiques (subject
                  unchanged: `factories/*/design/criteria.yml`), with an EMBEDDED `pinned_data`
                  witness — FSK's real, committed negative witness (all 4 axes below threshold).
  `generality`  — `v3.verify.checks.generality`; ADR-014's tooth (no substrate mechanism promoted
                  `general` on the strength of one domain), subject unchanged
                  (`docs/reference/parity.yml` + each domain's `factory.spec.yml` + `.proof/`,
                  recomputed through `v3.seed_loader`). The ONE gate v2 shipped with NO red witness at
                  all — this port EARNS one: a `sabotage_env` witness (`V3_GENERALITY_SABOTAGE`) that
                  calls the real, pure `audit_mechanism` law with two synthetic decorative claims
                  (single-domain evidence; a green pair that is not radically distinct) and asserts
                  both are caught.
  `plan`        — `v3.verify.checks.plan`; plan-as-DATA (`.gen/plan.json`) well-formedness, reusing
                  `v3.delegation.slot`'s already-ported manifest law for each WorkOrder, with a
                  `sabotage_env` witness (`V3_PLAN_SABOTAGE`) — 4 synthetic malformed plans (one per
                  defect class), NOT embedded (v2 had no committed fixture for this, only inline
                  Python literals). N/A (`na_when`) when `.gen/plan.json` is absent — planning is
                  opt-in.
  `dial`        — `v3.verify.dial`; the draft→harden dial's two-sided tooth (an adopted dial must
                  defer a non-empty PROPER subset of active stations), with a `sabotage_env` witness
                  (`V3_DIAL_SABOTAGE`) — a synthetic all-harden `DialProfile` fed straight to the real
                  law. N/A (`na_when`) when no factory has adopted (0 harden stations anywhere).
  `benchmark`   — `v3.verify.benchmark`; the sweet-spot-CRUD product-class target, with an EMBEDDED
                  `pinned_data` witness (`benchmarks/sweet-spot-crud.yml`) — real committed data: the
                  ceiling product (`full-stack-kotlin/snipeit`) failing the target IS the red side,
                  re-asserted on every green run. N/A (`na_when`) when no `benchmarks/*.yml` exists.
  `suite`       — `v3.verify.checks.suite_sweep`; v2's `pytest -q tests` translated to v3's actual
                  test corpus: re-run every OTHER registered gate's re-runnable red side (P2 itself).
                  One-sided: `ONE_SIDED["suite"]`.

N/A COUNTED APART (R-12), NOT FOLDED INTO GREEN. `plan`, `dial`, and `benchmark` are each opt-in and
can legitimately have nothing to check; a gate that says so must not look like an ordinary PASS. Each
declares a non-empty `Gate.na_when` and, on its N/A branch, prints a `SUMMARY` line starting with
`N/A` (`v3.kernel.report.Verdict`'s own bounded rendering). `_run_gate` below recognizes that shape —
ONLY for a gate that declared `na_when` — and reports `Outcome(..., NA, ...)` instead of PASS, so
`summarize` counts it apart and an all-N/A suite is never reported green.

WHY THIS SUITE IS RED, and why that is the correct state. `codegen_freeze` IS registered and it
FAILS — it reports two genuine, pre-existing violations owned by `full-stack-kotlin` (a malformed
waiver in an FSK work-doc, and a commit that fed `codegen/` with no open waiver in its own tree).
v2's own gate is independently confirmed red for the identical two reasons against the same tree, so
this is parity, not a port defect.

The alternatives were both worse. Leaving it unregistered would have kept this module green while a
working gate sat outside the count — the exact shape of "green because nobody asked what was left
out" that `gate_census` exists to catch. Weakening the detector, or writing meta a waiver for FSK's
debt, would be the fabricated green this project refuses; the standing rule is that **a red is
disposed of by the level that OWNS it** (LOG 2026-07-28), and meta does not clear FSK's board.

So the suite reports `red=1` with the cause named, exactly as `meta check` carries its 2/23. A
verification suite that goes red on real debt is working, not broken.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from ..kernel.report import Verdict
from .registry import FAIL, NA, PASS, Gate, Outcome, Registry, Witness, summarize
from .registry import ONE_SIDED

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
PY = sys.executable

#: the marker a `na_when`-declaring gate's own `Verdict` prints on its vacuous-true branch
#: (`SUMMARY    N/A: …` — see `v3.kernel.report.Verdict.render`). Recognized ONLY for a gate that
#: declared `na_when`, so an unrelated gate whose message happens to contain the substring is never
#: misread as opting out.
_NA_MARKER = re.compile(r"^SUMMARY\s+N/A\b")


def build_registry(root: Path) -> Registry:
    """Construct the `Registry` and register every gate. Pure, no I/O beyond the witness existence
    checks `Registry.register` already performs — safe to call at any time, including from
    `gate_census`, which is exactly why it must never run a subprocess or scan a tree.

    Split in two by PROVENANCE, not by taste: `_register_ported` carries v2's gates, whose
    dispositions `gate_census` audits; `_register_economy` carries the six INC-6 gates, which have
    no v2 original and must therefore stay OUT of that census. A reader asking "is this a port or a
    new tooth?" gets the answer from which function it is in.
    """
    root = Path(root)
    registry = Registry(root)
    _register_ported(registry)
    _register_economy(registry)
    return registry


def _register_ported(registry: Registry) -> None:
    """v2's gates, ported. Every name here appears in `gate_census.DISPOSITIONS`."""
    registry.register(Gate(
        name="compile",
        argv=(PY, "-m", "compileall", "-q", "v3", "seed"),
        proves="every .py under v3/ and seed/ parses without a SyntaxError",
        one_sided_because=ONE_SIDED["compile"],
    ))
    registry.register(Gate(
        name="isolation",
        argv=(PY, "-m", "v3.verify.checks.isolation"),
        proves="v3/ never statically imports `factories` — the platform never imports its products",
        one_sided_because=ONE_SIDED["isolation"],
    ))
    registry.register(Gate(
        name="quality",
        argv=(PY, "-m", "v3.verify.checks.quality"),
        proves="v3/+seed/ carry no file/function size violation and no import cycle, at v2's "
               "default thresholds",
        witness=Witness("fixture", "tests/fixtures/quality/monolith_shaped.py"),
    ))
    registry.register(Gate(
        name="pbt",
        argv=(PY, "-m", "v3.verify.checks.pbt"),
        proves="the graph property suite (P2 serde round-trip) holds under a fixed seed",
        witness=Witness("sabotage_env", "V3_PBT_SABOTAGE"),
    ))
    registry.register(Gate(
        name="security",
        argv=(PY, "-m", "v3.verify.checks.security"),
        proves="v3's own shipped substrate (v3/+seed/+.claude/hooks/+.claude/agents/) carries no "
               "hardcoded credential and every declared factory dependency is allowlisted",
        witness=Witness("fixture", "tests/fixtures/security/planted_secrets.txt"),
    ))
    registry.register(Gate(
        name="roles",
        argv=(PY, "-m", "v3.verify.checks.roles"),
        proves="every `.claude/agents/*.md` (meta + each factory) names a role in the closed "
               "vocabulary — agents specialize by ROLE, never by domain",
        witness=Witness("sabotage_env", "V3_ROLES_SABOTAGE"),
    ))
    registry.register(Gate(
        name="session_memory_parity",
        argv=(PY, "-m", "v3.verify.session_memory_parity"),
        proves="the ported `precompact` and `rehydrate` bodies derive the SAME FACTS v2's do — the "
               "open increment, the RTM verdicts, whether the snapshot's bytes landed — compared as "
               "fact-sets rather than as output, because the ports are English where v2 is Spanish "
               "and a string comparison would redden a correct port and greenlight a parroting one",
        witness=Witness("sabotage_env", "V3_SESSION_MEMORY_PARITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="column_law_parity",
        argv=(PY, "-m", "v3.verify.column_law_parity"),
        proves="the three law modules the hooks branch on (`cadence`, `instrument`, `hermetic`) "
               "answer as v2's do over a matrix that exercises distinct answers per function — the "
               "port of a body that decides whether a write is denied or a turn may close cannot be "
               "accepted on a pin, because a hollow one disables the column while staying green",
        witness=Witness("sabotage_env", "V3_COLUMN_LAW_PARITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="cli_parity",
        argv=(PY, "-m", "v3.verify.cli_parity"),
        proves="for every verb `v3.cli` DECLARES in its DISPATCH table, v3's flag surface matches "
               "v2's for that same verb, derived from `build_parser` at the oracle commit — so a "
               "verb can be 'ported' only in the sense the CI and the hooks actually invoke it, "
               "not merely present under the right name",
        witness=Witness("sabotage_env", "V3_CLI_PARITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="verb_census",
        argv=(PY, "-m", "v3.verify.verb_census"),
        proves="v2's whole CLI verb surface is derived from `build_parser` at the oracle commit and "
               "every verb carries a disposition, and — the tooth, node N-0088 — a verb v3 CLAIMS "
               "to dispatch must actually resolve, so a declared-but-absent target (which is how "
               "`v3.cli` came to be named by `v3.verify.kinds` while not existing) is red, not quiet",
        witness=Witness("sabotage_env", "V3_VERB_CENSUS_SABOTAGE"),
    ))
    registry.register(Gate(
        name="kinds",
        argv=(PY, "-m", "v3.verify.checks.kind_hygiene"),
        proves="every check-kind declared in a factory's station YAML or factory.spec.yml is in "
               "the frozen vocabulary `v3.verify.kinds.KINDS`",
        witness=Witness("sabotage_env", "V3_KIND_HYGIENE_SABOTAGE"),
    ))
    registry.register(Gate(
        name="deferred",
        argv=(PY, "-m", "v3.verify.checks.deferred"),
        proves="every factory spec's declared-deferred entries are honest under its own "
               "governance.deferral_tracking policy, with the accumulation measured",
        witness=Witness("fixture", "tests/fixtures/governance/strict_untracked.factory.spec.yml"),
    ))
    registry.register(Gate(
        name="design_eval",
        argv=(PY, "-m", "v3.verify.checks.design_eval"),
        proves="every factory that opted into design/criteria.yml re-verifies clean against its "
               "standing witness (must fail >=1 axis) and its covered products' pinned critiques",
        witness=Witness("pinned_data",
                        "factories/full-stack-kotlin/design/critiques/template-witness.json"),
    ))
    registry.register(Gate(
        name="generality",
        argv=(PY, "-m", "v3.verify.checks.generality"),
        proves="every substrate mechanism declared `general` in docs/reference/parity.yml is proven "
               "green in >=2 domains with >=1 radically distinct pair (ADR-014) — never trusted from "
               "prose alone",
        witness=Witness("sabotage_env", "V3_GENERALITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="plan",
        argv=(PY, "-m", "v3.verify.checks.plan"),
        proves="`.gen/plan.json`, when present, is a well-formed set of WorkOrders (valid slot "
               "manifests + an acyclic dependency DAG + honest deferrals) and every "
               "`.gen/escalations/*.json` is a valid S2->S3 handoff",
        witness=Witness("sabotage_env", "V3_PLAN_SABOTAGE"),
        na_when="no `.gen/plan.json` in the tree — planning is opt-in (SAFE-7)",
    ))
    registry.register(Gate(
        name="dial",
        argv=(PY, "-m", "v3.verify.dial"),
        proves="every factory that adopted the draft→harden dial (>=1 `tier: harden` active station) "
               "keeps harden a non-empty PROPER subset of its active stations",
        witness=Witness("sabotage_env", "V3_DIAL_SABOTAGE"),
        na_when="no factory has adopted the dial — 0 harden stations anywhere (opt-in)",
    ))
    registry.register(Gate(
        name="benchmark",
        argv=(PY, "-m", "v3.verify.benchmark"),
        proves="every benchmark's `sweet_spot` product(s) MEET its target and every `ceiling` "
               "product does NOT — re-derived from each product's committed product.yml + pin",
        witness=Witness("pinned_data", "benchmarks/sweet-spot-crud.yml"),
        na_when="no `benchmarks/*.yml` in the tree (opt-in)",
    ))

    registry.register(Gate(
        name="codegen_freeze",
        argv=(PY, "-m", "v3.verify.checks.codegen_freeze"),
        proves="the ADR-023 §3 codegen freeze is not pierced without a written waiver — in the "
               "working tree AND in every commit since the freeze came into force",
        witness=Witness("sabotage_env", "V3_CODEGEN_FREEZE_SABOTAGE"),
    ))
    registry.register(Gate(
        name="state_snapshot",
        argv=(PY, "-m", "v3.verify.checks.state_snapshot"),
        proves="STATE's «Ahora» is still a bounded SNAPSHOT and not a log: within the 45-line "
               "budget and carrying no closure older than 14 days (ADR-019 §3)",
        witness=Witness("sabotage_env", "V3_STATE_SNAPSHOT_SABOTAGE"),
    ))
    registry.register(Gate(
        name="state_fidelity",
        argv=(PY, "-m", "v3.verify.checks.state_fidelity"),
        proves="no «Ahora» line's COMPLETE/INCOMPLETE claim contradicts the RTM re-derived from "
               "`.proof/` — faithfulness, not freshness (ADR-019 §4)",
        witness=Witness("sabotage_env", "V3_STATE_FIDELITY_SABOTAGE"),
        na_when="no factory carries a `.proof/` directory — the statuses it would compare the "
                "prose against were never derived, so a PASS would be vacuous rather than true",
    ))
    registry.register(Gate(
        name="evidence_liveness",
        argv=(PY, "-m", "v3.verify.checks.evidence_liveness"),
        proves="every LIVING doc's CITES references resolve — `.md` paths and bare `ADR-NNN` — "
               "over the whole corpus; history (`decisions/`, `LOG.md`, closed `work/`) is exempt "
               "and EVIDENCES targets are recorded but never gated (ADR-026 F1)",
        witness=Witness("fixture", "tests/fixtures/docs/dangling_reference.md"),
    ))
    registry.register(Gate(
        name="projection",
        argv=(PY, "-m", "v3.verify.checks.projection"),
        proves="STATE's generated `meta:projection` block equals what the facts re-derive right now "
               "— open increment + per-factory RTM recomputed from `.proof/`, never a stored "
               "`passed: true` (ADR-007 §3)",
        witness=Witness("sabotage_env", "V3_PROJECTION_SABOTAGE"),
        na_when="no factory carries a `.proof/` directory — the facts have not been derived yet "
                "(`.proof/` is gitignored, so a fresh clone has none until `ci --rederive` runs); "
                "calling the projection stale there would be a false positive, not a finding",
    ))
    registry.register(Gate(
        name="docs",
        argv=(PY, "-m", "v3.verify.checks.docs_check"),
        proves="every authored doc in every level's home carries a current content-addressed seal, "
               "INDEX covers exactly the meta doc set, no entry doc has a dangling link, and no "
               "home's STATE is stale by last-commit time (ADR-009)",
        witness=Witness("sabotage_env", "V3_DOCS_SABOTAGE"),
    ))
    registry.register(Gate(
        name="suite",
        argv=(PY, "-m", "v3.verify.checks.suite_sweep"),
        proves="every OTHER registered gate's re-runnable red side still goes red when re-run (P2)",
        one_sided_because=ONE_SIDED["suite"],
    ))


def _register_economy(registry: Registry) -> None:   # + INC-7's two migration gates

    """INC-6's six. NONE of these is a port: §07.5 states the structural problem in one line — the
    engine's targets are GATED and green, the economy's are OBSERVED and red — and a number with no
    tooth drifts. They are absent from `gate_census` by construction, because paperwork for a gate
    that never existed in v2 is precisely what that census refuses."""
    registry.register(Gate(
        name="telemetry_liveness",
        argv=(PY, "-m", "v3.verify.checks.telemetry_liveness"),
        proves="every day with demonstrable activity (commits, `.proof/` writes, station_run) "
               "also carries an economy record — «no se midió» is distinguishable from «dio cero», "
               "and the detector is NOT a hook, because a hook cannot detect that hooks are off",
        witness=Witness("sabotage_env", "V3_TELEMETRY_LIVENESS_SABOTAGE"),
        na_when="no demonstrable activity in the window — the gate refuses to assert rather than "
                "certifying the instrument on the strength of nothing having happened",
    ))
    registry.register(Gate(
        name="ledger",
        argv=(PY, "-m", "v3.verify.checks.ledger_check"),
        proves="every recorded leaf carries a price attributable to a model AND a session class, "
               "with per-model costs that reconcile — a cost with no owner is not a measurement",
        witness=Witness("sabotage_env", "V3_LEDGER_SABOTAGE"),
        na_when="the ledger holds no entry in the window — reported as unmeasured, never as $0.00 "
                "(the whole defect this increment exists for, so it may not be a silent green)",
    ))
    registry.register(Gate(
        name="escape_threshold",
        argv=(PY, "-m", "v3.verify.checks.escape_threshold"),
        proves="the ADR-019 §6 observer EMITS: (a) entry-set headroom against the window plus the "
               "full corpus growth, and (b) the leaf relevance ratio — with real values or an "
               "explicit N/A. The threshold itself is not gated; its silence is",
        witness=Witness("sabotage_env", "V3_ESCAPE_THRESHOLD_SABOTAGE"),
        na_when="no leaf has been metered yet, so (b) has no subject — (a) is still emitted, and "
                "an observer with half its numbers says so instead of implying the other half",
    ))
    registry.register(Gate(
        name="iteration",
        argv=(PY, "-m", "v3.verify.checks.iteration_check"),
        proves="the host's retry loop is persisted honestly — no station record with an empty "
               "attempt list, no declared count outliving a truncated list — and the derivation "
               "actually surfaces red→green cycles and repeated failures (§09.4 A-2)",
        witness=Witness("sabotage_env", "V3_ITERATION_SABOTAGE"),
        na_when="no station has been run through the host runner yet — nothing to under-report",
    ))
    registry.register(Gate(
        name="compaction",
        argv=(PY, "-m", "v3.verify.checks.compaction"),
        proves="a PreCompact callback is wired into every leaf with `include_hook_events` on, so a "
               "compaction is counted by the event rather than by whoever remembers (§07.2 c), and "
               "the session-class vocabulary is well-formed",
        witness=Witness("sabotage_env", "V3_COMPACTION_SABOTAGE"),
    ))
    registry.register(Gate(
        name="rederive",
        argv=(PY, "-m", "v3.verify.rederive"),
        proves="every MIGRATED factory, run end to end on v3 out of a copy staged from git's tracked "
               "files, reproduces its committed `pinned_verdict.json` station for station (P1)",
        witness=Witness("sabotage_env", "V3_REDERIVE_SABOTAGE"),
    ))
    registry.register(Gate(
        name="migration_census",
        argv=(PY, "-m", "v3.verify.migration_census"),
        proves="nothing a MIGRATED factory's line exercises is still owed to a later increment — "
               "every check kind and build action is ported, needs no body, or is owed to the "
               "increment that migrates the earliest factory declaring it",
        witness=Witness("sabotage_env", "V3_MIGRATION_CENSUS_SABOTAGE"),
    ))
    registry.register(Gate(
        name="economy_census",
        argv=(PY, "-m", "v3.verify.checks.economy_census"),
        proves="no module producing an economic number references a transcript in executable code, "
               "and every module + public function of v2's economy surface carries exactly ONE "
               "disposition verified against an artifact at the oracle commit",
        witness=Witness("sabotage_env", "V3_ECONOMY_CENSUS_SABOTAGE"),
    ))
    # The three BEHAVIOURAL parity witnesses. Registered rather than left standalone because
    # `rederive` above proves P1 only, and P1 cannot tell a faithful port from a hollowed one:
    # `proof_sha` hashes check names and exit codes, so an executor rewritten to `return 0`
    # reproduces the same pin AND survives every line-level sabotage class, which perturbs the LINE
    # and never the executor's inputs (spec 11 §11.2, stated rather than discovered). These run v2's
    # real body at the oracle commit beside the port over one case matrix and compare exit codes —
    # the only instruments in the suite whose subject is a ported BODY. `eval_gate_parity` has
    # existed since V3-INC9 and was never registered; leaving it out is how an instrument stops
    # being run without anyone deciding to stop running it (node `N-0112`).
    registry.register(Gate(
        name="eval_gate_parity",
        argv=(PY, "-m", "v3.verify.eval_gate_parity"),
        proves="v3's ported `eval_gate` answers with the same exit code as v2's real body at the "
               "oracle commit, over a matrix of scenarios reaching several distinct codes",
        witness=Witness("sabotage_env", "V3_EVAL_GATE_PARITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="live_run_parity",
        argv=(PY, "-m", "v3.verify.live_run_parity"),
        proves="v3's ported `live_run` answers with the same exit code as v2's real body at the "
               "oracle commit — including the codes it passes through from a bootstrap or a live "
               "driver, and the DEFERRED path taken when there is neither a pin nor a provider",
        witness=Witness("sabotage_env", "V3_LIVE_RUN_PARITY_SABOTAGE"),
    ))
    registry.register(Gate(
        name="eval_floor_parity",
        argv=(PY, "-m", "v3.verify.eval_floor_parity"),
        proves="v3's ported `eval_floor` answers with the same exit code as v2's real body at the "
               "oracle commit, the degraded-evidence side included",
        witness=Witness("sabotage_env", "V3_EVAL_FLOOR_PARITY_SABOTAGE"),
    ))



def _run_gate(gate: Gate, root: Path) -> Outcome:
    """Run ONE gate's declared argv as a subprocess (the green side only — the red side, when
    re-runnable, is `suite`'s own job, not every invocation's). Any sabotage-env handle this gate
    itself carries is explicitly cleared, so a stray exported var can never masquerade as a clean run.

    A gate that declared `na_when` may report N/A instead of PASS on an exit-0 run: it prints a
    `SUMMARY N/A: …` line (`_NA_MARKER`) on its own vacuous-true branch. Only checked for gates that
    declared `na_when` — an ordinary gate's message is never reinterpreted (R-12: N/A is counted
    apart, never folded into green, but it must not be invented for a gate that never claimed one)."""
    env = dict(os.environ)
    if gate.witness is not None and gate.witness.kind == "sabotage_env":
        env.pop(gate.witness.handle, None)
    result = subprocess.run(gate.argv, cwd=root, env=env, capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    tail = (lines or result.stderr.strip().splitlines() or [""])[-1]
    if result.returncode == 0 and gate.na_when and any(_NA_MARKER.match(line) for line in lines):
        return Outcome(gate.name, NA, detail=f"N/A ({gate.na_when}): {tail[:160]}")
    status = PASS if result.returncode == 0 else FAIL
    return Outcome(gate.name, status, detail=f"exit {result.returncode}: {tail[:160]}")


def main(argv: list[str]) -> int:
    # `--skip a,b` / `--only a,b`: comma-separated gate names, PORTED from v2's `cmd_check` (same
    # wording, same discipline — a skip is PRINTED and never counts as green). Needed because the
    # external CI invokes `./meta check --skip projection,generality`; `--only` is new here (v2 never
    # grew it — see `v3.cli`'s and `v3.verify.cli_parity`'s docstrings for why that asymmetry is
    # deliberate, not a drift).
    opts: dict[str, str] = {}
    i = 0
    while i < len(argv):
        if argv[i] in ("--skip", "--only") and i + 1 < len(argv):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            return Verdict("v3-suite", 2, f"unrecognized argument {argv[i]!r}; usage: "
                           f"v3-suite [--skip a,b] [--only a,b]").emit()

    registry = build_registry(_ROOT)
    known = {g.name for g in registry.gates()}
    skip = {s.strip() for s in opts.get("skip", "").split(",") if s.strip()}
    only = {s.strip() for s in opts["only"].split(",") if s.strip()} if "only" in opts else None
    unknown = sorted((skip | (only or set())) - known)
    if unknown:
        return Verdict("v3-suite", 2, f"unknown gate name(s) {unknown}; known: "
                       f"{', '.join(sorted(known))}").emit()

    gates = [g for g in registry.gates() if (only is None or g.name in only) and g.name not in skip]
    excluded = sorted(known - {g.name for g in gates})
    if excluded:
        # Say only what the flag actually tells us. v2's wording ("evidence not re-derivable in this
        # environment") was true of ITS single caller and is an assertion about a REASON this code
        # cannot know: `--only compile` excludes 27 gates for no environmental reason at all. The
        # invariant worth printing is the one that holds either way — they were not run, and they do
        # not count as green.
        print(f"SKIPPED    {', '.join(excluded)} — excluded by invocation (--skip/--only); "
              f"not run, and they do NOT count as green")

    outcomes = [_run_gate(gate, _ROOT) for gate in gates]
    return summarize(outcomes, verb="v3-suite").emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
