"""doc_graph — ADR-026 Fase F1 (DOC-GRAPH-LIVENESS): fold the doc corpus into the project graph as Doc
nodes + `CITES` (Doc -> Doc) / `EVIDENCES` (Doc -> File/Artifact) edges, so "is this doc still
referenced?" is a graph query, not a literal grep (a literal grep produced a FALSE orphan for
`PLAN-EXECUTE-RUNBOOK.md`, cited bare — no `.md`, no backticks — from `cli.py:1104`).

Scope boundary (read before touching `evidence_liveness`): the MANDATORY tooth gates ONLY CITES-shaped
tokens (`.md` paths and bare `ADR-NNN`) found in LIVING (non-exempt) docs. `EVIDENCES` targets (arbitrary
code/proof paths a doc mentions) are recorded when they happen to exist, but their ABSENCE is NEVER
gated — many are legitimately ephemeral/gitignored (`.proof/`, `.gen/`, build output); gating them would
manufacture false reds unrelated to doc rot.

Robust ID matching (`ingest_doc_edges`): a doc may be cited by its full path, path-minus-`.md`, bare
basename, or (for ADRs) `ADR-NNN` — resolution tries each in a deterministic order, falling back to
filesystem existence and a repo-wide basename search before giving up.
"""
from __future__ import annotations

import os
import posixpath
import re
import subprocess
from pathlib import Path, PurePosixPath

from .. import docs_manifest
from .model import Edge, EdgeKind, Graph, Node, NodeKind

_SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", ".proof", ".gen", ".graph", ".pytest_cache"}
_ASF_DIRNAME = "Agent_Systems_Factory"

# Same one-liner `ingest.py` uses for ADR filenames — duplicated locally (that name is private there).
_ADR_FILE_RE = re.compile(r"^(\d{1,4})-")

_MD_LINK_RE = re.compile(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
_MD_BACKTICK_RE = re.compile(r"`([^`\s]+\.md)`")
_ADR_CITE_RE = re.compile(r"(?<!ASF/)\bADR-0*(\d{1,4})\b")

_CERRADO_RE = re.compile(r"Estado:\s*\*\*CERRADO\*\*")
_ABIERTO_RE = re.compile(r"Estado:\s*\*\*ABIERTO\*\*")

_BAD_CHARS = "*<>~…"
_BAD_DOTDOT_RE = re.compile(r"\.\.(?!/)")


# ── Doc node ingestion ───────────────────────────────────────────────────────
def ingest_docs(graph: Graph, repo_root: Path) -> int:
    """One Doc node per doc in `docs_manifest.doc_homes()` x `doc_set()` (reuse, single source — do not
    re-glob). attrs: relpath (POSIX, repo-relative), last_edit (`git log -1 --format=%cI -- <path>`,
    cwd=repo_root; "" if the command fails or is empty — never raise), exempt (bool, see `is_exempt`).
    Returns the count of Doc nodes added."""
    repo_root = Path(repo_root)
    n = 0
    for home in docs_manifest.doc_homes(repo_root):
        is_meta = home == repo_root
        for d in docs_manifest.doc_set(home, meta_extras=is_meta):
            rel = d.relative_to(repo_root).as_posix()
            text = d.read_text(encoding="utf-8")
            body = docs_manifest.split_seal(text)[1]
            attrs = {
                "relpath": rel,
                "last_edit": _last_edit(repo_root, rel),
                "exempt": is_exempt(rel, body),
            }
            graph.add_node(Node.make(NodeKind.DOC, rel, rel, attrs))
            n += 1
    return n


def _last_edit(repo_root: Path, rel: str) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", rel],
            cwd=repo_root, capture_output=True, text=True,
        )
    except OSError:
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout.strip()


def is_exempt(relpath: str, body: str) -> bool:
    """A doc is exempt from `evidence_liveness` (LIVING docs must resolve; these three classes don't):
    (a) `"decisions"` is a path part (immutable ADRs), (b) basename == "LOG.md" (append-only), (c) a
    `"work"` path part AND `body` matches `r"Estado:\\s*\\*\\*CERRADO\\*\\*"` (closed increment, frozen)."""
    p = PurePosixPath(relpath)
    if "decisions" in p.parts:
        return True
    if p.name == "LOG.md":
        return True
    if "work" in p.parts and _CERRADO_RE.search(body):
        return True
    return False


# ── extraction ────────────────────────────────────────────────────────────────
def _dropped(tok: str) -> bool:
    if any(c in tok for c in _BAD_CHARS):
        return True
    if _BAD_DOTDOT_RE.search(tok):
        return True
    return False


def extract_refs(body: str) -> list[tuple[str, str]]:
    """Pure regex extraction, no filesystem access. Returns (kind, token) pairs, kind in {"md", "adr"}:
    - "md": every markdown-link target ending `.md` AND every backtick-wrapped token ending `.md`.
    - "adr": every bare `ADR-NNN` NOT preceded by `ASF/` (`ASF/ADR-NNN` cites the sibling
      Agent_Systems_Factory repo's OWN decisions — out of scope, never extracted at all).
    A token (either kind) is DROPPED (never yielded) if it contains any of `*`, `<`, `>`, `~`, the
    unicode ellipsis `…`, OR a mid-token `..` not immediately followed by `/` (glob/placeholder prose
    like `docs/*.md`, `work/<incremento>.md`, `S0..S15-INCREMENT.md`; a genuine `../` parent-relative
    path like `../INDEX.md` must still be YIELDED — only bare mid-token `..` ranges are placeholder noise)."""
    refs: list[tuple[str, str]] = []
    for m in _MD_LINK_RE.finditer(body):
        tok = m.group(1)
        if not _dropped(tok):
            refs.append(("md", tok))
    for m in _MD_BACKTICK_RE.finditer(body):
        tok = m.group(1)
        if not _dropped(tok):
            refs.append(("md", tok))
    for m in _ADR_CITE_RE.finditer(body):
        tok = m.group(1)
        if not _dropped(tok):
            refs.append(("adr", tok))
    return refs


# ── ADR decisions table ────────────────────────────────────────────────────────
def _decisions_table(repo_root: Path) -> dict[int, str]:
    """{adr_num: relpath} from `docs/decisions/*.md` filenames matching `^(\\d{1,4})-` (same regex
    `ingest.py` uses for ADR ingestion — duplicated locally, `_ADR_FILE_RE`)."""
    repo_root = Path(repo_root)
    decisions_dir = repo_root / "docs" / "decisions"
    table: dict[int, str] = {}
    if not decisions_dir.is_dir():
        return table
    for md in sorted(decisions_dir.glob("*.md")):
        m = _ADR_FILE_RE.match(md.name)
        if not m:
            continue
        table[int(m.group(1))] = md.relative_to(repo_root).as_posix()
    return table


# ── edge resolution ───────────────────────────────────────────────────────────
def _lookup_table(doc_nodes: list[Node]) -> dict[str, str]:
    """{relpath, relpath-minus-.md, basename, basename-minus-.md} -> doc node id, first (sorted-id) wins."""
    table: dict[str, str] = {}
    for n in doc_nodes:
        rel = n.attrs["relpath"]
        base = PurePosixPath(rel).name
        for key in (rel, _strip_md(rel), base, _strip_md(base)):
            table.setdefault(key, n.id)
    return table


def _strip_md(s: str) -> str:
    return s[:-3] if s.endswith(".md") else s


def _rel_str(path: Path, repo_root: Path) -> str:
    """A stable, repo-relative-ish POSIX label for a resolved filesystem path (works for the ASF
    sibling too, via `os.path.relpath`, e.g. `../Agent_Systems_Factory/.claude/agents/x.md`)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return Path(os.path.relpath(path.resolve(), repo_root.resolve())).as_posix()


def _fs_hit(path: Path, repo_root: Path, graph: Graph) -> tuple[str, bool]:
    rel = _rel_str(path, repo_root)
    doc_id = f"{NodeKind.DOC.value}:{rel}"
    if graph.node(doc_id) is not None:
        return doc_id, True
    return rel, False


def _resolve_md(tok: str, citing_dir: PurePosixPath, lookup: dict[str, str],
                 repo_root: Path, asf_root: Path, graph: Graph) -> tuple[str, bool] | None:
    joined = posixpath.normpath(posixpath.join(str(citing_dir), tok))
    for candidate in (joined, tok, PurePosixPath(tok).name):
        hit = lookup.get(candidate)
        if hit:
            return hit, True

    fs_candidates = [repo_root / citing_dir / tok, repo_root / tok, asf_root / tok]
    for c in fs_candidates:
        if c.is_file():
            return _fs_hit(c, repo_root, graph)

    basename = PurePosixPath(tok).name
    for root in (repo_root, asf_root):
        if not root.is_dir():
            continue
        matches = sorted(
            p for p in root.rglob(basename)
            if not (set(p.relative_to(root).parts) & _SKIP_DIRS)
        )
        if matches:
            return _fs_hit(matches[0], repo_root, graph)
    return None


def ingest_doc_edges(graph: Graph, repo_root: Path) -> tuple[int, int, list[tuple[str, str]]]:
    """For every Doc node (sorted by id, deterministic), read its body (`docs_manifest.split_seal`), run
    `extract_refs`, and resolve each token — see the module docstring for the resolution order. Returns
    `(n_cites, n_evidences, unresolved)`. `unresolved` is the SOLE input `evidence_liveness` reads — the
    gate must NOT re-implement extraction/resolution, it must call this function and filter by
    `graph.node(f"{NodeKind.DOC.value}:{rel}").attrs["exempt"]`."""
    repo_root = Path(repo_root)
    asf_root = repo_root.parent / _ASF_DIRNAME
    decisions = _decisions_table(repo_root)
    doc_nodes = sorted(graph.nodes_of(NodeKind.DOC), key=lambda n: n.id)
    lookup = _lookup_table(doc_nodes)

    n_cites = 0
    n_evidences = 0
    unresolved: list[tuple[str, str]] = []

    for doc in doc_nodes:
        rel = doc.attrs["relpath"]
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        body = docs_manifest.split_seal(text)[1]
        citing_dir = PurePosixPath(rel).parent

        for kind, tok in extract_refs(body):
            if kind == "md":
                hit = _resolve_md(tok, citing_dir, lookup, repo_root, asf_root, graph)
                if hit is None:
                    unresolved.append((rel, tok))
                    continue
                hit_id, is_doc = hit
                if is_doc:
                    graph.add_edge(Edge(doc.id, hit_id, EdgeKind.CITES))
                    n_cites += 1
                else:
                    file_id = f"{NodeKind.FILE.value}:{hit_id}"
                    if graph.node(file_id) is not None:
                        art_id = file_id
                    else:
                        art_node = Node.make(NodeKind.ARTIFACT, hit_id, hit_id, {"exists": True})
                        graph.add_node(art_node)
                        art_id = art_node.id
                    graph.add_edge(Edge(doc.id, art_id, EdgeKind.EVIDENCES))
                    n_evidences += 1
            else:  # "adr"
                num = int(tok)
                dec_rel = decisions.get(num)
                dec_doc_id = f"{NodeKind.DOC.value}:{dec_rel}" if dec_rel else None
                if dec_doc_id and graph.node(dec_doc_id) is not None:
                    graph.add_edge(Edge(doc.id, dec_doc_id, EdgeKind.CITES))
                    n_cites += 1
                else:
                    unresolved.append((rel, f"ADR-{tok}"))
    return n_cites, n_evidences, unresolved


# ── liveness (reachability) ────────────────────────────────────────────────────
def live_roots(graph: Graph, repo_root: Path) -> set[str]:
    """Doc node ids considered inherently live: `docs/STATE.md` of every `doc_homes()` home + `CLAUDE.md`
    of every home that has one + any Doc whose body matches `r"Estado:\\s*\\*\\*ABIERTO\\*\\*"` (an open
    increment)."""
    repo_root = Path(repo_root)
    roots: set[str] = set()
    for home in docs_manifest.doc_homes(repo_root):
        state = home / "docs" / "STATE.md"
        if state.is_file():
            roots.add(f"{NodeKind.DOC.value}:{state.relative_to(repo_root).as_posix()}")
        claude = home / "CLAUDE.md"
        if claude.is_file():
            roots.add(f"{NodeKind.DOC.value}:{claude.relative_to(repo_root).as_posix()}")
    for doc in graph.nodes_of(NodeKind.DOC):
        rel = doc.attrs.get("relpath", "")
        path = repo_root / rel
        if not path.is_file():
            continue
        body = docs_manifest.split_seal(path.read_text(encoding="utf-8"))[1]
        if _ABIERTO_RE.search(body):
            roots.add(doc.id)
    return roots


def reachable_docs(graph: Graph, repo_root: Path) -> set[str]:
    """Forward BFS over CITES edges (Doc -> Doc only) from `live_roots()`, returns the closure INCLUDING
    the roots themselves. Bounded fixed-point loop (a few hundred nodes, no external library needed)."""
    seen = set(live_roots(graph, repo_root))
    frontier = list(seen)
    while frontier:
        nxt: list[str] = []
        for nid in frontier:
            for e in graph.out_edges(nid, EdgeKind.CITES):
                if e.dst not in seen:
                    seen.add(e.dst)
                    nxt.append(e.dst)
        frontier = nxt
    return seen


def orphan_docs(graph: Graph, repo_root: Path) -> list[dict]:
    """Every Doc node whose id is NOT in `reachable_docs()`, as `{"relpath": ..., "last_edit": ...}`,
    sorted by `last_edit` ascending (oldest first; unknown/empty dates sort LAST)."""
    reachable = reachable_docs(graph, repo_root)
    orphans = [
        {"relpath": d.attrs.get("relpath", ""), "last_edit": d.attrs.get("last_edit", "")}
        for d in graph.nodes_of(NodeKind.DOC) if d.id not in reachable
    ]
    orphans.sort(key=lambda o: (o["last_edit"] == "", o["last_edit"]))
    return orphans
