<!-- meta:doc sha=c28b323880e03de166ce6a749db9fce6f497e6ac updated=2026-07-11T17:43Z -->
# Incremento SLOT-FOOTPRINT-TOOTH

> **Doc de gobierno.** Status: **OPEN** (creado 2026-07-11T17:26Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
Make the delegation boundary HONEST (SOTA-PARITY INC-1, closes GAP-1): slot acceptance becomes
deterministic on the git-OBSERVED change footprint — changes ⊆ `allow_globs ∪ {verdict_path} ∪ .gen/** ∪
baseline_dirty` — closing (a) the **Bash escape** (a `bash -c 'cat > outside.py'` bypassed the PreToolUse
Write-hook; the persisted change is now caught at SubagentStop AND at acceptance) and (b) the **fail-open**
(`except: return 0` in both hooks while a slot was active → now manifest-present + law/manifest/git
undecidable = exit 2, FAIL-CLOSED), and DECLARING the irreducible residual (transient Bash side-effects)
in `HONEST-STATE §7` with its OS-sandbox trigger. Column work (trust-chain): written and reviewed with the
brain's own eyes, never delegated (SELF-IMPROVEMENT §3). Design implemented verbatim from
`SOTA-PARITY-DIRECTION-INCREMENT.md §4 INC-1`.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | **The law** (`seed/delegation.py`, single-source, propagated by M1 `copy_seed`): PURE `footprint_problems(slot, changed_paths)` (no subprocess in the law — the transport collects `git status --porcelain -uall`); `write_slot(root, manifest, baseline_dirty=None)` records the paths already dirty at slot-open (pre-dirty tree can't false-red); `manifest_problems` validates `baseline_dirty` shape. Accessor `src/metafactory/delegation.py` re-exports. | ✅ |
| 2 | **Transports fail-closed + footprint** (`.claude/hooks/{blast_radius,verdict_required}.py`, byte-identical in `template/factory/harness/`): manifest ABSENT → inert (exit 0, unchanged); manifest PRESENT + law/manifest broken → **exit 2** (was fail-OPEN); `verdict_required` additionally collects the git footprint (repo-prefix re-based for factory-inside-repo roots, both rename sides, `-uall`) and blocks any out-of-slot persisted change. | ✅ |
| 3 | **Gate `slot_footprint`** (`verify/checks/slot_footprint.py` + row in `cmd_check` — a `command` row like `pbt`/`security`, no station-KIND vocab change): GREEN side (clean synthetic fixture → `[]`) · RED side (out-of-slot path MUST be flagged, else decorative) · FAIL-CLOSED witness (real hooks vs synthetic root with broken law → exit 2; no manifest → exit 0). `--live` mode = the acceptance re-check (belt over suspenders, catches a generator killed mid-flight). | ✅ |
| 4 | **Callers**: `generate-slot` skill (record `baseline_dirty` at slot-open; green verdict → run `slot_footprint --live` BEFORE accepting; honest-residual note) · `orchestrator.md` (footprint claim now honest; acceptance step; + INC-6's batched repomap-first line — one column stretch, prefix-hygiene (e)) · `generator.md` (hard-rule: Bash writes are caught at stop; scratch goes under `.gen/`). | ✅ |
| 5 | **Propagation + residual**: re-materialize m00→m01 ×5 (agent-systems-factory·dummy·full-stack·full-stack-kotlin·iot) → `column_parity`/`column_full`/`least_priv` green; `HONEST-STATE §7` declares the transient-side-effects residual + trigger for OS-sandbox (INC-7 hard version). | ✅ |
| 6 | **Proof**: tests (law pure + hooks subprocess: footprint block/unblock, fail-closed ×3 synthetic roots) · `meta check` 22/22 · LIVE witness: scratch generator escapes via Bash → SubagentStop exit 2 traced → cleans up → passes. | ✅ |

## Criterio de cierre (demostrable, no narrable)
1. `meta check` green **including new gate `slot_footprint` both sides** → **22/22 green**
   (`.meta_check/metacheck-2026-07-11T1740Z.log`; suite 53 passed in `tests/test_delegation.py` alone).
2. Live proof by blocking: scratch slot `live-footprint-proof` (with `baseline_dirty`=31 in-progress paths);
   generator (Sonnet, agent `a5ed5500654009604`) created `zz_live_escape.tmp` via Bash (Write-hook blind,
   confirmed) → tried to stop → **SubagentStop BLOCKED**, first line traced verbatim:
   `verdict_required: out-of-slot change footprint (SLOT-FOOTPRINT-TOOTH) — a slot is only accepted when
   git-observed changes ⊆ allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty:` → removed the escape →
   stopped cleanly; acceptance re-check `slot_footprint --live` exit 0 (`footprint ⊆ contract, 32 paths`);
   green verdict with `acceptance_exit_code: 0`; slot cleared, scratch removed.
3. Fail-closed proven deterministically: `test_hooks_fail_closed_when_law_broken` /
   `_on_malformed_manifest` / `_inert_without_manifest_even_if_law_broken` (synthetic roots, real hook
   subprocesses) + the gate's standing witness re-run on every `meta check`.
4. Factories inherit byte-identically: m00+m01 ×5 PASS, `column_parity` green (drift = red tooth intact);
   exactly `seed/delegation.py` + the 2 hooks changed per factory (`git status` bounded).
5. Residual DECLARED, not silent: `HONEST-STATE §7` entry with the INC-7 trigger (first security-sensitive
   slot or first observed escape). Estimated ≈150 LOC design → actual: law ~35 + hooks ~60 + gate ~150
   (gate includes the standing fail-closed witness, beyond the design's minimum).
