#!/usr/bin/env python3
"""state_fidelity (ADR-019 §4, M3) — ported from v2's STATE-fidelity law. The doc-seal tells you
*whether STATE changed*; nothing tells you *whether it is TRUE*. This closes that gap: it proves the
prose of «Ahora» does not CONTRADICT the truth re-derivable from `.proof/`.

    python3 -m v3.verify.checks.state_fidelity
    V3_STATE_FIDELITY_SABOTAGE=1 python3 -m v3.verify.checks.state_fidelity   # red side; must ALSO exit 0

This docstring does not spell the legacy package's path, on purpose: `v3.verify.import_boundary`
rule 3 bans naming the v2 substrate under `v3/`, because a string is how a dynamic import or a path
injection hides. Describing what was ported costs nothing; naming the path it came from does.

The oracle already exists: the per-factory RTM re-derived from `.proof/` (`v3.memory.projection`).
Faithfulness is not correctness — but the gap the literature usually leaves open here closes WITH
TEETH precisely because the ground truth is DETERMINISTIC proof, never prose or an LLM judgement.
Two-sided contract, unchanged from what it ported (`fidelity_problems`, and the policy constants
`WINDOW_CHARS` / `_POS_RE` / `_NEG_RE`):
  (a) «Ahora» must not claim *done* what the proof does not back — `(slug, COMPLETE)` when the
      re-derived status is INCOMPLETE → a contradiction.
  (b) what the proof marks COMPLETE must not be contradicted — `(slug, INCOMPLETE)` when the
      re-derived status is COMPLETE → a contradiction.

It does NOT auto-rewrite: it FAILS and SIGNALS. Scope is only the editable PROSE under `## Ahora`
(the generated fact-projection block is governed by the `projection` gate). Vocabulary is the proof's
OWN status words (COMPLETE/INCOMPLETE + Spanish flexions, UPPERCASE), coupling the detector tightly
to the oracle and keeping the false-positive surface near zero.

WHY THE WITNESS IS BEHIND A `sabotage_env` HANDLE, and not embedded in the green run (v2's shape: a
private `_tooth_bites()` runs synthetic oracle + prose INSIDE the same process, so it can fail but
cannot be re-run independently). Under `v3.verify.registry`'s registration law a gate needs a
re-runnable handle; a private in-process helper carrying only Python literals is not one. So the same
cases move behind `V3_STATE_FIDELITY_SABOTAGE=1`, unchanged in shape — TWO contradiction classes that
MUST be caught, plus the two NEGATIVE controls that must NOT trip (truthful prose; a status token
outside the window of any slug). A tooth that bites everything is as useless as one that bites
nothing, and those two controls are what prove it actually discriminates.

CONTRACT (`v3.verify.registry.Gate.red_run`'s docstring — the opposite of the obvious one): the
sabotage run exits **0** when all four planted cases behaved as required, printing what happened; it
exits **1** with `GATE DECORATIVO` when any one of them did not. Reported per-case so a partial catch
is visible rather than silently rounded up to green.

THE N/A BRANCH, and why it lives HERE and never in the ported law. `.proof/` is gitignored. Measured
in a clean clone of this repo: the RTM re-derives to INCOMPLETE for every factory (no proof to
recompute yet), and on such a tree `fidelity_problems` legitimately returns no contradiction — but
vacuously, because the prose never makes a per-factory claim inside the window on a tree with nothing
derived. A PASS there would assert "the prose does not contradict the facts" when the facts were
never derived at all. So: when NO factory in this tree carries a `.proof/` directory, this gate
reports N/A (`SUMMARY N/A: …`, exit 0, never a shade of green or red) and names the remedy. `fidelity_
problems` itself kept answering exactly what the oracle answered — the retired parity oracle
(`corpus_parity`, retired at V3-EXTRACT-CORPUS-PARITY) imported both and compared them every run
during the rebuild, which is why this branch still lives in the gate and not the ported law: folding
it into the law would have broken that comparison and quietly changed what the law MEANT.

`state_snapshot` gets no such branch: it reads only `docs/STATE.md` and needs no `.proof/` to answer.

Argv: an optional single repo-root path, like every other registered v3 gate."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ...kernel.report import Verdict
from ...memory import projection
from . import state_snapshot

# Distance (in chars between the two spans on the same line) within which a status token is read as a
# claim ABOUT a factory slug. Bounds cross-talk: a status far from every slug is not a claim about one.
WINDOW_CHARS = 60

# The proof's own status vocabulary, UPPERCASE (the RTM emits "COMPLETE (11/11)" / "INCOMPLETE (…)").
# Matching uppercase only keeps ordinary lowercase Spanish prose ("una solución completa") from tripping
# the gate — a contradiction quotes the status token, it doesn't paraphrase it. `\b` so INCOMPLETE's
# embedded "COMPLETE" is not mis-read as positive.
_POS_RE = re.compile(r"\b(?:COMPLETE|COMPLETA|COMPLETO|COMPLETAS|COMPLETOS)\b")
_NEG_RE = re.compile(r"\b(?:INCOMPLETE|INCOMPLETA|INCOMPLETO|INCOMPLETAS|INCOMPLETOS)\b")

# Chars that continue a slug token: a slug match flanked by one of these is part of a LONGER token
# (so `full-stack` inside `full-stack-kotlin` is rejected, the longest real slug wins).
_SLUG_BOUNDARY = re.compile(r"[A-Za-z0-9-]")

_ROOT = Path(__file__).resolve().parents[3]   # checks -> verify -> v3 -> repo root
_SABOTAGE_VAR = "V3_STATE_FIDELITY_SABOTAGE"


def _slug_spans(line: str, slug: str) -> list[tuple[int, int]]:
    """Spans where `slug` appears as a WHOLE token (not a prefix/suffix of a longer slug-like token)."""
    spans: list[tuple[int, int]] = []
    for m in re.finditer(re.escape(slug), line):
        s, e = m.start(), m.end()
        before_ok = s == 0 or not _SLUG_BOUNDARY.match(line[s - 1])
        after_ok = e == len(line) or not _SLUG_BOUNDARY.match(line[e])
        if before_ok and after_ok:
            spans.append((s, e))
    return spans


def _gap(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Chars strictly between two non-overlapping spans (0 if adjacent/overlapping)."""
    return max(0, b[0] - a[1], a[0] - b[1])


def _status_tokens(line: str) -> list[tuple[tuple[int, int], str]]:
    """(span, polarity) for each status token in the line; polarity is 'POS' or 'NEG'."""
    out: list[tuple[tuple[int, int], str]] = []
    for m in _POS_RE.finditer(line):
        out.append(((m.start(), m.end()), "POS"))
    for m in _NEG_RE.finditer(line):
        out.append(((m.start(), m.end()), "NEG"))
    return out


def fidelity_problems(now_body: list[str], statuses: dict[str, tuple[str, int, int]]) -> list[str]:
    """[] if no «Ahora» line makes a factory-status claim that CONTRADICTS the re-derived RTM.

    `statuses` is `projection.rtm_statuses` output `{slug: (status, sat, total)}` — the deterministic
    oracle. Each status TOKEN is attributed to the NEAREST slug on its line within `WINDOW_CHARS`; a
    claim contradicts the oracle when its polarity disagrees with the slug's re-derived status. A slug
    with status '—' (no requirements) can't be contradicted and is skipped."""
    problems: list[str] = []
    slugs = [s for s in statuses if statuses[s][0] in ("COMPLETE", "INCOMPLETE")]
    for line in now_body:
        # All bounded slug occurrences on this line (slug -> its spans), and all status tokens.
        occ: list[tuple[tuple[int, int], str]] = []
        for slug in slugs:
            for span in _slug_spans(line, slug):
                occ.append((span, slug))
        if not occ:
            continue
        for tok_span, polarity in _status_tokens(line):
            # Attribute the token to the nearest slug occurrence within the window.
            nearest = min(occ, key=lambda o: _gap(o[0], tok_span))
            if _gap(nearest[0], tok_span) > WINDOW_CHARS:
                continue
            slug = nearest[1]
            derived, sat, tot = statuses[slug]
            claims_done = polarity == "POS"
            contradiction = (claims_done and derived == "INCOMPLETE") or (
                not claims_done and derived == "COMPLETE")
            if contradiction:
                claimed = "COMPLETE" if claims_done else "INCOMPLETE"
                problems.append(
                    f"«Ahora» afirma {slug} {claimed} pero el proof re-derivado dice {derived} "
                    f"({sat}/{tot}): {line.strip()[:90]}")
    return problems


# ── the sabotage witness (P2: re-runnable, not embedded) ────────────────────────────────────────
_FALSE_DONE = "false_done"                  # (a) claims COMPLETE what is INCOMPLETE — must be CAUGHT
_FALSE_INCOMPLETE = "false_incomplete"      # (b) claims INCOMPLETE what is COMPLETE — must be CAUGHT
_TRUE_PROSE_SILENT = "true_prose_silent"    # truthful prose — must stay SILENT
_OUT_OF_WINDOW_SILENT = "out_of_window_silent"   # token far from any slug — must stay SILENT
_CLASSES: tuple[str, ...] = (_FALSE_DONE, _FALSE_INCOMPLETE, _TRUE_PROSE_SILENT, _OUT_OF_WINDOW_SILENT)


def _run_sabotage() -> int:
    """A synthetic oracle + synthetic prose, no filesystem. Each contradiction mode MUST bite; the
    two negative controls MUST NOT — a tooth that bites everything discriminates nothing."""
    statuses = {"alpha": ("COMPLETE", 2, 2), "beta": ("INCOMPLETE", 1, 3)}
    passed: list[str] = []

    # (a) claims done what isn't: beta is INCOMPLETE, «Ahora» says COMPLETE.
    if fidelity_problems(["beta quedó COMPLETE tras el merge"], statuses):
        passed.append(_FALSE_DONE)
    # (b) contradicts a real completion: alpha is COMPLETE, «Ahora» says INCOMPLETE.
    if fidelity_problems(["alpha sigue INCOMPLETE por un bug"], statuses):
        passed.append(_FALSE_INCOMPLETE)
    # true prose (each status matches the oracle) must NOT fire.
    if not fidelity_problems(["alpha quedó COMPLETE", "beta sigue INCOMPLETE"], statuses):
        passed.append(_TRUE_PROSE_SILENT)
    # a contradicting token far from any slug (> window) must NOT fire.
    if not fidelity_problems(["beta " + "x" * (WINDOW_CHARS + 20) + " COMPLETE"], statuses):
        passed.append(_OUT_OF_WINDOW_SILENT)

    if len(passed) == len(_CLASSES):
        return Verdict("v3-state-fidelity (SABOTAGE)", 0,
                       f"{len(passed)}/{len(_CLASSES)} planted case(s) behaved as required "
                       f"({', '.join(passed)})").emit()

    missed = [name for name in _CLASSES if name not in passed]
    return Verdict("v3-state-fidelity (SABOTAGE)", 1,
                   f"GATE DECORATIVO: {len(passed)}/{len(_CLASSES)} planted case(s) behaved as "
                   f"required ({', '.join(passed) or 'none'}) — missed {missed}: no teeth on those "
                   f"cases").emit()


def _no_proof_anywhere(root: Path) -> bool:
    """True iff not a single factory directory in this tree carries a `.proof/` — a fresh clone
    (`.proof/` is gitignored). On such a tree the RTM re-derives INCOMPLETE for every factory, and a
    PASS here would be a false positive about DERIVATION, never a finding about this law."""
    facdir = Path(root) / "factories"
    if not facdir.is_dir():
        return True
    return not any((f / ".proof").is_dir() for f in facdir.iterdir() if f.is_dir())


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return Verdict("v3-state-fidelity", 2, f"takes at most one path argument; got {argv!r}").emit()

    if os.environ.get(_SABOTAGE_VAR) == "1":
        return _run_sabotage()

    root = Path(argv[0]).resolve() if argv else _ROOT

    if _no_proof_anywhere(root):
        return Verdict("v3-state-fidelity", 0,
                       "N/A: no factory in this tree carries a `.proof/` directory — the facts have "
                       "not been derived yet (run `ci --rederive` to derive them first); reporting "
                       "PASS here would assert the prose doesn't contradict facts that were never "
                       "computed (R-12)").emit()

    state_path = root / "docs" / "STATE.md"
    try:
        text = state_path.read_text(encoding="utf-8")
    except OSError as e:  # noqa: BLE001 — an unreadable STATE is reportable, not a crash
        return Verdict("v3-state-fidelity", 1, f"no pude leer {state_path}: {e}").emit()

    body = state_snapshot.extract_now_lines(text)
    if body is None:
        return Verdict("v3-state-fidelity", 1,
                       "no encontré la sección `## Ahora` en STATE.md (no puedo verificar fidelidad)"
                       ).emit()

    statuses = projection.rtm_statuses(root)
    problems = fidelity_problems(body, statuses)
    if problems:
        return Verdict("v3-state-fidelity", 1,
                       f"«Ahora» CONTRADICE la verdad re-derivable del `.proof/` (ADR-019 §4): "
                       f"{len(problems)} problem(s)", failures=tuple(problems),
                       next_action="corregí «Ahora» para que no contradiga el RTM (la verdad vive en "
                                   "`.proof/`; re-derivala, no la reescribas a mano)").emit()

    checked = ", ".join(f"{s}={statuses[s][0]}" for s in statuses) or "sin fábricas"
    return Verdict("v3-state-fidelity", 0,
                   f"«Ahora» no contradice el RTM re-derivado [{checked}]",
                   counts={"now_lines": len(body)}).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
