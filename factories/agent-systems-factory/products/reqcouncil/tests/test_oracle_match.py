"""H6 §3 oracle-matching protocol, replayed OFFLINE (fake embedder + fake judge).

The recall/precision/NFR-recall math and the borderline audit sample are pinned here so a
live matching run's numbers are trustworthy; only the embed/judge API calls are stubbed.
"""

from __future__ import annotations

import re

from reqcouncil.eval.oracle import GoldenReq, match_requirements, stories_to_golden


def _fake_embed(texts):
    """Deterministic bag-of-words vectors over the union vocab of THIS call."""
    toks = [re.findall(r"[a-z]+", t.lower()) for t in texts]
    vocab = sorted({w for ts in toks for w in ts})
    idx = {w: i for i, w in enumerate(vocab)}
    out = []
    for ts in toks:
        v = [0.0] * len(vocab)
        for w in ts:
            v[idx[w]] += 1.0
        out.append(v)
    return out


PRODUCED = [
    "The user can log in with email and password",   # 0
    "The user can reset a forgotten password by email",  # 1
    "The app offers a dark mode theme",              # 2
    "The user can export data to a CSV file",        # 3
]
GOLDEN = [
    GoldenReq("FUNC01", "A user logs in using email and password", False),
    GoldenReq("FUNC02", "A user can recover a forgotten password", False),
    GoldenReq("NOTF01", "The system must sustain 99.9% availability", True),  # NFR, no match
]
# The judge says YES only for these (gold_id, produced_index) pairs; NFR stays unmatched.
_YES = {("FUNC01", 0), ("FUNC02", 1)}
_PROD_IDX = {t: j for j, t in enumerate(PRODUCED)}
_GOLD_ID = {g.text: g.id for g in GOLDEN}


def _fake_judge(gold_text, cand_text):
    return 1 if (_GOLD_ID[gold_text], _PROD_IDX[cand_text]) in _YES else 0


def test_recall_precision_nfr_by_hand():
    r = match_requirements(PRODUCED, GOLDEN, embed_fn=_fake_embed, judge_fn=_fake_judge, top_k=5)
    assert r.n_gold == 3 and r.n_produced == 4
    assert r.n_gold_matched == 2                 # FUNC01, FUNC02
    assert r.recall == round(2 / 3, 4)
    assert r.n_produced_matched == 2             # produced 0 and 1
    assert r.precision == 0.5
    assert r.critical_nfr_recall == 0.0          # the single NFR gold went unmatched


def test_match_rows_are_auditable():
    r = match_requirements(PRODUCED, GOLDEN, embed_fn=_fake_embed, judge_fn=_fake_judge, top_k=5)
    by_id = {m["gold_id"]: m for m in r.matches}
    assert by_id["FUNC01"]["matched"] and by_id["FUNC01"]["matched_produced"] == 0
    assert by_id["NOTF01"]["matched"] is False and by_id["NOTF01"]["matched_produced"] is None
    # the winning candidate carries verdict 1; candidates after a match are not re-judged
    win = next(c for c in by_id["FUNC02"]["candidates"] if c["produced"] == 1)
    assert win["verdict"] == 1
    assert sum(1 for c in by_id["FUNC02"]["candidates"] if c["verdict"] is not None) <= 5


def test_borderline_audit_sample_emitted():
    r = match_requirements(PRODUCED, GOLDEN, embed_fn=_fake_embed, judge_fn=_fake_judge, top_k=5)
    audit = r.audit_sample
    k = max(1, round(0.10 * 3))  # == 1
    assert len(audit["borderline_yes"]) == k
    assert len(audit["borderline_no"]) == k
    assert audit["borderline_no"][0]["gold_id"] == "NOTF01"  # only unmatched gold w/ candidates
    assert all("cosine" in row for row in audit["borderline_yes"] + audit["borderline_no"])


def test_empty_produced_is_zero_not_crash():
    r = match_requirements([], GOLDEN, embed_fn=_fake_embed, judge_fn=_fake_judge)
    assert r.recall == 0.0 and r.precision == 0.0 and r.n_gold_matched == 0
    assert all(m["matched"] is False for m in r.matches)


def test_no_nfr_gold_reports_none():
    golden = stories_to_golden(["a", "b"])  # all FR
    r = match_requirements(["a"], golden, embed_fn=_fake_embed,
                           judge_fn=lambda g, c: 1 if g == c else 0)
    assert r.critical_nfr_recall is None
    assert r.recall == 0.5  # only "a" matches
