# runs/pinned — pin registry (H6 §7)

> The no_regression base of each experiment is EXPLICIT here, never guessed. This table
> is PARSED by `reqcouncil/eval/gates.py` (strict 5 columns; `-` = none) — keep the
> format intact. `gated: yes` rows are blocked by `config/thresholds.yml`; `gated: no`
> rows are evidence pins (documented reds, drills) that no gate reads. A pending gated
> experiment carries `-` as pin and its note becomes the written `n/a` reason.

| experiment | pin | previous_green | gated | note |
|---|---|---|---|---|
| E0 | e0-dsv4flash | e0 | yes | judge calibration, 760 pairs (H2); previous green = qwen3-32b arm |
| E1 | e1-h4-dsv4flash | e1-dsv4flash | yes | deliberating council over int1 (H4 gate); base = H3 non-deliberating arm |
| E2-wepgcomp | e2-wepgcomp | - | yes | first E2 pin (industry, WER 2025 corpus, pt); no previous green; reds carry waivers in thresholds.yml |
| E2-maislugar | e2-maislugar | - | yes | first E2 pin (industry, WER 2025 corpus, pt); no previous green; reds carry waivers in thresholds.yml |
| E3 | e3-n20-seed7 | - | no | reported, not gated (design/03 §3): ReqElicitBench N=20 seed=7, summary.json is the evidence |
| E4 | e4-dsv4flash | - | no | reported, not gated: 12-cell ablation (e4-table.json = Tabla 4.5); b-wepgcomp audit verdict = abstraction mismatch, judge sound |
| E1-red-gap-hunter | e1-h4-red1 | - | no | documented RED (H4 gap_hunter cope round), kept as evidence — never a base |
| H5-drill | h5-review-drill | - | no | auto-reviewer catch-rate drill 3/3 (H5); the HUMAN drill will pin as h6-human-drill |
| H6-drill | h6-model-reviewer-drill | - | no | CONTRACT AMENDMENT 2026-07-06 (H6 §9): model reviewer (clean-room subagent, no decoy knowledge), NOT human — human catch-rate stays UNMEASURED. catch_rate 0.0 by reject-edit metric BUT written reasons identify all 3 decoys with 0 false alarms (detection 3/3): the decision vocabulary lacks a fix-anchors action — instrument finding, informe 4.3.d/4.5 |
