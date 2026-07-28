"""spec_doc_check — structural conformance of two spec documents against LIVE artifacts.

Level L2+ of the conformance ladder (§12). Presence is not sufficiency: `spec_schema_cover` already
proves that every gate name and every check kind is *mentioned* somewhere in `docs/spec/`. This tool
proves something stronger and much harder to fake:

  --mode catalogs   `16-catalogs.md` carries ONE ROW PER GATE with its red-side witness DECLARED,
                    and one row per check kind. The witness cell must be a path, or an explicit
                    `one-sided` / `NONE — DEBT`. It may not be blank and it may not be prose: a
                    catalogue whose witness column is decorative would hide exactly the gate that
                    cannot go red (`generality`, today).

  --mode golden     `17-golden-example.md` carries the dummy factory's REAL station outcomes, and
                    the kernel of §14 recomputes each `proof_sha` from the document's own table.
                    They must equal the COMMITTED `factories/dummy/pinned_verdict.json`. A worked
                    example that cannot reproduce the pin is a story, not a golden example.

Two-sided: SPEC_DOC_SABOTAGE=1 perturbs the parsed content; both modes MUST go red.

Usage:  python3 tools/spec_doc_check.py --mode catalogs|golden|all
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "docs" / "spec" / "16-catalogs.md"
GOLDEN = ROOT / "docs" / "spec" / "17-golden-example.md"
GOLDEN_BLOCK = re.compile(r"<!--\s*golden:\s*dummy\s*-->\s*\n```json\n(.*?)\n```", re.DOTALL)
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*)$")
WITNESS = re.compile(r"(\.py\b|/|one-sided|NONE\s*[—-]\s*DEBT)", re.IGNORECASE)


def gate_names() -> set[str]:
    """The gates `meta check` actually runs, read from the source of truth (ast, not prose)."""
    tree = ast.parse((ROOT / "src" / "metafactory" / "cli.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "cmd_check":
            names = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    for k, v in zip(sub.keys, sub.values):
                        if (isinstance(k, ast.Constant) and k.value == "name"
                                and isinstance(v, ast.Constant) and isinstance(v.value, str)):
                            names.add(v.value)
            return names
    return set()


def kind_names() -> set[str]:
    sys.path.insert(0, str(ROOT / "src"))
    from metafactory.verify.checks.registry import KINDS
    return set(KINDS)


def _rows(text: str) -> dict[str, str]:
    """Every markdown table row whose FIRST cell is a `backticked` token → the rest of the row."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m:
            out.setdefault(m.group(1).strip(), m.group(2))
    return out


def check_catalogs(sabotage: bool) -> list[str]:
    if not CATALOGS.exists():
        return [f"CONF-S7: {CATALOGS.relative_to(ROOT)} does not exist"]
    text = CATALOGS.read_text(encoding="utf-8")
    rows = _rows(text)
    if sabotage:
        rows.pop(sorted(rows)[0], None)          # remove one documented entry
    problems: list[str] = []
    for g in sorted(gate_names()):
        if g not in rows:
            problems.append(f"CONF-S7: gate `{g}` has no row in 16-catalogs.md")
        elif not WITNESS.search(rows[g]):
            problems.append(f"CONF-S7: gate `{g}` declares no red-side witness "
                            f"(use a path, `one-sided`, or `NONE — DEBT`)")
    for k in sorted(kind_names()):
        if k not in rows:
            problems.append(f"CONF-S6: check kind `{k}` has no row in 16-catalogs.md")
    return problems


def check_golden(sabotage: bool) -> list[str]:
    if not GOLDEN.exists():
        return [f"CONF-G1: {GOLDEN.relative_to(ROOT)} does not exist"]
    m = GOLDEN_BLOCK.search(GOLDEN.read_text(encoding="utf-8"))
    if not m:
        return ["CONF-G1: no `<!-- golden: dummy -->` json block in 17-golden-example.md"]
    try:
        doc = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        return [f"CONF-G1: the golden block is not valid JSON: {exc}"]

    sys.path.insert(0, str(ROOT / "tools"))
    from spec_conformance import extract, load_module
    src, _ = extract(ROOT, "kernel")
    kernel = load_module(src, False)

    pin = json.loads((ROOT / "factories" / "dummy" / "pinned_verdict.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    stations = doc.get("stations") or []
    if sabotage and stations:
        stations = [dict(stations[0], checks=(stations[0].get("checks") or []) + [["zz", 1]])] \
            + stations[1:]

    seen = set()
    for st in stations:
        sid = str(st.get("id"))
        seen.add(sid)
        checks = [{"name": str(n), "exit": int(e)} for n, e in (st.get("checks") or [])]
        # CONF-G2 — the kernel of §14 recomputes the document's own declared sha.
        recomputed = kernel["compute_proof_sha"](sid, checks)
        if recomputed != str(st.get("proof_sha")):
            problems.append(f"CONF-G2: station {sid}: the declared checks do not produce the "
                            f"declared proof_sha")
            continue
        # CONF-G3 — and that sha is the COMMITTED pin.
        if sid not in pin:
            problems.append(f"CONF-G3: station {sid} is not in dummy's committed pin")
        elif pin[sid] != recomputed:
            problems.append(f"CONF-G3: station {sid}: recomputed sha != committed pin")
        # CONF-G4 — `passed` must be derivable and true for a pinned station.
        if kernel["recompute_passed"](checks) is not True:
            problems.append(f"CONF-G4: station {sid}: a pinned station must recompute as passed")
    missing = sorted(set(pin) - seen)
    if missing:
        problems.append(f"CONF-G5: the golden example omits pinned station(s): {', '.join(missing)}")
    return problems


RATIONALE = ROOT / "docs" / "spec" / "18-rationale.md"
ENTRY = re.compile(r"^###\s+(R-\d+)\s*·\s*(.+?)\s*$")


def check_rationale(sabotage: bool) -> list[str]:
    """§18.8 — a rejection without a reopening condition is dogma; with one it is engineering.

    Every `R-N` entry must declare BOTH the measurement that refused it and the falsifiable
    condition that puts it back on the table. "never" is permitted but must be written, so that
    claiming permanence is a visible act rather than an omission.
    """
    if not RATIONALE.exists():
        return [f"CONF-R1: {RATIONALE.relative_to(ROOT)} does not exist"]
    lines = RATIONALE.read_text(encoding="utf-8").splitlines()
    entries: dict[str, list[str]] = {}
    current = None
    for line in lines:
        m = ENTRY.match(line)
        if m:
            current = m.group(1)
            entries[current] = []
        elif line.startswith("## "):
            current = None
        elif current:
            entries[current].append(line)
    if not entries:
        return ["CONF-R1: no `### R-N · …` entries found — the register is empty"]
    if sabotage and entries:
        victim = sorted(entries)[0]
        entries[victim] = [ln for ln in entries[victim] if "Reopens when" not in ln]

    problems = []
    for eid in sorted(entries):
        body = "\n".join(entries[eid])
        if "**Evidence:**" not in body:
            problems.append(f"CONF-R2: {eid} declares no **Evidence:** — a rejection needs a "
                            f"measurement, not a feeling")
        if "**Reopens when:**" not in body:
            problems.append(f"CONF-R3: {eid} declares no **Reopens when:** — a rejection without a "
                            f"reopening condition is dogma (write `never` and argue it, if so)")
    return problems


def main(argv: list[str]) -> int:
    mode = "all"
    if "--mode" in argv:
        mode = argv[argv.index("--mode") + 1]
    sabotage = os.environ.get("SPEC_DOC_SABOTAGE") == "1"

    problems: list[str] = []
    if mode in ("catalogs", "all"):
        problems += check_catalogs(sabotage)
    if mode in ("golden", "all"):
        problems += check_golden(sabotage)
    if mode in ("rationale", "all"):
        problems += check_rationale(sabotage)

    if sabotage:
        if problems:
            print("VERDICT    spec-doc-check (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the perturbation was detected: {len(problems)} problem(s)")
            return 0
        print("VERDICT    spec-doc-check (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a perturbed document passed")
        return 1

    if problems:
        print(f"VERDICT    spec-doc-check [{mode}] — FAIL   (exit 1)")
        print(f"SUMMARY    {len(problems)} problem(s)")
        for p in problems[:6]:
            print(f"FAILURES   {p}")
        if len(problems) > 6:
            print(f"FAILURES   … and {len(problems) - 6} more")
        return 1
    print(f"VERDICT    spec-doc-check [{mode}] — PASS   (exit 0)")
    print(f"SUMMARY    {len(gate_names())} gate(s) + {len(kind_names())} kind(s) catalogued; "
          f"dummy's pin reproduces from the golden example")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
