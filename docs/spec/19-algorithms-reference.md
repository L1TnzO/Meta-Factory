<!-- meta:doc sha=87f584c6f51479c37ece19c47de345e150dfa98a updated=2026-07-28T04:01Z -->
# 19 — Reference implementations: seal, slot law, sequence (NORMATIVE, EXECUTABLE)

> Like §14 and §15, the marked blocks here are extracted and executed by
> `tools/spec_conformance.py`. Three subsystems whose law is small enough to state exactly and whose
> mistakes are expensive: the **document seal** (how the corpus knows it has not rotted), the **slot
> law** (what a delegated model may change and when its work counts), and the **sequence** (how a
> line orders itself and how deferral stays safe).
>
> Each has a real oracle, not a synthetic one:
> · the seal is checked against **every sealed document in this repository**;
> · the slot law is checked **differentially against the live implementation** — two independent
>   implementations agreeing is what makes green meaningful (the same argument the research corpus
>   used for its claims);
> · the sequence is checked against the real station filenames of a factory line.

## 1. The document seal

The corpus is content-addressed: each authored document carries an in-band seal whose hash is git's
own blob id over the document **body** (the text after the seal line). Because the hash covers
content and not path, a byte-identical move churns nothing — which is what made migrating sixteen
documents between homes a no-op (§06.3).

<!-- spec-impl: docseal -->
```python
"""Document seal: git's blob address over the body. Stdlib only, no I/O.

Why git's algorithm and not a fresh one: the id is then reproducible with `git hash-object --stdin`
by anyone, with no tooling of ours, which is the point of a content address.
"""
import hashlib
import re

SEAL_RE = re.compile(r"^<!-- meta:doc sha=([0-9a-f]{40}) updated=(\S+) -->\s*$")
_RESIDUAL_SEAL_RE = re.compile(r"^<!-- meta:doc sha=\S+ updated=\S+ -->\s*$")


def git_blob_sha(data: bytes) -> str:
    """git's own content address: sha1 over b'blob <len>\\0' + data. Identical to
    `git hash-object --stdin`."""
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def split_seal(text: str) -> tuple[str | None, str]:
    """(seal_line | None, body). Only a FIRST line matching SEAL_RE counts as a seal."""
    head, _, rest = text.partition("\n")
    return (head, rest) if SEAL_RE.match(head) else (None, text)


def body_of(text: str) -> str:
    return split_seal(text)[1]


def seal_sha(text: str) -> str | None:
    """The sha the document CLAIMS, or None if it carries no seal."""
    seal, _ = split_seal(text)
    return SEAL_RE.match(seal).group(1) if seal else None


def seal_ok(text: str) -> bool:
    """Is the claimed sha the actual blob id of the body? This is the whole rot detector.

    Fail-closed: a document with no seal is NOT ok — silence is not freshness.
    """
    seal, body = split_seal(text)
    if seal is None:
        return False
    return SEAL_RE.match(seal).group(1) == git_blob_sha(body.encode("utf-8"))


def render_seal(body: str, updated: str) -> str:
    """Produce a sealed document. `updated` is provenance and is NOT part of the hash — the same body
    re-stamped at a different time keeps the same sha, so a touch is not a change."""
    return f"<!-- meta:doc sha={git_blob_sha(body.encode('utf-8'))} updated={updated} -->\n{body}"


def strip_residual_seals(body: str) -> str:
    """Drop LEADING seal-shaped lines from a body.

    History this encodes, because it will otherwise be re-introduced: a placeholder seal written by
    an author (`sha=PENDING`) does not match SEAL_RE, so stamping used to PREPEND a fresh seal ABOVE
    it — hashing a pseudo-seal with a false date into the body forever (19 documents were measured in
    that state). Any seal-shaped line LEADING a body is residue of that bug and never legitimate
    content: prose that quotes a seal indents or backticks it, and never at body start.

    Only the leading run is touched. Mid-document prose is never rewritten.
    """
    lines = body.splitlines(keepends=True)
    i = 0
    while i < len(lines) and _RESIDUAL_SEAL_RE.match(lines[i].rstrip("\n")):
        i += 1
    return "".join(lines[i:]) if i else body
```

**I/O specified in prose (not in the block, per §12 rule 2):** stamping walks each doc home's
`docs/**/*.md`, re-renders the seal, and regenerates `INDEX.md` as a table of
`path · sha · updated · title`. The `decisions/` class is declared immutable: existing residual
seals there are left alone (de-churn beats purity), everything else self-heals on stamp.

## 2. The slot law

What a delegated model may change, and when its output counts. Three layers cover one property —
*the agent changed only what it was allowed to change* — because each layer sees a different slice of
reality (§05.4).

<!-- spec-impl: slotlaw -->
```python
"""The slot law: pure predicates over a manifest. Stdlib only, no I/O, no git, no subprocess.

The transport (a PreToolUse hook, a SubagentStop hook, a `--live` sweep) is deliberately NOT here:
the law must be unit-testable and identical in all three, or the three layers could disagree.
"""
import fnmatch

MANIFEST_REQUIRED_KEYS = ("slot_id", "allow_globs", "verdict_path",
                          "iteration_gate_cmd", "acceptance_gate_cmd")
VERDICT_REQUIRED_KEYS = ("slot_id", "status", "check", "exit_code")
VERDICT_STATUSES = ("green", "red")


def write_allowed(slot: dict, rel: str | None) -> bool:
    """May the worker write `rel` (a root-relative POSIX path)? Fail-CLOSED.

    `rel is None` means the path escaped the repository — never allowed. The caller performs that
    resolution; keeping it outside makes this predicate total and testable.
    """
    if rel is None:
        return False
    if rel == ".gen" or rel.startswith(".gen/"):
        return True                      # the worker's own gitignored scratch + verdict area
    verdict = str(slot.get("verdict_path") or "")
    if verdict and rel == verdict:
        return True
    return any(fnmatch.fnmatch(rel, str(g)) for g in (slot.get("allow_globs") or []))


def footprint_problems(slot: dict, changed_paths: list) -> list[str]:
    """The tooth a Write-hook cannot be: a Bash-mediated write bypasses PreToolUse but still PERSISTS
    as a git-visible change, and is caught here.

    `changed_paths` are root-relative POSIX paths observed changed since the slot opened (the caller
    collects them from `git status --porcelain --untracked-files=all` — staged, unstaged, untracked,
    both rename sides). Returns [] iff every path is inside
    allow_globs ∪ {verdict_path} ∪ .gen/** ∪ baseline_dirty.

    `baseline_dirty` exists so a tree that was already dirty when the slot opened cannot false-red
    the slot — a false red is as corrosive as a false green, because it trains people to ignore it.
    """
    globs = [str(g) for g in (slot.get("allow_globs") or [])]
    verdict = str(slot.get("verdict_path") or "")
    baseline = {str(b) for b in (slot.get("baseline_dirty") or [])}
    problems = set()
    for raw in changed_paths:
        rel = str(raw).strip().replace("\\", "/")
        if not rel or rel in baseline:
            continue
        if rel == ".gen" or rel.startswith(".gen/"):
            continue
        if verdict and rel == verdict:
            continue
        if any(fnmatch.fnmatch(rel, g) for g in globs):
            continue
        problems.add(f"{rel}: changed outside the slot footprint "
                     f"(allow_globs ∪ verdict ∪ .gen/ ∪ baseline_dirty)")
    return sorted(problems)


def verdict_problems(slot: dict, verdict: dict | None, oversized: list | None = None) -> list[str]:
    """Is the worker's verdict well-formed, and does a GREEN one actually mean anything?

    The rule that carries the split gate: a green verdict on a slot that declared a heavy
    `acceptance_gate_cmd` is only real if that gate exited 0. The fast iteration gate passing on
    every retry is necessary and NOT sufficient — otherwise a worker could iterate to a local green
    that the real suite would reject.
    """
    if verdict is None:
        return [f"no verdict at {slot.get('verdict_path')!r} (write it before finishing)"]
    if not isinstance(verdict, dict):
        return ["the verdict must be a JSON object"]
    out = []
    missing = [k for k in VERDICT_REQUIRED_KEYS if k not in verdict]
    if missing:
        out.append(f"incomplete verdict: missing {missing}")
    if verdict.get("status") not in VERDICT_STATUSES:
        out.append(f"verdict.status invalid: {verdict.get('status')!r} "
                   f"(expected one of {VERDICT_STATUSES})")
    if verdict.get("status") == "green":
        if slot.get("acceptance_gate_cmd") and verdict.get("acceptance_exit_code") != 0:
            out.append("green verdict but the acceptance gate did not pass "
                       f"(acceptance_exit_code={verdict.get('acceptance_exit_code')!r})")
        if oversized:
            out.append("green verdict but a generated file exceeds `file_budget`: "
                       + "; ".join(str(o) for o in oversized))
    return out
```

## 3. The sequence

How a line orders itself, how a station's predecessors are resolved, and why deferring a station
never orphans the ones after it.

<!-- spec-impl: sequence -->
```python
"""Line ordering and predecessor resolution. Pure: the line is DATA, this is the law over it."""


def natural_key(name: str) -> tuple:
    """Numeric-aware ordering so that `s9` precedes `s10`.

    Plain lexicographic order puts `s10` before `s9`, which silently reorders a line the moment it
    grows past nine stations — a defect that only appears in the products you care about most.
    """
    out, num, saw = [], "", False
    for ch in str(name):
        if ch.isdigit():
            num += ch
            saw = True
        else:
            if saw:
                out.append((1, int(num)))
                num, saw = "", False
            out.append((0, ch))
    if saw:
        out.append((1, int(num)))
    return tuple(out)


def order_stations(names: list) -> list:
    """File order of a line: natural key, skipping `_`-prefixed files (partials, not stations)."""
    return sorted([n for n in names if not str(n).startswith("_")], key=natural_key)


def active_in(station: dict, dial: str = "harden") -> bool:
    """Is the station active under the draft→harden dial?

    `activation: off` is inactive always. A `tier: harden` station is deferred under `--mode draft`.
    The dial is excluded from the proof digest, so adopting it re-pins nothing (§07.3).
    """
    if str(station.get("activation", "always")) == "off":
        return False
    return not (str(dial) == "draft" and str(station.get("tier", "core")) == "harden")


def predecessors(line: list, station_id: str, dial: str = "harden") -> list:
    """Which stations must be GREEN before this one may run.

    Explicit `depends_on` is a fan-in: ALL of them. Otherwise the predecessor is the previous ACTIVE
    station in file order.

    The property that makes deferral safe: a deferred predecessor is TRANSPARENT — the gate falls
    through to *its* predecessors instead of treating the chain as satisfied. Skipping a station must
    never silently satisfy the ones that depended on it.
    """
    index = {str(s.get("id")): i for i, s in enumerate(line)}
    i = index.get(str(station_id))
    if i is None:
        return []
    node = line[i]
    if node.get("depends_on"):
        return [str(d) for d in node["depends_on"]]
    if node.get("requires_prev"):
        return [str(node["requires_prev"])]
    for j in range(i - 1, -1, -1):
        if active_in(line[j], dial):
            return [str(line[j].get("id"))]
    return []
```

## 4. What is NOT specified here, and why

| Not here | Where | Why |
| --- | --- | --- |
| collecting `git status` | the transport | subprocess output is I/O; the law stays pure so all three enforcement layers share one implementation |
| walking doc homes, writing `INDEX.md` | the transport | filesystem traversal, specified in prose above |
| running the stations | the runner (§03.4) | the kernel and the law never execute anything |
| **RTM derivation** | §03.6, prose only | **honest gap:** its pure core is thin — nearly all of its truth is I/O against `.proof/` and the filesystem — so an executable block would specify almost nothing and would give a false sense of coverage. Recorded as an open node rather than faked |
