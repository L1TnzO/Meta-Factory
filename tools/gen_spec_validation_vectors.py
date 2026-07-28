#!/usr/bin/env python3
"""gen_spec_validation_vectors — the ORACLE generator for v3's spec model/loader/validator port
(V3-INC4, Phase 4).

v2-side (`tools/`, free to import `metafactory` — this script lives OUTSIDE the boundary v3 must
never cross, `v3.verify.import_boundary`). It materialises `v3/oracle_ref.json`'s pinned commit
OUTSIDE the repo (`git archive <ref> | tar -x`, into a `tempfile.mkdtemp()` — never `git worktree`,
which mutates `.git/` and would leave state the slot-footprint sweep sees as a stray change), then
calls v2's REAL `metafactory.spec.{load_spec,validate}` over two kinds of vectors:

ACCEPT vectors — every committed factory spec (`factories/*/factory.spec.yml`, 5 of them), loaded and
validated by v2's own code. All 5 are expected `valid` (measured, not assumed — see `decision` below).
Each accept vector embeds the RAW spec YAML text (read AT THE REF) so the ported gate can feed the
exact same bytes to v3's loader/validator independently, plus a STRUCTURAL DIGEST of the loaded model
(station ids in order, per-station depends_on/tier/activation/status and check counts, capability and
requirement ids) — enough that a port which quietly drops a field is caught rather than nodded through.

REJECT vectors — the part that matters (a validator that accepts everything passes the accept side
perfectly). Every validation RULE actually implemented in v2's `validator.py` is enumerated below as
one entry in `RULE_INVENTORY`; for each one this script builds exactly one MUTANT: a REAL committed
spec (`dummy` or `agent-systems-factory`, chosen because it already carries the field the rule needs),
minimally mutated at the PARSED-DICT level (never hand-edited YAML text) to violate exactly that rule,
then re-serialised and run through v2's real `load_spec`+`validate`. v2's decision MUST be `invalid`;
if a mutation is unexpectedly accepted, that is a finding about v2 — recorded in `accepted_unexpectedly`,
never silently dropped or "fixed" by picking a different mutation. Rule granularity is ONE PER DISTINCT
`p.append(...)`/return statement in `validator.py`; where the SAME statement fires for more than one
kind of entity (station vs capability vs proof_check vs machinery section — `_status_problem`,
`_deferral_problem`, `_tech_primitive_problem` are each invoked at 2-4 call sites), it is counted and
mutated ONCE (the code path is identical; the entity is incidental) — this is recorded in each rule's
`applies_to` field so the choice is visible, not hidden.

OFFENDING IDENTIFIER. Rather than predict textually what v2's message will say (risky — e.g. a cycle's
`hit` node depends on DFS iteration order over the mutated graph), each mutation declares a small list
of CANDIDATE identifier substrings it expects to appear; after running v2's real validator, the script
searches the returned problems for the first candidate that actually appears and records THAT as
`offending_identifier`. If none of a mutation's candidates appear in a non-empty problem list, that is a
mutation-design bug (the intended rule did not fire the way this script predicted) and generation
ABORTS loudly rather than recording a wrong or empty identifier.

NORMALISATION. None needed here (unlike `gen_check_argv_vectors.py`): nothing in the spec model/loader/
validator's output depends on `sys.executable` or the materialised tree's absolute path.

Usage:  python3 tools/gen_spec_validation_vectors.py   # writes docs/spec/fixtures/spec-validation-vectors.json
Prints counts only (context economy, I-7) — never the vectors themselves.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_ORACLE_REF_FILE = _ROOT / "v3" / "oracle_ref.json"
_FIXTURE = _ROOT / "docs" / "spec" / "fixtures" / "spec-validation-vectors.json"

_ACCEPT_GLOB = "factories/*/factory.spec.yml"
_DUMMY = "factories/dummy/factory.spec.yml"
_ASF = "factories/agent-systems-factory/factory.spec.yml"


def _oracle() -> dict:
    return json.loads(_ORACLE_REF_FILE.read_text(encoding="utf-8"))


def _materialize(ref: str) -> Path:
    """`git archive <ref> | tar -x` into a fresh tempdir OUTSIDE the repo (LAW #1). Never `git
    worktree` (it mutates `.git/`, leaving state the slot-footprint sweep would see as a stray
    change)."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        raise ValueError(f"oracle_ref does not look like a commit sha: {ref!r}")
    tmp = Path(tempfile.mkdtemp(prefix="mf-spec-oracle-"))
    archive = subprocess.Popen(["git", "archive", ref], stdout=subprocess.PIPE, cwd=_ROOT)
    tar = subprocess.run(["tar", "-x", "-C", str(tmp)], stdin=archive.stdout)
    archive.stdout.close()
    rc_archive = archive.wait()
    if rc_archive != 0 or tar.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"materialising {ref} failed (git archive={rc_archive}, tar={tar.returncode})")
    return tmp


# ── the rule inventory: every distinct refusal branch in v2's validator.py ──────────────────────────
# (family, applies_to) is documentary; `mutate` operates on a deep-copied dict parsed from `base`'s
# real YAML; `candidates` are identifier substrings the generator searches v2's real problems for
# (see OFFENDING IDENTIFIER above) — never hand-predicted message text.
Mutation = dict


def _mut(rule_id: str, family: str, base: str, applies_to: str, description: str,
         mutate: Callable[[dict], None], candidates: list[str]) -> Mutation:
    return {"rule_id": rule_id, "family": family, "base": base, "applies_to": applies_to,
            "description": description, "mutate": mutate, "candidates": candidates}


def _dup_station(d: dict) -> None:
    d["domain"]["station_sequence"].append({"id": "s00", "name": "dup probe", "activation": "always"})


def _dup_capability(d: dict) -> None:
    d["domain"]["capabilities"].append(copy.deepcopy(d["domain"]["capabilities"][0]))


def _dup_requirement(d: dict) -> None:
    d["requirements"]["functional"].append(copy.deepcopy(d["requirements"]["functional"][0]))


def _add_inactive_dep_target(d: dict) -> None:
    d["domain"]["station_sequence"].append(
        {"id": "s_inactive_probe", "name": "probe", "activation": "off"})
    d["domain"]["station_sequence"][1]["depends_on"] = ["s00", "s_inactive_probe"]


MUTATIONS: list[Mutation] = [
    # ── schema (validate_schema) ─────────────────────────────────────────────────────────────────
    _mut("schema.name_required", "schema", "dummy", "factory.name",
         "factory.name set to empty string",
         lambda d: d["factory"].__setitem__("name", ""),
         ["factory.name"]),
    _mut("schema.slug_pattern", "schema", "dummy", "factory.slug",
         "factory.slug set to a value violating ^[a-z][a-z0-9-]*$",
         lambda d: d["factory"].__setitem__("slug", "Dummy!"),
         ["Dummy!"]),
    _mut("schema.produces_required", "schema", "dummy", "domain.produces",
         "domain.produces set to empty string",
         lambda d: d["domain"].__setitem__("produces", ""),
         ["domain.produces"]),
    _mut("schema.stations_nonempty", "schema", "dummy", "domain.station_sequence",
         "domain.station_sequence emptied",
         lambda d: d["domain"].__setitem__("station_sequence", []),
         ["domain.station_sequence"]),
    _mut("schema.station_id_required", "schema", "dummy", "domain.station_sequence[0].id",
         "first station's id set to empty string",
         lambda d: d["domain"]["station_sequence"][0].__setitem__("id", ""),
         ["a station has no id", "domain.station_sequence"]),
    _mut("schema.station_id_unique", "schema", "dummy", "domain.station_sequence",
         "a new station appended with id 's00', duplicating the first station's id",
         _dup_station, ["s00"]),

    # ── substrate (validate_substrate) ───────────────────────────────────────────────────────────
    _mut("substrate.column_required", "substrate", "dummy", "factory_substrate.anti_rubber_stamp_column",
         "anti_rubber_stamp_column set to false",
         lambda d: d["factory_substrate"].__setitem__("anti_rubber_stamp_column", False),
         ["anti_rubber_stamp_column"]),
    _mut("substrate.verdict_bus_max_lines", "substrate", "dummy", "factory_substrate.verdict_bus.max_lines",
         "verdict_bus.max_lines set to 0",
         lambda d: d["factory_substrate"]["verdict_bus"].__setitem__("max_lines", 0),
         ["verdict_bus.max_lines"]),

    # ── rtm (rtm_closure) ─────────────────────────────────────────────────────────────────────────
    _mut("rtm.requirements_nonempty", "rtm", "dummy", "requirements",
         "requirements.functional and .nonfunctional both emptied",
         lambda d: d.__setitem__("requirements", {"functional": [], "nonfunctional": []}),
         ["requirements"]),
    _mut("rtm.id_format", "rtm", "dummy", "requirements.functional[0].id",
         "first requirement's id changed to 'REQ-1' (violates REQ-<AREA>-NNN)",
         lambda d: d["requirements"]["functional"][0].__setitem__("id", "REQ-1"),
         ["REQ-1"]),
    _mut("rtm.id_unique", "rtm", "dummy", "requirements.functional",
         "the first requirement duplicated (same id REQ-F-001) and appended",
         _dup_requirement, ["REQ-F-001"]),
    _mut("rtm.satisfied_by_nonempty", "rtm", "dummy", "requirements.functional[0].satisfied_by",
         "first requirement's satisfied_by emptied",
         lambda d: d["requirements"]["functional"][0].__setitem__("satisfied_by", []),
         ["REQ-F-001"]),
    _mut("rtm.satisfied_by_active", "rtm", "dummy", "requirements.functional[0].satisfied_by",
         "first requirement's satisfied_by pointed at an unknown station id",
         lambda d: d["requirements"]["functional"][0].__setitem__("satisfied_by", ["zzz-unknown"]),
         ["zzz-unknown"]),

    # ── grammar_v2 · capabilities (_validate_capabilities) ───────────────────────────────────────
    _mut("grammar.capability_id_unique", "grammar_v2", "dummy", "domain.capabilities",
         "the first capability duplicated (same id) and appended",
         _dup_capability, ["invariant_marker"]),
    _mut("grammar.status_enum", "grammar_v2", "dummy", "domain.capabilities[0].status "
         "(shared `_status_problem`, also called for station/proof_check status)",
         "first capability's status set to a value outside STATUS_VALUES",
         lambda d: d["domain"]["capabilities"][0].__setitem__("status", "not-a-real-status"),
         ["not-a-real-status"]),
    _mut("grammar.deferral_trigger_required", "grammar_v2", "asf", "station[s0].deferral "
         "(shared `_deferral_problem`, also called for capability/proof_check deferral)",
         "ASF station s0 (a real bare `declared-deferred`) given a deferral block missing `trigger`",
         lambda d: d["domain"]["station_sequence"][0].__setitem__(
             "deferral", {"since": "2026-07-28"}),
         ["station[s0]"]),
    _mut("grammar.deferral_since_format", "grammar_v2", "asf", "station[s0].deferral.since",
         "ASF station s0 given a deferral block with a non-date `since`",
         lambda d: d["domain"]["station_sequence"][0].__setitem__(
             "deferral", {"trigger": "x", "since": "notadate"}),
         ["station[s0]"]),
    _mut("grammar.deferral_strict_required", "grammar_v2", "asf", "station[s0] / "
         "proof_checks[spec_admission] under governance.deferral_tracking=strict",
         "top-level governance.deferral_tracking set to 'strict' (0 of 5 committed specs adopt "
         "it); ASF's real bare declared-deferred station s0 + its proof_check now need a deferral",
         lambda d: d.__setitem__("governance", {"deferral_tracking": "strict"}),
         ["station[s0]", "spec_admission"]),
    _mut("grammar.tech_requires_primitive", "grammar_v2", "dummy", "machinery.harness "
         "(shared `_tech_primitive_problem`, also called for capabilities)",
         "machinery.harness.primitive removed while .tech remains set",
         lambda d: d["machinery"]["harness"].__delitem__("primitive"),
         ["machinery.harness"]),
    _mut("grammar.primitive_format", "grammar_v2", "dummy", "machinery.harness.primitive",
         "machinery.harness.primitive changed to a value not matching DES-<n>",
         lambda d: d["machinery"]["harness"].__setitem__("primitive", "FOO-1"),
         ["FOO-1"]),
    _mut("grammar.capability_built_requires_proof", "grammar_v2", "dummy",
         "domain.capabilities[0] (status=built)",
         "first capability's proof cleared while status stays 'built'",
         lambda d: d["domain"]["capabilities"][0].__setitem__("proof", ""),
         ["invariant_marker"]),

    # ── grammar_v2 · stations (_validate_stations_v2) ────────────────────────────────────────────
    _mut("grammar.depends_on_self", "grammar_v2", "dummy", "domain.station_sequence[0].depends_on",
         "first station given depends_on pointing at itself",
         lambda d: d["domain"]["station_sequence"][0].__setitem__("depends_on", ["s00"]),
         ["s00"]),
    _mut("grammar.depends_on_known", "grammar_v2", "dummy", "domain.station_sequence[0].depends_on",
         "first station given depends_on pointing at an unknown station id",
         lambda d: d["domain"]["station_sequence"][0].__setitem__(
             "depends_on", ["nonexistent_station_zzz"]),
         ["nonexistent_station_zzz"]),
    _mut("grammar.depends_on_active", "grammar_v2", "dummy", "domain.station_sequence[1].depends_on",
         "a new inactive station appended; the 2nd station's depends_on extended to include it",
         _add_inactive_dep_target, ["s_inactive_probe"]),
    _mut("grammar.depends_on_acyclic", "grammar_v2", "dummy", "domain.station_sequence",
         "first station given depends_on -> s01, which already depends_on -> s00 (a 2-cycle)",
         lambda d: d["domain"]["station_sequence"][0].__setitem__("depends_on", ["s01"]),
         ["cycle detected"]),
    _mut("grammar.proof_check_runs_in_enum", "grammar_v2", "dummy",
         "domain.station_sequence[2].proof_checks[0].runs_in",
         "s02's proof_check runs_in changed to a value outside RUNS_IN_VALUES",
         lambda d: d["domain"]["station_sequence"][2]["proof_checks"][0].__setitem__(
             "runs_in", "bogus_env"),
         ["bogus_env"]),

    # ── grammar_v2 · requirements (_validate_requirements_v2) ────────────────────────────────────
    _mut("grammar.verified_by_no_phantom", "grammar_v2", "dummy",
         "requirements.functional[2].verified_by",
         "REQ-F-003's verified_by changed to an unknown proof_check name",
         lambda d: d["requirements"]["functional"][2].__setitem__(
             "verified_by", ["ghost_verifier_zzz"]),
         ["ghost_verifier_zzz"]),
    _mut("grammar.capability_ref_no_phantom", "grammar_v2", "dummy",
         "requirements.functional[0].capability",
         "REQ-F-001's capability changed to an unknown capability id",
         lambda d: d["requirements"]["functional"][0].__setitem__(
             "capability", "ghost_capability_zzz"),
         ["ghost_capability_zzz"]),

    # ── grammar_v2 · machinery surfaces (_emit_shape_problems / _named_items_problems /
    #    _validate_harness_surface) ───────────────────────────────────────────────────────────────
    _mut("grammar.machinery_emit_shape", "grammar_v2", "dummy", "machinery.infra.emit[0]",
         "first infra.emit entry's `dest` key removed",
         lambda d: d["machinery"]["infra"]["emit"][0].__delitem__("dest"),
         ["needs a dest"]),
    _mut("grammar.machinery_emit_content_string", "grammar_v2", "dummy", "machinery.infra.emit[0]",
         "first infra.emit entry's `content` set to a non-string",
         lambda d: d["machinery"]["infra"]["emit"][0].__setitem__("content", 123),
         ["content must be a string"]),
    _mut("grammar.machinery_emit_list", "grammar_v2", "dummy", "machinery.infra.emit",
         "machinery.infra.emit replaced with a non-list value (shared with machinery.mcp.emit)",
         lambda d: d["machinery"]["infra"].__setitem__("emit", "oops"),
         ["machinery.infra.emit"]),
    _mut("grammar.machinery_named_items", "grammar_v2", "dummy", "machinery.infra.services[0]",
         "first infra.services entry's `name` key removed (shared with machinery.mcp.tools)",
         lambda d: d["machinery"]["infra"]["services"][0].__delitem__("name"),
         ["machinery.infra.services[0]"]),
    _mut("grammar.machinery_named_items_list", "grammar_v2", "dummy", "machinery.infra.services",
         "machinery.infra.services replaced with a non-list value (shared with machinery.mcp.tools)",
         lambda d: d["machinery"]["infra"].__setitem__("services", "oops"),
         ["machinery.infra.services"]),
    _mut("grammar.machinery_harness_item_name", "grammar_v2", "dummy", "machinery.harness.agents[0]",
         "first harness.agents entry's `name` key removed",
         lambda d: d["machinery"]["harness"]["agents"][0].__delitem__("name"),
         ["machinery.harness.agents[0]"]),
    _mut("grammar.machinery_harness_kind_list", "grammar_v2", "dummy", "machinery.harness.agents",
         "machinery.harness.agents replaced with a non-list value (shared across agents/commands/skills)",
         lambda d: d["machinery"]["harness"].__setitem__("agents", "oops"),
         ["machinery.harness.agents"]),
    _mut("grammar.machinery_harness_command_run", "grammar_v2", "dummy",
         "machinery.harness.commands[0].run",
         "the 'greet' command's run list emptied",
         lambda d: d["machinery"]["harness"]["commands"][0].__setitem__("run", []),
         ["machinery.harness.commands[greet]"]),
]

#: Rules with no mutant, visible rather than hidden (none currently — every branch identified in
#: validator.py has an entry in MUTATIONS above). Kept as a list so a future rule that genuinely
#: cannot be exercised is recorded here instead of silently absent.
RULES_WITHOUT_MUTANT: list[str] = []

_BASES = {"dummy": _DUMMY, "asf": _ASF}


def _station_digest(station) -> dict:
    return {
        "id": station.id, "activation": station.activation, "status": station.status,
        "tier": station.tier, "depends_on": list(station.depends_on),
        "builds_count": len(station.builds), "checks_count": len(station.checks),
        "proof_checks_count": len(station.proof_checks),
    }


def _loader_digest(spec) -> dict:
    """Enough to catch a port that quietly drops a field: station ids IN ORDER + per-station
    shape, capability/requirement ids, which machinery sections are present."""
    return {
        "slug": spec.slug, "name": spec.name, "maturity": spec.maturity, "produces": spec.produces,
        "station_ids": [s.id for s in spec.stations],
        "stations": [_station_digest(s) for s in spec.stations],
        "capability_ids": [c.id for c in spec.capabilities],
        "requirement_ids": [r.id for r in spec.requirements],
        "machinery_present": {
            "harness": bool(spec.machinery.harness), "mcp": bool(spec.machinery.mcp),
            "infra": bool(spec.machinery.infra),
        },
    }


def generate(ref: str) -> tuple[dict, dict]:
    tmp = _materialize(ref)
    try:
        sys.path.insert(0, str(tmp / "src"))
        for name in [n for n in sys.modules if n == "metafactory" or n.startswith("metafactory.")]:
            del sys.modules[name]

        from metafactory.spec import load_spec, validate

        work = Path(tempfile.mkdtemp(prefix="mf-spec-mutants-"))
        try:
            # ── ACCEPT vectors: every committed factory spec, as-is ──────────────────────────────
            accept_vectors: list[dict] = []
            for spec_path in sorted(tmp.glob(_ACCEPT_GLOB)):
                text = spec_path.read_text(encoding="utf-8")
                spec = load_spec(spec_path)
                problems = validate(spec)
                accept_vectors.append({
                    "origin": str(spec_path.relative_to(tmp)),
                    "spec_yaml": text,
                    "decision": "valid" if not problems else "invalid",
                    "problems": problems,
                    "loader_digest": _loader_digest(spec),
                })

            # ── REJECT vectors: one real-spec mutant per validator rule ──────────────────────────
            base_yaml = {key: (tmp / path).read_text(encoding="utf-8") for key, path in _BASES.items()}
            base_dict = {key: yaml.safe_load(text) for key, text in base_yaml.items()}

            reject_vectors: list[dict] = []
            accepted_unexpectedly: list[dict] = []
            for i, m in enumerate(MUTATIONS):
                d = copy.deepcopy(base_dict[m["base"]])
                m["mutate"](d)
                mutant_text = yaml.safe_dump(d, sort_keys=False)
                mutant_path = work / f"mutant_{i:03d}.yml"
                mutant_path.write_text(mutant_text, encoding="utf-8")

                spec = load_spec(mutant_path)
                problems = validate(spec)

                if not problems:
                    accepted_unexpectedly.append({
                        "rule_id": m["rule_id"], "base": m["base"],
                        "description": m["description"],
                    })
                    continue

                joined = "\n".join(problems)
                identifier = next((c for c in m["candidates"] if c in joined), None)
                if identifier is None:
                    raise RuntimeError(
                        f"mutation design bug: rule {m['rule_id']!r} produced problems {problems!r} "
                        f"but none of its candidate identifiers {m['candidates']!r} appear in them")

                reject_vectors.append({
                    "rule_id": m["rule_id"], "family": m["family"], "base": m["base"],
                    "applies_to": m["applies_to"], "description": m["description"],
                    "spec_yaml": mutant_text, "decision": "invalid",
                    "problems": problems, "offending_identifier": identifier,
                })
        finally:
            shutil.rmtree(work, ignore_errors=True)

        rule_inventory = [
            {"rule_id": m["rule_id"], "family": m["family"], "applies_to": m["applies_to"],
             "has_mutant": True}
            for m in MUTATIONS
        ] + [
            {"rule_id": rid, "family": "?", "applies_to": "?", "has_mutant": False}
            for rid in RULES_WITHOUT_MUTANT
        ]

        payload = {
            "_doc": "Oracle for v3's spec model/loader/validator port (V3-INC4, Phase 4). "
                    "`accept_vectors` are the 5 committed factory.spec.yml files, loaded+validated "
                    "by v2's REAL code; `reject_vectors` are one MUTANT per validator rule, each a "
                    "real committed spec minimally mutated at the parsed-dict level. Every vector "
                    "embeds its own full spec_yaml so the ported gate never depends on the working "
                    "tree drifting after generation. Regenerate: "
                    "python3 tools/gen_spec_validation_vectors.py.",
            "oracle_ref": ref,
            "generated_by": "tools/gen_spec_validation_vectors.py",
            "rule_inventory": rule_inventory,
            "rules_without_mutant": RULES_WITHOUT_MUTANT,
            "accepted_unexpectedly": accepted_unexpectedly,
            "accept_vectors": accept_vectors,
            "reject_vectors": reject_vectors,
            "counts": {
                "accept_vectors": len(accept_vectors),
                "accept_valid": sum(1 for v in accept_vectors if v["decision"] == "valid"),
                "reject_vectors": len(reject_vectors),
                "rules_total": len(rule_inventory),
                "rules_with_mutant": sum(1 for r in rule_inventory if r["has_mutant"]),
                "rules_without_mutant": len(RULES_WITHOUT_MUTANT),
                "accepted_unexpectedly": len(accepted_unexpectedly),
            },
        }
        stats = dict(payload["counts"])
        return payload, stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    gen-spec-validation-vectors — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    ref = _oracle()["oracle_ref"]
    payload, stats = generate(ref)

    if stats["accept_vectors"] == 0 or stats["reject_vectors"] == 0:
        print("VERDICT    gen-spec-validation-vectors — FAIL   (exit 1)")
        print(f"SUMMARY    zero accept or reject vectors ({stats}); the fixture would be vacuous")
        return 1

    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _FIXTURE.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("VERDICT    gen-spec-validation-vectors — PASS   (exit 0)")
    print(f"SUMMARY    {stats['accept_vectors']} accept vector(s), {stats['reject_vectors']} "
          f"reject vector(s) covering {stats['rules_with_mutant']}/{stats['rules_total']} rule(s) "
          f"@ {ref[:12]} -> {_FIXTURE.relative_to(_ROOT)}")
    print(f"COUNTS     {stats}")
    if payload["accepted_unexpectedly"]:
        print(f"NOTE       {len(payload['accepted_unexpectedly'])} mutation(s) were ACCEPTED by v2 "
              f"unexpectedly — see accepted_unexpectedly in the fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
