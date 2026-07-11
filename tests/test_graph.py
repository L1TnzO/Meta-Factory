"""test_graph — the project-spine (ADR-017, Fase 1). Every closure criterion of GRAPH-SPINE-KEYSTONE
is proven BY BLOCKING here: re-derivation from the AST, RTM+ADR ingest + a no-LLM 2-hop query,
incrementality (touch 1 file => re-derive only its subgraph), the two-sided quality-gate tooth, and the
delegation billing-ledger split.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from metafactory.graph.billing import BillingLedger, LedgerEntry
from metafactory.graph.build import (
    build_code_graph,
    governing_adrs,
    graph_from_fragments,
    requirements_for_proof,
    requirements_satisfied_by,
)
from metafactory.graph.doc_graph import ingest_docs, is_exempt, live_roots
from metafactory.graph.incremental import incremental_rebuild
from metafactory.graph.ingest import ingest_adrs, ingest_rtm
from metafactory.graph.model import Edge, EdgeKind, Graph, Node, NodeKind, content_hash
from metafactory.graph.python_index import index_file
from metafactory.graph.quality import (
    Thresholds,
    discover_authored_codegen,
    evaluate_file,
    evaluate_graph,
    import_cycles,
)
from metafactory.graph.repomap import pagerank, rank_files, repo_map

REPO = Path(__file__).resolve().parents[1]

_SAMPLE = '''from a.b import c, d
from ...pkg import helper

class Greeter:
    def hi(self, n):
        return c(n) + greet(n)

def greet(n):
    import os            # deferred / function-level: must NOT count as a module dep
    return d(n)
'''


# ── model: content-addressing, serde, traversal ────────────────────────────────
def test_node_is_content_addressed_and_stable():
    a = Node.make(NodeKind.FILE, "x/y.py", "y.py", {"loc": 3})
    b = Node.make(NodeKind.FILE, "x/y.py", "y.py", {"loc": 3})
    assert a.id == b.id == "File:x/y.py"
    assert a.content_hash == b.content_hash
    c = Node.make(NodeKind.FILE, "x/y.py", "y.py", {"loc": 4})
    assert c.content_hash != a.content_hash   # payload change => hash change


def test_graph_serde_roundtrip_and_traversal():
    g = Graph()
    f = Node.make(NodeKind.FILE, "f.py", "f.py", {})
    s = Node.make(NodeKind.SYMBOL, "f.py::foo", "foo", {})
    g.add_node(f); g.add_node(s)
    g.add_edge(Edge(s.id, f.id, EdgeKind.DEFINED_IN))
    g.add_edge(Edge(s.id, f.id, EdgeKind.DEFINED_IN))   # dedup
    assert len(g.edges) == 1
    # forward + reverse one-hop
    assert g.reachable(s.id, [(EdgeKind.DEFINED_IN, True)]) == [f.id]
    assert g.reachable(f.id, [(EdgeKind.DEFINED_IN, False)]) == [s.id]
    g2 = Graph.from_json(g.to_json())
    assert {n.id for n in g2.nodes} == {f.id, s.id} and len(g2.edges) == 1


# ── Fase 1: structural index from the AST ───────────────────────────────────────
def test_index_file_symbols_imports_calls(tmp_path):
    (tmp_path / "src").mkdir()
    rel = "src/m.py"
    (tmp_path / rel).write_text(_SAMPLE, encoding="utf-8")
    frag = index_file(tmp_path, rel)
    names = {n.name for n in frag.nodes}
    assert {"m.py", "Greeter", "Greeter.hi", "greet"} <= names
    fnode = next(n for n in frag.nodes if n.kind == NodeKind.FILE)
    # absolute import kept; relative resolved against package src/  -> "pkg.helper" (level 3 from src.m's pkg)
    assert "a.b.c" in fnode.attrs["imports"] and "a.b.d" in fnode.attrs["imports"]
    # the deferred `import os` inside greet() must NOT appear (module-level only)
    assert "os" not in fnode.attrs["imports"]
    hi = next(n for n in frag.nodes if n.name == "Greeter.hi")
    assert "greet" in hi.attrs["calls"] and "c" in hi.attrs["calls"]
    assert len([e for e in frag.edges if e.kind == EdgeKind.DEFINED_IN]) == 3


def test_relative_import_resolves_to_file_edge():
    """A real substrate file with relative imports must yield File->File IMPORTS edges (else cycle
    detection / coupling would be decorative)."""
    g, _ = build_code_graph(REPO)
    imports = [e for e in g.edges if e.kind == EdgeKind.IMPORTS]
    assert len(imports) > 30
    reg = "File:src/metafactory/verify/checks/registry.py"
    renderer = "File:src/metafactory/codegen/renderer.py"
    assert any(e.src == reg and e.dst == renderer for e in imports)


# ── Fase 2: ingest RTM + ADR, no-LLM 2-hop query ────────────────────────────────
def test_governing_adrs_two_hop_no_llm():
    g, _ = build_code_graph(REPO)
    ingest_adrs(g, REPO)
    sym = "Symbol:src/metafactory/verify/checks/generality_parity.py::_radically_distinct"
    adrs = governing_adrs(g, sym)
    # that file's source cites ADR-012 and ADR-014 -> Decision:012, Decision:014, via symbol->file<-ADR
    assert "Decision:012" in adrs and "Decision:014" in adrs


def test_ingest_rtm_edges_and_query():
    g, _ = build_code_graph(REPO)
    n = ingest_rtm(g, REPO, "dummy")
    assert n >= 1
    stations = g.nodes_of(NodeKind.STATION)
    proofs = g.nodes_of(NodeKind.PROOF)
    assert stations and proofs
    # station --SATISFIES--> requirement (1 hop) and proof --VERIFIES--> station --SATISFIES--> req (2 hop)
    sid = next(s.id for s in stations)
    assert requirements_satisfied_by(g, sid)
    pid = next(p.id for p in proofs)
    assert requirements_for_proof(g, pid)


def test_artifact_unifies_with_indexed_file():
    """An ingested artifact whose path is an indexed File node REUSES that node (code graph <-> RTM)."""
    g = Graph()
    fid = "File:factories/dummy/build/greeting.py"
    g.add_node(Node.make(NodeKind.FILE, "factories/dummy/build/greeting.py", "greeting.py", {"loc": 1}))
    cap = Node.make(NodeKind.CAPABILITY, "dummy:greet", "greet")
    art = Node.make(NodeKind.ARTIFACT, "dummy:build/greeting.py", "build/greeting.py")
    g.add_node(cap); g.add_node(art)
    # simulate unify: edge from the File id (not a fresh Artifact) to the capability
    g.add_edge(Edge(fid, cap.id, EdgeKind.IMPLEMENTS))
    assert g.node(fid) is not None
    assert g.reachable(fid, [(EdgeKind.IMPLEMENTS, True)]) == [cap.id]


# ── Fase 3: incrementality ──────────────────────────────────────────────────────
def test_incremental_touch_one_file(tmp_path):
    root = tmp_path
    (root / "src").mkdir()
    (root / "src/a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (root / "src/b.py").write_text("def b():\n    return 2\n", encoding="utf-8")
    roots = ("src",)
    g, store = build_code_graph(root, roots)
    assert len(store) == 2
    # no change -> nothing dirty
    _, _, dirty, reused = incremental_rebuild(root, store, roots)
    assert dirty == [] and sorted(reused) == ["src/a.py", "src/b.py"]
    # touch exactly one file -> only it re-derives
    (root / "src/a.py").write_text("def a():\n    return 99\n", encoding="utf-8")
    _, new_store, dirty, reused = incremental_rebuild(root, store, roots)
    assert dirty == ["src/a.py"]
    assert reused == ["src/b.py"]
    # the reused fragment is the SAME object (not re-parsed)
    assert new_store["src/b.py"] is store["src/b.py"]


def test_incremental_equals_full(tmp_path):
    root = tmp_path
    (root / "src").mkdir()
    (root / "src/a.py").write_text("import x\ndef a():\n    return b()\ndef b():\n    return 1\n", encoding="utf-8")
    g_full, store = build_code_graph(root, ("src",))
    g_inc, _, _, _ = incremental_rebuild(root, {}, ("src",))   # from empty store == full build
    assert g_full.to_dict() == g_inc.to_dict()


# ── Fase 4: deterministic quality gate, two-sided ───────────────────────────────
def test_quality_two_sided_tooth(tmp_path):
    th = Thresholds(max_file_loc=50, max_funcs_per_file=3, max_func_loc=10)
    # RED: a file that blows every limit
    big = "\n".join(["def f{}():".format(i) + "\n    x = 0" * 12 for i in range(6)])
    (tmp_path / "big.py").write_text(big, encoding="utf-8")
    assert evaluate_file(tmp_path, "big.py", th)            # non-empty -> RED
    # GREEN: a small healthy file
    (tmp_path / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    assert evaluate_file(tmp_path, "ok.py", th) == []       # empty -> GREEN


def test_quality_substrate_clean_synthetic_monolith_red():
    th = Thresholds()
    g, _ = build_code_graph(REPO)
    assert evaluate_graph(g, th).clean                       # the live substrate passes (no new monolith)
    # The gate's permanent RED witness is a synthetic monolith-shaped fixture (the real 8.5k-line monolith
    # scaffold_product.py was split into a package in Fase 3 MONOLITH-REFACTOR). It must violate the size
    # metrics under the DEFAULT thresholds, else the gate would be decorative.
    fixture = "tests/fixtures/quality/monolith_shaped.py"
    assert (REPO / fixture).exists()
    viols = evaluate_file(REPO, fixture, th)
    assert {v.metric for v in viols} >= {"funcs", "func_loc"}


def test_factory_codegen_forward_tooth_no_monolith():
    # Fase 3 MONOLITH-REFACTOR forward frontier: authored factory codegen (a glob, no factory named) must
    # not be a size/count monolith. func_loc is EXEMPT (codegen returns long template strings). Post-split,
    # every authored scaffolder file passes — proving the FSK monolith was actually broken up.
    th = replace(Thresholds(), max_func_loc=10 ** 9)
    files = discover_authored_codegen(REPO)
    assert files, "expected to discover authored factory codegen"
    assert not any("/build/" in f or "__pycache__" in f for f in files)
    offenders = {f: evaluate_file(REPO, f, th) for f in files}
    assert all(not v for v in offenders.values()), \
        f"factory codegen monolith(s): {{k: v for k, v in offenders.items() if v}}"


def test_factory_codegen_forward_tooth_fires_on_monolith():
    # RED side: the synthetic monolith-shaped fixture, if it lived in a factory codegen dir, MUST violate
    # the size/count metrics (func_loc exempt) — the tooth is not decorative.
    th = replace(Thresholds(), max_func_loc=10 ** 9)
    viols = evaluate_file(REPO, "tests/fixtures/quality/monolith_shaped.py", th)
    assert {v.metric for v in viols} >= {"funcs"}            # >80 functions trips it; func_loc is exempt


def test_import_cycle_detection():
    g = Graph()
    a = Node.make(NodeKind.FILE, "a.py", "a.py", {}); b = Node.make(NodeKind.FILE, "b.py", "b.py", {})
    g.add_node(a); g.add_node(b)
    assert import_cycles(g) == []
    g.add_edge(Edge(a.id, b.id, EdgeKind.IMPORTS))
    g.add_edge(Edge(b.id, a.id, EdgeKind.IMPORTS))
    assert import_cycles(g) == [["a.py", "b.py"]]


def test_quality_gate_check_passes_and_self_guards():
    from metafactory.verify.checks import quality_gate
    assert quality_gate.main([str(REPO)]) == 0
    # decorative-guard: absurdly lax thresholds make the monolith pass -> the gate must report itself toothless
    lax = '{"max_file_loc": 100000, "max_funcs_per_file": 100000, "max_func_loc": 100000}'
    assert quality_gate.main([str(REPO), lax]) == 1


# ── Fase 5: billing-ledger split ────────────────────────────────────────────────
def test_billing_split_and_roundtrip(tmp_path):
    # single-source pricing (ADR-021, PRICING-LEDGER INC-1): BillingLedger no longer takes a 2-tuple
    # pricing dict — every model is ALWAYS priced via `graph.pricing.PRICING` (opus is now priced > 0,
    # never the old honest-TBD 0.0). Dollars recomputed from the dated table: sonnet 2/10, opus 5/25.
    led = BillingLedger("run-x")
    led.record(LedgerEntry("mod.py", "generate", "sonnet", input_tokens=1000, output_tokens=200, source="harness"))
    led.record(LedgerEntry("design", "brain", "opus", input_tokens=5000, output_tokens=1000, source="estimate"))
    led.record(LedgerEntry("read", "read", "haiku", input_tokens=800, output_tokens=50))
    split = led.split_by_role()
    assert set(split) == {"brain", "generate", "read"}
    assert split["generate"]["models"] == ["sonnet"]
    # sonnet: 1000*2/1e6 + 200*10/1e6 = 0.002 + 0.002 = 0.004
    # opus:   5000*5/1e6 + 1000*25/1e6 = 0.025 + 0.025 = 0.05 (single-source -> priced, not TBD anymore)
    sm = led.split_by_model()
    assert sm["sonnet"]["est_cost_usd"] == pytest.approx(0.004)
    assert sm["opus"]["est_cost_usd"] == pytest.approx(0.05)
    p = led.save(tmp_path / "led.json")
    again = BillingLedger.load(p)
    assert again.totals()["total_tokens"] == led.totals()["total_tokens"]


def test_emitted_ledger_shows_three_model_split():
    """The build's own ledger (closure criterion #4) records the Opus/Sonnet/Haiku split."""
    led = BillingLedger.load(REPO / "docs/work/GRAPH-SPINE-KEYSTONE-billing.json")
    models = set(led.split_by_model())
    assert {"opus", "sonnet", "haiku"} <= models
    roles = set(led.split_by_role())
    assert {"brain", "generate", "read"} <= roles


# ── ADR-026: doc_graph dual-accept header grammar (Estado/ABIERTO/CERRADO + Status/OPEN/CLOSED) ────────
def test_doc_graph_is_exempt_english_closed_header():
    """An English `Status: **CLOSED**` work-doc classifies as exempt/frozen, same as the legacy Spanish
    `Estado: **CERRADO**` case — dual-accept, not a replacement."""
    body_en = "# Incremento\n\n> Status: **CLOSED** (closed 2026-01-01T00:00Z)\n"
    assert is_exempt("docs/work/SOME-INCREMENT.md", body_en) is True
    body_es = "# Incremento\n\n> Estado: **CERRADO** (cerrado 2026-01-01T00:00Z)\n"
    assert is_exempt("docs/work/SOME-INCREMENT.md", body_es) is True


def test_doc_graph_live_roots_english_open_header(tmp_path):
    """An English `Status: **OPEN**` work-doc is picked up as a live root (open increment), same as the
    legacy Spanish `Estado: **ABIERTO**` case."""
    (tmp_path / "docs" / "work").mkdir(parents=True)
    (tmp_path / "docs" / "STATE.md").write_text("# STATE\n", encoding="utf-8")
    en_path = tmp_path / "docs" / "work" / "ENGLISH-INCREMENT.md"
    en_path.write_text("# Incremento\n\n> Status: **OPEN** (creado 2026-01-01T00:00Z)\n", encoding="utf-8")
    es_path = tmp_path / "docs" / "work" / "SPANISH-INCREMENT.md"
    es_path.write_text("# Incremento\n\n> Estado: **ABIERTO** (creado 2026-01-01T00:00Z)\n", encoding="utf-8")
    graph = Graph()
    ingest_docs(graph, tmp_path)
    roots = live_roots(graph, tmp_path)
    assert f"{NodeKind.DOC.value}:docs/work/ENGLISH-INCREMENT.md" in roots
    assert f"{NodeKind.DOC.value}:docs/work/SPANISH-INCREMENT.md" in roots


# ── Fase 6: repo-map (PageRank) ─────────────────────────────────────────────────
def test_repomap_ranks_and_bounds():
    g, _ = build_code_graph(REPO)
    pr = pagerank(g)
    assert abs(sum(pr.values()) - 1.0) < 1e-6
    rf = rank_files(g)
    assert rf and rf == sorted(rf, key=lambda x: (-x[1], x[0]))
    digest = repo_map(g, budget_chars=1500)
    assert len(digest) <= 1500 + 200      # bounded (allow one trailing block)
    assert ".py" in digest
