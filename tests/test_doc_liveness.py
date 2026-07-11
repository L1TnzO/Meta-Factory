"""test_doc_liveness — ADR-026 Fase F1 (DOC-GRAPH-LIVENESS): the doc corpus folded into the project graph
as Doc nodes + CITES/EVIDENCES edges, robust ID matching, liveness/reachability, and the two-sided
`evidence_liveness` gate. Small, fast, tmp_path-based for the unit surface + a real-repo integration proof.
"""
from __future__ import annotations

from pathlib import Path

from metafactory._seed import repo_root
from metafactory.graph.doc_graph import (
    extract_refs,
    ingest_doc_edges,
    ingest_docs,
    is_exempt,
    live_roots,
    orphan_docs,
    reachable_docs,
)
from metafactory.graph.model import Graph, Node, NodeKind
from metafactory.verify.checks import evidence_liveness


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ── extract_refs ──────────────────────────────────────────────────────────────
def test_extract_refs_md_link():
    assert extract_refs("See [x](docs/foo.md) for details.") == [("md", "docs/foo.md")]


def test_extract_refs_md_backtick():
    assert extract_refs("See `docs/bar.md` for details.") == [("md", "docs/bar.md")]


def test_extract_refs_asf_adr_not_extracted():
    assert extract_refs("See ASF/ADR-006 for the sibling repo's own decision.") == []


def test_extract_refs_bare_adr_extracted():
    assert extract_refs("See ADR-007 for the rationale.") == [("adr", "7")]


def test_extract_refs_drops_glob_star():
    assert extract_refs("see `docs/*.md`") == []


def test_extract_refs_drops_angle_brackets():
    assert extract_refs("see `work/<incremento>.md`") == []


def test_extract_refs_drops_tilde():
    assert extract_refs("see `docs/~backup.md`") == []


def test_extract_refs_drops_ellipsis():
    assert extract_refs("see `docs/…continued.md`") == []


def test_extract_refs_drops_mid_token_dotdot():
    assert extract_refs("see `S0..S15-INCREMENT.md`") == []


def test_extract_refs_keeps_genuine_parent_relative():
    assert extract_refs("see `../INDEX.md`") == [("md", "../INDEX.md")]


# ── ingest_docs + ingest_doc_edges ─────────────────────────────────────────────
def _build_ingest_tree(tmp_path: Path) -> Path:
    """docs/STATE.md -> [notes](docs/reference/NOTES.md) + `column.md` (EVIDENCES, real non-doc .md
    outside doc_homes()) + a broken `docs/work/MISSING.md`; docs/reference/NOTES.md -> ../work/GUIDE.md;
    docs/work/GUIDE.md is a leaf."""
    _write(tmp_path / "docs" / "STATE.md", (
        "# STATE\n\n"
        "See [notes](docs/reference/NOTES.md) for details.\n"
        "Also see `column.md` for the substrate glossary.\n"
        "Broken: `docs/work/MISSING.md` does not exist.\n"
    ))
    _write(tmp_path / "docs" / "reference" / "NOTES.md", (
        "# Notes\n\nPoints to `../work/GUIDE.md`.\n"
    ))
    _write(tmp_path / "docs" / "work" / "GUIDE.md", "# Guide\n\nNo further citations.\n")
    _write(tmp_path / "column.md", "# column\n\nnot a sealed doc, a real file.\n")
    return tmp_path


def test_ingest_docs_counts_three(tmp_path):
    root = _build_ingest_tree(tmp_path)
    graph = Graph()
    n = ingest_docs(graph, root)
    assert n == 3
    rels = {d.attrs["relpath"] for d in graph.nodes_of(NodeKind.DOC)}
    assert rels == {"docs/STATE.md", "docs/reference/NOTES.md", "docs/work/GUIDE.md"}


def test_ingest_doc_edges_cites_evidences_unresolved(tmp_path):
    root = _build_ingest_tree(tmp_path)
    graph = Graph()
    ingest_docs(graph, root)
    n_cites, n_evidences, unresolved = ingest_doc_edges(graph, root)
    assert n_cites == 2       # STATE->NOTES (md link), NOTES->GUIDE (backtick, ../ relative)
    assert n_evidences == 1   # STATE-> column.md (real file, not a Doc node)
    assert unresolved == [("docs/STATE.md", "docs/work/MISSING.md")]


# ── is_exempt ──────────────────────────────────────────────────────────────────
def test_is_exempt_decisions():
    assert is_exempt("docs/decisions/001-foo.md", "# Foo\n") is True


def test_is_exempt_log():
    assert is_exempt("docs/LOG.md", "# LOG\n") is True


def test_is_exempt_cerrado_work_doc():
    body = "# Incremento\n\n> Estado: **CERRADO** (cerrado 2026-01-01T00:00Z)\n"
    assert is_exempt("docs/work/SOME-INCREMENT.md", body) is True


def test_is_exempt_false_for_living_reference_doc():
    assert is_exempt("docs/reference/GUIDE.md", "# Guide\n") is False


def test_is_exempt_false_for_open_work_doc():
    body = "# Incremento\n\n> Estado: **ABIERTO** (creado 2026-01-01T00:00Z)\n"
    assert is_exempt("docs/work/SOME-INCREMENT.md", body) is False


# ── live_roots / reachable_docs / orphan_docs ──────────────────────────────────
def _build_reach_tree(tmp_path: Path) -> Path:
    """STATE.md -[CITES]-> a.md -[CITES]-> b.md (2-hop chain, b.md not directly cited by the root); a
    stand-alone orphan.md that nobody cites."""
    _write(tmp_path / "docs" / "STATE.md", "# STATE\n\nSee [a](docs/a.md).\n")
    _write(tmp_path / "docs" / "a.md", "# A\n\nSee `docs/b.md`.\n")
    _write(tmp_path / "docs" / "b.md", "# B\n\nA leaf, no citations.\n")
    _write(tmp_path / "docs" / "orphan.md", "# Orphan\n\nNobody cites this doc.\n")
    return tmp_path


def test_live_roots_includes_state(tmp_path):
    root = _build_reach_tree(tmp_path)
    graph = Graph()
    ingest_docs(graph, root)
    roots = live_roots(graph, root)
    assert f"{NodeKind.DOC.value}:docs/STATE.md" in roots


def test_reachable_docs_transitive_chain_not_orphan(tmp_path):
    root = _build_reach_tree(tmp_path)
    graph = Graph()
    ingest_docs(graph, root)
    ingest_doc_edges(graph, root)
    reach = reachable_docs(graph, root)
    assert f"{NodeKind.DOC.value}:docs/b.md" in reach


def test_orphan_docs_flags_uncited_doc(tmp_path):
    root = _build_reach_tree(tmp_path)
    graph = Graph()
    ingest_docs(graph, root)
    ingest_doc_edges(graph, root)
    orphans = {o["relpath"] for o in orphan_docs(graph, root)}
    assert "docs/orphan.md" in orphans
    assert "docs/b.md" not in orphans


# ── integration: the real repo + the RED witness ───────────────────────────────
def test_real_repo_evidence_liveness_green():
    assert evidence_liveness.main([str(repo_root())]) == 0


def test_red_witness_fixture_is_unresolved():
    root = repo_root()
    graph = Graph()
    ingest_docs(graph, root)
    fixture_rel = "tests/fixtures/docs/dangling_reference.md"
    graph.add_node(Node.make(
        NodeKind.DOC, fixture_rel, fixture_rel, {"relpath": fixture_rel, "exempt": False}))
    _, _, unresolved = ingest_doc_edges(graph, root)
    toks = [tok for rel, tok in unresolved if rel == fixture_rel]
    assert toks, "the fixture's own dangling reference should be unresolved"
