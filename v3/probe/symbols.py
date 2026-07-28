#!/usr/bin/env python3
"""Resolve §10's claims against the SDK that is actually installed, and pin the answers as DATA.

§10 was written by reading a wheel that is no longer on disk. Every architectural decision in it
rests on a symbol existing with a particular shape, so this is the tooth §11 asks for: *the test
fails loudly if any quoted SDK symbol moves*.

    python3 v3/probe/symbols.py                              # the gate; rewrites v3/sdk_facts.json
    V3_SDK_PROBE_SABOTAGE=1 python3 v3/probe/symbols.py      # the red side; must ALSO exit 0

DELIBERATELY NO TIMESTAMP in the artifact. `sdk_facts.json` is byte-stable for a given SDK, so `git
diff` after an upgrade shows exactly which claims changed and nothing else — the same reason
`proof_sha` excludes clocks. The file is a drift detector, not a log.

HONEST LIMIT. This is introspection: it proves a symbol EXISTS with a given shape, never that it
BEHAVES as §10 assumes. Whether a `deny` actually denies, whether a parent hook fires for a subagent,
what `max_budget_usd` does on exceed — none of that is decidable here. Those are the behavioural
questions (Q1-Q3, Q6, Q7) and they need a live run; this file records them as `unanswered` rather
than letting introspection imply an answer it cannot give.
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import json
import os
import subprocess
import sys
import typing
from pathlib import Path

from .claims import CLAIMS

# MODULE NOTE. The first draft of this file reached its sibling with a `sys.path.insert` and a
# comment explaining why that was acceptable. The boundary gate written an hour earlier refused it —
# correctly: it forbids path surgery categorically, because "just this once, into our own directory"
# is how a boundary erodes. v3 became a real package instead, which removes the insert rather than
# excusing it. Run with `python3 -m v3.probe.symbols`.

_ARTIFACT = Path(__file__).resolve().parent.parent / "sdk_facts.json"
_PKG = "claude_agent_sdk"

#: Sentinel a live probe writes when a question could not be exercised. Shared so the index and the
#: probe cannot drift into disagreeing about what counts as an answer.
_NOT_MEASURED = "NOT MEASURED"


def _resolve(name: str):
    """Find a symbol in the package namespace, then in its `types` module. Returns (obj, where)."""
    import claude_agent_sdk as sdk

    if hasattr(sdk, name):
        return getattr(sdk, name), _PKG
    try:
        types_mod = __import__(f"{_PKG}.types", fromlist=["types"])
    except Exception:
        return None, None
    if hasattr(types_mod, name):
        return getattr(types_mod, name), f"{_PKG}.types"
    return None, None


def _member_names(obj) -> set[str]:
    """Field names of a dataclass / TypedDict / plain class, whichever it turns out to be."""
    names: set[str] = set()
    if dataclasses.is_dataclass(obj):
        names |= {f.name for f in dataclasses.fields(obj)}
    for attr in ("__required_keys__", "__optional_keys__"):
        names |= set(getattr(obj, attr, ()) or ())
    names |= set(getattr(obj, "__annotations__", {}) or {})
    for base in getattr(obj, "__mro__", ())[1:]:
        names |= set(getattr(base, "__annotations__", {}) or {})
    try:
        names |= set(inspect.signature(obj).parameters) - {"self", "args", "kwargs"}
    except (TypeError, ValueError):
        pass
    return names


def _method_names(obj) -> set[str]:
    return {n for n, _ in inspect.getmembers(obj, callable) if not n.startswith("_")}


def _admitted_values(obj) -> set[str]:
    """Values of a Literal alias, an Enum, or a plain container of strings.

    A union of Literals (`Literal['a'] | Literal['b']`, which is how this SDK spells its event
    vocabularies) yields NESTED Literal types from `get_args`, not the strings. Flattening one level
    is the difference between reading the vocabulary and reporting the whole thing missing — the
    first run of this probe made exactly that mistake and blamed the SDK for it.
    """
    values: set[str] = set()
    for arg in typing.get_args(obj):
        nested = typing.get_args(arg)
        values |= {str(v) for v in nested} if nested else {str(arg)}
    if values:
        return values
    if isinstance(obj, type) and issubclass(obj, enum.Enum):
        return {m.name for m in obj} | {str(m.value) for m in obj}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return {str(v) for v in obj}
    return set()


def _check(claim: dict) -> dict:
    """Resolve ONE claim. Returns the claim enriched with observed/status — the DATA, not a verdict."""
    target, kind = claim["target"], claim["kind"]
    obj, where = _resolve(target)
    out = {**claim, "found_in": where}

    if obj is None:
        return {**out, "status": "MISSING", "detail": f"`{target}` is not exported by {_PKG} or {_PKG}.types"}
    if kind == "export":
        return {**out, "status": "ok"}

    expected = set(claim.get("expect", ()))
    if kind == "params":
        try:
            observed = set(inspect.signature(obj).parameters)
        except (TypeError, ValueError) as exc:
            return {**out, "status": "UNINSPECTABLE", "detail": str(exc)}
    elif kind == "fields":
        observed = _member_names(obj)
    elif kind == "methods":
        observed = _method_names(obj)
    elif kind == "values":
        observed = _admitted_values(obj)
    else:
        return {**out, "status": "BAD-CLAIM", "detail": f"unknown claim kind {kind!r}"}

    missing = sorted(expected - observed)
    if missing:
        return {**out, "status": "MOVED", "missing": missing,
                "detail": f"{target} no longer carries: {', '.join(missing)}"}
    return {**out, "status": "ok"}


def _environment() -> dict:
    """Facts about the box, as data. Cheap, and the first thing a cold reader needs."""
    try:
        import claude_agent_sdk as sdk
        sdk_version = getattr(sdk, "__version__", "unknown")
    except Exception as exc:  # pragma: no cover - the caller reports it
        sdk_version = f"IMPORT-FAILED: {exc}"
    try:
        cli = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30)
        cli_version = cli.stdout.strip() or cli.stderr.strip()
    except Exception as exc:
        cli_version = f"UNAVAILABLE: {exc}"
    return {
        "sdk_version": sdk_version,
        "cli_version": cli_version,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "credentials_file_present": (Path.home() / ".claude" / ".credentials.json").exists(),
        "anthropic_api_key_in_env": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


#: The behavioural questions introspection CANNOT answer, each bound to the artifact that answers it
#: and the key inside it. Recorded as a KEY that is present and empty rather than absent: a missing
#: key reads as an oversight, `unanswered` is a commitment (§10.11 + ADR-031 A2).
_BEHAVIOURAL = {
    "Q1": ("does a parent hook fire for SUBAGENT tool calls, with subagent context populated?",
           "subagent_facts.json", "Q1_parent_hook_fires_for_subagent_tool_calls"),
    "Q2": ("can_use_tool vs PreToolUse: which runs first, and does one deny short-circuit the other?",
           "behaviour_facts.json", "Q7_permission_was_invoked"),
    "Q3": ("SubagentStop semantics on a KILLED task — enough to retire the --live sweep?",
           "subagent_facts.json", "Q3_kill_semantics"),
    "Q6": ("max_budget_usd on exceed: error, stop, or truncation?",
           "behaviour_facts.json", "Q6_budget_terminal_reason"),
    "Q7": ("does a hook callback's DENY actually deny, from inside the session? (decides INC-2)",
           "behaviour_facts.json", "Q7_hook_deny_enforces"),
    "Q8b": ("does the PYTHON client inherit the CLI's stored credentials?",
            "behaviour_facts.json", "Q8b_python_client_inherits_credentials"),
}


def _behavioural_index() -> dict:
    """ONE index of the behavioural answers, resolved from the live artifacts beside this one.

    The close criterion of INC-0 asks for the answers in one place. They are PRODUCED by two live
    probes and would otherwise be scattered across three files, so this reads them back and reports
    per question: answered (with the value) or unanswered. Deterministic — it reads committed JSON,
    adds no clock, and keeps `sdk_facts.json` byte-stable.
    """
    cache: dict[str, dict] = {}
    out: dict[str, dict] = {}
    for qid, (question, artifact, key) in _BEHAVIOURAL.items():
        if artifact not in cache:
            path = _ARTIFACT.parent / artifact
            try:
                cache[artifact] = json.loads(path.read_text(encoding="utf-8")).get("answers", {})
            except (OSError, ValueError):
                cache[artifact] = {}
        answers = cache[artifact]
        record = {"question": question, "source": artifact}
        value = answers.get(key)
        # A PRESENT key whose value says "NOT MEASURED" is not an answer. The first version of this
        # index counted it as one, which would have let INC-0 close reporting 6/6 answered while one
        # of them was a sentence admitting the opposite — a vacuous green wearing a value.
        if key not in answers or value is None or (
            isinstance(value, str) and value.startswith(_NOT_MEASURED)
        ):
            record["answer"] = value
            record["status"] = "unanswered"
        else:
            record["answer"] = value
        out[qid] = record
    return out


def run(claims: tuple[dict, ...]) -> tuple[dict, list[dict]]:
    results = [_check(c) for c in claims]
    failures = [r for r in results if r["status"] != "ok"]
    facts = {
        "source": "docs/spec/10-target-sdk.md, resolved against the installed SDK",
        "environment": _environment(),
        "claims": results,
        "behavioural": _behavioural_index(),
    }
    return facts, failures


def main(argv: list[str]) -> int:
    if argv:
        print("VERDICT    v3-sdk-symbols — FAIL   (exit 2)")
        print(f"SUMMARY    takes no arguments; got {argv!r}")
        return 2

    if os.environ.get("V3_SDK_PROBE_SABOTAGE") == "1":
        planted = ({"id": "C-SABOTAGE", "ref": "<planted>", "kind": "export",
                    "target": "ClaudeAgentOptions_THAT_MOVED"},)
        _, failures = run(planted)
        if failures:
            print("VERDICT    v3-sdk-symbols (SABOTAGE) — PASS   (exit 0)")
            print(f"SUMMARY    the planted drift was detected: {failures[0]['status']}")
            return 0
        print("VERDICT    v3-sdk-symbols (SABOTAGE) — FAIL   (exit 1)")
        print("SUMMARY    GATE DECORATIVO: a symbol that does not exist resolved green")
        return 1

    if not CLAIMS:  # Lock #1 (I-1): an empty claim set is False, never vacuously true
        print("VERDICT    v3-sdk-symbols — FAIL   (exit 2)")
        print("SUMMARY    zero claims to resolve; a green would be vacuous")
        return 2

    facts, failures = run(CLAIMS)
    _ARTIFACT.write_text(json.dumps(facts, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    env = facts["environment"]
    if failures:
        print("VERDICT    v3-sdk-symbols — FAIL   (exit 1)")
        print(f"SUMMARY    {len(failures)}/{len(CLAIMS)} claim(s) of §10 no longer hold "
              f"(sdk {env['sdk_version']}, cli {env['cli_version']})")
        for f in failures[:6]:
            print(f"FAILURES   {f['id']} {f['ref']}: {f['detail']}")
        if len(failures) > 6:
            print(f"FAILURES   … and {len(failures) - 6} more")
        print(f"ARTIFACT   {_ARTIFACT.relative_to(Path.cwd()) if _ARTIFACT.is_relative_to(Path.cwd()) else _ARTIFACT}")
        return 1

    print("VERDICT    v3-sdk-symbols — PASS   (exit 0)")
    print(f"SUMMARY    {len(CLAIMS)}/{len(CLAIMS)} claims of §10 hold "
          f"(sdk {env['sdk_version']}, cli {env['cli_version']}); "
          f"{sum(1 for r in facts['behavioural'].values() if r.get('status') == 'unanswered')}"
          f"/{len(_BEHAVIOURAL)} behavioural question(s) still unanswered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
