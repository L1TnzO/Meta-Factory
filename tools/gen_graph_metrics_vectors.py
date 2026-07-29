#!/usr/bin/env python3
"""gen_graph_metrics_vectors — the ORACLE generator for v3's code-graph port (V3-INC4-GRAPH-SLICE).

v2-side (`tools/`, free to import `metafactory` — this script lives OUTSIDE the boundary v3 must
never cross, `v3.verify.import_boundary`). Like `gen_check_argv_vectors.py` before it: materialises
`v3/oracle_ref.json`'s pinned commit OUTSIDE the repo (`git archive <ref> | tar -x`, into a
`tempfile.mkdtemp()` — never `git worktree`), then runs v2's OWN, REAL graph code (`build.py`,
`quality.py`, `python_index.py`, `model.py`) freshly imported from that materialised tree — never the
working tree, which can drift under anyone's edits (ADR-031 §2.1: the oracle is a commit).

DECLARED INPUT SET. Not the whole `src/metafactory` (13.7k LOC across 102 files — the "natural
choice" the brief offers but not the only honest one): this fixture measures v2's own **graph
package**, `src/metafactory/graph/` (15 files, ~2026 LOC at oracle_ref), as the fixed structural
input. That is deliberately BROADER than the 5 modules V3-INC4 ports (866 LOC): it includes
`doc_graph.py`/`cli.py`/`repomap.py`/`incremental.py`/`ingest.py`/`billing.py`/`pricing.py`/
`affected*.py` too, none of which is ported here — using them only as MEASUREMENT INPUT (their
LOC/imports/function shapes) is how this fixture proves the ported `build.py`/`quality.py` measure
correctly for ANY input, not merely the 5 files fitted to their own port. `input_root` below is the
one fact `v3.verify.graph_parity` needs to rebuild the same tree; every file's raw `source` is
embedded in the fixture (the same move `spec-validation-vectors.json` makes with `spec_yaml`) so the
GATE never needs `git` or a v2 import at verify time — it self-contains its own oracle.

RED CASES, generated the same way — by calling v2's REAL code, never hand-asserted:
  * the committed monolith fixture (`tests/fixtures/quality/monolith_shaped.py`, present in the
    SAME materialised whole-tree archive) must trip >=1 violation under v2's default thresholds;
  * a SYNTHETIC two-file mutual import (module-level on both sides) must be detected as a cycle;
  * a SYNTHETIC pair where the "back edge" is a DEFERRED import (inside a function body on one
    side) must NOT be detected as a cycle — v2's own subtlety (cycle detection counts only
    module-level imports; python_index.py's `_module_level_imports` skips function/class bodies).

Usage:  python3 tools/gen_graph_metrics_vectors.py     # writes docs/spec/fixtures/graph-metrics-vectors.json
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

_ROOT = Path(__file__).resolve().parents[1]
_ORACLE_REF_FILE = _ROOT / "v3" / "oracle_ref.json"
_FIXTURE = _ROOT / "docs" / "spec" / "fixtures" / "graph-metrics-vectors.json"

_INPUT_ROOT = "src/metafactory/graph"
_MONOLITH_RELPATH = "tests/fixtures/quality/monolith_shaped.py"

# ── synthetic RED sources, written into their own throwaway trees at generation time ────────────
_CYCLE_A = "import synth_cycle_b\n\n\ndef func_a(x):\n    return synth_cycle_b.func_b(x) + 1\n"
_CYCLE_B = "import synth_cycle_a\n\n\ndef func_b(x):\n    return x + 1\n"
_DEFER_A = ("def func_a(x):\n"
            "    import synth_defer_b   # module-level would close the cycle; a deferred one must not\n"
            "    return synth_defer_b.func_b(x) + 1\n")
_DEFER_B = "import synth_defer_a\n\n\ndef func_b(x):\n    return x + 1\n"


def _oracle() -> dict:
    return json.loads(_ORACLE_REF_FILE.read_text(encoding="utf-8"))


def _materialize(ref: str) -> Path:
    """`git archive <ref> | tar -x` into a fresh tempdir OUTSIDE the repo (LAW #1). Never `git
    worktree` (it mutates `.git/`, leaving state the slot-footprint sweep would see as a stray
    change). No pathspec: the whole tree at `ref`, so the monolith fixture is in it too."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        raise ValueError(f"oracle_ref does not look like a commit sha: {ref!r}")
    tmp = Path(tempfile.mkdtemp(prefix="mf-graph-oracle-"))
    archive = subprocess.Popen(["git", "archive", ref], stdout=subprocess.PIPE, cwd=_ROOT)
    tar = subprocess.run(["tar", "-x", "-C", str(tmp)], stdin=archive.stdout)
    archive.stdout.close()
    rc_archive = archive.wait()
    if rc_archive != 0 or tar.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"materialising {ref} failed (git archive={rc_archive}, tar={tar.returncode})")
    return tmp


def _fresh_v2_graph_modules(src_root: Path):
    """Insert `src_root` at the FRONT of sys.path and import v2's graph modules fresh — dropping any
    cached `metafactory.*` module first, so a second call in the same process cannot silently reuse
    a previous materialisation's code."""
    sys.path.insert(0, str(src_root))
    for name in [n for n in sys.modules if n == "metafactory" or n.startswith("metafactory.")]:
        del sys.modules[name]
    from metafactory.graph import build as v2_build
    from metafactory.graph import model as v2_model
    from metafactory.graph import quality as v2_quality
    return v2_build, v2_quality, v2_model


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for relpath, source in files.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def _violation_to_dict(v) -> dict:
    return {"relpath": v.relpath, "metric": v.metric, "value": v.value, "limit": v.limit}


def _threshold_to_dict(th) -> dict:
    return {"max_file_loc": th.max_file_loc, "max_funcs_per_file": th.max_funcs_per_file,
            "max_func_loc": th.max_func_loc}


def _file_vector(graph, model_mod, relpath: str, source: str) -> dict:
    fid = f"File:{relpath}"
    node = graph.node(fid)
    if node is None:
        raise RuntimeError(f"{relpath}: build_code_graph produced no File node (unexpected)")
    syms = [graph.node(e.src) for e in graph.in_edges(fid, model_mod.EdgeKind.DEFINED_IN)]
    funcs = sorted(
        ({"qualname": s.attrs["qualname"], "loc": int(s.attrs["loc"])} for s in syms
         if s and s.attrs.get("symtype") == "function"),
        key=lambda d: d["qualname"],
    )
    classes = [s for s in syms if s and s.attrs.get("symtype") == "class"]
    return {
        "relpath": relpath,
        "source": source,
        "loc": int(node.attrs.get("loc", -1)),
        "function_count": len(funcs),
        "class_count": len(classes),
        "per_function_loc": funcs,
        "imports": list(node.attrs.get("imports", [])),
    }


def generate(ref: str) -> tuple[dict, dict]:
    tmp = _materialize(ref)
    try:
        v2_build, v2_quality, v2_model = _fresh_v2_graph_modules(tmp / "src")

        # ── (a) structural vectors, over the declared input root ────────────────────────────────
        graph, fragments = v2_build.build_code_graph(tmp, roots=(_INPUT_ROOT,))
        files_vectors = [
            _file_vector(graph, v2_model, rel, (tmp / rel).read_text(encoding="utf-8"))
            for rel in sorted(fragments)
        ]
        cycles = v2_quality.import_cycles(graph)

        # ── (b) quality vectors, same input, v2's default thresholds ────────────────────────────
        th = v2_quality.Thresholds()
        violations = [_violation_to_dict(v) for v in v2_quality.file_violations(graph, th)]

        # ── (c) RED cases — the point ────────────────────────────────────────────────────────────
        monolith_source = (tmp / _MONOLITH_RELPATH).read_text(encoding="utf-8")
        monolith_violations = [_violation_to_dict(v)
                                for v in v2_quality.evaluate_file(tmp, _MONOLITH_RELPATH, th)]
        if not monolith_violations:
            raise RuntimeError(f"{_MONOLITH_RELPATH}: v2's OWN quality gate reports zero violations "
                              f"at {ref} — the oracle would be vacuous, refusing to write a fixture")

        cyc_tree = Path(tempfile.mkdtemp(prefix="mf-graph-synth-cycle-"))
        try:
            _write_tree(cyc_tree, {"src/synth_cycle_a.py": _CYCLE_A, "src/synth_cycle_b.py": _CYCLE_B})
            cyc_graph, _ = v2_build.build_code_graph(cyc_tree, roots=("src",))
            expected_cycle = v2_quality.import_cycles(cyc_graph)
        finally:
            shutil.rmtree(cyc_tree, ignore_errors=True)
        if not expected_cycle:
            raise RuntimeError("synthetic mutual-import case: v2's OWN cycle detector found nothing "
                              "— the RED witness would be vacuous")

        defer_tree = Path(tempfile.mkdtemp(prefix="mf-graph-synth-defer-"))
        try:
            _write_tree(defer_tree, {"src/synth_defer_a.py": _DEFER_A, "src/synth_defer_b.py": _DEFER_B})
            defer_graph, _ = v2_build.build_code_graph(defer_tree, roots=("src",))
            deferred_cycles = v2_quality.import_cycles(defer_graph)
        finally:
            shutil.rmtree(defer_tree, ignore_errors=True)
        if deferred_cycles:
            raise RuntimeError(f"deferred-import case: v2's OWN detector reported a cycle anyway "
                              f"({deferred_cycles}) — the negative witness does not hold, cannot "
                              f"record a false claim about v2's behaviour")

        payload = {
            "_doc": "Oracle for v3's code-graph port (V3-INC4-GRAPH-SLICE): structural + quality "
                    "metrics v2's REAL graph code (model/python_index/build/quality) produces over "
                    "its own graph package at oracle_ref, plus the RED cases (monolith fixture, a "
                    "synthetic import cycle, and a synthetic deferred-import NON-cycle) that make the "
                    "port falsifiable. Every real file's raw `source` is embedded so "
                    "`v3.verify.graph_parity` never needs git or a v2 import to re-derive parity — "
                    "it rebuilds the tree from this fixture and runs the PORTED code over it. "
                    "Regenerate: python3 tools/gen_graph_metrics_vectors.py.",
            "oracle_ref": ref,
            "generated_by": "tools/gen_graph_metrics_vectors.py",
            "input_root": _INPUT_ROOT,
            "structural": {"files": files_vectors, "cycles": cycles},
            "quality": {"thresholds": _threshold_to_dict(th), "violations": violations},
            "red": {
                "monolith": {"relpath": _MONOLITH_RELPATH, "source": monolith_source,
                             "violations": monolith_violations},
                "synthetic_cycle": {"files": {"src/synth_cycle_a.py": _CYCLE_A,
                                              "src/synth_cycle_b.py": _CYCLE_B},
                                    "expected_cycles": expected_cycle},
                "deferred_import_not_cycle": {"files": {"src/synth_defer_a.py": _DEFER_A,
                                                        "src/synth_defer_b.py": _DEFER_B},
                                              "expected_cycles": deferred_cycles},
            },
        }
        stats = {
            "structural_files": len(files_vectors), "real_cycles": len(cycles),
            "quality_violations": len(violations), "monolith_violations": len(monolith_violations),
            "synthetic_cycle_components": len(expected_cycle),
        }
        return payload, stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    gen-graph-metrics-vectors — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    ref = _oracle()["oracle_ref"]
    payload, stats = generate(ref)

    if stats["structural_files"] == 0:
        print("VERDICT    gen-graph-metrics-vectors — FAIL   (exit 1)")
        print("SUMMARY    zero structural vectors generated; the fixture would be vacuous")
        return 1

    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _FIXTURE.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("VERDICT    gen-graph-metrics-vectors — PASS   (exit 0)")
    print(f"SUMMARY    {stats['structural_files']} file(s) @ {ref[:12]}, "
          f"{stats['quality_violations']} quality violation(s), {stats['real_cycles']} real cycle(s); "
          f"RED: monolith={stats['monolith_violations']} violation(s), "
          f"synthetic cycle={stats['synthetic_cycle_components']} component(s) → "
          f"{_FIXTURE.relative_to(_ROOT)}")
    print(f"COUNTS     {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
