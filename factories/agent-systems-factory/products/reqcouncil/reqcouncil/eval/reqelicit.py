"""E3 adapter + sampler for ReqElicitBench (docs/design/03, H6 §2).

Joins the published DeepSeek-V3.2 (no_thinking) dialogues with the benchmark's task
metadata, renders each dialogue as a speaker-tagged transcript the H1 ingest parses,
and draws a deterministic stratified sample.

MEASURED CORRECTION (2026-07-06): the join is by **(task_name, initial_requirements)**,
not `task_name` alone — 2 task names are REUSED for genuinely distinct tasks (different
initial_requirements, golden stories and application_type). A name-only join under-counts
to 98 and is ambiguous for those 4 rows; the unambiguous key yields **100** scenarios
(all 100 DeepSeek dialogues match a unique test.json task; the 101st test task has no
dialogue and is correctly excluded). This corrects the "98" written in the H6 contract.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..config import REPO_ROOT

DATA_ROOT = REPO_ROOT / "datasets" / "reqelicitbench"
TEST_JSON = DATA_ROOT / "ReqElicitGym" / "data" / "test.json"
# The base published condition matching our provider family (H6 §2 decision).
DEFAULT_ARM = "DeepSeek-V3.2_no_thinking_all.json"

EXPECTED_SCENARIOS = 100  # measured (name, initial_requirements) join — see module docstring


@dataclass(frozen=True)
class Scenario:
    """One joined dialogue + gold. `conversation` is (interviewer, user) per turn."""

    task_id: str
    name: str
    application_type: str
    initial_requirements: str
    golden_stories: tuple[str, ...]        # user_stories (the gold, per dialogue)
    implicit_requirements: tuple[str, ...] # test.json Implicit Requirements[*].RequirementText
    conversation: tuple[tuple[str, str], ...]

    @property
    def turn_order(self) -> int:
        """Stable numeric order from task_id (`task_57` -> 57) for deterministic sampling."""
        tail = self.task_id.rsplit("_", 1)[-1]
        return int(tail) if tail.isdigit() else 0


def _collapse(text: str) -> str:
    """Whitespace-collapse a turn so it renders on ONE parseable line (round-trip safe)."""
    return " ".join(str(text or "").split())


def load_scenarios(
    arm_file: str = DEFAULT_ARM, *, data_root: Path | None = None
) -> list[Scenario]:
    root = data_root or DATA_ROOT
    test = json.loads((TEST_JSON if data_root is None else root / "ReqElicitGym" / "data" / "test.json").read_text(encoding="utf-8"))
    conv = json.loads((root / "conversation_result" / arm_file).read_text(encoding="utf-8"))

    by_key: dict[tuple[str, str], dict] = {}
    for e in test:
        by_key[(e["name"], e["initial_requirements"])] = e

    scenarios: list[Scenario] = []
    for c in conv:
        key = (c["task_name"], c["initial_requirements"])
        meta = by_key.get(key)
        if meta is None:
            continue  # dialogue with no gold task (should not happen for the DeepSeek arm)
        implicit = tuple(
            str(item["RequirementText"]).strip()
            for item in (meta.get("Implicit Requirements") or [])
            if str(item.get("RequirementText") or "").strip()
        )
        turns = tuple(
            (str(t.get("interviewer") or ""), str(t.get("user") or ""))
            for t in c["conversation"]
        )
        scenarios.append(
            Scenario(
                task_id=c["task_id"],
                name=c["task_name"],
                application_type=meta["application_type"],
                initial_requirements=c["initial_requirements"],
                golden_stories=tuple(c["user_stories"]),
                implicit_requirements=implicit,
                conversation=turns,
            )
        )

    if len(scenarios) != EXPECTED_SCENARIOS:
        raise ValueError(
            f"reqelicit join: expected {EXPECTED_SCENARIOS} scenarios, found {len(scenarios)} "
            f"(arm={arm_file})"
        )
    return scenarios


def render_transcript(scenario: Scenario) -> str:
    """Render as `[H:MM:SS] spk_0: <interviewer>` / `spk_1: <user>`, one line per side.

    Speakers strictly alternate 0,1,0,1 so the H1 parser never merges turns; every side
    (even an empty one, faithful to the corpus) is a distinct parseable line. Timestamps
    are synthetic and monotonic — the parser stores but never reasons over them.
    """
    lines: list[str] = []
    for i, (interviewer, user) in enumerate(scenario.conversation):
        lines.append(f"[0:{i:02d}:00] spk_0: {_collapse(interviewer)}")
        lines.append(f"[0:{i:02d}:30] spk_1: {_collapse(user)}")
    return "\n".join(lines) + "\n"


def expected_turns(scenario: Scenario) -> list[tuple[int, str]]:
    """The (speaker, collapsed_text) turns `render_transcript` must round-trip to."""
    out: list[tuple[int, str]] = []
    for interviewer, user in scenario.conversation:
        out.append((0, _collapse(interviewer)))
        out.append((1, _collapse(user)))
    return out


def _hare_quota(counts: dict[str, int], n: int) -> dict[str, int]:
    """Largest-remainder (Hare) apportionment of `n` across strata, deterministic.

    Floor of each proportional share, then hand out the remaining seats to the largest
    fractional remainders; ties are broken by stratum name (stable, reproducible).
    """
    total = sum(counts.values())
    if total == 0 or n <= 0:
        return {k: 0 for k in counts}
    shares = {k: n * c / total for k, c in counts.items()}
    quota = {k: int(math.floor(s)) for k, s in shares.items()}
    remaining = n - sum(quota.values())
    order = sorted(counts, key=lambda k: (-(shares[k] - quota[k]), k))
    for k in order[:remaining]:
        quota[k] += 1
    return quota


def sample(scenarios: list[Scenario], n: int = 20, *, seed: int = 7) -> list[Scenario]:
    """Proportional-stratified sample by `application_type` (Hare quotas).

    Deterministic: within each stratum the first `quota` scenarios by `turn_order` are
    taken (task_id is the stable tiebreak). `seed` is recorded in the run summary for
    provenance; the selection itself is fully determined by (scenarios, n) given the
    frozen corpus, so a re-run is byte-identical.
    """
    if n > len(scenarios):
        raise ValueError(f"cannot sample {n} from {len(scenarios)} scenarios")
    strata: dict[str, list[Scenario]] = defaultdict(list)
    for s in scenarios:
        strata[s.application_type].append(s)
    counts = {k: len(v) for k, v in strata.items()}
    quota = _hare_quota(counts, n)

    chosen: list[Scenario] = []
    for app_type in sorted(strata):
        picks = sorted(strata[app_type], key=lambda s: s.turn_order)[: quota[app_type]]
        chosen.extend(picks)
    chosen.sort(key=lambda s: s.turn_order)
    return chosen
