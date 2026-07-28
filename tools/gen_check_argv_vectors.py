#!/usr/bin/env python3
"""gen_check_argv_vectors — the ORACLE generator for v3's check-kind port (V3-INC4-KINDS-PORT).

v2-side (`tools/`, free to import `metafactory` — this script lives OUTSIDE the boundary v3 must
never cross, `v3.verify.import_boundary`). It materialises `v3/oracle_ref.json`'s pinned commit
OUTSIDE the repo (`git archive <ref> | tar -x`, into a `tempfile.mkdtemp()` — never `git worktree`,
which mutates `.git/` and would leave state the slot-footprint sweep sees as a stray change), walks
every committed station YAML AT THAT COMMIT (`src/metafactory/stations/*.yml` +
`factories/*/stations/*.yml` — verified by listing, not assumed), and calls v2's REAL
`resolve_check` with the same ctx/station/subst shape the engine itself builds
(`metafactory.cli._subst_for`, the exact function `cmd_station`/`_run_product_line` call — read, not
invented). One vector per declared check. Any of the 29 KINDS with zero real declaration anywhere in
the sweep gets exactly one SYNTHETIC vector instead (`"synthetic": true`), so coverage is total and
the absence of a real declaration stays visible rather than hidden.

NORMALISATION. `sys.executable` and the materialised tree's own absolute path are ENVIRONMENT, not
MAPPING (a different machine/CI would see different values for the same behaviour) — both are
replaced (`"<PY>"`, `"<ROOT>"`) in every recorded `argv` and `subst_keys`. v2's own hardcoded
`metafactory.*` executor-module targets are recorded VERBATIM (this script is free to name them —
the import boundary in `v3/` binds only `v3/verify/kinds.py` and `v3/verify/kinds_parity.py`); the
ported side never writes v2's package name down at all — it hardcodes the ALREADY-SWAPPED `v3.*`
result directly (see `v3/verify/kinds.py`'s docstring, "THE PORT RULE"). `kinds_parity` proves that
swap is exact by applying it to the oracle side at comparison time, reading which name to swap FROM
out of this fixture's own `v2_package` provenance field (below) rather than hardcoding it — a value
compared, never dereferenced.

PROVENANCE. The payload stamps `"v2_package"`, v2's own top-level package name, DERIVED from
`resolve_check.__module__.split(".")[0]` (this script imports the real function; asking it what
module it lives in is not a guess) — never hand-typed, so a fixture regenerated after v2's package
was ever renamed would carry the truth automatically instead of silently going stale.

MEta stations (`src/metafactory/stations/*.yml`) are TEMPLATES: the real engine only ever runs one
against a target factory's own `subst` (`meta station <id> --factory <slug>`), so each of their
checks is resolved once per real factory found in the sweep (5 real contexts, not one invented one) —
`origin` records which.

Usage:  python3 tools/gen_check_argv_vectors.py     # writes docs/spec/fixtures/check-argv-vectors.json
Prints counts only (context economy, I-7) — never the vectors themselves.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_ORACLE_REF_FILE = _ROOT / "v3" / "oracle_ref.json"
_FIXTURE = _ROOT / "docs" / "spec" / "fixtures" / "check-argv-vectors.json"

#: Minimal, valid check dicts for kinds a real sweep finds zero declarations of. Never executed (this
#: script only records the ARGV a call to `resolve_check` builds; it runs no subprocess), so any
#: plausible value satisfies the kind's required keys (docs/spec/16-catalogs.md §2).
_SYNTHETIC_CHECKS: dict[str, dict] = {
    "py_compile": {"name": "s_py_compile", "kind": "py_compile", "files": ["seed/verifier.py"]},
    "import_runs": {"name": "s_import_runs", "kind": "import_runs", "code": "assert True"},
    "artifact_contains": {"name": "s_artifact_contains", "kind": "artifact_contains",
                           "file": "README.md", "marker": "Meta-Factory"},
    "spec_validate": {"name": "s_spec_validate", "kind": "spec_validate", "spec": "factory.spec.yml"},
    "rtm_closure": {"name": "s_rtm_closure", "kind": "rtm_closure", "spec": "factory.spec.yml"},
    "design_review": {"name": "s_design_review", "kind": "design_review", "spec": "factory.spec.yml"},
    "pytest": {"name": "s_pytest", "kind": "pytest", "path": "tests"},
    "isolation": {"name": "s_isolation", "kind": "isolation"},
    "docs_check": {"name": "s_docs_check", "kind": "docs_check"},
    "command": {"name": "s_command", "kind": "command", "cmd": ["true"]},
    "column_selftest": {"name": "s_column_selftest", "kind": "column_selftest"},
    "column_full": {"name": "s_column_full", "kind": "column_full"},
    "bus_bounded": {"name": "s_bus_bounded", "kind": "bus_bounded"},
    "product_run": {"name": "s_product_run", "kind": "product_run"},
    "boundary_survives": {"name": "s_boundary_survives", "kind": "boundary_survives"},
    "rtm_rederive": {"name": "s_rtm_rederive", "kind": "rtm_rederive"},
    "rtm_tree": {"name": "s_rtm_tree", "kind": "rtm_tree"},
    "clean_runner": {"name": "s_clean_runner", "kind": "clean_runner"},
    "agent_shadow": {"name": "s_agent_shadow", "kind": "agent_shadow"},
    "product_env": {"name": "s_product_env", "kind": "product_env",
                     "workdir": ".", "bootstrap": [], "cmd": ["true"]},
    "command_runs": {"name": "s_command_runs", "kind": "command_runs"},
    "infra_up": {"name": "s_infra_up", "kind": "infra_up", "workdir": ".",
                 "up": ["true"], "proof": ["true"], "down": ["true"], "bootstrap": []},
    "mcp_tools": {"name": "s_mcp_tools", "kind": "mcp_tools", "workdir": ".",
                  "prove": ["true"], "tools": ["ping"]},
    "eval_gate": {"name": "s_eval_gate", "kind": "eval_gate", "workdir": ".", "scorer": ["true"],
                  "output": "out.json", "degraded": "bad.json", "thresholds": {"score": 0.5},
                  "bootstrap": []},
    "eval_floor": {"name": "s_eval_floor", "kind": "eval_floor", "workdir": ".", "command": ["true"],
                   "evidence": "evidence.json", "degraded": "bad.json", "thresholds": "floor.yml",
                   "bootstrap": []},
    "live_run": {"name": "s_live_run", "kind": "live_run", "workdir": ".", "run": ["true"],
                 "output": "out.json", "degraded": "bad.json", "properties": ["p1"],
                 "scorer": ["true"], "thresholds": {"m": 0.1}, "provider_env": "FAKE_API_KEY",
                 "bootstrap": []},
    "blast_radius": {"name": "s_blast_radius", "kind": "blast_radius",
                      "baseline": "baseline_verdicts.json"},
    "scenario_corpus": {"name": "s_scenario_corpus", "kind": "scenario_corpus",
                        "corpus": "scenarios/corpus.yml"},
    "products_rederive": {"name": "s_products_rederive", "kind": "products_rederive"},
}


def _oracle() -> dict:
    return json.loads(_ORACLE_REF_FILE.read_text(encoding="utf-8"))


def _materialize(ref: str) -> Path:
    """`git archive <ref> | tar -x` into a fresh tempdir OUTSIDE the repo. Never `git worktree` (it
    mutates `.git/`, leaving state the slot-footprint sweep would see as a stray change)."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        raise ValueError(f"oracle_ref does not look like a commit sha: {ref!r}")
    tmp = Path(tempfile.mkdtemp(prefix="mf-oracle-"))
    archive = subprocess.Popen(["git", "archive", ref], stdout=subprocess.PIPE, cwd=_ROOT)
    tar = subprocess.run(["tar", "-x", "-C", str(tmp)], stdin=archive.stdout)
    archive.stdout.close()
    rc_archive = archive.wait()
    if rc_archive != 0 or tar.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"materialising {ref} failed (git archive={rc_archive}, tar={tar.returncode})")
    return tmp


def _normalize(value, py: str, root: str):
    """Replace this process's interpreter and the materialised tree's own absolute root with
    environment-neutral placeholders — recursively, so it applies to argv lists AND subst dicts."""
    if isinstance(value, str):
        return value.replace(py, "<PY>").replace(root, "<ROOT>")
    if isinstance(value, list):
        return [_normalize(v, py, root) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v, py, root) for k, v in value.items()}
    return value


def _synthetic_subst(tmp: Path) -> dict:
    return {
        "slug": "synthetic", "name": "Synthetic Factory", "maturity": "prototype",
        "produces": "synthetic", "factory_root": str(tmp / "factories" / "dummy"),
        "meta_root": str(tmp), "spec_path": "factory.spec.yml", "max_lines": 10,
    }


def generate(ref: str) -> tuple[dict, dict]:
    """Materialise `ref`, walk every committed station YAML, resolve every declared check through
    v2's REAL `resolve_check`. Returns (fixture_payload, stats)."""
    tmp = _materialize(ref)
    try:
        sys.path.insert(0, str(tmp / "src"))
        for name in [n for n in sys.modules if n == "metafactory" or n.startswith("metafactory.")]:
            del sys.modules[name]

        from metafactory.cli import _subst_for
        from metafactory.spec import load_spec
        from metafactory.verify.checks.registry import KINDS, resolve_check

        v2_package = resolve_check.__module__.split(".")[0]
        py, root = sys.executable, str(tmp.resolve())
        vectors: list[dict] = []

        # ── every real factory's own subst (the same one `_run_product_line`/`cmd_station` build) ──
        factory_ctx: dict[str, tuple[Path, dict]] = {}
        for spec_path in sorted(tmp.glob("factories/*/factory.spec.yml")):
            fdir = spec_path.parent
            spec = load_spec(spec_path)
            factory_ctx[spec.slug] = (fdir, _subst_for(spec, fdir))

        def _resolve_yaml_checks(path: Path, subst: dict, origin: str) -> None:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            station_id = str(data.get("id", path.stem))
            station = SimpleNamespace(id=station_id)
            for check in (data.get("checks") or []):
                if not isinstance(check, dict) or "kind" not in check:
                    continue
                argv = resolve_check(check, None, station, subst)
                vectors.append({
                    "kind": check["kind"], "check": check, "station": station_id,
                    "subst_keys": _normalize(subst, py, root),
                    "argv": _normalize(list(argv), py, root),
                    "origin": origin, "synthetic": False,
                })

        # ── factory-owned stations: resolved with THAT factory's own subst ──
        for path in sorted(tmp.glob("factories/*/stations/*.yml")):
            slug = path.parent.parent.name
            if slug not in factory_ctx:
                continue
            _, subst = factory_ctx[slug]
            _resolve_yaml_checks(path, subst, f"{path.relative_to(tmp)}@factory={slug}")

        # ── meta stations: TEMPLATES — resolved once per real factory context (that is the only
        #    shape the engine ever runs them in, `meta station <id> --factory <slug>`) ──
        for path in sorted(tmp.glob("src/metafactory/stations/*.yml")):
            for slug in sorted(factory_ctx):
                _, subst = factory_ctx[slug]
                _resolve_yaml_checks(path, subst, f"{path.relative_to(tmp)}@factory={slug}")

        # ── coverage: any of the 29 kinds with zero real vectors gets exactly one synthetic one ──
        seen = {v["kind"] for v in vectors}
        synth_subst = _synthetic_subst(tmp)
        for kind in KINDS:
            if kind in seen:
                continue
            check = _SYNTHETIC_CHECKS[kind]
            station = SimpleNamespace(id="synthetic")
            argv = resolve_check(check, None, station, synth_subst)
            vectors.append({
                "kind": kind, "check": check, "station": "synthetic",
                "subst_keys": _normalize(synth_subst, py, root),
                "argv": _normalize(list(argv), py, root),
                "origin": "synthetic", "synthetic": True,
            })

        vectors.sort(key=lambda v: (v["kind"], v["origin"], v["station"]))

        per_kind: dict[str, dict] = {k: {"real": 0, "synthetic": 0} for k in KINDS}
        for v in vectors:
            per_kind[v["kind"]]["synthetic" if v["synthetic"] else "real"] += 1
        real_total = sum(1 for v in vectors if not v["synthetic"])
        synth_total = sum(1 for v in vectors if v["synthetic"])

        payload = {
            "_doc": "Oracle for v3's check-KIND port (V3-INC4-KINDS-PORT). Every vector is "
                    "{kind, check, station, subst_keys, argv, origin, synthetic} recorded by calling "
                    "v2's REAL registry.resolve_check at oracle_ref, materialised outside the repo "
                    "(never the working tree, ADR-031 §2.1). `subst_keys` is the FULL substitution "
                    "dict `resolve_check` was called with (not just its keys) — the parity gate feeds "
                    "it straight back in. `v2_package` is v2's own top-level package name, derived "
                    "from resolve_check.__module__, not hand-typed — kinds_parity reads it (never "
                    "hardcodes it) to swap argv's head segment before comparing to the ported side. "
                    "Regenerate: python3 tools/gen_check_argv_vectors.py.",
            "oracle_ref": ref,
            "generated_by": "tools/gen_check_argv_vectors.py",
            "v2_package": v2_package,
            "kinds": list(KINDS),
            "counts": {
                "total_vectors": len(vectors), "real_vectors": real_total,
                "synthetic_vectors": synth_total, "per_kind": per_kind,
            },
            "vectors": vectors,
        }
        stats = {"total": len(vectors), "real": real_total, "synthetic": synth_total,
                 "kinds_with_no_real_declaration": sorted(k for k, c in per_kind.items()
                                                          if c["real"] == 0)}
        return payload, stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    gen-check-argv-vectors — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    ref = _oracle()["oracle_ref"]
    payload, stats = generate(ref)

    if stats["total"] == 0:
        print("VERDICT    gen-check-argv-vectors — FAIL   (exit 1)")
        print("SUMMARY    zero vectors generated; the fixture would be vacuous")
        return 1

    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _FIXTURE.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("VERDICT    gen-check-argv-vectors — PASS   (exit 0)")
    print(f"SUMMARY    {stats['total']} vector(s) ({stats['real']} real, {stats['synthetic']} "
          f"synthetic) across {len(payload['kinds'])} kind(s) @ {ref[:12]} → "
          f"{_FIXTURE.relative_to(_ROOT)}")
    print(f"COUNTS     {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
