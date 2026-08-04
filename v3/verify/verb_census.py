#!/usr/bin/env python3
"""verb_census — who still calls a human verb, is every disposition well-formed, and does v3's dispatch claim RESOLVE?

    python3 -m v3.verify.verb_census                              # the gate
    V3_VERB_CENSUS_SABOTAGE=1 python3 -m v3.verify.verb_census    # the red side; must ALSO exit 0

THE FAILURE THIS PREVENTS is `N-0088`, on record since V3-INC5 and named a P1 blocker by INC-11:
`v3.verify.kinds` fixes `_CLI = "v3.cli"` and hands out argv that names it, and the parity gate that
checks that argv (`kinds_parity`) compares STRINGS against the recorded fixture — it never asks
whether the module the string names actually EXISTS. A verb v3 claims to run is, today, exactly as
real as a verb it does not: both produce the same argv, both look ported, and only one of them can be
imported. That gap is this census's whole reason to exist, and it is also why the population here is
not a hand-typed table: a table someone forgot to grow is precisely the shape of bug `N-0088` names.

TWO THINGS ARE DERIVED, nothing typed by hand — a THIRD used to be (v2's own `build_parser()` verb
surface, read via `git show` at the oracle commit) and it is GONE (V3-EXTRACT-OBLIGATIONS phase 3):
that half compared a derived v2 vocabulary against this file's own dispositions, and it died with the
ancestor along with its Lock (a census that parsed zero v2 verbs was RED). What is left does not need
v2 to be askable at all:

  * WHO CALLS EACH ONE — the tracked working tree (`git ls-files`), bucketed by the CLASS of file
    that invokes it (the enforcement column, tooling, human docs, or the one committed check-argv
    fixture), so a verb's LIVE evidence is visibly `dead` rather than silently absent from the report.
  * WHAT v3 CLAIMS — `v3.cli`'s own declared verb -> dotted-target mapping, parsed the same
    ast-not-executed way. This lands BEFORE `v3/cli.py` exists (V3-INC11 P1 is what writes it), and an
    empty claimed set is the correct, honest state of that fact — not an error.

Alongside them, `HUMAN_VERB_DISPOSITION` below is an AUTHORED, closed record — not re-derived every
run — of the human verbs INC-12 P7 decided about; it no longer needs a freshly-parsed v2 surface to
justify its own existence, because deciding is a one-time act and its DECISIONS are what this file
still enforces the shape of.

THE TOOTH, in one sentence: **every target v3 claims to dispatch a verb to must actually resolve** —
importable via `importlib.util.find_spec`, and if the claim names an attribute, that attribute must
exist on the imported module. A verb that is declared but cannot dispatch is `N-0088` in one row, and
it turns the gate red — this is the check `kinds_parity` does not perform.

THE GREEN LAW: exit 0 iff (a) v3 claims at least one verb OR `HUMAN_VERB_DISPOSITION` decides at
least one — a census watching nothing is RED, never vacuously green (Lock #1, re-armed over the
SURVIVING population now that the oracle-derived one is gone); AND (b) every row of
`HUMAN_VERB_DISPOSITION` carries a well-formed decision; AND (c) every verb v3 CLAIMS resolves.
`decided`/`to_port` count the disposition table; `claimed`/`unresolved` count v3's own dispatch map.

THE RED SIDE plants three perturbations, each in the SUBJECT, never the platform. Witness 1
synthesizes an in-memory claimed verb pointing at a dotted target that cannot resolve, feeds it
through the exact same `check` function the green run uses (so the law under test is the real one,
not a stand-in), and asserts the result is rejected. Witness 2 (same switch) plants an in-memory FILE
instead of an in-memory claim: a synthetic column-path `.py` file whose only content is a docstring
naming a verb, and asserts `classify` refuses to call that a `column` invocation — proof that the
LIVE-tree classification machinery still tells a mention from a real invocation even though `check`
no longer calls it directly (that consumer was the oracle-derived population, and it is gone with it).
Witness 3 is LOCK #1 re-armed: zero v3 claims AND zero disposition rows must be RED. None of the three
shells out to anything but `git ls-files` (read-only, and only witness 2 touches the tree at all —
witnesses 1 and 3 are pure in-memory).

INVOCATION VS MENTION (this correction, N-0088-adjacent). `column`/`tooling` used to be ONE free-text
regex over each bucket's whole file contents, so `graph`/`outcome`/`checkpoint` were `column` purely
because `.claude/hooks/context_nudge.py` NAMES them inside a nudge STRING printed to a HUMAN, and
`station` the same way via `.claude/hooks/gate_guard.py`'s docstring and its own regex PATTERN — none
of the four is ever an argv a machine builds. Reading "the column breaks without this" off "somebody
wrote this word" is the defect this file exists to end, so the search had to stop matching prose.

An occurrence now counts as INVOCATION only with invocation SHAPE: in a `.py` file (`ast`, never
regex, never imported) the verb sits inside a list/tuple literal that ALSO holds a launcher constant
(`metafactory.cli`/`v3.cli`/`meta`/`./meta`) — e.g. `[sys.executable, "-m", "metafactory.cli",
"verify"]` — or inside a `subprocess.run/check_call/Popen(...)` call whose argv carries one; in a
`.sh`/`.yml`/`.yaml`/`.json` file the verb shares a non-comment LINE with a launcher — e.g.
`run: ./meta ci --rederive`; a `.md` file is NEVER an invocation. Everything else — docstring, comment,
prose f-string, a regex pattern's own source — is a MENTION, and a verb whose only evidence anywhere
is a mention falls through to `human` ("a person types it", not "a machine runs it"). `classify`
records the mention rather than discarding it; `check`'s `mention_only` count is how many verbs used
to inflate `column`/`tooling` this way — the size of the illusion this correction removes.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

from ..kernel.report import Verdict

_V3 = Path(__file__).resolve().parent.parent
_ROOT = _V3.parent
_LINE_FIXTURE = "docs/spec/fixtures/check-argv-vectors.json"

_FACTORY_TOOLS_RE = re.compile(r"^factories/[^/]+/tools/")
_FACTORY_DOCS_RE = re.compile(r"^factories/[^/]+/docs/")
_PRODUCT_DOCS_RE = re.compile(r"^products/[^/]+/docs/")
_BUCKETS = ("line", "column", "tooling", "human")

_SABOTAGE_VERB = "__sabotage_verb__"
_SABOTAGE_TARGET = "v3.cli:verb_that_does_not_exist"
_SABOTAGE_MENTION_VERB = "__sabotage_mention_verb__"
_SABOTAGE_MENTION_PATH = ".claude/hooks/__sabotage_mention__.py"

#: How a launcher names "run the CLI" at all; present is necessary but never sufficient on its own.
#: Compiled (never a bare string constant): a launcher token appears verbatim in files OUTSIDE v3, and
#: a literal `"metafactory.cli"` constant here would itself be a rule-3 boundary violation — this is
#: the SAME escaped-dot-regex device `_list_pattern` already used, applied to exact-match too.
_LAUNCHER_RES = tuple(re.compile(p + r"\Z") for p in (r"metafactory\.cli", r"v3\.cli", r"meta", r"\./meta"))
#: File kinds with LINE-based invocation evidence; anything else (incl. `.md`) is a mention only.
_LINE_EXTS = (".sh", ".yml", ".yaml", ".json")
_SUBPROCESS_CALL_ATTRS = ("run", "check_call", "Popen")
_LAUNCHER_LINE_RE = re.compile(r"(?<![\w-])(?:\./)?meta(?![\w-])|metafactory\.cli|v3\.cli")


def _is_launcher(token: str) -> bool:
    return any(p.match(token) for p in _LAUNCHER_RES)


# ── each verb's live callers, bucketed by the searched tree ────────────────────────────────────────
# (what used to be section "(1)" — deriving v2's verb surface from `build_parser()` at the oracle
# commit — retired with V3-EXTRACT-OBLIGATIONS phase 3: `_const_str`/`_assign_target`/`_walk`/
# `v2_verbs` are gone, along with the population-diff they fed. `classify` below is unchanged and
# stays exercised — proven by the red side's witness 2 — because it never depended on the oracle in
# the first place: its evidence was always the tracked working tree.
def _bucket(relpath: str) -> str | None:
    if (relpath.startswith(".claude/hooks/") or relpath == ".claude/settings.json"
            or relpath.startswith(".github/workflows/") or relpath.startswith("seed/")):
        return "column"
    if (relpath.startswith("tools/") or relpath.startswith(".claude/skills/")
            or relpath.startswith(".claude/agents/") or relpath.startswith("template/")
            or _FACTORY_TOOLS_RE.match(relpath)):
        return "tooling"
    if (relpath.startswith("docs/") or _FACTORY_DOCS_RE.match(relpath) or _PRODUCT_DOCS_RE.match(relpath)):
        return "human"
    return None


def _git_ls_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        raise FileNotFoundError(f"git ls-files: {out.stderr.strip()}")
    return [line for line in out.stdout.splitlines() if line]


def _str_consts(node: ast.AST) -> list[str]:
    """Every string constant reachable under `node`, in walk order."""
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _py_invocation_sequences(source: str, filename: str) -> list[list[str]]:
    """Ordered string-constant sequences out of THIS `.py` file's list/tuple literals and
    `subprocess.run`/`check_call`/`Popen` calls that ALSO carry a launcher constant — rule (a) and (b)
    of the invocation law. `ast`-only, never regex, never imported; a syntax error yields no evidence
    (a scanned file need not even be valid for THIS interpreter) rather than raising."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    sequences: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            consts = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
              and node.func.attr in _SUBPROCESS_CALL_ATTRS):
            consts = [c for a in (*node.args, *(kw.value for kw in node.keywords)) for c in _str_consts(a)]
        else:
            continue
        if any(_is_launcher(c) for c in consts):
            sequences.append(consts)
    return sequences


def _qualifying_lines(text: str) -> list[str]:
    """Non-comment lines (leading `#` after optional whitespace = comment, all four kinds) that ALSO
    carry a launcher token — the `.sh`/`.yml`/`.yaml`/`.json` invocation rule."""
    return [line for line in text.splitlines()
            if not line.strip().startswith("#") and _LAUNCHER_LINE_RE.search(line)]


def _bucket_evidence(root: Path, extra_files: list[tuple[str, str]] | None = None) -> dict:
    """Everything `classify` needs, gathered ONCE per run (LIVE-CALLER question, not the oracle one —
    ADR-031 §2.1 governs part (1), not this): `mentions` — the OLD free-text blob per bucket, evidence
    a HUMAN could read the name, never proof a machine runs it; `py_sequences`/`qualifying_lines` —
    column/tooling ONLY, the actual invocation evidence (`.py` via ast, `.sh`/`.yml`/`.yaml`/`.json` via
    line). `.md` and any other extension feed `mentions` only. `extra_files` (relpath, text) fold in
    exactly like a tracked file, bucketed by the same `_bucket()` — the sabotage's second witness plants
    one this way to prove a mention in a column-class path still refuses to count as an invocation."""
    mention_blobs: dict[str, list[str]] = {"column": [], "tooling": [], "human": []}
    py_sequences: dict[str, list[list[str]]] = {"column": [], "tooling": []}
    qualifying_lines: dict[str, list[str]] = {"column": [], "tooling": []}

    def _absorb(rel: str, text: str) -> None:
        bucket = _bucket(rel)
        if bucket is None:
            return
        mention_blobs[bucket].append(text)
        if bucket not in ("column", "tooling"):
            return
        suffix = Path(rel).suffix.lower()
        if suffix == ".py":
            py_sequences[bucket].extend(_py_invocation_sequences(text, rel))
        elif suffix in _LINE_EXTS:
            qualifying_lines[bucket].extend(_qualifying_lines(text))

    for rel in _git_ls_files(root):
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        _absorb(rel, text)
    for rel, text in (extra_files or []):
        _absorb(rel, text)

    fixture = root / _LINE_FIXTURE
    line_text = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    return {
        "mentions": {"line": line_text, **{k: "\n".join(v) for k, v in mention_blobs.items()}},
        "py_sequences": py_sequences,
        "qualifying_lines": qualifying_lines,
    }


def _tok(token: str) -> str:
    """A token match with hyphen-aware boundaries: `\\b` alone treats `-` as a boundary, so a bare
    search for verb `product` would false-hit inside `product-run`."""
    return r"(?<![\w-])" + re.escape(token) + r"(?![\w-])"


def _verb_seq(parent: str | None, name: str) -> str:
    """The bare token-adjacency pattern (no launcher prefix): `parent\\s+name`, or just `name` for a
    top-level verb. Shared by the free-text mention patterns and the line-based invocation check."""
    tokens = [parent, name] if parent else [name]
    return r"\s+".join(_tok(t) for t in tokens)


def _seq_invoked(sequences: list[list[str]], parent: str | None, name: str) -> bool:
    """True iff `[parent, name]` (or `[name]`) appears as a CONTIGUOUS run inside any evidence
    sequence gathered by `_py_invocation_sequences` — each sequence already carries proof a launcher
    was present somewhere in it, so contiguity of the verb tokens is the only thing left to check."""
    tokens = [parent, name] if parent else [name]
    n = len(tokens)
    return any(seq[i:i + n] == tokens for seq in sequences for i in range(len(seq) - n + 1))


def _list_pattern(tokens: list[str]) -> re.Pattern:
    """A quoted argv-list occurrence: `["metafactory.cli", "increment", "open", ...]`, JSON or
    Python source, single- or double-quoted, across a comma+whitespace/newline separator."""
    q = "['\"]"
    quoted = r"\s*,\s*".join(q + _tok(t) + q for t in tokens)
    return re.compile(q + r"metafactory\.cli" + q + r"\s*,\s*" + quoted)


def _verb_patterns(parent: str | None, name: str) -> tuple[re.Pattern, ...]:
    tokens = [parent, name] if parent else [name]
    seq = _verb_seq(parent, name)
    meta_pat = re.compile(r"(?:^|[\s;&|`\"'(])(?:\./)?meta\s+" + seq)
    mod_pat = re.compile(r"metafactory\.cli\s+" + seq)
    return (meta_pat, mod_pat, _list_pattern(tokens))


def classify(verbs: list[tuple[str, str | None]], *,
            extra_files: list[tuple[str, str]] | None = None) -> dict[str, dict]:
    """full_verb -> {'membership': {bucket: bool, ...}, 'strongest': bucket, 'mentions': {bucket: bool}}.

    `line` keeps the strict quoted argv-list form (already invocation-shaped — the fixture also carries
    rendered TEMPLATE prose that can mention `meta station m04` as an EXAMPLE, never an argv). `column`
    and `tooling` now require a genuine INVOCATION; a verb whose only evidence anywhere is a mention
    falls through to `human`. `extra_files` lets the sabotage plant a synthetic file with no disk write;
    production callers never pass it."""
    ev = _bucket_evidence(_ROOT, extra_files)
    mentions_blob = ev["mentions"]
    result: dict[str, dict] = {}
    for full, parent in verbs:
        name = full.rsplit("/", 1)[-1]
        tokens = [parent, name] if parent else [name]
        list_pat = _list_pattern(tokens)
        seq_re = re.compile(_verb_seq(parent, name))
        text_patterns = _verb_patterns(parent, name)

        invoked_column = (_seq_invoked(ev["py_sequences"]["column"], parent, name)
                          or any(seq_re.search(l) for l in ev["qualifying_lines"]["column"]))
        invoked_tooling = (_seq_invoked(ev["py_sequences"]["tooling"], parent, name)
                           or any(seq_re.search(l) for l in ev["qualifying_lines"]["tooling"]))
        mentions = {b: any(p.search(mentions_blob[b]) for p in text_patterns)
                    for b in ("column", "tooling", "human")}

        membership = {
            "line": bool(list_pat.search(mentions_blob["line"])),
            "column": invoked_column,
            "tooling": invoked_tooling,
            "human": mentions["human"] or (mentions["column"] and not invoked_column)
                     or (mentions["tooling"] and not invoked_tooling),
        }
        strongest = next((b for b in _BUCKETS if membership[b]), "dead")
        result[full] = {"membership": membership, "strongest": strongest, "mentions": mentions}
    return result


# ── (3) what v3 claims, and (4) the importability law ───────────────────────────────────────────────
def v3_claims() -> dict[str, str]:
    """verb -> dotted target, parsed out of `v3.cli`'s own source (never executed). Absent module ⇒
    the empty claim set — legitimate, since this slot lands before `v3/cli.py` exists."""
    try:
        spec = importlib.util.find_spec("v3.cli")
    except (ImportError, ValueError, ModuleNotFoundError):
        return {}
    if spec is None or not spec.origin:
        return {}
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"), filename=spec.origin)
    claims: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for key, value in zip(node.value.keys, node.value.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    claims[key.value] = value.value
    return claims


def resolve(target: str) -> tuple[bool, str]:
    """The importability LAW (closes `N-0088`): `module[:attr]` must import, and if an attribute is
    named, it must exist on the imported module. Never executes the target, only resolves it."""
    module_part, _, attr_part = target.partition(":")
    if not module_part:
        return False, f"empty module in target {target!r}"
    try:
        spec = importlib.util.find_spec(module_part)
    except (ImportError, ValueError, ModuleNotFoundError, AttributeError, TypeError):
        spec = None
    if spec is None:
        return False, f"module {module_part!r} does not resolve"
    if attr_part:
        try:
            module = importlib.import_module(module_part)
        except Exception as exc:  # a module that resolves but explodes on import is still a lie
            return False, f"module {module_part!r} found but failed to import: {exc!r}"
        if not hasattr(module, attr_part):
            return False, f"module {module_part!r} has no attribute {attr_part!r}"
    return True, ""


# ── the law, shared by the green run and the sabotage ────────────────────────────────────────────
# ── the human verbs, decided (V3-INC12 P7) ─────────────────────────────────────────────────────────
#: INC-11 declared 20 unported verbs a LOSS with the argument "no machine depends on them". True, and
#: exactly the point: the HUMAN is who INC-12 is about. So the census stops counting them and starts
#: DECIDING them. `unported` is not a defect; **UNDECIDED is**, and that is what this table makes red.
#:
#: A decision is `("port"|"drop", reason)`. `drop` must name the REPLACEMENT — where the capability
#: went, or why the operator no longer needs it — because a drop with no replacement is a capability
#: leaving through a hole nobody wrote down (the `gate_wrap` lesson: it was dropped honestly, its
#: absence WAS recorded, and that record is how INC-12 found the run-log hole in P1).
HUMAN_VERB_DISPOSITION: dict[str, tuple[str, str]] = {
    # --- navigation: the operator's "go and look" surface. The strongest port candidates, and the
    # reason they are not ported HERE is scope, not doubt: four verbs over `v3.graph` is its own
    # bounded increment, and INC-12 is already XL.
    "graph":         ("port", "the no-LLM navigation surface CLAUDE.md itself routes to; deferred to "
                              "its own increment with `v3/graph/` already ported and unwired"),
    "graph/build":   ("port", "same arc as `graph`"),
    "graph/query":   ("port", "same arc as `graph`"),
    "graph/repomap": ("port", "same arc as `graph`"),
    # --- economy: an attached operator asking "what did this cost" is a legitimate escape-hatch
    # question, and the typed data exists (INC-6). Same deferral, same reason.
    "outcome":       ("port", "per-increment ΔRTM + cost; `v3/economy/outcome.py` is ported and "
                              "unwired — the verb is the missing half"),
    "billing":       ("port", "the ledger console over `v3/economy/ledger.py`, likewise unwired"),
    "metrics":       ("port", "the observability read over `v3/economy/`; likewise unwired"),
    # --- superseded by a GATE. The capability did not leave: it stopped being something a human
    # asks for and became something the suite decides every run, which is strictly stronger.
    "benchmark":     ("drop", "replaced by the `benchmark` GATE in `meta check` — helpdesk MEETS / "
                              "snipeit EXCEEDS is re-derived, not asked for"),
    "dial":          ("drop", "replaced by the `dial` GATE in `meta check`"),
    # --- the WorkOrder console. Its NAME was the third collision INC-12 found (P4): v2's `meta plan`
    # is `.gen/plan.json`, not the node tree. Kept unported so the name stays honest and free.
    "plan":          ("drop", "the `.gen/plan.json` WorkOrder console; its validator runs as the "
                              "`plan` gate, and the project's node tree got its own verb "
                              "(`meta plan-tree`) rather than squatting this name"),
    "plan/check":    ("drop", "same; the gate re-runs exactly this validator"),
    "plan/next":     ("drop", "same; `v3.plan.next_slot` exists and no line calls it"),
    "plan/status":   ("drop", "same"),
    # --- docs navigation: the operator has a better tool, and one of these is already gone.
    "doc":           ("drop", "grep over `docs/` is the retrieval CLAUDE.md actually prescribes; the "
                              "corpus itself is guarded by the `docs`/`projection` gates"),
    "doc/orphans":   ("drop", "same; orphan detection lives in `v3/graph/doc_graph.py`"),
    "doc/slice":     ("drop", "its module was DELETED at INC-11 with this named as the reason "
                              "(`deletion_manifest`: 'backs `meta doc slice`, an unported human verb')"),
    # --- each already answered elsewhere, and the answer is not "we forgot".
    "jdk-run":       ("drop", "the JDK resolution that load-bears is `tools/toolchain.sh`, which is "
                              "NOT the substrate and survives on purpose (node N-0121)"),
    "new":           ("drop", "scaffolding a new factory needs the META line, which does not run on "
                              "v3 (node N-0098) — a verb here would refuse, and the node is the "
                              "honest place for that"),
    "recall":        ("drop", "a tombstone before the rebuild began; `§11.4` lists it as dropped"),
    "rehydrate":     ("drop", "the payload is INJECTED, not asked for: the `SessionStart` hook prints "
                              "it and, since INC-12 P3, the host injects a per-leaf one "
                              "(`v3.memory.rehydrate.leaf_context`). A human verb to print it by hand "
                              "would be a third caller of a thing that already has two"),
}

_DECISIONS = ("port", "drop")


def check(*, extra_claims: dict[str, str] | None = None, sabotage: str = "") -> tuple[list[str], dict]:
    """The two live laws: every v3 dispatch claim resolves, and every row of the AUTHORED
    `HUMAN_VERB_DISPOSITION` table is well-formed. `sabotage="empty_population"` empties BOTH v3's
    claims and the disposition table for LOCK #1's red-side witness — the population `check` still
    watches once the oracle-derived one (v2's own verb surface) is gone."""
    problems: list[str] = []
    if sabotage == "empty_population":
        claims: dict[str, str] = {}
        disposition_table: dict[str, tuple[str, str]] = {}
    else:
        claims = dict(v3_claims())
        if extra_claims:
            claims.update(extra_claims)
        disposition_table = HUMAN_VERB_DISPOSITION

    if not claims and not disposition_table:
        problems.append("v3 claims ZERO verbs and HUMAN_VERB_DISPOSITION decides ZERO more: the "
                        "census watches nothing — never vacuously true (Lock #1)")

    unresolved = 0
    for verb, target in sorted(claims.items()):
        ok, why = resolve(target)
        if not ok:
            unresolved += 1
            problems.append(f"v3 claims to dispatch {verb!r} -> {target!r}, which does not resolve: {why}")

    # THE TOOTH (V3-INC12 P7): every row of the closed, authored decision table must name a decision
    # from the closed set, and a `drop` must name where the capability went — a drop with no
    # replacement is a capability leaving through a hole nobody wrote down.
    for verb, row in sorted(disposition_table.items()):
        decision = row[0] if isinstance(row, tuple) and row else None
        if decision not in _DECISIONS:
            problems.append(f"{verb!r}: decision {decision!r} is outside the closed set {_DECISIONS}")
        elif decision == "drop" and not (len(row) > 1 and str(row[1]).strip()):
            problems.append(f"{verb!r}: dropped with no replacement named — a drop with no "
                            f"replacement is a capability leaving through a hole nobody wrote down")
    # A row for a verb v3 DOES claim is stale bookkeeping, and stale bookkeeping is how a table
    # stops being read. Caught here rather than discovered by someone trusting it.
    for verb in sorted(disposition_table):
        if verb in claims:
            problems.append(f"{verb!r} carries a disposition row but v3 now claims to dispatch it — "
                            f"the row is stale and must be removed")

    counts = {"claimed": len(claims), "unresolved": unresolved, "decided": len(disposition_table),
              "to_port": sum(1 for r in disposition_table.values() if r[0] == "port")}
    return problems, counts


def _run_sabotage() -> int:
    control, _ = check()
    if control:
        return Verdict("v3-verb-census (SABOTAGE)", 1,
                       f"the census is not clean, so no catch is attributable: {control[0]}").emit()

    caught: list[str] = []
    missed: list[str] = []

    # witness 1: a v3 claim pointing at a target that cannot resolve (N-0088's own shape).
    problems, _ = check(extra_claims={_SABOTAGE_VERB: _SABOTAGE_TARGET})
    ok = any(_SABOTAGE_VERB in p and "does not resolve" in p for p in problems)
    (caught if ok else missed).append("unresolvable_dispatch_claim")

    # witness 2: a verb named ONLY inside a docstring of a synthetic column-path `.py` file must stay a
    # mention, never a `column` invocation. Non-vacuous on purpose: also demands the free-text search
    # DID see the mention, so a broken `_verb_patterns` cannot pass this by accident.
    synthetic_text = (f'"""prose only: someone might type `meta {_SABOTAGE_MENTION_VERB}` someday, '
                      f'but nothing here runs it."""\n')
    classes = classify([(_SABOTAGE_MENTION_VERB, None)],
                       extra_files=[(_SABOTAGE_MENTION_PATH, synthetic_text)])
    info = classes[_SABOTAGE_MENTION_VERB]
    ok = bool(info["mentions"]["column"] and not info["membership"]["column"])
    (caught if ok else missed).append("mention_stays_mention")

    # witness 3: LOCK #1, re-armed over the population `check` still watches now that v2's own verb
    # surface is gone — v3 claiming zero verbs AND the disposition table deciding zero must be RED,
    # never vacuously green (perturbs BOTH from genuinely non-empty, per INC-5).
    problems, _ = check(sabotage="empty_population")
    ok = any("Lock #1" in p for p in problems)
    (caught if ok else missed).append("empty_disposition_lock")

    print(f"PLANTS caught={caught} na=[] missed={missed}")
    if missed:
        return Verdict("v3-verb-census (SABOTAGE)", 1,
                       f"GATE DECORATIVO: {len(caught)}/3 caught ({', '.join(caught) or 'none'}) — "
                       f"missed {missed}").emit()
    return Verdict("v3-verb-census (SABOTAGE)", 0,
                   f"{len(caught)}/3 planted perturbations caught ({', '.join(caught)})").emit()


def main(argv: list[str]) -> int:
    if argv:
        return Verdict("v3-verb-census", 2, f"takes no arguments; got {argv!r}").emit()

    if os.environ.get("V3_VERB_CENSUS_SABOTAGE") == "1":
        return _run_sabotage()

    problems, counts = check()
    if problems:
        return Verdict("v3-verb-census", 1,
                       f"{len(problems)} problem(s): a malformed/undecided disposition row, or a v3 "
                       f"claim that does not resolve", counts=counts, failures=tuple(problems),
                       next_action="an unresolved v3 claim is N-0088; a malformed row is a decision "
                                   "outside the closed set or a drop with no replacement named"
                       ).emit()
    return Verdict("v3-verb-census", 0,
                   f"{counts['claimed']} verb(s) claimed by v3, {counts['unresolved']} unresolved; "
                   f"{counts['decided']} human verb(s) decided ({counts['to_port']} to port)",
                   counts=counts).emit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
