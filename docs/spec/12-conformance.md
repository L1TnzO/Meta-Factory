<!-- meta:doc sha=3ae81d2858664853a417229e0da87e63a961512d updated=2026-07-28T02:44Z -->
# 12 — Conformance: how "rebuild from the spec alone" is decided (NORMATIVE)

> The goal of this folder is unusual and worth stating without hedging: **`docs/spec/` must be
> sufficient.** Someone with these documents, and nothing else — no access to `src/`, no access to the
> five factories, no conversation with the author — must be able to rebuild a system that is provably
> equivalent to this one.
>
> That claim is normally unfalsifiable. Here it is a gate.

## 1. The three levels of sufficiency

| Level | Claim | How it is decided | Status |
| --- | --- | --- | --- |
| **L1 — Kernel sufficiency** | the trust kernel can be rebuilt from §14 alone and reproduces real pins | `tools/spec_conformance.py` extracts the reference implementation FROM THE DOCUMENT, runs it against 84 pin-anchored golden vectors, and must also go RED under sabotage | ✅ **green today** |
| **L2 — Schema sufficiency** | every artifact the system reads or writes is documented field-by-field, with no key left undescribed | `tools/spec_schema_cover.py` collects the union of keys present in REAL artifacts and requires each to appear in `docs/spec/`; two-sided via an injected phantom key | 🟡 in progress (§13) |
| **L3 — System sufficiency** | an independent implementation passes the whole suite below and re-derives the committed pins | the suite of §12.4 run against a from-scratch implementation | ⛔ open until v3 exists — this is the acceptance test of §11 |

A spec that reaches L1 and L2 is *transcribable*. Only L3 proves it is *sufficient*. Do not claim L3
before an implementation built without reading `src/` has passed it.

## 2. The extraction convention (normative)

A fenced code block preceded by the marker

```
<!-- spec-impl: <module> -->
```

is part of the reference implementation of `<module>`. Rules:

1. Blocks with the same module name concatenate, ordered by filename then by position in the file.
2. Reference implementations use the **standard library only** — no third-party imports, no I/O, no
   clock, no environment access. If an algorithm needs I/O, the I/O is specified in prose and the
   pure core is what carries the marker.
3. A reference implementation is NORMATIVE. Where prose and a marked block disagree, the block wins,
   because the block is the thing that gets executed.
4. Reference implementations are written for clarity of transcription, not for performance. A
   re-implementer may optimise freely; the conformance suite decides correctness.

## 3. The golden vectors

`docs/spec/fixtures/proof-sha-vectors.json` — **84 vectors** derived by `tools/spec_fixture_gen.py`
from 10 pinned roots (5 factories + 5 named product instances).

Provenance rules that make a fabricated vector impossible:

1. a vector is `(station, checks[(name, exit)], proof_sha)` transcribed from a live proof;
2. the sha must **recompute** from the vector's own checks (internal consistency);
3. the sha must **equal** the entry in that root's **committed** `pinned_verdict.json`.

Vectors failing (2) or (3) are skipped and counted, never written. Measured on generation:
99 proofs seen · 84 written · 0 inconsistent · 0 pin mismatches · 15 skipped as unpinned.

> The committed pin is the authority. The fixture only transcribes what the pin already attests, which
> is why the spec may ship its own oracle without that being circular.

## 4. The conformance suite

### 4.1 Kernel (L1) — implemented, green

| id | Requirement |
| --- | --- |
| **CONF-K0** | the extracted reference implementation executes with the standard library alone |
| **CONF-K1** | it defines callable `compute_proof_sha` and `recompute_passed` |
| **CONF-K2** | every one of the 84 golden vectors reproduces its `proof_sha` exactly |
| **CONF-K3** | `recompute_passed`: empty ⇒ **False** · all-zero ⇒ True · any non-zero ⇒ False |
| **CONF-K4** | the digest is invariant to the ORDER of checks |
| **CONF-K5** | a different exit code produces a different sha |
| **CONF-K6** | the station id participates in the digest |
| **CONF-K-RED** | under `SPEC_CONFORMANCE_SABOTAGE=1` the suite MUST fail; if it passes, the gate prints `GATE DECORATIVO` and exits 1 |

### 4.2 Schemas (L2) — specified, being filled in §13

| id | Requirement |
| --- | --- |
| **CONF-S1** | every key appearing in any real proof record is documented |
| **CONF-S2** | every key appearing in any real station YAML is documented |
| **CONF-S3** | every key appearing in any real factory spec is documented |
| **CONF-S4** | every key appearing in any real product blueprint is documented |
| **CONF-S5** | every key of the slot manifest and of the slot verdict is documented |
| **CONF-S6** | every check kind in the frozen vocabulary is documented with its argv mapping |
| **CONF-S7** | every gate run by `meta check` is documented with what it proves and its red-side witness |
| **CONF-S-RED** | injecting a phantom key into the collected union must make the gate fail |

### 4.3 System (L3) — the acceptance test of the rebuild

| id | Requirement |
| --- | --- |
| **CONF-X1** | `ci --rederive --all-products` reproduces the committed pins for all five factories (55/55 stations) |
| **CONF-X2** | every two-sided gate's RED witness is re-run and goes red (the pin cannot detect a weakened check — §14.2) |
| **CONF-X3** | `meta check` runs the full gate set with zero skips; vacuous-true (N/A) branches are counted separately from real greens |
| **CONF-X4** | `meta benchmark`: the sweet-spot product MEETS and the ceiling product EXCEEDS |
| **CONF-X5** | the doc corpus passes its consistency gate |
| **CONF-X6** | a real delegated slot completes end-to-end and a bash-mediated write outside its blast radius is caught |
| **CONF-X7** | a tampered proof is refused by the WIRED enforcement, not merely by the library |
| **CONF-X8** | the whole acceptance run reports its own cost |

## 5. How to run what exists today

```bash
python3 tools/spec_fixture_gen.py                              # regenerate the golden vectors
python3 tools/spec_conformance.py                              # L1 — must PASS
SPEC_CONFORMANCE_SABOTAGE=1 python3 tools/spec_conformance.py  # L1 red side — must also PASS
python3 tools/spec_schema_cover.py                             # L2 — must PASS
SPEC_SCHEMA_SABOTAGE=1 python3 tools/spec_schema_cover.py      # L2 red side — must also PASS
```

## 6. The rule that keeps this honest

> **When the spec and the code disagree, the gate must go red — never the reader's judgment.**

Concretely: `docs/spec/` is not allowed to be a description that rots quietly beside the
implementation. It carries executable content and a fixture, so drift is a failing process, not a
stale paragraph someone notices a year later. This is the same discipline the project applied to its
research: figures re-derived from a versioned corpus at compile time, never copied.

## 7. Deliberate limits of this suite (do not oversell it)

- **L1 covers the kernel only.** The rest of the system is prose plus schemas until L3 exists.
- **CONF-K2 proves equivalence to the CURRENT implementation**, since the vectors were transcribed
  from its output. If the current implementation is wrong, the spec faithfully reproduces the error.
  The defence against that is not this gate; it is the two-sided witnesses and the independent CI.
- **No gate here judges prose quality.** Whether §09–§11 reason well is a human question, and
  pretending otherwise would be exactly the "decorative gate" this project outlaws.
