"""The economy: what a run COST, derived from typed usage — never from a transcript.

ONE SENTENCE, and every module here is a consequence of it:

    «no se midió» has to be distinguishable from «dio cero», at every layer.

v2 derives the economy by PARSING THE TRANSCRIPT FILE — a path under the CLI's own session store,
read by a `Stop` hook. That mechanism has two independent failure modes and the project has now met
both. The first is the one §07 already records: the emitter matched a renamed tool and the delegation
share silently read 0.0 %. The second was measured on 2026-07-30 and is worse, because nothing in the
system said it: between 2026-07-13 and 2026-07-28 the capture layer wrote NOTHING AT ALL, while the
KPI kept reporting a number. A zero nobody wrote is indistinguishable from a zero that was measured.

So this package refuses two things by construction:

  1. **It never reads a transcript.** Every number comes from the typed `ResultMessage` the host
     already receives (`total_cost_usd`, `usage`, `model_usage`, `num_turns`, `terminal_reason`) and
     from the host's own loop variables. Asserted, not promised: `v3.economy.census` scans this
     package for any transcript reference and goes red on one.

  2. **It never reports 0 for "nothing was recorded".** Every aggregate carries `measured`, and an
     aggregate over an empty selection answers `measured=False` with a reason — it does not answer
     zero. `Aggregate.total_cost_usd` on an unmeasured aggregate is `None`, not `0.0`.

WHAT LIVES WHERE

    store.py      the append-only JSONL substrate the four series share
    ledger.py     per-leaf cost and token accounting from typed usage        (F1)
    meter.py      the ADR-019 §6 escape meter: corpus-vs-window, leaf relevance   (F2)
    iteration.py  retries, red→green cycles, repeated failures               (F3)
    outcome.py    the per-increment outcome, from the ledger rather than a transcript
    census.py     where v2's economy surface went, derived at the oracle commit

WHAT IS DELIBERATELY NOT HERE. No budget ENFORCEMENT. `max_budget_usd` is pinned (`C-16`) and its
behaviour measured (`budget_exhausted`), but §11.5 is explicit that no increment improves anything
before INC-11 — the session classes are typed DATA in `v3.control.budget` and the runtime tooth is
post-cutover. Recording what a class costs is measurement; stopping a session is policy.
"""
