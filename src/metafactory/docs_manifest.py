"""docs_manifest — ADR-009: content-addressed docs via an in-band seal + generated INDEX.

Separates "did it change?" (compare a hash, cheap) from "what does it say?" (load the
doc, costly). Reuses git's blob-hash algorithm (content-addressed Merkle tree) rather
than inventing hashing. The seal is the FIRST line of each `.md`, so a `Read` already
carries the doc's identity into context — no extra tool call. The sha is over the body
EXCLUDING the seal line, so re-stamping is idempotent (no chicken-and-egg churn).

Stamped by a PostToolUse hook (cheap, frequent, zero model); `meta check` verifies it.
Boundary: the seal TRIAGES (what changed / what's stale) — it never replaces reading the
doc you are about to DECIDE on. A design error is expensive; reading is cheap.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SEAL_RE = re.compile(r"^<!-- meta:doc sha=([0-9a-f]{40}) updated=(\S+) -->\s*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def git_blob_sha(data: bytes) -> str:
    """The git blob object id of `data` — git's own content-address (sha1 over
    'blob <len>\\0<data>'). Identical to `git hash-object --stdin`."""
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def doc_set(home: Path, *, meta_extras: bool = True) -> list[Path]:
    """The sealed docs of ONE doc-home: everything under `<home>/docs/**.md`.
    For the meta home (`meta_extras=True`, the default) the two root entry docs
    (START-HERE.md, CLAUDE.md) are also sealed; a factory/product home seals only
    its authored `docs/` narrative — its `CLAUDE.md` is a generated/projected
    artifact (ADR-016 Fase 2), not authored, so it is NOT sealed in-tree.
    INDEX.md (generated) is excluded from the sealed set."""
    home = Path(home)
    docs = sorted((home / "docs").rglob("*.md"))
    if meta_extras:
        for name in ("START-HERE.md", "CLAUDE.md"):
            p = home / name
            if p.exists():
                docs.append(p)
    return [d for d in docs if d.name != "INDEX.md"]


def doc_homes(repo_root: Path) -> list[Path]:
    """Every doc-home, by level (ADR-016 Fase 2 §3): the meta (repo_root) + each
    factory + each product that owns a `docs/` dir. DATA-agnostic — splits the path,
    never hardcodes a factory/product slug. Order: meta, then per factory the factory
    then its products."""
    repo_root = Path(repo_root)
    homes = [repo_root]
    factories = repo_root / "factories"
    if factories.is_dir():
        for f in sorted(p for p in factories.iterdir() if p.is_dir()):
            if (f / "docs").is_dir():
                homes.append(f)
            prods = f / "products"
            if prods.is_dir():
                for p in sorted(q for q in prods.iterdir() if q.is_dir()):
                    if (p / "docs").is_dir():
                        homes.append(p)
    return homes


def split_seal(text: str) -> tuple[str | None, str]:
    head, _, rest = text.partition("\n")
    if SEAL_RE.match(head):
        return head, rest
    return None, text


# H-5 (COLUMN-MAINT, COUNCIL-360 §4.1): an author-left placeholder seal (`sha=PENDING`) does NOT match
# SEAL_RE, so `stamp` used to PREPEND the fresh seal above it — hashing a pseudo-seal with a FALSE date
# into the body forever (19 docs measured, incl. immutable decisions). Any full seal-shaped line (real
# or placeholder) LEADING the body is residue of that bug — never legitimate content (prose that quotes
# a seal indents or backticks it, and never at body start).
_RESIDUAL_SEAL_RE = re.compile(r"^<!-- meta:doc sha=\S+ updated=\S+ -->\s*$")


def strip_residual_seals(body: str) -> str:
    """Drop LEADING pseudo-seal lines from a doc body (H-5). Only the leading run is touched —
    mid-document prose is never rewritten."""
    lines = body.splitlines(keepends=True)
    i = 0
    while i < len(lines) and _RESIDUAL_SEAL_RE.match(lines[i].rstrip("\n")):
        i += 1
    return "".join(lines[i:]) if i else body


def _is_immutable(path: Path) -> bool:
    """decisions/ is the declared-immutable doc class: existing residuals there stay (de-churn beats
    purity — the explicit H-5 decision, COLUMN-MAINT); everything else self-heals on stamp."""
    return "decisions" in path.parts


def body_of(text: str) -> str:
    return split_seal(text)[1]


def title_of(text: str) -> str:
    for line in body_of(text).splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


def stamp(path: Path) -> bool:
    """Re-stamp a doc; return True if the seal changed (body edited), False if idempotent.
    H-5 hardening: leading pseudo-seals in the body are STRIPPED before hashing (self-healing),
    except under decisions/ (immutable class — existing residuals stay, de-churn by decision)."""
    text = path.read_text(encoding="utf-8")
    seal, body = split_seal(text)
    if not _is_immutable(path):
        body = strip_residual_seals(body)
    sha = git_blob_sha(body.encode("utf-8"))
    if seal:
        m = SEAL_RE.match(seal)
        if m and m.group(1) == sha:
            return False  # unchanged body -> keep `updated`, no churn
    path.write_text(f"<!-- meta:doc sha={sha} updated={utc_now()} -->\n{body}", encoding="utf-8")
    return True


def build_index(repo_root: Path) -> str:
    repo_root = Path(repo_root)
    rows = []
    for d in doc_set(repo_root):
        text = d.read_text(encoding="utf-8")
        seal, body = split_seal(text)
        sha = git_blob_sha(body.encode("utf-8"))
        updated = SEAL_RE.match(seal).group(2) if seal else "—"
        rows.append((str(d.relative_to(repo_root)), sha[:12], updated, title_of(text)))
    lines = [
        "<!-- generated by metafactory.docs_manifest — do not edit by hand (ADR-009) -->",
        "# INDEX — manifiesto content-addressed de docs (vista GENERADA, no a mano)",
        "",
        "> Regenerado por el hook `doc_stamp` (PostToolUse) y verificado por `meta check`.",
        "> El sha dice *si cambió*; para *qué dice*, abrí el doc. Triaje, no reemplazo de lectura.",
        "",
        "| Doc | sha (git blob, body) | updated | resumen |",
        "| --- | --- | --- | --- |",
    ]
    for rel, sha, updated, title in rows:
        lines.append(f"| `{rel}` | `{sha}` | {updated} | {title} |")
    return "\n".join(lines) + "\n"


def sync(repo_root: Path) -> list[str]:
    """Stamp every doc of EVERY level's home (meta + factories + products) and
    regenerate the meta INDEX.md. Returns the docs whose seal changed (repo-relative)."""
    repo_root = Path(repo_root)
    changed: list[str] = []
    for home in doc_homes(repo_root):
        for d in doc_set(home, meta_extras=(home == repo_root)):
            if stamp(d):
                changed.append(str(d.relative_to(repo_root)))
    (repo_root / "INDEX.md").write_text(build_index(repo_root), encoding="utf-8")
    return changed


def _state_fresh_problem(repo_root: Path, home: Path, *, meta_extras: bool) -> str | None:
    """Skip-safe freshness, PER HOME: this home's `docs/STATE.md` should not be older (by
    last commit) than the newest doc in this home's set. Per-home so editing a factory doc
    never forces re-touching the META STATE (ADR-016 Fase 2 — closes P4, no cross-coupling).
    Returns a problem string, or None if OK or git data unavailable."""
    def last_commit(p: Path) -> int:
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%ct", "--", str(p)],
                cwd=repo_root, capture_output=True, text=True,
            )
            return int(out.stdout.strip()) if out.stdout.strip() else 0
        except (OSError, ValueError):
            return 0

    state = home / "docs" / "STATE.md"
    if not state.exists():
        return None
    state_t = last_commit(state)
    if state_t == 0:
        return None  # not committed yet -> nothing to compare against
    newest = max((last_commit(d) for d in doc_set(home, meta_extras=meta_extras) if d != state), default=0)
    if newest > state_t:
        rel = state.relative_to(repo_root)
        return f"{rel} is older (by last commit) than a newer doc in its level — STATE may be stale"
    return None


def check(repo_root: Path) -> list[str]:
    """Return a list of consistency problems (empty == clean). All file-IO, zero model.
    The seal-integrity tooth (1) + freshness (4) run for EVERY level's doc-home (meta +
    factories + products, ADR-016 Fase 2 §3); the meta-navigation checks — INDEX coverage
    (2) and entry-doc links (3) — run for the meta home only (each factory navigates via
    its own STATE, not a generated INDEX)."""
    repo_root = Path(repo_root)
    problems: list[str] = []

    for home in doc_homes(repo_root):
        is_meta = home == repo_root
        docs = doc_set(home, meta_extras=is_meta)

        # (1) every doc carries a correct, current seal  [all levels]
        for d in docs:
            text = d.read_text(encoding="utf-8")
            seal, body = split_seal(text)
            rel = d.relative_to(repo_root)
            if seal is None:
                problems.append(f"{rel}:1: missing content-addressed seal (run the doc_stamp hook)")
                continue
            if SEAL_RE.match(seal).group(1) != git_blob_sha(body.encode("utf-8")):
                problems.append(f"{rel}:1: stale seal (sha != body) — doc edited without re-stamping")
            # H-5 tooth: a leading pseudo-seal in the body is pipeline residue (false date poisoning
            # INDEX triage). decisions/ exempt (immutable class, residuals grandfathered by decision).
            if not _is_immutable(d) and strip_residual_seals(body) != body:
                problems.append(f"{rel}:2: residual pseudo-seal in body (H-5) — re-run doc-sync to strip")

        # (2) INDEX.md exists and covers exactly the doc set  [meta only]
        if is_meta:
            index = repo_root / "INDEX.md"
            if not index.exists():
                problems.append("INDEX.md: missing (run docs_manifest sync)")
            else:
                listed = set(re.findall(r"\| `([^`]+\.md)` \|", index.read_text(encoding="utf-8")))
                actual = {str(d.relative_to(repo_root)) for d in docs}
                for missing in sorted(actual - listed):
                    problems.append(f"INDEX.md: does not list {missing} (drifted index)")
                for extra in sorted(listed - actual):
                    problems.append(f"INDEX.md: lists nonexistent {extra} (dangling)")

            # (3) no dangling relative .md links in the entry docs  [meta only]
            for name in ("START-HERE.md", "docs/STATE.md"):
                p = repo_root / name
                if not p.exists():
                    continue
                for target in re.findall(r"\]\(([^)]+\.md)[^)]*\)", p.read_text(encoding="utf-8")):
                    if target.startswith(("http://", "https://")):
                        continue
                    if not (p.parent / target.split("#")[0]).resolve().exists():
                        problems.append(f"{name}: dangling link -> {target}")

        # (4) freshness (skip-safe), per home
        fresh = _state_fresh_problem(repo_root, home, meta_extras=is_meta)
        if fresh:
            problems.append(fresh)

    return problems


def _main(argv: list[str]) -> int:
    from ._seed import repo_root as _rr
    root = _rr()
    cmd = argv[0] if argv else "check"
    if cmd == "sync":
        changed = sync(root)
        print(f"docs sync: {len(changed)} re-stamped" + (f" ({', '.join(changed)})" if changed else ""))
        return 0
    if cmd == "index":
        print(build_index(root))
        return 0
    if cmd == "check":
        problems = check(root)
        for p in problems:
            print(p)
        print(f"docs check: {len(problems)} problem(s)")
        return 0 if not problems else 1
    print("usage: docs_manifest [sync|index|check]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
