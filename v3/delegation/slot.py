"""The slot contract: what a delegated leaf may do, written down before it is allowed to run.

A slot is the unit of delegation. It carries the DOMAIN (which is why one `generator` serves every
factory — ADR-020), the blast radius, and the two gates that decide whether its work is accepted. It
lives on disk as JSON because it is EVIDENCE: it must survive a crash, and the footprint sweep reads
it back after the fact.

── ON PYDANTIC (R-14, decided here because this is the file whose trigger it named) ──────────────

ADR-023 §2 requires asking what the community already validated before hand-writing anything, and
§18 R-14 deferred the answer to exactly this moment, when the manifest stops being in-process and
starts being PARSED. Decided: **not for this file.**

The reason is specific and not a preference for writing our own code. Pydantic's default posture is
COERCION — it will happily turn `"1"` into `1`, a string into a list-of-one, a missing optional into
a default. That is the right posture for an API boundary and the wrong one for a security boundary:
this manifest is what makes `blast_radius` bounded, and a malformed manifest must DENY, never be
repaired into something plausible. Strict mode exists, but then one is writing configuration to
obtain the behaviour one would otherwise have written directly — and the trust chain is the one thing
this project writes and reviews with its own eyes.

The decision is scoped, not a blanket rejection: for the STATION YAML and the FACTORY SPEC — large
schemas, no security frontier, coercion harmless — pydantic remains a live candidate and R-14 is
re-triggered at INC-4, where those are ported.

── FAIL-CLOSED, and what that means concretely ───────────────────────────────────────────────────

Every unknown shape, every missing key, every type surprise is a REFUSAL. A slot that does not
validate is not a slot with problems; it is not a slot, and nothing may be spawned against it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: Where the live manifest lives, relative to the run root. Same path as v2 on purpose: it is
#: evidence, and an operator who knows where to look should keep knowing.
MANIFEST_PATH = ".gen/active_slot.json"

REQUIRED_KEYS = ("slot_id", "allow_globs", "verdict_path", "iteration_gate_cmd", "acceptance_gate_cmd")

#: Closed vocabularies (the PWF harvest, §Fase 4 of REAIM): a value outside them is a refusal, not a
#: warning. Adding a member is a governance act.
#:
#: THESE ARE THE SEED'S VALUES, DELIBERATELY, and the reason is worth the paragraph. INC-3 shipped
#: this file with invented alternatives (`untrusted/bounded/trusted`, `.../expensive`,
#: `none/workspace/...`) and `side_effects` as a scalar instead of a list. Nothing announced it, so
#: it read as a port. It was not: `seed/delegation.py:60-62` and the spec (§13:375-377, §05:43) both
#: say `low/medium/high`, `cheap/standard/premium`, and a LIST of `files/network/process`.
#:
#: The consequence was invisible until INC-4's `plan` gate met a real file: every WorkOrder written
#: by v2 — every plan, every archived manifest — is REFUSED by v3 for naming a value that was legal
#: when it was written. A vocabulary is a wire format between the two systems while both exist, and
#: renaming one silently turns "this manifest is malformed" and "this manifest is old" into the same
#: message. Aligned back, so the two systems refuse the same slots for the same reasons — which is
#: what the `WALL_MAX_S` note below already promised on this file's behalf.
TRUST_LEVELS = ("low", "medium", "high")
COST_CLASSES = ("cheap", "standard", "premium")
SIDE_EFFECTS = ("files", "network", "process")

#: A slot that needs longer than this is too big and must be SPLIT — change-scope == verification
#: scope. The number is v2's, kept so the two systems refuse the same slots.
WALL_MAX_S = 1800


@dataclass(frozen=True)
class Slot:
    slot_id: str
    allow_globs: tuple[str, ...]
    verdict_path: str
    iteration_gate_cmd: tuple[str, ...]
    acceptance_gate_cmd: tuple[str, ...]
    trust_level: str = "medium"
    cost_class: str = "standard"
    side_effects: tuple[str, ...] = ("files",)
    max_wall_s: int = 600
    #: Paths ALREADY dirty when the slot opened. Without this the footprint sweep would blame the
    #: generator for someone else's uncommitted work — and a sweep that cries wolf gets disabled.
    baseline_dirty: tuple[str, ...] = ()
    raw: dict = field(default_factory=dict, repr=False)


def problems(data: object) -> list[str]:
    """Validate a manifest as it comes off disk. Returns EVERY problem, so a fix is one pass.

    Written against `object`, not `dict`, because "it came back as a list" is exactly the shape a
    hand-written validator forgets and a security boundary cannot afford to.
    """
    if not isinstance(data, dict):
        return [f"manifest is {type(data).__name__}, not an object"]

    out: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in data:
            out.append(f"missing required key `{key}`")

    slot_id = data.get("slot_id")
    if "slot_id" in data and (not isinstance(slot_id, str) or not slot_id.strip()):
        out.append("`slot_id` must be a non-empty string")

    globs = data.get("allow_globs")
    if "allow_globs" in data:
        if not isinstance(globs, list) or not globs:
            out.append("`allow_globs` must be a non-empty list: an unbounded slot is not a slot")
        elif not all(isinstance(g, str) and g.strip() for g in globs):
            out.append("`allow_globs` entries must be non-empty strings")

    for key in ("iteration_gate_cmd", "acceptance_gate_cmd"):
        value = data.get(key)
        if key in data and (not isinstance(value, list) or not value
                            or not all(isinstance(part, str) for part in value)):
            out.append(f"`{key}` must be a non-empty list of strings (argv, never a shell string)")

    verdict = data.get("verdict_path")
    if "verdict_path" in data and (not isinstance(verdict, str) or not verdict.strip()):
        out.append("`verdict_path` must be a non-empty string")

    for key, vocabulary in (("trust_level", TRUST_LEVELS), ("cost_class", COST_CLASSES)):
        if key in data and data[key] not in vocabulary:
            out.append(f"`{key}`={data[key]!r} is outside the closed vocabulary {vocabulary}")

    # `side_effects` is a LIST of members, not one member (seed/delegation.py:44,50,144-150 and
    # §13:377). A slot can both write files and spawn processes; a scalar cannot say so, and
    # accepting a bare string here would quietly read "network" as the whole blast surface.
    effects = data.get("side_effects")
    if "side_effects" in data:
        if not isinstance(effects, list) or not all(isinstance(e, str) for e in effects):
            out.append("`side_effects` must be a LIST of strings — a slot's blast surface is a set, "
                       "and a bare string would read as the whole of it")
        else:
            for effect in effects:
                if effect not in SIDE_EFFECTS:
                    out.append(f"`side_effects` member {effect!r} is outside the closed vocabulary "
                               f"{SIDE_EFFECTS}")

    wall = data.get("max_wall_s")
    if "max_wall_s" in data:
        # `bool` is an `int` in Python, and `True` seconds is not a duration. This is the kind of
        # coercion a permissive parser would wave through.
        if isinstance(wall, bool) or not isinstance(wall, int) or not 0 < wall <= WALL_MAX_S:
            out.append(f"`max_wall_s` must be an int in (0, {WALL_MAX_S}]; a slot needing longer "
                       f"must be SPLIT")

    baseline = data.get("baseline_dirty", [])
    if not isinstance(baseline, list) or not all(isinstance(p, str) for p in baseline):
        out.append("`baseline_dirty` must be a list of root-relative paths")

    return out


def load(root: Path) -> tuple[Slot | None, list[str]]:
    """Read the live manifest. Returns (slot, problems) — never raises, never guesses.

    A missing manifest is NOT a problem: `blast_radius` is inert without one, which is the property
    that makes the hook safe to install everywhere. A manifest that exists and is broken IS a
    problem, and a fatal one — that asymmetry is the whole fail-closed posture.
    """
    path = Path(root) / MANIFEST_PATH
    if not path.exists():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{MANIFEST_PATH} exists but does not parse: {exc}"]

    found = problems(data)
    if found:
        return None, found
    return Slot(
        slot_id=data["slot_id"],
        allow_globs=tuple(data["allow_globs"]),
        verdict_path=data["verdict_path"],
        iteration_gate_cmd=tuple(data["iteration_gate_cmd"]),
        acceptance_gate_cmd=tuple(data["acceptance_gate_cmd"]),
        trust_level=data.get("trust_level", "bounded"),
        cost_class=data.get("cost_class", "standard"),
        side_effects=tuple(data.get("side_effects", ("files",))),
        max_wall_s=data.get("max_wall_s", 600),
        baseline_dirty=tuple(sorted(data.get("baseline_dirty", []))),
        raw=data,
    ), []


def write(root: Path, manifest: dict, baseline_dirty: list[str] | None = None) -> tuple[Path, list[str]]:
    """Write a manifest, refusing to write an invalid one.

    Validating BEFORE writing matters: a manifest on disk is what a spawned agent is bounded by, and
    an invalid one that reached disk would either deny everything (and look like a bug) or, worse,
    be repaired by a permissive reader into something nobody chose.
    """
    if baseline_dirty is not None:
        manifest = {**manifest, "baseline_dirty": sorted({str(p) for p in baseline_dirty})}
    found = problems(manifest)
    if found:
        return Path(root) / MANIFEST_PATH, found
    path = Path(root) / MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, []
