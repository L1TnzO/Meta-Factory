<!-- meta:doc sha=163b3cbe08ea26e615309f5581c88750cbe53403 updated=2026-07-27T21:41Z -->
# 01 — Vocabulary and domain model (descriptive)

> Every term below is a THING IN THE REPO, not a metaphor. Where a term has a data shape, the shape is
> given. Where two words are used for the same thing in the codebase, that is recorded as debt.

## 1. The three levels

The system governs itself at three nested levels; almost every rule in it is level-aware (ADR-016).

| Level | Root | Owns | Work-docs home |
| --- | --- | --- | --- |
| **meta** | repo root | the substrate (`src/metafactory`), the seed, the column, the meta line `m00..m08` | `docs/work/` |
| **factory** | `factories/<slug>/` | its own spec, its station line `s0..sN`, its codegen, its docs | `factories/<slug>/docs/work/` |
| **product** | `factories/<slug>/products/<p>/` | its blueprint (`product.yml`), its proofs, its pinned verdict | `factories/<slug>/products/<p>/docs/work/` |

Level is resolved by **path arithmetic**, not configuration — `seed/lifecycle.py:86-102`.

## 2. Core nouns

| Term | What it is | Data shape / anchor |
| --- | --- | --- |
| **Factory spec** | the typed description of a factory | `factory.spec.yml`; keys `factory · domain · machinery · factory_substrate · requirements · governance` (`spec/validator.py:29-59`, `spec/model.py`) |
| **Product blueprint** | the typed description of ONE product built by a factory | `products/<p>/product.yml`; e.g. `station_activation · package_name · api_title · frontend_surface · roles · owner_bypass_roles · entities` (`factories/full-stack-kotlin/products/helpdesk/product.yml`) |
| **Station** | one stage of a line: it BUILDS artifacts and RUNS checks | dataclass `id · name · activation · builds[] · checks[] · requires_prev · depends_on[] · tier · raw` (`engine/station.py:12-25`) |
| **Line / Sequence** | the ordered DAG of stations | `engine/sequence.py:25-101`; loaded from `stations/*.yml`, ordered by natural key so `s9 < s10` (`sequence.py:16-22`) |
| **Check** | one falsifiable assertion inside a station | `{name, kind, ...}` → an argv; `exit 0 == pass` (`verify/checks/registry.py:1-4`) |
| **Kind** | the CLOSED vocabulary of check shapes | 29 entries in `registry.KINDS` (`registry.py:21-28`) |
| **Proof** | the machine-written record of a station run | `.proof/<station>.json` = `{station, passed, checks:[{name,cmd,exit}], computed_at, proof_sha, writer, log_path}` (`seed/verifier.py:90-143`) |
| **proof_sha** | the content hash that makes re-derivation decidable | `sha256({station, sorted[(name,exit)]})` — **excludes** timestamps, stdout, machine (`seed/verifier.py:62-72`) |
| **Pin** | the frozen expected verdict of a whole line | `pinned_verdict.json` = `{station_id: proof_sha}` (`cli.py:498-511`) |
| **Gate** | the mechanism that refuses to open a station until its predecessors are proven | `engine/gate.py:28-45` |
| **Verdict (bus)** | the BOUNDED text an agent is allowed to read instead of the log | `@dataclass Verdict{verb,status,exit_code,summary,counts,failures,artifact,next_action}`, ≤10 lines (`verify/report.py:23-32,87-101`) |
| **RTM** | requirements traceability matrix, re-derived not narrated | static: `validator.py:62-81` · dynamic tree: `verify/rtm.py:70-94` |
| **Increment** | the unit of work; a `.md` in a level's `docs/work/` with `Status: **OPEN**` | `seed/lifecycle.py:33,37-52` |
| **Slot** | a bounded delegation contract given to a generator model | `.gen/active_slot.json`, schema in `seed/delegation.py:34-159` |
| **Column** | the trust-chain: hooks + agents + seed law that cannot be delegated | `column_scope.py`; 11 roles at meta, 6 at factory |
| **Seed** | the minimal law that must exist before anything else and is written by hand | `seed/{column.md,delegation.py,lifecycle.py,verifier.py}` |

## 3. Core verbs (the CLI surface as it exists today)

`meta` is the single entrypoint (`src/metafactory/cli.py`). Grouped by what they actually do:

| Group | Verbs | Note |
| --- | --- | --- |
| build | `new · station · product-run · product new|list` | drive the lines |
| prove | `check · verify · ci [--rederive] · pin · promote · rtm · benchmark · dial` | produce/compare evidence |
| navigate | `graph build|query|repomap · doc slice|orphans · journal · rehydrate` | context economy |
| govern | `increment open|close|… · checkpoint · doc-sync · plan` | lifecycle + memory |
| account | `billing · outcome · metrics` | cost and result |
| environment | `jdk-run` | toolchain shim |
| tombstone | `recall` | **retired** (ADR-019 §2); the verb still exists only to redirect (`cli.py:1060`) |

> **Debt recorded:** the verb surface is ~30 entries reached by shelling out and parsing stdout. §09
> and §10 argue this is the single largest piece of accidental complexity in the system.

## 4. Roles (the CLOSED agent vocabulary)

Single source `src/metafactory/agent_roles.py`; enforced repo-wide by the `roles` gate.

| Role | Model today | Tools | Purpose |
| --- | --- | --- | --- |
| `orchestrator` | opus | Read, Grep, Glob, Bash, Edit, Write, Agent(...) | designs contracts, decides scope, reads verdicts |
| `generator` | sonnet | Read, Write, Edit, Bash, Grep, Glob | writes bulk code inside ONE slot, self-verifies |
| `verifier` | haiku | Read, Grep, Glob, Bash | digests ONE bulky artifact into a bounded summary |
| `reviewer` | opus | Read, Grep, Glob, Bash | reviews the irreducible residue (security / persistent red) |
| `evaluator` | sonnet | Read, Grep, Glob, Bash | scores subjective quality against written criteria (ADR-027) |

Legacy synonyms kept alive on purpose: `writer→generator`, `triage→verifier` (`agent_roles.py:39-42`).
**Specialization is by ROLE (model · tools · verification contract), never by domain** — the domain
travels per-invocation in the slot manifest (ADR-020).

## 5. Words that mean the same thing (naming debt)

| Used interchangeably | Should be | Where it hurts |
| --- | --- | --- |
| `writer` / `generator`, `triage` / `verifier` | one name | `agent_roles.LEGACY_SYNONYMS` exists only to tolerate this |
| `Status: **OPEN**` / `Estado: **ABIERTO**` | one language | dual-accept regex `seed/lifecycle.py:33` |
| "gate" (station gate) / "gate" (a `meta check` entry) / "gate" (the iteration/acceptance command of a slot) | three distinct concepts | reader confusion; §10 renames them `gate` / `check` / `slot-gate` |
| "verdict" (bus line) / "verdict" (slot verdict file) / "verdict" (pinned verdict) | three distinct concepts | §10 renames them `report` / `slot-verdict` / `pin` |
| `.proof/` vs `pinned_verdict.json` vs `.gen/` | fine as-is | — |

## 6. The two things that must never be confused

1. **A check** is evidence: it runs a process and records its exit code. **A gate** is control: it
   decides whether the next station may run. Evidence is durable and hashable; control is not.
2. **A model decides nothing that a gate can decide.** The model chooses WHAT to attempt and writes
   the artifact; the exit code decides whether the attempt counts. Wherever the current system lets a
   model's prose stand as the record, that is named honestly in §04.7.
