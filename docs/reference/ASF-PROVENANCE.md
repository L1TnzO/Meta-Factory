<!-- meta:doc sha=ecb890708027ef386179de0482967ec7aa7a02ca updated=2026-07-11T16:01Z -->
# ASF — provenance pin of the frozen reference

> type: reference (stable) · created: 2026-06-15T02:48Z
> Content-addressed pin of the original ASF (harvested source + parity oracle). The engineer's
> decision (2026-06-14, after closing ASF-REGEN): **pin identity, do NOT copy the tree**. It makes
> "exactly what was harvested/compared" immutable and verifiable without dragging 60M/1.1G into
> the repo. Consistent with ADR-006 (ASF frozen, untouched) and ADR-009's content-addressing /
> `proof_sha`.

## The pin

| Field | Value |
| --- | --- |
| commit | `b1fcb1ff26ac7c960361042bac7dd9ae82bc6a2f` |
| tree | `1a47adc816abaeae068bea2f0d42bbab91ac6ca9` |
| branch | `feat/v2-source-grounding` |
| HEAD msg | `build(s08): s08 — gate opened` |
| location | `../../Agent_Systems_Factory/` (SIBLING git repo, OUTSIDE the Meta-Factory) |
| dirty when pinned | only `.claude/memory/journal.jsonl` (ephemeral, session journal — NOT material for the harvest) |
| size | 60M without `.git`/`.venv` · 1.1G with |

## Verify the pin (two verifiers; arithmetic, no model)

```
git -C ../../Agent_Systems_Factory rev-parse HEAD        # → b1fcb1ff26ac7c960361042bac7dd9ae82bc6a2f
git -C ../../Agent_Systems_Factory rev-parse 'HEAD^{tree}'# → 1a47adc816abaeae068bea2f0d42bbab91ac6ca9
```

If they differ, the reference changed since the harvest: re-read the delta before trusting any
parity judgment or `reference/ASF-LESSONS.md` / `reference/REGEN-AUDIT.md`.

## Why pin and not copy (the decision, recorded)

- **The SHA is ALREADY the immutable identity**: git hashes the tree+history. Copying it in either
  nests a second `.git` (dirty) or flattens it and **loses the history** → it would end up *less*
  frozen.
- **Its value is being an INDEPENDENT reference** (two-verifiers, parity oracle). Putting it in
  the repo puts it under the same custody it was supposed to audit from outside.
- **Redundant**: the regenerated chassis already lives in-repo at `factories/agent-systems-factory/`.
- **The harvest is already done** (`ASF-LESSONS.md` extracted the substrate; `factory.spec.yml`
  descended the opinions; parity was redefined and proven by re-derivation, which doesn't need
  ASF). ASF's remaining role is archival → a pin is enough.

## If the bytes ever need to be ported

(e.g. cloning Meta_Factory onto a machine without ASF alongside it): `git submodule add` pointing
at the ASF repo @ this SHA, or a `git bundle` archived as an artifact. **Not necessary today** —
the pin covers the provenance; the bytes are a `git clone` of the sibling repo away.
