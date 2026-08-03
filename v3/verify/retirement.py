#!/usr/bin/env python3
"""retirement — WHAT HAPPENS TO EVERY GATE THAT DEPENDS ON THE DEAD ANCESTOR, as DATA.

    from v3.verify.retirement import RETIREMENT, Row, population

PASO 3 of `docs/work/V3-EXTRACT-DIRECTION-INCREMENT.md` (`N-0135`). The law over this table is
`v3.verify.checks.retirement_census` — same split as `extract_manifest` / `extract_package`: the
decisions are authored here, the teeth live in the gate.

THE RULE THIS TABLE SERVES (P7 of INC-12): *retiring is allowed; retiring without deciding is not,
and a retirement with no PROOF that the subject disappeared is a tooth extraction dressed as cleanup.*

    THE MEASUREMENT THAT WROTE THIS FILE (2026-08-03/04) — it corrected the direction doc twice.

    (1) THE POPULATION IS DERIVED, NOT LISTED. The direction doc classified "class C" with the
    heuristic `'_show' in src or 'oracle_ref' in src`. That counted `codegen_freeze` IN (it matches on
    its own `git show` of the freeze epoch and never touches the oracle) and `cli_parity` /
    `verb_census` OUT (they reach the oracle TRANSITIVELY, importing `_V2_CLI`/`_oracle`/`_show` from
    `gate_census`, naming no v2 path themselves). The honest population is the one-hop symbol closure
    of `import_boundary._ORACLE_READERS` — a set that ALREADY carries two-sided teeth: that module
    goes red when an enumerated reader is missing from the tree AND when a reader holds a carve-out it
    no longer uses. Derived, it is exactly 11, and 11 is therefore the row count nobody chose.

    (2) FIVE OF THE ELEVEN ARE THE ONLY EXERCISE OF A LIVE v3 BODY. `eval_floor`, `eval_gate` and
    `live_run` are check KINDS, not registered gates (`"eval_gate" in build_registry(...)` is False):
    their sole suite-level coverage is the parity matrix. `column_law_parity` is the only behavioural
    exercise of the COLUMN's decision functions, and `session_memory_parity` the only one of
    `precompact`/`rehydrate`. Retiring those five, as the direction doc's plan said to, would have
    deleted 54 live cases and left the column with no behavioural test at all. THE VALUE OF A PARITY
    HARNESS WAS NEVER THE COMPARISON — IT WAS THE MATRIX; the oracle merely supplied the expected
    answers. Pin the answers and the matrix outlives the ancestor. Three more (`economy_census`,
    `migration_census`, `verb_census`) mix oracle assertions with assertions over the CURRENT tree, so
    retiring the module drops the live half with the dead one.

    Three true retirements, eight decisions that carry an obligation. The obligations are COUNTED,
    never hidden: `open_obligations=N` is on the census's SUMMARY line, and claiming a discharge that
    did not happen is red.

Zero model; every field is checkable against the tree (I-3). Names no domain (ADR-012).
"""
from __future__ import annotations

from dataclasses import dataclass

RETIRE = "retire"
KEEP = "keep"
DECISIONS = (RETIRE, KEEP)

#: The v2 substrate's root. Named here ONCE, as the subject of a disposition rather than as something
#: to read — `import_boundary` rule 3 bans naming it to READ it, which is exactly the distinction this
#: table is about. Nothing in this module or its gate opens a path under it or shells out to git.
V2_ROOT = "src/metafactory/"


@dataclass(frozen=True, slots=True)
class Row:
    """One decision. `subject` is what the module's law reads OUT OF THE DEAD ANCESTOR — for a
    `retire` the census must prove every entry is absent from the tree and travels with nothing.
    `obligation` is what is still owed (None == nothing owed); `discharged` is a CLAIM the census
    checks against the derived population, never a note."""
    gate: str | None
    decision: str
    subject: tuple[str, ...]
    reason: str
    obligation: str | None
    discharged: bool


#: module relpath -> Row. Keyed on the MODULE because that is what the population is derived from; the
#: gate it feeds (if any) is a field, since one population member (`v3/economy/census.py`) backs a gate
#: registered under a different module and one (`gate_census`) backs no gate at all.
RETIREMENT: dict[str, Row] = {

    # ---- the three genuine retirements: their whole law is about a thing that no longer exists ----
    "v3/verify/deletion_manifest.py": Row(
        gate="deletion_manifest",
        decision=RETIRE,
        subject=(V2_ROOT,),
        reason="It asserts that every file of the dead substrate's file population carries a "
               "disposition. Every assertion it makes is about v2 and none is about v3, so there is "
               "no live half to preserve: once the population is gone the question is not false, it "
               "is unanswerable, and it was answered — that is what the migration's close means. "
               "NOTE, against the direction doc: its `population()` is deliberately NOT reused as "
               "this census's proof engine. Doing so would make the retirement census itself read the "
               "oracle — the one gate in the repo that could not travel, failing its own law on its "
               "first run in the destination. Absence is provable without git.",
        obligation=None,
        discharged=True,
    ),
    "v3/verify/cli_parity.py": Row(
        gate="cli_parity",
        decision=RETIRE,
        subject=(V2_ROOT + "cli.py",),
        reason="It pins v3's flag surface to a dead ancestor's. Unlike the five matrices below, "
               "fossilising its expectations would be ACTIVELY HARMFUL: it would freeze this CLI to "
               "the shape of a version that governs nothing, so every legitimate evolution of the "
               "verb surface would land red for the wrong reason. What is worth keeping from it — "
               "that no verb silently disappears and that every claimed verb resolves importably — "
               "is `verb_census` C2..C6, which survives its own cut and is registered.",
        obligation=None,
        discharged=True,
    ),
    "v3/verify/gate_census.py": Row(
        gate=None,
        decision=RETIRE,
        subject=(V2_ROOT + "cli.py",),
        reason="The single oracle-reading FAÇADE (`_V2_CLI`/`_oracle`/`_show`) plus v2's 23-gate "
               "dispositions. It backs no registered gate; it exists so the other readers do not each "
               "grow their own `git show`. It dies when its last consumer is cut — and it is listed "
               "here precisely because a module that only ever appears as somebody else's import is "
               "how a dependency survives a cleanup nobody aimed at it.",
        obligation="its last two consumers (`cli_parity`, deleted here, and `verb_census`, whose C1/C7 "
                   "cut is still owed) must stop importing it before the file can go",
        discharged=False,
    ),

    # ---- keep · PIN: the oracle's last act is to leave its answers behind as data -----------------
    "v3/verify/column_law_parity.py": Row(
        gate="column_law_parity",
        decision=KEEP,
        subject=(V2_ROOT + "memory/cadence.py", V2_ROOT + "memory/instrument.py",
                 V2_ROOT + "verify/hermetic.py"),
        reason="THE COLUMN. `edit_allowed` decides whether a write is denied; `stop_block`/`preflight` "
               "decide whether a turn may close. This is the only BEHAVIOURAL exercise those decision "
               "functions have, and a hollow port of any of them disables the column while every gate "
               "stays green. Retiring it would remove the single test standing between this repo and "
               "that failure — the most dangerous act available in this increment, and the direction "
               "doc's plan contained it.",
        obligation="pin the oracle's DECISIONS over the 7-function matrix as module data (captured "
                   "while the ancestor is still reachable, from a run that was green at capture "
                   "time), then delete the extraction and compare v3 against the pin",
        discharged=False,
    ),
    "v3/verify/session_memory_parity.py": Row(
        gate="session_memory_parity",
        decision=KEEP,
        subject=(V2_ROOT + "memory/precompact.py", V2_ROOT + "memory/rehydrate.py"),
        reason="The only exercise of `precompact`/`rehydrate` over their fixture matrix. It compares "
               "derived FACT-SETS rather than output — which is exactly why the matrix survives "
               "translation and is worth pinning: the facts (which increment is open, which RTM "
               "verdicts, whether the bytes landed) are language-independent, so the pin stays "
               "meaningful in a repo where the ancestor's Spanish prose is not even a memory.",
        obligation="pin the oracle's fact-sets over the 4-function matrix, then delete the extraction",
        discharged=False,
    ),
    "v3/verify/eval_gate_parity.py": Row(
        gate="eval_gate_parity",
        decision=KEEP,
        subject=(V2_ROOT + "verify/checks/eval_gate.py",),
        reason="`eval_gate` is a check KIND, not a registered gate — measured: it is absent from "
               "`build_registry`. This 13-case exit-code matrix is its ONLY suite-level coverage, so "
               "retiring the harness would leave a kind that products' lines execute with no test at "
               "all, and nothing would report the loss.",
        obligation="pin the 13 expected exit codes, then delete the two-body oracle extraction",
        discharged=False,
    ),
    "v3/verify/eval_floor_parity.py": Row(
        gate="eval_floor_parity",
        decision=KEEP,
        subject=(V2_ROOT + "verify/checks/eval_floor.py", V2_ROOT + "verify/checks/eval_gate.py"),
        reason="Same shape and same reason as `eval_gate_parity`: `eval_floor` is a kind with no "
               "registered gate, and this 14-case matrix is its only coverage.",
        obligation="pin the 14 expected exit codes, then delete the two-body oracle extraction",
        discharged=False,
    ),
    "v3/verify/live_run_parity.py": Row(
        gate="live_run_parity",
        decision=KEEP,
        subject=(V2_ROOT + "verify/checks/live_run.py", V2_ROOT + "verify/checks/eval_gate.py"),
        reason="Same shape and same reason again, for `live_run`: 16 cases (pin / DEFERRED / "
               "PROPOSING), and no other exercise of the kind exists.",
        obligation="pin the 16 expected exit codes, then delete the two-body oracle extraction",
        discharged=False,
    ),

    # ---- keep · CUT: half the law is about the ancestor, half about the tree in front of us -------
    "v3/economy/census.py": Row(
        gate="economy_census",
        decision=KEEP,
        subject=(V2_ROOT + "memory/", V2_ROOT + "memory/metrics.py", V2_ROOT + "memory/journal.py",
                 V2_ROOT + "memory/precompact.py"),
        reason="Mixed, measured assertion by assertion. Its oracle half (every v2 memory module and "
               "economy function carries exactly one disposition; REPLACED/DROPPED/DEFERRED rows name "
               "real phrases at the oracle) dies with the ancestor. Its live half does not: A1 — no "
               "metered source reads a raw transcript, over `v3/economy/*.py`, `v3/memory/journal.py`, "
               "`v3/host/session.py`, `v3/host/runner.py`, `v3/control/budget.py` — is a standing law "
               "over the CURRENT tree, and A4 checks that declared PORTED/ALREADY paths exist on disk. "
               "Retiring the module drops both without a word.",
        obligation="cut A2·A3·A5·A6·A7 (the oracle half), keep A1 and A4 armed with their own red side",
        discharged=False,
    ),
    "v3/verify/migration_census.py": Row(
        gate="migration_census",
        decision=KEEP,
        subject=(V2_ROOT + "codegen/renderer.py",),
        reason="Mixed. The v2 build-action vocabulary it derives (B1·B3·B4) dies; B2 — when a MIGRATED "
               "factory declares a check kind, its executor module must exist — is a live law over "
               "`factories/*/stations/*.yml` and `v3/host/builds.py`, and B5 is the Lock #1 that keeps "
               "an empty YAML population from passing as agreement. Both travel with the package.",
        obligation="cut B1·B3·B4, keep B2 and B5 armed",
        discharged=False,
    ),
    "v3/verify/verb_census.py": Row(
        gate="verb_census",
        decision=KEEP,
        subject=(V2_ROOT + "cli.py",),
        reason="Mixed, and the most load-bearing of the three: C2..C6 classify every verb against the "
               "LIVE tracked tree, check that `HUMAN_VERB_DISPOSITION` uses a closed decision set, "
               "that dropped verbs name a replacement, and that every v3 claim resolves to an "
               "importable module and attribute. That is also where the seven unported human verbs are "
               "still owed — the disposition table is the only place that fact is written down. Only "
               "C1 (derive v2's verb surface) and C7 (its Lock on zero verbs parsed) need the "
               "ancestor.",
        obligation="cut C1·C7 and the `gate_census` import with them — which is also what discharges "
                   "`gate_census`'s own row",
        discharged=False,
    ),
}
