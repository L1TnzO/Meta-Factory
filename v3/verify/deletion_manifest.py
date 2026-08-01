#!/usr/bin/env python3
"""deletion_manifest — the manifest a human signs before `rm -rf src/metafactory/`.

    python3 -m v3.verify.deletion_manifest                             # the gate
    V3_DELETION_MANIFEST_SABOTAGE=1 python3 -m v3.verify.deletion_manifest   # red side; must ALSO exit 0

THE FAILURE THIS PREVENTS. INC-11 P5 deletes `src/metafactory/` (102 modules, ~13.8k LOC, plus 9
station YAMLs). The pins cannot notice a silent loss: `proof_sha` hashes check NAMES and EXIT CODES,
so anything v2 did that no pinned station exercises can vanish and every number stays identical.
`gate_census` answers this for v2's 23 gates, `migration_census` for the check kinds and build
actions, `verb_census` for the CLI verbs — each a slice of the surface. Nothing answers it for the
SUBSTRATE AS A WHOLE, and "we ported what we noticed" is precisely the shape of bug this repo keeps
re-finding.

THE ASYMMETRY THIS MODULE IS BUILT ON, and the whole point of it: the POPULATION is DERIVED, the
DISPOSITIONS are DECLARED. (1) is read via `git ls-tree` at the ORACLE COMMIT (never the working
tree — `v3.verify.gate_census._oracle`/`_show`'s own technique; v2 and v3 share a tree, so a claim
measured against uncommitted state measures whatever happened to be lying around). (2) is a
hand-maintained table, because a disposition is a HUMAN DECISION and must be written down, not
inferred — but the table is checked in BOTH directions against the population, so a file nobody wrote
a row for is `unaccounted` rather than silence, and a row naming a file that is not there is paperwork
for something imaginary.

FOUR DISPOSITIONS, resolved in this order:
  `ported`      a v3 module plausibly covers it — established by EVIDENCE (each row below was
                checked against the citing v3 module's own docstring or a structural correspondence,
                not name similarity), and the v3 target must actually be importable
                (`importlib.util.find_spec`) — an entry naming a module that does not exist is a LIE,
                the same law `verb_census` applies to `v3.cli` (node N-0088).
  `dropped`     declared dropped, WITH a non-empty reason — the six rows this table drops all quote
                `docs/spec/11-build-plan.md §4`'s own "Dropped" column.
  `must_move`   DATA v3 still needs that lives inside the doomed directory — exactly the META line's
                `stations/*.yml` — and it must name its destination path.
  `unaccounted` nothing above. THIS IS THE RED HERE, in the sense that it is the number the gate
                exists to report honestly, not to hide by padding the table. It is NOT a reason to
                exit non-zero (see GREEN LAW) — P5 is the increment that drives it to zero.

SEEDED from the known facts in this slot's own contract, each re-verified before being written (not
copied): the kernel-equivalents (`engine/*` -> `v3.kernel.*`, `verify/report.py` -> `v3.kernel.report`,
`spec/*` -> `v3.spec.*`, `_seed.py` -> `v3.seed_loader`); what this increment ported (`memory/cadence.py`,
`memory/instrument.py` PARTIAL, `verify/hermetic.py`, `memory/precompact.py`, `memory/rehydrate.py`,
`cli.py` PARTIAL); what `docs/spec/11-build-plan.md §4` drops (`column_parity`/`column_selftest` — "no
copies left to compare"); and the `stations/m*.yml` must-move. RESEARCHED beyond that seed by reading
each candidate v3 module's own docstring (most say "PORTED from v2's `<path>`" outright) or a directly
verified structural correspondence (`v3/graph/__init__.py`'s own module map for the graph slice,
`v3/economy/census.py`'s own module census for the memory package, `v3/verify/kinds.py`'s documented
"same argv, head segment swapped" port rule for the 21 check executors it names). Where none of that
held, the row is simply ABSENT — `doc_slice.py`, `gate_wrap.py`, `toolchain_run.py`, the whole
navigation/economy corner of `graph/` (`ingest.py`, `incremental.py`, `repomap.py`, `billing.py`,
`pricing.py`, `affected*.py`, `graph/cli.py` — `v3/graph/__init__.py` names them OUT OF SCOPE itself),
and the FSK/ASF-only check kinds (`agent_shadow`, `blast_radius`, `boundary_survives`, `bus_bounded`,
`clean_runner`, `column_full`, `command_runs`, `products_rederive`, `rtm_rederive`, `rtm_tree`,
`scenario_corpus`) are UNACCOUNTED, honestly, because no v3 module yet claims them.

GREEN LAW: exit 0 iff (a) the population is non-empty — a manifest over nothing is red, never
vacuously green (Lock #1); (b) every `ported` row's v3 target resolves; (c) every `dropped` row
carries a non-empty reason; (d) every `must_move` row names a destination; (e) every row's KEY is
itself a real member of the derived population — a row for a file that does not exist is the mirror
failure of an unaccounted file, and the same law catches both. `unaccounted > 0` is COUNTED, reported
prominently, and is **not** by itself a reason to go red — P5 is what drives it to zero; a gate that
reddened for work not yet done would be a progress bar wearing a gate's clothes.

RED SIDE plants its three perturbations on REAL, currently-unaccounted population members (so the
"row without a population match" law from (e) never fires as a confound — only the ONE defect class
under test does): (i) a `ported` row naming a v3 module that cannot be imported; (ii) a `dropped` row
with an empty reason; (iii) a `must_move` row with no destination. All three are fed through the exact
`check()` the green run uses. Exit 0 only if ALL are caught.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from ..kernel.report import Verdict

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_ORACLE_REF = _V3 / "oracle_ref.json"
_V2_SRC = "src/metafactory"

PORTED, DROPPED, MUST_MOVE = "ported", "dropped", "must_move"

#: v2 path (relative to `src/metafactory/`) -> (disposition, reason/target). The ONE hand-typed thing
#: in this module (see the module docstring for why) — checked, never trusted, against the population
#: derived below and against real importability for every `ported` row.
DISPOSITIONS: dict[str, tuple[str, str]] = {
    # ── kernel-equivalents (INC-1/INC-4, ADR-031) ───────────────────────────────────────────────
    "engine/gate.py": (PORTED, "v3.kernel.gate"),
    "engine/sequence.py": (PORTED, "v3.kernel.sequence"),
    "engine/station.py": (PORTED, "v3.kernel.station"),
    # RunContext + the station loop itself land together, as the "inversion" (§10.0/5bis) rewrote
    # interception into abstention — same job (own the sequence, decide `may_run`), new mechanism.
    "engine/runner.py": (PORTED, "v3.host.runner"),
    "engine/run_context.py": (PORTED, "v3.host.runner"),        # class RunContext lives here now
    "verify/report.py": (PORTED, "v3.kernel.report"),
    "spec/__init__.py": (PORTED, "v3.spec"),
    "spec/cli.py": (PORTED, "v3.spec.cli"),
    "spec/design.py": (PORTED, "v3.spec.design"),
    "spec/loader.py": (PORTED, "v3.spec.loader"),
    "spec/model.py": (PORTED, "v3.spec.model"),
    "spec/primitives.py": (PORTED, "v3.spec.primitives"),
    "spec/validator.py": (PORTED, "v3.spec.validator"),
    "_seed.py": (PORTED, "v3.seed_loader"),

    # ── ported THIS increment (V3-INC11) ────────────────────────────────────────────────────────
    "cli.py": (PORTED, "v3.cli"),                                # PARTIAL: 6 of 38 verbs
    "memory/cadence.py": (PORTED, "v3.control.cadence"),
    "memory/instrument.py": (PORTED, "v3.control.instrument"),   # PARTIAL: thrashing_rollup dropped
    "memory/precompact.py": (PORTED, "v3.memory.precompact"),    # PARTIAL: read half not reproduced
    "memory/rehydrate.py": (PORTED, "v3.memory.rehydrate"),      # PARTIAL: "preserved live state" not reproduced
    "verify/hermetic.py": (PORTED, "v3.verify.hermetic"),

    # ── dropped — both rows quote `docs/spec/11-build-plan.md §4`'s own "Dropped" column ─────────
    "verify/checks/column_parity.py": (DROPPED,
        "build-plan §4 Dropped: 'column_parity, column_selftest (no copies left to compare)' — "
        "§11.4: under composition the column exists once, so a parity check between copies has "
        "nothing left to compare"),
    "verify/checks/column_selftest.py": (DROPPED,
        "build-plan §4 Dropped: 'column_parity, column_selftest (no copies left to compare)' — "
        "same retirement clause as column_parity"),

    # ── must_move: the META line's own station DATA, still needed after the delete (docs/spec/20 §4) ──
    "stations/m00.yml": (MUST_MOVE, "stations/m00.yml"),
    "stations/m01.yml": (MUST_MOVE, "stations/m01.yml"),
    "stations/m02.yml": (MUST_MOVE, "stations/m02.yml"),
    "stations/m03.yml": (MUST_MOVE, "stations/m03.yml"),
    "stations/m04.yml": (MUST_MOVE, "stations/m04.yml"),
    "stations/m05.yml": (MUST_MOVE, "stations/m05.yml"),
    "stations/m06.yml": (MUST_MOVE, "stations/m06.yml"),
    "stations/m07.yml": (MUST_MOVE, "stations/m07.yml"),
    "stations/m08.yml": (MUST_MOVE, "stations/m08.yml"),

    # ── agent/column vocabulary + delegation law (ADR-018/020), verified by direct structural
    # correspondence (same set names, same `scope_for`/`column_for` shape; `v3.plan` itself cites
    # `v3.delegation.slot.problems` as "v3's ALREADY-PORTED equivalent" of v2's `manifest_problems`) ──
    "agent_roles.py": (PORTED, "v3.control.agent_roles"),
    "column_scope.py": (PORTED, "v3.control.column"),
    "delegation.py": (PORTED, "v3.delegation.slot"),
    "docs_manifest.py": (PORTED, "v3.memory.docs_manifest"),
    "plan.py": (PORTED, "v3.plan"),

    # ── the code-graph slice — `v3/graph/__init__.py`'s OWN module map (V3-INC4-GRAPH-SLICE +
    # V3-INC5-MEMORY-DOCS Fase 4); the same file names the navigation/economy corner OUT OF SCOPE ──
    "graph/build.py": (PORTED, "v3.graph.build"),
    "graph/doc_graph.py": (PORTED, "v3.graph.doc_graph"),
    "graph/model.py": (PORTED, "v3.graph.model"),
    "graph/pbt_properties.py": (PORTED, "v3.graph.pbt_properties"),  # SCOPE CUT: only P2 (serde), not P1
    "graph/python_index.py": (PORTED, "v3.graph.python_index"),
    "graph/quality.py": (PORTED, "v3.graph.quality"),

    # ── the economy surface (INC-6) — `v3/economy/census.py`'s OWN module census over v2's memory
    # package; `cadence`/`instrument`/`precompact`/`rehydrate` are re-verified above as PORTED since
    # (unlike that census's own snapshot) they have since landed under `v3.control`/`v3.memory` ──
    "memory/journal.py": (PORTED, "v3.memory.journal"),
    "memory/metrics.py": (PORTED, "v3.economy.ledger"),    # PARTIAL: 6 transcript readers dropped ("the transcript parser")
    "memory/projection.py": (PORTED, "v3.memory.projection"),
    "verify/outcome.py": (PORTED, "v3.economy.outcome"),   # rewritten: 3-shape re-derivation, not v2's bare number

    # ── measurement + gate merged into ONE v3 file apiece ───────────────────────────────────────
    "verify/benchmark.py": (PORTED, "v3.verify.benchmark"),
    "verify/checks/benchmark_gate.py": (PORTED, "v3.verify.benchmark"),
    "verify/dial.py": (PORTED, "v3.verify.dial"),
    "verify/checks/dial_gate.py": (PORTED, "v3.verify.dial"),

    # ── the check-kind vocabulary + argv resolution (D-3) ───────────────────────────────────────
    "verify/checks/registry.py": (PORTED, "v3.verify.kinds"),
    "verify/checks/kind_hygiene.py": (PORTED, "v3.verify.checks.kind_hygiene"),

    # ── check executors — each v3 module's own docstring says "PORTED from v2's `<this path>`" ──
    "verify/checks/artifact_contains.py": (PORTED, "v3.verify.checks.artifact_contains"),
    "verify/checks/codegen_freeze.py": (PORTED, "v3.verify.checks.codegen_freeze"),
    "verify/checks/declared_deferred.py": (PORTED, "v3.verify.checks.deferred"),
    "verify/checks/design_eval.py": (PORTED, "v3.verify.checks.design_eval"),
    "verify/checks/docs_check.py": (PORTED, "v3.verify.checks.docs_check"),
    "verify/checks/eval_floor.py": (PORTED, "v3.verify.checks.eval_floor"),
    "verify/checks/eval_gate.py": (PORTED, "v3.verify.checks.eval_gate"),
    "verify/checks/evidence_liveness.py": (PORTED, "v3.verify.checks.evidence_liveness"),
    "verify/checks/generality_parity.py": (PORTED, "v3.verify.checks.generality"),
    "verify/checks/infra_up.py": (PORTED, "v3.verify.checks.infra_up"),
    "verify/checks/least_priv.py": (PORTED, "v3.verify.composition"),
    "verify/checks/live_run.py": (PORTED, "v3.verify.checks.live_run"),
    "verify/checks/mcp_tools.py": (PORTED, "v3.verify.checks.mcp_tools"),
    "verify/checks/pbt_gate.py": (PORTED, "v3.verify.checks.pbt"),
    "verify/checks/plan_gate.py": (PORTED, "v3.verify.checks.plan"),
    "verify/checks/product_env.py": (PORTED, "v3.verify.checks.product_env"),
    "verify/checks/quality_gate.py": (PORTED, "v3.verify.checks.quality"),
    "verify/checks/role_hygiene.py": (PORTED, "v3.verify.checks.roles"),
    "verify/checks/security_scan.py": (PORTED, "v3.verify.checks.security"),
    "verify/checks/slot_footprint.py": (PORTED, "v3.verify.slot_footprint"),
    "verify/checks/state_fidelity.py": (PORTED, "v3.verify.checks.state_fidelity"),
    "verify/checks/state_snapshot.py": (PORTED, "v3.verify.checks.state_snapshot"),

    # ── build actions: v2's `apply_builds` -> v3.host.builds; `v3.verify.migration_census` tracks
    # the per-action split (4 of 11 handled today) — this row is the FILE-level fact it rests on ──
    "codegen/renderer.py": (PORTED, "v3.host.builds"),   # PARTIAL: 4 of 11 build actions handled

    # ── P5 GROUP A — package markers, CONTENT read at the oracle commit (not assumed empty). Each
    # re-export was traced to its origin submodule; a `git grep` at the oracle ref confirms no v2 file
    # ever imported these names via the PACKAGE (`from .<pkg> import <name>`) rather than the
    # submodule directly — except `codegen/__init__.py`'s `apply_builds`, consumed that way by
    # `engine/runner.py`, and covered by the `codegen/renderer.py` row above. So none of these eight
    # was independently load-bearing; each is dropped as pure package-layout boilerplate ────────────
    "__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: only `__all__ = [\"__version__\"]` plus a version string — no "
        "functional symbol"),
    "__main__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: `from .cli import main; raise SystemExit(main())` — v3.cli.py "
        "carries this exact `if __name__ == \"__main__\":` block itself, so `python -m v3.cli` needs "
        "no package-level forwarder"),
    "codegen/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: re-exports `apply_builds`, `render_text` from `.renderer` — "
        "both confirmed present in `v3.host.builds` (the codegen/renderer.py row above)"),
    "engine/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: re-exports RunContext/Station/Sequence/load_sequence/"
        "GateResult/open_gate/StationRun/run_station from its 5 submodules, each already PORTED above "
        "(engine/gate.py, engine/sequence.py, engine/station.py, engine/runner.py, "
        "engine/run_context.py). NOTED, not hidden: 5 of those 8 identifiers (Sequence, load_sequence, "
        "GateResult, open_gate, StationRun) do not survive under those exact names anywhere in v3 — "
        "`v3.kernel.gate.may_run` replaces `open_gate`/`GateResult` with a `(bool, blockers)` tuple, "
        "`v3.kernel.sequence` replaces the `Sequence` class/`load_sequence` with bare functions "
        "(`predecessors`/`active_in`/`order_stations`), `StationOutcome` replaces `StationRun` — a "
        "redesign already recorded on the submodule rows above, not something this marker adds or "
        "hides on its own"),
    "graph/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: re-exports Edge/EdgeKind/FileFragment/Graph/Node/NodeKind from "
        "`.model` — all 6 confirmed present in `v3.graph.model` (the graph/model.py row above)"),
    "memory/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: `from . import journal; __all__ = [\"journal\"]` — covered by "
        "the memory/journal.py row above"),
    "verify/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: re-exports `Verdict`, `format_verdict` from `.report` — "
        "`Verdict` is `v3.kernel.report.Verdict` (the verify/report.py row above); `format_verdict` "
        "has no standalone v3 counterpart by that name, folded instead into `Verdict.render()`/"
        "`.emit()` per that module's own docstring ('the rendering is kept ... the bound moves from "
        "please-keep-it-short to a function that cannot emit more than MAX_LINES')"),
    "verify/checks/__init__.py": (DROPPED,
        "package marker / re-export shim for v2's own package layout; v3 has its own and needs no "
        "counterpart. Content checked: re-exports `KINDS`, `resolve_check` from `.registry` — both "
        "confirmed present in `v3.verify.kinds` (the verify/checks/registry.py row above)"),

    # ── P5 GROUP B — executors for a check kind that ONLY the META line (m00..m08, factory emission
    # M0-M8) declares; v3 does not run that line at cutover. The line's DATA is `must_move`; its
    # executors are deliberately NOT ported — porting them would mean re-basing copy-comparison checks
    # onto composition (spec 10 §9), which is a REDESIGN and spec 11 §5 forbids improving anything
    # before cutover. Declared loss, node N-0098. Where named, the pointer names a v3 module over the
    # same PROPERTY — NOT evidence the meta-line check itself survives (the name-similarity trap this
    # table already refuses once for column_parity/column_selftest) ───────────────────────────────
    "verify/checks/agent_shadow.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4)"),
    "verify/checks/boundary_survives.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4) "
        "-> v3.verify.import_boundary covers a SIMILAR boundary property, not evidence this check "
        "survives"),
    "verify/checks/bus_bounded.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4) "
        "-> v3.kernel.report is the bounded verdict bus itself, not evidence this check survives"),
    "verify/checks/clean_runner.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4)"),
    "verify/checks/column_full.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4) "
        "-> v3.verify.column_live covers a SIMILAR column property, not evidence this check survives"),
    "verify/checks/command_runs.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4)"),
    "verify/checks/products_rederive.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4) "
        "-> v3.verify.rederive covers a SIMILAR re-derivation property, not evidence this check "
        "survives"),
    "verify/checks/rtm_rederive.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4) "
        "-> v3.memory.projection covers a SIMILAR RTM-from-proofs property, not evidence this check "
        "survives"),
    "verify/checks/rtm_tree.py": (DROPPED,
        "executor for a check kind that ONLY the META line (m00..m08, factory emission M0-M8) "
        "declares; v3 does not run that line at cutover. Declared loss, node N-0098 (build-plan §4). "
        "Reuses v2's own verify/rtm.py (dropped below, same group) as its single source "
        "-> v3.memory.projection covers a SIMILAR RTM-from-proofs property, not evidence this check "
        "survives"),

    # ── P5 GROUP C — the code-graph navigation/economy corner: ADR-019 §5 put this out of scope for
    # v3, and `v3/graph/__init__.py`'s OWN docstring names these files OUT of scope by filename ──────
    "graph/affected.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),
    "graph/affected_report.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names `affected*.py` OUT of "
        "scope in its own module map ('the navigation/economy surface ... None of those is imported "
        "from here')"),
    "graph/billing.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),
    "graph/cli.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here'). "
        "Additionally backs `meta graph`, an unported HUMAN verb (verb_census)"),
    "graph/incremental.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),
    "graph/ingest.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),
    "graph/pricing.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),
    "graph/repomap.py": (DROPPED,
        "ADR-019 §5 put this out of scope for v3; `v3/graph/__init__.py` names it OUT of scope in its "
        "own module map ('the navigation/economy surface ... None of those is imported from here')"),

    # ── P5 GROUP D — one decision each ──────────────────────────────────────────────────────────────
    "doc_slice.py": (DROPPED, "backs `meta doc slice`, an unported human verb (verb_census)"),
    "gate_wrap.py": (DROPPED,
        "VERIFIED at the oracle commit: wraps a VERBOSE subprocess so a caller sees exactly ONE "
        "VERDICT line, with the full combined stdout+stderr preserved on disk (CONTEXT-ECONOMY §2). "
        "Its only caller in v2 was `toolchain_run.py` (dropped below, same group) — no other v2 file "
        "imports it, and no v3 module wraps an ad-hoc verbose subprocess this way (`v3.host.runner."
        "run_check` captures a check's output but never logs or bounds it into a VERDICT line; "
        "grepped the whole v3 tree for `log_dir`/`gate_logs` — nothing)"),
    "toolchain_run.py": (DROPPED,
        "backs `meta jdk-run`; the JDK resolution that actually load-bears lives in "
        "`tools/toolchain.sh`, which is NOT part of the substrate and survives (node N-0121)"),
    "memory/overlap.py": (DROPPED,
        "the three-memory overlap observer; explicitly an observer, never a gate"),
    "codegen/delegation_brain.py": (DROPPED,
        "dead: the delegation-brain swap it existed for was abandoned"),
    "verify/cost_report.py": (DROPPED,
        "superseded by v3's TYPED economy (`v3.economy.{ledger,meter,outcome}`), which INC-6 built "
        "rather than ported"),
    "verify/mutation.py": (DROPPED,
        "VERIFIED at the oracle commit: a general-purpose stdlib mutation-testing instrument (E4/H-3, "
        "COUNCIL-360 §6.4.5) — seeds one operator mutation at a time into a caller-named target file, "
        "re-runs a caller-supplied gate command, classifies KILLED/ESCAPED by exit code, reports an "
        "escape rate. No v3 module offers this as a reusable, general instrument: `v3.verify."
        "spec_parity` has a SIMILARLY-NAMED 'mutant' concept, but only as a fixed CI fixture over the "
        "spec validator's own rule inventory, not a callable campaign tool against an arbitrary file — "
        "the same name-similarity trap this table already refuses once"),
    "verify/rtm.py": (DROPPED,
        "VERIFIED: `v3.memory.projection.rtm_statuses` re-derives only a SUMMARY — per-factory "
        "(satisfied, total) counts, checking that each requirement's `satisfied_by` stations have a "
        "recomputing-green proof. v2's `verify/rtm.py` builds the full evidence TREE (req -> "
        "capability -> station -> proof -> artifact) and additionally checks (a) the requirement's "
        "declared capability is a REAL capability (the L5->L1 edge) and (b) every artifact that "
        "capability declares EXISTS on disk (the C4 'artifact leaf', which catches STALE EVIDENCE: a "
        "proof that says passed while the artifact it certifies vanished). Neither (a) nor (b) is "
        "reproduced anywhere in v3 today — a real gap, not a rename, so this stays dropped rather than "
        "ported"),
    "verify/verdict.py": (DROPPED,
        "VERIFIED: NOT the same concept as `v3.kernel.report`'s bounded CLI verdict bus despite the "
        "shared word — this is the Fase-G promotion-domination law (`SELF-IMPROVEMENT.md §4`): "
        "re-derive a factory's (line_green, rtm_satisfied, rtm_total) on a throwaway clone and refuse "
        "a `meta promote` that would lower any downstream factory's verdict. Confirmed unported by "
        "v3.cli's OWN docstring: \"`promote` needs a blast-radius sweep + a scenario corpus + a "
        "baseline store that v3 does not have, so it REFUSES rather than pretending\""),
    "verify/checks/blast_radius.py": (DROPPED,
        "VERIFIED: `v3.delegation.footprint` (the git-observed SLOT-FOOTPRINT sweep, allow_globs vs. "
        "what git saw changed) and `v3.control.hooks` (in-process PreToolUse/PreCompact defensive "
        "hooks) are a same-word-different-concept, not this gate — read both, neither implements "
        "`meta promote`'s downstream-factory domination sweep. This is the gate wired to "
        "`verify/verdict.py` (dropped above, same group; see its entry for the direct v3.cli "
        "confirmation) via `from .. import verdict as V`; it is unported for the identical reason"),
    "verify/checks/scenario_corpus.py": (DROPPED,
        "FSK/ASF-only check kind that no MIGRATED factory line declares (migration_census); not "
        "exercised by any pinned station"),
}

#: Real, currently-UNACCOUNTED population members, used only by the sabotage — see the module
#: docstring's RED SIDE paragraph for why real (not synthetic) keys are chosen.
_SABOTAGE_PORTED_PATH = "verify/rtm.py"
_SABOTAGE_PORTED_TARGET = "v3.verify.checks.nonexistent_executor"
_SABOTAGE_DROPPED_PATH = "verify/verdict.py"
_SABOTAGE_MUST_MOVE_PATH = "memory/overlap.py"


def _oracle() -> dict:
    return json.loads(_ORACLE_REF.read_text(encoding="utf-8"))


def population(ref: str) -> list[str]:
    """Every `*.py` under `src/metafactory/` and every `*.yml` under `src/metafactory/stations/`, AT
    the oracle commit — via `git ls-tree`, never the working tree (the same law `gate_census._show`
    and `migration_census`'s oracle reads use, ADR-031 §2.1). Paths are relative to `src/metafactory/`,
    matching how the DISPOSITIONS table above spells its keys."""
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "--", _V2_SRC],
                         capture_output=True, text=True, cwd=_ROOT)
    if out.returncode != 0:
        raise FileNotFoundError(f"git ls-tree -r {ref} -- {_V2_SRC}: {out.stderr.strip()}")
    prefix = _V2_SRC + "/"
    found: list[str] = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        rel = line[len(prefix):]
        if rel.endswith(".py") or (rel.startswith("stations/") and rel.endswith(".yml")):
            found.append(rel)
    return sorted(found)


def _ref_binding_problems() -> list[str]:
    """The price of reading v2 at a commit rather than the working tree: prove it. A working-tree
    read would succeed at ANY ref; this one must fail at one that names no tree (same technique as
    `gate_census._ref_binding_problems`, `economy_census.ref_binding_problems`)."""
    bogus = "0" * 40
    try:
        population(bogus)
    except FileNotFoundError:
        return []
    return [f"{_V2_SRC} was readable at a nonexistent ref: the manifest is reading the working tree, "
            f"not a commit"]


def resolve(target: str) -> tuple[bool, str]:
    """The importability LAW a `ported` row must satisfy — `module[:attr]`, never executed, only
    resolved. Identical shape to `verb_census.resolve` (both close N-0088's family of bug: a claim
    that names something that is not there)."""
    module_part, _, attr_part = target.partition(":")
    if not module_part:
        return False, f"empty module in target {target!r}"
    try:
        spec = importlib.util.find_spec(module_part)
    except (ImportError, ValueError, ModuleNotFoundError, AttributeError, TypeError):
        spec = None
    if spec is None:
        return False, f"module {module_part!r} does not resolve"
    if attr_part:
        try:
            module = importlib.import_module(module_part)
        except Exception as exc:  # a module that resolves but explodes on import is still a lie
            return False, f"module {module_part!r} found but failed to import: {exc!r}"
        if not hasattr(module, attr_part):
            return False, f"module {module_part!r} has no attribute {attr_part!r}"
    return True, ""


def check(ref: str, *, extra: dict[str, tuple[str, str]] | None = None) -> tuple[list[str], dict]:
    """The law, shared by the green run and the sabotage. `extra` folds in synthetic rows (the
    sabotage's own perturbations) on top of the real table — never used by production callers."""
    problems: list[str] = []
    pop = population(ref)
    if not pop:
        problems.append(f"derived ZERO files from {_V2_SRC} @ {ref[:8]}: an empty population is "
                        f"never vacuously true (Lock #1)")
    problems.extend(_ref_binding_problems())

    table = dict(DISPOSITIONS)
    if extra:
        table.update(extra)
    pop_set = set(pop)

    # The mirror failure of `unaccounted`: a row naming a file that is not (or no longer) there.
    for path in sorted(set(table) - pop_set):
        problems.append(f"{path}: carries a disposition but is not part of the derived v2 "
                        f"population @ {ref[:8]} — paperwork for something imaginary")

    counts = {"population": len(pop), PORTED: 0, DROPPED: 0, MUST_MOVE: 0, "unaccounted": 0}
    for path in pop:
        row = table.get(path)
        if row is None:
            counts["unaccounted"] += 1
            continue
        disposition, value = row
        if disposition == PORTED:
            counts[PORTED] += 1
            ok, why = resolve(value)
            if not ok:
                problems.append(f"{path}: declared ported to {value!r}, which does not resolve: {why}")
        elif disposition == DROPPED:
            counts[DROPPED] += 1
            if not value.strip():
                problems.append(f"{path}: declared dropped with an EMPTY reason — a drop with no "
                                f"reason is a deletion nobody wrote down")
        elif disposition == MUST_MOVE:
            counts[MUST_MOVE] += 1
            if not value.strip():
                problems.append(f"{path}: declared must_move with no destination path")
        else:
            problems.append(f"{path}: unknown disposition {disposition!r}")

    return problems, counts


def _run_sabotage(ref: str) -> int:
    control, _ = check(ref)
    if control:
        return Verdict("v3-deletion-manifest (SABOTAGE)", 1,
                       f"the manifest is not clean, so no catch is attributable: {control[0]}").emit()

    witnesses: list[tuple[str, bool]] = []

    problems, _ = check(ref, extra={_SABOTAGE_PORTED_PATH: (PORTED, _SABOTAGE_PORTED_TARGET)})
    witnesses.append(("unresolvable ported target caught",
                      any(_SABOTAGE_PORTED_PATH in p and "does not resolve" in p for p in problems)))

    problems, _ = check(ref, extra={_SABOTAGE_DROPPED_PATH: (DROPPED, "")})
    witnesses.append(("empty dropped reason caught",
                      any(_SABOTAGE_DROPPED_PATH in p and "EMPTY reason" in p for p in problems)))

    problems, _ = check(ref, extra={_SABOTAGE_MUST_MOVE_PATH: (MUST_MOVE, "")})
    witnesses.append(("empty must_move destination caught",
                      any(_SABOTAGE_MUST_MOVE_PATH in p and "no destination path" in p
                          for p in problems)))

    caught = sum(1 for _, ok in witnesses if ok)
    if caught == len(witnesses):
        return Verdict("v3-deletion-manifest (SABOTAGE)", 0,
                       f"{caught}/{len(witnesses)} planted perturbations caught").emit()
    missed = ", ".join(name for name, ok in witnesses if not ok)
    return Verdict("v3-deletion-manifest (SABOTAGE)", 1,
                   f"GATE DECORATIVO: only {caught}/{len(witnesses)} planted perturbations caught; "
                   f"missed: {missed}").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-deletion-manifest", 2, f"takes no arguments; got {argv!r}").emit()
    ref = _oracle()["oracle_ref"]

    if os.environ.get("V3_DELETION_MANIFEST_SABOTAGE") == "1":
        return _run_sabotage(ref)

    problems, counts = check(ref)
    if problems:
        return Verdict("v3-deletion-manifest", 1,
                       f"{len(problems)} problem(s) in the deletion manifest @ {ref[:8]}",
                       counts=counts, failures=tuple(problems),
                       next_action="unaccounted alone is not a defect — P5 drives it to zero before "
                                   "the delete; anything else means a row is a lie").emit()
    return Verdict("v3-deletion-manifest", 0,
                   f"{counts['population']} v2 files/stations derived @ {ref[:8]}: "
                   f"{counts[PORTED]} ported, {counts[DROPPED]} dropped, {counts[MUST_MOVE]} "
                   f"must-move; UNACCOUNTED {counts['unaccounted']} — P5 must drive this to zero "
                   f"before `src/metafactory/` may be deleted", counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
