"""C1 — the `generate` creative slot, proven by blocking at the STATION+COLUMN level.

Drives the REAL engine (`run_station`) + the REAL seed verifier + the REAL gate (not a mock):
a station GENERATES an artifact via a generator declared in DATA, and the column VERIFIES it.
The three scenarios are the C1 gate (ROADMAP §Fase C):
  - generate -> column verifies -> gate OPEN
  - corrupt the BRIEF (generation's input) -> wrong artifact -> column SHUT
  - generator produces nothing -> artifact absent -> column SHUT (the substrate never fakes it)

Hermetic: meta_root is the real repo (so checks can `python -m metafactory...` and the verdict
comes from the real seed), but record_active=False keeps proofs in tmp_path and writes no
active.json/journal — a test never leaks into the real line.
"""
from __future__ import annotations

import sys
from pathlib import Path

from metafactory._seed import repo_root
from metafactory.engine.run_context import RunContext
from metafactory.engine.runner import run_station
from metafactory.engine.sequence import Sequence
from metafactory.engine.station import Station

PY = sys.executable
# Generator declared in DATA: reads the brief, emits the artifact. Deterministic so the proof is
# reproducible; a live `claude -p "<brief>"` would be the same seam with different `via` data.
_GEN = ("import os; "
        "open(os.environ['METAFACTORY_DEST'],'w').write(open(os.environ['METAFACTORY_BRIEF']).read())")
MARKER = "C1_GEN_OK"


def _gen_station(brief: str, *, dest: str = "build/artifact.py", via=None) -> Station:
    return Station.from_dict({
        "id": "c1demo", "name": "generate + verify",
        "builds": [{"action": "generate", "dest": dest, "brief": brief,
                    "via": via if via is not None else [PY, "-c", _GEN]}],
        "checks": [{"name": "invariant", "kind": "artifact_contains", "file": dest, "marker": MARKER}],
    })


def _run(tmp_path: Path, station: Station):
    ctx = RunContext(root=tmp_path, meta_root=repo_root())
    seq = Sequence([station])
    return run_station(ctx, station, seq, {}, stations_dir=tmp_path, spec_path=None,
                       record_active=False)


# ── the C1 gate ────────────────────────────────────────────────────────────────

def test_generate_then_column_verifies_gate_opens(tmp_path):
    """A station generates an artifact via a DECLARED generator; the column verifies it -> OPEN.
    The substrate wrote neither the artifact (the generator did) nor the verdict (the seed did)."""
    run = _run(tmp_path, _gen_station(f"def greet(): return {MARKER!r}"))
    assert (tmp_path / "build" / "artifact.py").read_text() == f"def greet(): return {MARKER!r}"
    assert run.passed is True
    assert run.gate.opened is True
    assert run.proof["writer"] == "seed/verifier.py"  # verdict by the trust root, not the runner


def test_corrupt_brief_makes_column_shut(tmp_path):
    """Corrupt the BRIEF (generation's input): the generator faithfully emits an artifact WITHOUT
    the invariant -> the column SHUTs. Proves the artifact genuinely flows brief->generator->dest."""
    run = _run(tmp_path, _gen_station("def greet(): return 'CORRUPTED'"))
    assert (tmp_path / "build" / "artifact.py").read_text() == "def greet(): return 'CORRUPTED'"
    assert run.passed is False
    assert run.gate.opened is False


def test_generator_produces_nothing_column_shut(tmp_path):
    """A generator that writes nothing -> artifact ABSENT -> column SHUT. The substrate does not
    fake the artifact, and an absent artifact is never a spurious pass."""
    run = _run(tmp_path, _gen_station("irrelevant", via=[PY, "-c", "pass"]))
    assert not (tmp_path / "build" / "artifact.py").exists()
    assert run.passed is False
    assert run.gate.opened is False


def test_same_seam_gates_a_non_python_artifact(tmp_path):
    """principle #6: the SAME seam+column gate a TypeScript artifact — no per-tech branch anywhere."""
    st = _gen_station(f"export const greet = () => '{MARKER}';", dest="build/mod.ts")
    run = _run(tmp_path, st)
    assert (tmp_path / "build" / "mod.ts").read_text() == f"export const greet = () => '{MARKER}';"
    assert run.passed is True and run.gate.opened is True
