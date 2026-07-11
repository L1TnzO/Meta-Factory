<!-- meta:doc sha=834edc3d9ac616ce4ba54e083046e3f2da653e32 updated=2026-07-11T05:30Z -->
# Incremento ENGLISH-CLI-STRINGS

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-07-11T05:24Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
F2 batch (b) of ADR-026 / `DOC-CLEANUP-DIRECTION`: the living CLI/user-facing string layer goes English —
verdict grammar `VEREDICTO/RESUMEN/PRÓXIMO → VERDICT/SUMMARY/NEXT` (+ statuses `DESVIADO→DEVIATED`,
`BLOQUEADA→BLOCKED`) across src+tests, the work-doc header grammar goes English FORWARD with dual-accept
parsers (`Estado: **ABIERTO/CERRADO**` history is immutable and must parse forever), and the
F2(a)-deferred column strings (hook deny-messages, `debt()` output) land by the brain's own eyes.

## Scope (measured this session)
| Piece | Measure | Route |
| --- | --- | --- |
| Verdict grammar emitters | 136 occurrences, 11 src files (93 in `cli.py`) + 7 test files; EMIT-ONLY (no parser matches the tokens — verified by grep over `re.compile/search/match/startswith/split`) | slot A (generator) |
| Other user-facing Spanish output in `src/metafactory/**` (check reasons, argparse help, banners incl. SessionStart rehydration header) | ≈494 Spanish-char lines over 55 files (superset incl. comments; only OUTPUT strings in scope) | slot A (generator) |
| `Estado:` header grammar consumers | `seed/lifecycle.py:_OPEN_RE` (the LAW — column) · `graph/doc_graph.py` `_ABIERTO_RE/_CERRADO_RE` · `verify/checks/state_snapshot.py` closure marks · `cli.py` open-template :657 + close-flip :767 · `codegen_freeze` delegates to lifecycle ✓ | lifecycle = by eyes; src consumers = slot B |
| Hook deny-messages + docstrings (`.claude/hooks/` ×12, `template/factory/harness/.claude/hooks/` ×6) + `tests/test_column_full.py` couplings (`Cerrojo N` ×4) | column (trust-chain, ADR-017/SELF-IMPROVEMENT §3) | by eyes + re-materialize m00+m01 ×5 |
| `seed/lifecycle.py` `debt()` strings | 4 strings | by eyes |

## Deliberate NON-scope (honest)
- Spanish CODE COMMENTS/docstrings in `src/metafactory/**` that neither reach a user nor quote the
  grammar: not named by ADR-026 §1 (which scopes *output* strings); they anglicize opportunistically
  under ADR-017's forward rule when their files are next touched. Blanket translation = high semantic-no-op
  risk for zero context-cost gain (they don't enter model context unless the file is read).
- `kind_hygiene.py` «vocabulario CERRADO» = closed-vocabulary sense, not doc grammar — translation only, no
  grammar semantics.
- Frozen factory codegen hits (`factories/full-stack-kotlin/codegen/scaffold/server.py`) — ADR-023 freeze;
  a waiver for string cosmetics is not warranted.
- Immutable docs (closed work docs, decisions/, LOG) keep `Estado: **ABIERTO/CERRADO**` forever — that is
  WHY parsers are dual-accept, never mass-translated (ADR-026 §1).
- Living `reference/` mentions of «Cerrojo» etc.: batch (c) (meta living docs).

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Column by eyes: `seed/lifecycle.py` dual-accept `_OPEN_RE` (`(?:Estado\|Status): **(ABIERTO\|OPEN\|CERRADO\|CLOSED)**`) + English `debt()` strings · 18 hook files' messages/docstrings · `test_column_full.py` sync · re-materialize m00+m01 ×5 (`column_parity` green, `.proof/` diff empty) | ⏳ PARTIAL: lifecycle ✅ (+3 dual-grammar tests) · meta hooks done 4/12: increment_guard, session_start, gate_guard, commit_guard · REMAINING: meta hooks stop_proof, proof_protect, doc_stamp, mem_capture, mem_rollup (+ eyeball context_nudge, verdict_required, blast_radius, pre_compact for accent-less Spanish) · template hooks ×6 (`Cerrojo N`→`Lock N`, sync `test_column_full.py`) · re-materialize m00+m01 ×5 |
| 2 | Slot A → `generator`: user-facing output strings in `src/metafactory/**` → English (exact token map; NO logic/identifier changes) + test-assertion sync. Gate: full pytest + grep-zero `VEREDICTO\|RESUMEN\|PRÓXIMO` in src+tests | ⏳ |
| 3 | Slot B → `generator`: dual-accept in `doc_graph.py`/`state_snapshot.py` + `cli.py` header template & close-flip emit English (`Status: **OPEN/CLOSED**`) + dual-grammar test cases (both grammars recognized open/closed; Spanish-open→English-close flip) | ⏳ |
| 4 | Live proof + close: flip THIS doc's header to `Status: **OPEN**` mid-increment (edit-gate must keep authorizing) → `meta increment close` writes the English close marker | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `grep -rn "VEREDICTO\|RESUMEN\|PRÓXIMO" src/ tests/ seed/ .claude/ template/` → 0 hits.
2. Full pytest green · `meta check` green (incl. `column_parity`, `column_full`, `state_snapshot`,
   `evidence_liveness`) · `git diff .proof/` empty (content-blind proof_sha, as in F2(a)).
3. Dual-accept proven live: this doc closes FROM an English `Status: **OPEN**` header via
   `meta increment close`; the 100+ Spanish-header closed docs still classify as closed
   (`meta doc orphans` / graph build unchanged counts).
4. Slot verdicts on file for A and B (`.gen/*.verdict.json`), accepted on gate exit 0, diffs
   spot-checked as strings-only.
