<!-- meta:doc sha=29ab1ca997ad36573e59e8b8fa54e51499cd4eca updated=2026-07-11T03:20Z -->
# Incremento DOC-GRAPH-LIVENESS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-11T00:56Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
F1 of `work/DOC-CLEANUP-DIRECTION-INCREMENT.md` (ADR-026): fold the doc set into the project graph as
Doc nodes + `CITES`/`EVIDENCES` edges with robust ID matching, add the two-sided gate `evidence_liveness`
to `meta check` (LIVING docs' path refs must resolve), and add the non-gating observer `meta doc orphans`
(unreachable-from-live-roots + real last-edit date → candidates, not reds).

## Design (fixed here — this is the contract; the generator implements it, does not re-derive it)

**New module** `src/metafactory/graph/doc_graph.py` (own file — the 2026-06-25 multi-file rule):
- `model.py`: add `NodeKind.DOC = "Doc"` and `EdgeKind.CITES = "CITES"` (Doc→Doc) + `EdgeKind.EVIDENCES =
  "EVIDENCES"` (Doc→File/Artifact, best-effort — see boundary below).
- `ingest_docs(graph, repo_root) -> int` — one Doc node per doc in `docs_manifest.doc_homes()` ×
  `doc_set()` (reuse, single-source discovery — no new doc-set logic). `attrs`: `relpath`, `last_edit`
  (git `log -1 --format=%cI`, or `""` if uncommitted), `exempt` (bool — see exemption rule below).
- `extract_refs(body) -> list[tuple[str,str]]` — pure regex, `(kind, token)` pairs, `kind ∈ {"md","adr"}`:
  - `"md"`: markdown-link targets `](...\.md)` **and** backtick-wrapped `` `...\.md` `` tokens.
  - `"adr"`: bare `ADR-NNN` **not** preceded by `ASF/` (negative lookbehind — `ASF/ADR-NNN` cites the
    SIBLING project's own decisions, out of this repo, never gated here).
  - Skip (never even attempted) any token containing `*`, `<`, `>`, `~`, or the unicode ellipsis `…`
    (glob/placeholder prose, e.g. `` `docs/*.md` ``, `` `work/<incremento>.md` ``), or containing a
    mid-token `..` **not** immediately followed by `/` (a range like `S0..S15`, not a `../` parent path —
    `../INDEX.md` must still be attempted).
- `ingest_doc_edges(graph, repo_root) -> tuple[int, int, list[tuple[str,str]]]` — for every Doc node,
  read its body, extract refs, resolve each `"md"` token in this order: (1) path relative to the citing
  doc's directory, (2) the literal repo-relative path, (3) bare-basename match against known Doc ids,
  (4) filesystem existence fallback (citing-dir-relative, repo-root-relative, **and**
  `repo_root.parent / "Agent_Systems_Factory"` for legitimate cross-repo ASF citations — CLAUDE.md's
  documented `ASF/ADR-NNN` convention extends to non-ADR paths too, e.g. `.claude/agents/factory-writer.md`),
  (5) repo-wide basename search (`rglob`, excluding `.git/__pycache__/node_modules/dist/.proof/.gen/
  .graph/.pytest_cache`, first sorted match) — this is what makes `column.md`/`greet.md`/`INDEX.md`/
  adopted-product docs (e.g. `PROVENANCE.md`) resolve without being sealed Doc nodes. A resolved target
  that IS a Doc node → `CITES` edge; a resolved target that is some OTHER existing file → `EVIDENCES`
  edge (reuse the FILE node if the code graph already indexed it, else mint an `ARTIFACT` node — mirror
  `ingest_rtm`'s unify-or-mint pattern in `ingest.py`). `"adr"` tokens resolve against a `decisions/NNN-*`
  table (same `^(\d{1,4})-` filename regex `ingest.py` already uses) → `CITES`. Return `(n_cites,
  n_evidences, unresolved)` where `unresolved` is **only** the `"md"`/`"adr"`-shaped tokens that failed
  ALL of the above — this exact list is the gate's red-side input (single source, the gate does not
  re-derive extraction).
- `live_roots(graph, repo_root) -> set[str]` (Doc ids) — `docs/STATE.md` + `CLAUDE.md` of every doc-home,
  plus any work/ Doc whose body matches `Estado:\s*\*\*ABIERTO\*\*` (open increment).
- `reachable_docs(graph, repo_root) -> set[str]` — forward BFS over `CITES` edges from `live_roots()`
  (`Graph.reachable` already does one-hop; loop it to a fixed point — bounded, the doc graph is a few
  hundred nodes).
- `orphan_docs(graph, repo_root) -> list[dict]` — every Doc node id not in `reachable_docs()`, each as
  `{"relpath":…, "last_edit":…}`, sorted by `last_edit` (oldest first — the archive-candidate order).

**Exemption rule** (`exempt` attr, ADR-026's doc-mutation-by-type given teeth): a Doc is exempt from the
`evidence_liveness` gate iff its relpath has `"decisions"` as a path part (immutable), OR its basename is
`LOG.md` (append-only), OR it is under a `work/` dir AND its body matches `Estado:\s*\*\*CERRADO\*\*`
(closed increment — frozen like a decision). Everything else is LIVING and its refs must resolve.

**Gate** `src/metafactory/verify/checks/evidence_liveness.py` (mirror `quality_gate.py`'s two-sided
shape), argv `[repo_root]`:
- GREEN — `ingest_docs` + `ingest_doc_edges` over the real repo; for every `(rel, token)` in `unresolved`
  whose Doc is NOT exempt, print `{rel}: unresolved reference {token!r}` and exit 1 if any.
- RED witness (two-sided tooth) — a synthetic LIVING-shaped fixture
  `tests/fixtures/docs/dangling_reference.md` (own file, NOT under any `doc_homes()` home so it never
  pollutes the real doc set/INDEX) containing one deliberately-broken backtick `.md` reference. The gate
  scans JUST this fixture (reusing the same extract+resolve primitives against the real repo's Doc-id
  table, so the fixture's target genuinely does not exist anywhere) and must find it unresolved — if it
  came back clean the gate is decorative → gate FAILS (same idiom as `quality_gate.py`'s
  `monolith_shaped.py` witness).
- Wire as check `"evidence_liveness"` in `cmd_check`'s `checks` list (`cli.py`, `kind: "command"`,
  alongside `docs`/`quality`/`pbt` — same pattern, no new `KINDS` entry needed).

**Observer** (non-gating) — `meta doc orphans` CLI subcommand (`cmd_doc_orphans` in `cli.py`, new
`doc` sub-parser or extend an existing `doc_slice`-style group): builds the doc graph, prints
`orphan_docs()` as a table (`relpath · last_edit`), never a red exit (informational — feeds F3
DRIFT-AUDIT). Exit 0 always.

**Tests** `tests/test_doc_liveness.py` (renamed from the originally-planned *test_doc_graph* — the "graph"
stem collides with `affected_tests`' name-match heuristic, over-selecting it for `graph/build.py` changes
it does not import, breaking `test_graph_affected_pbt.py`'s heuristic-⊆-precise property): `extract_refs`
unit cases (markdown-link, backtick, bare ADR, ASF/
lookbehind, each exclusion filter) · `ingest_docs`+`ingest_doc_edges` over a tmp_path fixture tree (a
handful of synthetic docs exercising CITES/EVIDENCES/unresolved) · `live_roots`/`reachable_docs`/
`orphan_docs` over the same fixture · the gate's RED witness (`tests/fixtures/docs/dangling_reference.md`
IS flagged) AND a GREEN case (a fixture with only resolving refs is NOT flagged).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `graph/model.py` +DOC/+CITES/+EVIDENCES · `graph/doc_graph.py` (ingest+resolve+reachability+orphans) · `tests/test_doc_liveness.py` | ✅ |
| 2 | `verify/checks/evidence_liveness.py` (two-sided) + `tests/fixtures/docs/dangling_reference.md` + wire into `cmd_check` | ✅ |
| 3 | `meta doc orphans` CLI observer (`cli.py`) | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `pytest -q tests/test_doc_liveness.py` green; `evidence_liveness` gate green over the REAL repo (the
   pre-existing rot instances found in-session were fixed in the main thread — a dangling mention of the
   pruned *START-HERE.md* in MEMORY-ARCHITECTURE.md, a wrong decision filename — *…two-domain-parity…* for
   `014-paridad-de-dos-dominios.md` — in MATURITY-PLAN.md, and a proposed-but-never-created
   *metrics/SUMMARY* doc cited as real in OBSERVABILITY-METRICS.md; the gate itself caught the residue of
   the first fix attempt, proving the tooth before it ever landed).
2. `evidence_liveness`'s RED witness (`tests/fixtures/docs/dangling_reference.md`) fires (two-sided, not
   decorative) — verified independently, not narrated.
3. `meta doc orphans` runs, exits 0, prints ≥1 real orphan candidate with a real (non-empty) `last_edit`.
4. `meta check` full suite green (20/20 → 21/21 with `evidence_liveness` added).
