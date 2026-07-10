"""H6 §7 — blocking gates over PINNED runs (design/03 §3): zero-LLM, hermetic, CI-safe.

Reads `config/thresholds.yml` + the committed `runs/pinned/**` and emits one verdict per
(gate, experiment): **green | red | waived | n/a**. The exit contract (design/04 §3) is
«all gates green, or red WITH a written reason»:

- `n/a` is for experiments whose pin is EXPLICITLY pending in `runs/pinned/INDEX.md`
  (pin column `-`) — the reason is the INDEX note, never a silent hole.
- `waived` is a RED with a written reason as DATA: a `waivers:` entry in thresholds.yml
  ({gate, corpus, reason, date}). Unused waivers are surfaced (stale waiver = drift).
- `no_regression` compares each higher-is-better metric of a pin against the *previous
  green* pin of the SAME experiment; the base is EXPLICIT in INDEX.md, never guessed.

INDEX.md is load-bearing (parsed here, strict 5-column table) — a registry that lies
(missing dir, red base, unknown gated experiment) is a hard ValueError, not a verdict
(golden.py lesson: refuse silently-wrong data instead of coping with it).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..config import REPO_ROOT

PINNED_DIR = REPO_ROOT / "runs" / "pinned"

# Which run.json key carries each gated metric (first present wins: E1 pins say
# `cci_vs_37_golden`, E2 pins say `cci`).
GATE_METRIC_KEYS: dict[str, tuple[str, ...]] = {
    "judge_agreement": ("agreement",),
    "fidelity": ("fidelity",),
    "critical_nfr_recall": ("critical_nfr_recall",),
    "cci_band": ("cci", "cci_vs_37_golden"),
}

# Which blocking gate applies to which pinned experiment (design/03 §3). E3/E4 are
# REPORTED, not gated — they never appear here (H6 §5/§6).
GATED_EXPERIMENTS: dict[str, tuple[str, ...]] = {
    "E0": ("judge_agreement",),
    "E1": ("fidelity", "cci_band"),
    "E2-wepgcomp": ("fidelity", "critical_nfr_recall", "cci_band"),
    "E2-maislugar": ("fidelity", "critical_nfr_recall", "cci_band"),
}

# no_regression compares higher-is-better metrics only; CCI is toward-1 (not monotone)
# and is covered by cci_band instead.
REGRESSION_METRICS = (
    "agreement",
    "fidelity",
    "citation_coverage",
    "oracle_recall",
    "oracle_precision",
    "critical_nfr_recall",
)

_INDEX_COLUMNS = ("experiment", "pin", "previous_green", "gated", "note")
_KNOWN_GATES = tuple(GATE_METRIC_KEYS) + ("no_regression",)
_WAIVER_KEYS = ("gate", "corpus", "reason", "date")


@dataclass(frozen=True)
class PinRow:
    experiment: str
    pin: str | None            # dir name under runs/pinned, or None (pending)
    previous_green: str | None  # no_regression base pin, or None
    gated: bool
    note: str


@dataclass(frozen=True)
class GateVerdict:
    gate: str
    target: str          # experiment id
    verdict: str         # green | red | waived | n/a
    value: float | None
    threshold: str
    reason: str = ""     # written reason for n/a / waived / red


@dataclass(frozen=True)
class GatesResult:
    verdicts: list[GateVerdict]
    green: bool          # True iff no RED remains (waived / n-a do not block)
    report: str
    unused_waivers: list[dict] = field(default_factory=list)


def parse_index(path: Path) -> list[PinRow]:
    """The pin registry, STRICT: header must match, every gated experiment present."""
    if not path.is_file():
        raise ValueError(f"pin registry missing: {path}")
    table = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
             if ln.strip().startswith("|")]
    if len(table) < 2:
        raise ValueError(f"{path.name}: no table found")
    header = tuple(c.strip() for c in table[0].strip("|").split("|"))
    if header != _INDEX_COLUMNS:
        raise ValueError(f"{path.name}: header {header} != {_INDEX_COLUMNS}")

    rows: list[PinRow] = []
    for line in table[2:]:  # skip header + separator
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(_INDEX_COLUMNS):
            raise ValueError(f"{path.name}: row has {len(cells)} cells: {line!r}")
        exp, pin, prev, gated, note = cells
        if gated not in {"yes", "no"}:
            raise ValueError(f"{path.name}: {exp}: gated must be yes|no, got {gated!r}")
        pin_v = None if pin == "-" else pin
        prev_v = None if prev == "-" else prev
        if pin_v is None and prev_v is not None:
            raise ValueError(f"{path.name}: {exp}: previous_green without a pin")
        rows.append(PinRow(exp, pin_v, prev_v, gated == "yes", note))

    by_exp: dict[str, PinRow] = {}
    for r in rows:
        if r.experiment in by_exp:
            raise ValueError(f"{path.name}: duplicate experiment {r.experiment!r}")
        by_exp[r.experiment] = r
    gated_in_index = {r.experiment for r in rows if r.gated}
    expected = set(GATED_EXPERIMENTS)
    if gated_in_index != expected:
        raise ValueError(
            f"{path.name}: gated experiments {sorted(gated_in_index)} != "
            f"expected {sorted(expected)}"
        )
    return rows


def load_waivers(thresholds: dict) -> list[dict]:
    """`waivers:` block validated as DATA — a typo'd waiver would be silently useless."""
    waivers = thresholds.get("waivers") or []
    for i, w in enumerate(waivers):
        if not isinstance(w, dict) or [k for k in _WAIVER_KEYS if not str(w.get(k) or "").strip()]:
            raise ValueError(f"waiver {i}: needs non-empty {{gate, corpus, reason, date}}: {w!r}")
        if w["gate"] not in _KNOWN_GATES:
            raise ValueError(f"waiver {i}: unknown gate {w['gate']!r} (known: {_KNOWN_GATES})")
        if w["corpus"] not in GATED_EXPERIMENTS:
            raise ValueError(
                f"waiver {i}: unknown corpus {w['corpus']!r} "
                f"(gated: {sorted(GATED_EXPERIMENTS)})"
            )
    return waivers


def _load_run(pinned_dir: Path, pin: str, *, role: str) -> dict:
    path = pinned_dir / pin / "run.json"
    if not path.is_file():
        raise ValueError(f"INDEX.md registers {role} pin {pin!r} but {path} is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(run: dict, gate: str, pin: str) -> float:
    for key in GATE_METRIC_KEYS[gate]:
        if key in run:
            return float(run[key])
    raise ValueError(
        f"pin {pin!r}: run.json lacks metric for gate {gate!r} "
        f"(looked for {GATE_METRIC_KEYS[gate]})"
    )


def evaluate_gates(thresholds: dict, *, pinned_dir: Path | None = None) -> GatesResult:
    pinned_dir = pinned_dir or PINNED_DIR
    rows = parse_index(pinned_dir / "INDEX.md")
    waivers = load_waivers(thresholds)
    used: set[int] = set()
    gates_cfg = thresholds["gates"]
    verdicts: list[GateVerdict] = []

    def close(gate: str, target: str, ok: bool, value: float | None,
              threshold: str, reason: str = "") -> None:
        verdict, why = ("green", "") if ok else ("red", reason)
        if not ok:
            for i, w in enumerate(waivers):
                if w["gate"] == gate and w["corpus"] == target:
                    verdict = "waived"
                    why = f"{w['reason']} ({w['date']})"
                    used.add(i)
                    break
        verdicts.append(GateVerdict(gate, target, verdict, value, threshold, why))

    by_exp = {r.experiment: r for r in rows}
    for exp, exp_gates in GATED_EXPERIMENTS.items():
        row = by_exp[exp]  # completeness enforced by parse_index
        if row.pin is None:
            for gate in exp_gates:
                verdicts.append(GateVerdict(
                    gate, exp, "n/a", None, _render_threshold(gate, gates_cfg),
                    f"no pin registered (INDEX: {row.note})"))
            verdicts.append(GateVerdict(
                "no_regression", exp, "n/a", None,
                _render_threshold("no_regression", gates_cfg),
                f"no pin registered (INDEX: {row.note})"))
            continue

        run = _load_run(pinned_dir, row.pin, role=exp)
        for gate in exp_gates:
            value = round(_metric(run, gate, row.pin), 4)
            cfg = gates_cfg[gate]
            if gate == "cci_band":
                ok = float(cfg["min"]) <= value <= float(cfg["max"])
            else:
                ok = value >= float(cfg["min"])
            close(gate, exp, ok, value, _render_threshold(gate, gates_cfg),
                  f"pin {row.pin}")

        if row.previous_green is None:
            verdicts.append(GateVerdict(
                "no_regression", exp, "n/a", None,
                _render_threshold("no_regression", gates_cfg),
                "no previous green pin registered (INDEX)"))
        else:
            base = _load_run(pinned_dir, row.previous_green, role=f"{exp} base")
            if base.get("green") is not True:
                raise ValueError(
                    f"INDEX.md: {exp}: previous_green {row.previous_green!r} "
                    "is not a green pin")
            allowed = float(gates_cfg["no_regression"]["max_drop_pts"]) / 100.0
            drops = {
                m: round(float(base[m]) - float(run[m]), 4)
                for m in REGRESSION_METRICS if m in run and m in base
            }
            if not drops:
                raise ValueError(
                    f"{exp}: no shared regression metrics between "
                    f"{row.pin!r} and {row.previous_green!r}")
            bad = {m: d for m, d in drops.items() if d > allowed}
            worst = max(drops.values())
            close("no_regression", exp, not bad, worst,
                  _render_threshold("no_regression", gates_cfg),
                  f"vs {row.previous_green}: dropped {bad}" if bad
                  else f"vs {row.previous_green}")

    unused = [w for i, w in enumerate(waivers) if i not in used]
    green = not any(v.verdict == "red" for v in verdicts)
    report = _render_report(verdicts, green, unused)
    return GatesResult(verdicts, green, report, unused)


def _render_threshold(gate: str, gates_cfg: dict) -> str:
    cfg = gates_cfg[gate]
    if gate == "cci_band":
        return f"in [{cfg['min']}, {cfg['max']}]"
    if gate == "no_regression":
        return f"drop <= {cfg['max_drop_pts']}pts"
    return f">= {cfg['min']}"


def _render_report(verdicts: list[GateVerdict], green: bool, unused: list[dict]) -> str:
    lines = ["=== eval gates — config/thresholds.yml vs runs/pinned (hermetic, zero-LLM) ==="]
    for v in verdicts:
        val = "-" if v.value is None else f"{v.value:.4f}"
        line = f"{v.gate:<22}{v.target:<15}{val:<10}{v.threshold:<18}{v.verdict.upper()}"
        if v.reason:
            line += f"  ({v.reason})"
        lines.append(line)
    for w in unused:
        lines.append(f"STALE WAIVER (matched nothing red): {w['gate']}/{w['corpus']} — {w['reason']}")
    counts = {s: sum(1 for v in verdicts if v.verdict == s)
              for s in ("green", "red", "waived", "n/a")}
    lines.append(
        f"GATES: {'GREEN' if green else 'RED'} — "
        + " · ".join(f"{n} {s}" for s, n in counts.items())
    )
    return "\n".join(lines)
