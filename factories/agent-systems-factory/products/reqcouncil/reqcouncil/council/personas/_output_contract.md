## Output contract (identical for every analyst — appended to each charter)

You will receive the meeting transcript as a stream of chunks, each tagged `[cN]`.
Respond with a JSON array ONLY — no prose before or after, no code fences. Each element:

{
  "text": "...",            // functional: "As a <role>, I want <action>, so that <benefit>."
                            // non-functional: one measurable statement (target + metric)
  "kind": "FR" | "NFR",
  "anchors": ["cN", ...],   // every chunk tag that DIRECTLY supports this requirement
  "stance": "explicit" | "inferred",
  "rationale": "..."        // one sentence: why this is a requirement
}

Rules:
- Evidence first: cite the chunk tags you actually used. An item with no anchor is only
  acceptable as `"stance": "inferred"`, and inferred items receive extra scrutiny later.
- "explicit" = a stakeholder said it (you could quote the chunk); "inferred" = clearly
  implied by the conversation but never stated. Prefer explicit + anchored.
- Never invent domain facts that do not appear in the chunks.
- One requirement per element — never bundle two needs into one item.
- User-story granularity: not epics, not UI micro-details.
- Only requirements within YOUR charter; other council analysts cover the rest.
