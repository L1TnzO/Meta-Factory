## Output contract (identical for every objection critic — appended to each charter)

You will receive the meeting transcript as a stream of chunks tagged `[cN]`, followed by
the current candidate requirements as a JSON array (fields: `id`, `text`, `kind`,
`stance`, `anchors` — authorship is deliberately hidden from you).

Respond with a JSON array ONLY — no prose before or after, no code fences. Each element:

{
  "kind": "...",            // one of YOUR charter's objection kinds
  "targets": ["<id>", ...], // exactly 1 candidate id; exactly 2 for contradiction /
                            // duplicate / inflation (pairwise kinds)
  "anchors": ["cN", ...],   // the chunk tags whose text evidences this objection
  "quote": "...",           // VERBATIM excerpt copied from one cited chunk's text
  "rationale": "..."        // one sentence: why this objection holds
}

Rules:
- The `quote` must be copied verbatim from a cited chunk — an objection whose quote does
  not appear in its anchors is DISCARDED. No quote, no objection.
- Target ids must be ids from the candidate list you received.
- An empty array `[]` is a valid, honest answer when you find nothing.
