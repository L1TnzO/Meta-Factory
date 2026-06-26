"""state_fidelity (ADR-019 §4, M3) — the FIDELITY gate. The ADR-009 stamp tells you *whether STATE
changed*; nothing told you *whether it is TRUE*. This closes that gap: it proves the prose of «Ahora»
does not CONTRADICT the truth re-derivable from `.proof/`.

The oracle already exists: `meta check` re-derives each factory's RTM from `.proof/`. Faithfulness ≠
correctness (Wallat; ClawVM): we can close the gap the literature leaves open WITH TEETH precisely
because our ground-truth is DETERMINISTIC proof, not prose nor an LLM-judge. Two-sided contract:
  (a) «Ahora» must not claim *done* what the proof does not back — `(slug, COMPLETE)` when R=INCOMPLETE → RED.
  (b) what the proof marks COMPLETE must not be contradicted — `(slug, INCOMPLETE)` when R=COMPLETE → RED.

It does NOT auto-rewrite (auto-rewriting is what causes drift; ADR-019 §Rechazado): it FAILS and SIGNALS.
Scope: only the editable PROSE under `## Ahora` (the generated `meta:projection` block is governed by
`projection`). Vocabulary = the proof's OWN status words (COMPLETE/INCOMPLETE + es flexions, UPPERCASE),
coupling the assertion-detector tightly to the oracle and keeping the false-positive surface near zero.

Sibling in style to `state_snapshot`: a pure detector + a two-sided synthetic tooth + a decorative guard.
The result flows to the `fidelity` series (M5) by NAME — `instrument.FIDELITY_CHECKS` already lists it.

Argv: <meta_root>. Exit 0 = PASS (no «Ahora» claim contradicts the re-derived RTM + tooth alive),
1 = FAIL (a contradiction / unreadable STATE / decorative tooth)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

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
    """(span, polarity) for each status token in the line; polarity ∈ {'POS','NEG'}."""
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


def _tooth_bites() -> bool:
    """Two-sided RED tooth on synthetic oracle + prose, no filesystem. Each contradiction mode MUST
    bite; true prose and an out-of-window token MUST NOT. If any fails, the check is decorative."""
    statuses = {"alpha": ("COMPLETE", 2, 2), "beta": ("INCOMPLETE", 1, 3)}
    # (a) claims done what isn't: beta is INCOMPLETE, «Ahora» says COMPLETE.
    bites_a = bool(fidelity_problems(["beta quedó COMPLETE tras el merge"], statuses))
    # (b) contradicts a real completion: alpha is COMPLETE, «Ahora» says INCOMPLETE.
    bites_b = bool(fidelity_problems(["alpha sigue INCOMPLETE por un bug"], statuses))
    # true prose (each status matches the oracle) must NOT fire.
    fp_true = bool(fidelity_problems(
        ["alpha quedó COMPLETE", "beta sigue INCOMPLETE"], statuses))
    # a contradicting token far from any slug (> window) must NOT fire.
    fp_window = bool(fidelity_problems(["beta " + "x" * (WINDOW_CHARS + 20) + " COMPLETE"], statuses))
    return bites_a and bites_b and not fp_true and not fp_window


def main(argv: list[str]) -> int:
    from ...memory import projection

    args = [a for a in argv if not a.startswith("--")]
    meta_root = Path(args[0]).resolve() if args else Path.cwd()
    state_path = meta_root / "docs" / "STATE.md"

    try:
        text = state_path.read_text(encoding="utf-8")
    except OSError as e:  # noqa: BLE001 — un STATE ilegible es reportable, no un crash
        print(f"STATE_FIDELITY ROJO — no pude leer {state_path}: {e}")
        return 1
    body = state_snapshot.extract_now_lines(text)
    if body is None:
        print("STATE_FIDELITY ROJO — no encontré la sección `## Ahora` en STATE.md (no puedo verificar fidelidad)")
        return 1

    statuses = projection.rtm_statuses(meta_root)
    problems = fidelity_problems(body, statuses)
    if problems:
        print("STATE_FIDELITY ROJO — «Ahora» CONTRADICE la verdad re-derivable del `.proof/` (ADR-019 §4):")
        for p in problems:
            print(f"  ✗ {p}")
        print("  -> corregí «Ahora» para que NO contradiga el RTM (la verdad vive en `.proof/`; "
              "re-derivala con `meta rtm`). El gate NO auto-reescribe: falla y señala.")
        return 1

    if not _tooth_bites():
        print("STATE_FIDELITY DECORATIVO — el detector no marcó una afirmación falsa sintética → sin dientes")
        return 1

    checked = ", ".join(f"{s}={statuses[s][0]}" for s in statuses) or "sin fábricas"
    print(f"OK state_fidelity: «Ahora» no contradice el RTM re-derivado [{checked}]; "
          f"diente RED vivo (afirma-done-falso + contradice-COMPLETE, ventana {WINDOW_CHARS}ch)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
