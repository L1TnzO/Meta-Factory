"""The gate registry, and the law that a gate cannot register without a way to fail.

Transcribed from `docs/spec/18-rationale.md` R-10 (a gate that cannot fail proves nothing —
"tightened in v3 to a registration requirement") and R-12 (N/A is honest; N/A silently counted as
PASS is not).

WHAT CHANGES FROM v2. There, the gate list is a literal inside `cmd_check` and two-sidedness is a
convention: 14 of 23 gates happen to carry a red witness, three carry none at all, and nothing in
the machine notices. The census lives in a documentation table, which is to say it lives nowhere
the machine can read. Here the list is DATA and the witness is a REGISTRATION ARGUMENT, so the
question "can this gate fail?" is answered before the suite runs, not audited afterwards.

THE LAW, in one sentence: a gate registers iff it declares either a reachable red witness or an
enumerated, pre-argued reason for being one-sided.

Four refusals, and the third is the one that closes a real hole in v2:

  1. NO ARGV — a gate that is not a process cannot produce evidence. I-1: a green is traceable to
     an OS process that exited 0.
  2. NEITHER witness NOR `one_sided` — the R-10 case. This is what `generality` has to answer.
  3. A FIXTURE THAT IS NOT THERE. v2 treats a missing red-side fixture as N/A and stays green
     (SAFE-7 — never faked green, but also never armed). The failure mode is quiet: delete the
     fixture and the tooth is gone while the suite still reports the gate as passing. Here it
     refuses to register, so a disarmed gate is loud.
  4. `one_sided` INVENTED AT THE CALL SITE. The exemption reads from a closed constant below and
     the rationale must match it byte for byte, so claiming it means editing this file — the same
     shape as `agent_roles` and `KINDS`, for the same reason: an exemption anyone can grant in
     passing is not an exemption, it is a default.

THE HONEST LIMIT, stated rather than discovered later. Registration checks the DECLARATION: that a
witness exists, is of a known kind, and is reachable. It cannot check that the witness still BITES
— that costs a process, and it is P2's job (`11-build-plan.md §2`), which re-runs the red side
rather than assuming it. Two moments, deliberately: the declaration is enforced here at import
time; the bite is enforced by running it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Closed vocabulary. A new kind is an edit here plus an argument, never a string at a call site.
WITNESS_KINDS = (
    "sabotage_env",   # the gate re-runs ITSELF with this env var set and must flip. Handle: VAR name.
    "fixture",        # a committed file that must trip the check. Handle: repo-relative path.
    "pinned_data",    # committed DATA whose re-evaluation must fail (a ceiling that must not MEET).
)

# The ONLY gates allowed to be one-sided, each with the reason, checked verbatim. These are test
# runners: their red side is the tests they run, so a separate witness would be a second copy of
# the same fact rather than an independent one.
ONE_SIDED: dict[str, str] = {
    "compile": "a syntax gate's red side is a syntax error; a committed one would break every other gate first",
    "isolation": "the red side is the import it forbids; committing it would violate the invariant it guards",
    "suite": "a test runner's red side is its own corpus — each ported test carries its own RED fixture",
}

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

PASS, FAIL, NA = "PASS", "FAIL", "N/A"


class RegistrationRefused(Exception):
    """Raised at registration, never at run time — the point is that the suite does not start."""


@dataclass(frozen=True)
class Witness:
    """How this gate is known to be able to fail."""

    kind: str
    handle: str

    @property
    def is_embedded(self) -> bool:
        """A fixture/pinned-data witness is asserted INSIDE the gate's own green run; a sabotage
        witness is a second process. The runner needs to know which, because only the second one
        can be re-run independently."""
        return self.kind != "sabotage_env"


@dataclass(frozen=True)
class Gate:
    name: str
    argv: tuple[str, ...]
    proves: str
    witness: Witness | None = None
    one_sided_because: str = ""
    na_when: str = ""   # the vacuous-true branch, named. "" means the gate has none.

    def red_run(self) -> tuple[tuple[str, ...], dict[str, str]] | None:
        """The command that RE-RUNS this gate's witness, or None when the red side is embedded in
        the green run.

        CONTRACT, and it is the opposite of the obvious one: the returned command must exit **0**,
        reporting that it planted its problem and CAUGHT it. It is not "the command that must fail".

        The obvious convention — a red side is anything non-zero — cannot tell a witness that bit
        from a module with a syntax error, a bad import, or any crash. Under it, deleting the body
        of a gate would certify its witness as working, which is precisely backwards. Requiring the
        red side to exit 0 forces it to REPORT the catch, so the sweep is reading an assertion
        rather than an absence. Every gate in `v3/verify/` already works this way (`*_SABOTAGE=1`
        prints `GATE DECORATIVO` and exits 1 when the planted problem is NOT caught); this docstring
        used to say the reverse, and `suite_sweep` faithfully implemented the reverse.
        """
        if self.witness is None or self.witness.is_embedded:
            return None
        return self.argv, {self.witness.handle: "1"}


class Registry:
    """Holds the gates and refuses the ones that cannot fail."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._gates: dict[str, Gate] = {}

    def register(self, gate: Gate) -> Gate:
        problem = self._refuse(gate)
        if problem:
            raise RegistrationRefused(f"{gate.name or '<unnamed>'}: {problem}")
        self._gates[gate.name] = gate
        return gate

    def _refuse(self, gate: Gate) -> str:
        if not gate.name.strip():
            return "a gate with no name cannot be reported, skipped, or argued about"
        if gate.name in self._gates:
            return "already registered — a second definition would silently shadow the first"
        if not gate.argv:
            return ("no argv: a gate is a process whose exit code IS the evidence (I-1); "
                    "an in-process assertion is not a gate")
        if not gate.proves.strip():
            return "no statement of what it proves — an unstated claim cannot be shown to have decayed"

        has_witness, claims_one_sided = gate.witness is not None, bool(gate.one_sided_because)
        if has_witness and claims_one_sided:
            return "declares BOTH a red witness and a one-sided exemption; one of the two is untrue"
        if not has_witness and not claims_one_sided:
            return ("no red witness and no one-sided exemption (R-10): a gate that cannot fail "
                    "proves nothing, and this is the moment that is supposed to hurt")

        if claims_one_sided:
            return self._refuse_one_sided(gate)
        return self._refuse_witness(gate.witness)   # type: ignore[arg-type]

    def _refuse_one_sided(self, gate: Gate) -> str:
        if gate.name not in ONE_SIDED:
            return (f"claims a one-sided exemption but is not in the closed ONE_SIDED constant; "
                    f"granting one means editing {__name__} and arguing it there")
        if gate.one_sided_because != ONE_SIDED[gate.name]:
            return ("one-sided rationale does not match the constant verbatim — the reason is "
                    "single-source, so a call site cannot restate it into something weaker")
        return ""

    def _refuse_witness(self, witness: Witness) -> str:
        if witness.kind not in WITNESS_KINDS:
            return f"unknown witness kind {witness.kind!r}; known: {', '.join(WITNESS_KINDS)}"
        if not witness.handle.strip():
            return f"witness of kind {witness.kind!r} with an empty handle points at nothing"
        if witness.kind == "sabotage_env":
            if not _ENV_NAME.match(witness.handle):
                return f"sabotage handle {witness.handle!r} is not an environment variable name"
            return ""
        if not (self.root / witness.handle).exists():
            return (f"red-side {witness.kind} {witness.handle!r} is not in the tree: the gate would "
                    f"run with its tooth removed and still report green (the v2 N/A hole)")
        return ""

    # ── reading ──────────────────────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self._gates)

    def __contains__(self, name: object) -> bool:
        return name in self._gates

    def names(self) -> list[str]:
        return sorted(self._gates)

    def gates(self) -> list[Gate]:
        return [self._gates[n] for n in self.names()]

    def get(self, name: str) -> Gate:
        return self._gates[name]

    def two_sided(self) -> list[Gate]:
        return [g for g in self.gates() if g.witness is not None]


@dataclass(frozen=True)
class Outcome:
    """One gate's result. `status` is one of PASS / FAIL / N/A and N/A is never a shade of PASS."""

    gate: str
    status: str
    detail: str = ""


def summarize(outcomes: list[Outcome], verb: str = "check"):
    """R-12: three counts, printed apart. An all-N/A suite is NOT green.

    The last rule is Lock #1's shape, one level up: the kernel refuses to call a station passed on
    an empty check list, and a suite of nothing but vacuous branches is the same claim wearing a
    different hat — everything that could have been decided was skipped.
    """
    from ..kernel.report import Verdict

    green = [o for o in outcomes if o.status == PASS]
    red = [o for o in outcomes if o.status == FAIL]
    na = [o for o in outcomes if o.status == NA]
    unknown = [o for o in outcomes if o.status not in (PASS, FAIL, NA)]

    counts = {"green": len(green), "red": len(red), "n/a": len(na)}
    if unknown:
        return Verdict(verb, 2, f"{len(unknown)} outcome(s) with a status outside PASS/FAIL/N-A",
                       counts=counts, failures=tuple(f"{o.gate}: {o.status!r}" for o in unknown))
    if red:
        return Verdict(verb, 1, f"{len(red)} gate(s) red", counts=counts,
                       failures=tuple(f"{o.gate}: {o.detail}" for o in red))
    if not green:
        return Verdict(verb, 1,
                       f"nothing was decided: {len(na)} gate(s) N/A and none green — a suite that "
                       f"skipped everything is not a passing suite", counts=counts)
    return Verdict(verb, 0, f"{len(green)} gate(s) green, {len(na)} N/A (counted apart, R-12)",
                   counts=counts)
