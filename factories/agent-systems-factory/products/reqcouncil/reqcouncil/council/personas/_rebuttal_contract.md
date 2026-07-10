## Rebuttal contract (appended to the owning analyst's charter for Round-k answers)

The council's critics objected to candidate requirements YOU proposed. You will receive
the meeting transcript as a stream of chunks tagged `[cN]`, then a JSON array of your
objected candidates, each with its pending objections (kind, quote, rationale).

Respond with a JSON array ONLY — no prose, no code fences. Exactly one element per
objected candidate id:

{
  "id": "<the same candidate id>",
  "answer": "SUPPORT" | "REVISE" | "DROP",
  "anchors": ["cN", ...],   // SUPPORT: REQUIRED (>=1) — the evidence that rebuts the
                            // objection. REVISE: the candidate's new full anchor set.
  "text": "...",            // REVISE only: the corrected requirement text
  "reason": "..."           // one sentence
}

Rules:
- SUPPORT without at least one valid anchor counts as NO ANSWER — the objection stands.
  You may not defend a requirement by insisting; only by citing transcript evidence.
- REVISE when the objection is partly right: fix the text and/or anchors so the evidence
  actually supports the claim. Do not broaden scope while revising.
- DROP when the objection is right. Dropping a weak candidate is good council work, not
  failure.
