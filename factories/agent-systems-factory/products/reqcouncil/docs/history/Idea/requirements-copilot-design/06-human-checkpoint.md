# 06 · Human Checkpoint

The plane where autonomy stops. The human engineer is the only interlocutor with the client and approves every output before it is used; the system recommends, the human decides (`00` §3). This document covers the interrupt payload, the directed review experience, the one cognitive forcing function, how an edit re-enters the graph state, and the automation-bias evidence that shapes all of it.

The governing fact: **all the rigor in `04` and `05` is wasted if the engineer rubber-stamps the output.** The review UX is engineered to force attention onto exactly the places the system is least sure.

---

## 1. The review packet

The dynamic `interrupt()` at the analysis→decision boundary (`03` §7) surfaces a JSON-serializable payload — the **review packet**. It contains:

```
ranked draft           the requirements, ordered worst-first (§2)
per-item confidence     the calibrated score from the attribution ladder (04 §3)
grounded / inferred     the flag per requirement (04 §4)
evidence links          backward-walk pointers to fragments / image regions (05 §7)
flagged gaps            the gap-hunter's ranked "may be missing" hypotheses (03 §4)
flagged conflicts       the conflict detector's contradiction pairs
```

This packet is not a finished spec to approve. It is a directed work list designed to make the engineer's review fast and pointed.

---

## 2. Ordering — directed, not a wall of output

The single most important UX decision, and it inverts the usual instinct. Instead of showing the confident requirements first, surface the **shakiest items and the gaps at the top**, so the engineer's freshest attention lands where the system is least sure.

- **Worst-first.** Low-confidence and `inferred` items at the top. A requirement the system grounded firmly in a clear statement needs less scrutiny than one it inferred from parametric knowledge.
- **Gaps next.** The gap-hunter's ranking drives the order of the "may be missing" section.
- **Frequency-format uncertainty.** Express uncertainty as "supported by 1 of 4 stakeholder mentions," not as a bare probability or a vague "low confidence." Humans calibrate against frequencies far better than against abstract percentages.
- **"DRAFT FOR VALIDATION" everywhere.** Never present any item as final. The label is not decoration; it is a constant reminder that the artifact is provisional and the human owns the decision.

A wall of uniformly-presented output is the failure mode. The whole point of the ranked draft, the confidence scores, and the gap flags is to *order the human's attention*.

---

## 3. The cognitive forcing function

### The evidence

The HCI research is blunt and counterintuitive: **explanations alone do not reduce overreliance on AI.** Showing the user why the model concluded something does not make them check it — and worse, a fluent explanation can *increase* acceptance. What does reduce overreliance is a **cognitive forcing function (CFF)**: a design that interrupts the reflexive "looks good, approve" and forces an active judgment. The controlled study (Buçinca, Malaya, Gajos, CSCW 2021, N≈199) found cognitive forcing significantly reduced overreliance compared to simple explainable-AI approaches — with a real trade-off: users rated the designs that reduced overreliance the most as the *least* pleasant to use.

### The design implication

- **Apply one cognitive forcing function, not several.** Stacking many yields diminishing returns and piles on cognitive load (and the usability cost is real). One well-placed CFF is the sweet spot.
- A concrete, low-friction CFF for this system: **require the engineer to mark each flagged item accept/reject with a one-line reason** before the draft can be finalized. The act of writing a reason for a low-confidence or inferred item is enough to break the rubber-stamp reflex without grinding the review to a halt.
- **Accountability framing.** Emphasize the engineer's responsibility for the final artifact. Framing the human as the accountable author (which they are — see `08` §3) measurably reduces automation bias.

### Why this sits next to all the attribution work

The attribution ladder (`04`) produces confidence and grounded flags; the trace (`05`) produces the evidence links. But those are inputs to a human decision, and the decision is where bias bites. A system that surfaces beautiful evidence and a confident synthesis, with no forcing function, optimizes for the exact conditions under which a reviewer defers. The CFF is what closes that gap.

---

## 4. How an edit re-enters state

The engineer edits and approves; the edits go back through `Command(resume=<edited payload>)` (`03` §7). Two things must happen, and both preserve traceability:

1. **The edit is written into the blackboard state.** Because the interrupting node re-executes on resume, the resume handler must be idempotent — it applies the human's edits to state without re-running extraction (`03` §7, the idempotency caveat).
2. **The edit is recorded as provenance.** Log it as a PROV `Activity` `wasAssociatedWith` the human `Agent`. Create a new requirement version that `wasDerivedFrom` the model's draft, marked `pav:curatedBy` the human and linked by `pav:previousVersion` (`05` §6).

The payoff: the human's contribution is fully traceable. Months later you can see exactly what the model proposed versus what the engineer changed — which is both an audit capability and, over time, training signal for where the model systematically over- or under-extracts.

---

## 5. What "good" looks like

The review experience succeeds when the engineer spends their attention proportionally to the system's uncertainty: most scrutiny on the inferred and low-confidence items and the ranked gaps, least on the firmly-grounded ones, with every decision recorded. Measure the review's **catch-rate** (how often the engineer corrects a genuinely wrong or missing requirement), not just its throughput. A review that is fast because the engineer approves everything is not a good review — it is the automation-bias failure mode wearing the mask of efficiency.
