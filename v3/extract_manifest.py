#!/usr/bin/env python3
"""extract_manifest — WHAT TRAVELS when this platform is extracted to another repo, as DATA.

    from v3.extract_manifest import PACKAGE, BORN_FRESH, classify

PASO 1 of `docs/work/V3-EXTRACT-DIRECTION-INCREMENT.md` (`N-0133`). Prose cannot be verified and
cannot be diffed; a copy list can. This module is the single source for the extraction, and
`v3.verify.checks.extract_package` is its tooth.

WHY A SECOND CATEGORY. A path a traveling module names is not automatically a path that must be
COPIED: some are this repo's own accumulated STATE (its plan tree, its proofs, its increment
work-docs), and the destination repo grows its own from turn one. Collapsing the two would either
force us to copy one repo's history into another, or leave "it isn't in the manifest" meaning both
"it is born fresh" and "we forgot it". So a reference resolves to exactly one of three: PACKAGE
(copied), BORN_FRESH (deliberately NOT copied, destination creates it), or a PACKING HOLE (red).

    THE MEASUREMENT THAT WROTE THIS FILE (2026-08-03, and it corrected the direction doc).
    The direction doc's §1 pinned a "minimal package" of eight entries, measured as "13 gates green ·
    0 red · 4 N/A in a foreign repo". That green was the recurring bug of this project wearing a new
    hat: it looked green because nobody asked what was left OUT of the count. Sweeping the string
    literals of all 151 traveling modules found 24 existing repo paths the eight entries did not
    cover, and among them were `.claude/` (the COLUMN — hooks, agents, skills, settings: without it
    there is no harness at all, so the extracted repo would have had zero delegation law), `stations/`
    (the m00..m08 meta line that BUILDS factories), `template/` (the factory template), `specs/`
    (the factory specs `generality` resolves) and `docs/reference/` (`primitives.yml`, which
    `v3/spec/primitives.py` loads at RUNTIME, plus `dep-allowlist.yml` and `parity.yml`). The other
    29 gates could not report the omission because they never registered: the suite REFUSED to
    register them (INC-4's law), and a gate that never ran cannot vote on what is missing.

Zero model; every row is re-derivable from the tree (I-3). Names no domain (ADR-012).
"""
from __future__ import annotations

#: (repo-relative path, WHY it travels). The reason is not decoration: `extract_package` rejects a
#: row without one, because a copy list nobody justified is how a package silently grows forever.
PACKAGE: tuple[tuple[str, str], ...] = (
    ("v3/", "the platform itself — CLI, kernel, host, verify, memory, spec, economy. Measured "
            "2026-08-03: 130/130 modules import in an empty repo, zero imports to v2."),
    ("seed/", "Stage-0 trust chain. The hooks load it BY PATH, not by import, so no import graph "
              "would ever have revealed this dependency — only the path sweep does."),
    (".claude/", "THE COLUMN: hooks, agents, skills, settings.json. Without it the harness has no "
                 "teeth — blast-radius, verdict-required and the slot law all live here. Omitted "
                 "from the direction doc's measured package; see this module's docstring."),
    ("tools/", "`spec_conformance.py` extracts the executable blocks out of docs/spec/; "
               "`toolchain.sh` finds/installs the JDK the product lines need."),
    ("docs/spec/", "NOT documentation — CODE. The plan algebra EXECUTES out of "
                   "`15-plan-and-memory.md §5` and the kernel out of `§14`. Dropping it breaks "
                   "`plan_tree` and `leaf_context`."),
    ("docs/reference/", "runtime DATA, not prose: `primitives.yml` is loaded by `v3/spec/"
                        "primitives.py` at runtime, `dep-allowlist.yml` by `security`, "
                        "`parity.yml` by `generality`."),
    ("stations/", "the m00..m08 META LINE — the stations that BUILD a factory. Extracting the "
                  "platform without them yields something that can verify but cannot construct."),
    ("template/", "the factory template a new factory is materialized from."),
    ("specs/", "`specs/<slug>.factory.spec.yml` — the factory specs `generality` resolves "
               "alongside `factories/<slug>/factory.spec.yml`."),
    ("factories/", "the products. Also the SUBJECT of `codegen_freeze`, which is why that gate is "
                   "`keep` and not `retire` in PASO 3's census."),
    ("tests/fixtures/", "the red-side fixtures of the class-B gates. They travel WITH their gate or "
                        "the suite refuses to register it (PASO 2)."),
    ("benchmarks/", "`sweet-spot-crud.yml` — the pinned data witness of the `benchmark` gate."),
    ("meta", "the one-line transport the external CI and the hooks invoke (ADR-005 §4)."),
    (".github/workflows/", "THE SECOND VERIFIER (ADR-005). Also absent from the direction doc's "
                           "measured package: extracting without it leaves a repo whose only "
                           "verifier is the machine that wrote the code, and nothing would have "
                           "reported the loss — the two-verifier law would simply stop existing."),
    ("CLAUDE.md", "the routing law. `doc_stamp`, `docs_manifest`, `meter`, `doc_graph` and the "
                  "column-law parity all resolve it by name; the destination EDITS it in place "
                  "rather than inventing one."),
    (".gitignore", "what keeps `.proof/`, `.gen/` and every build tree OUT of git. Found by "
                   "EXECUTING this manifest (V3-EXTRACT-CUTOVER), not by reading it: no module "
                   "names it, so the sufficiency law — which derives from code literals — could "
                   "never have seen it. Without it the destination COMMITS its own evidence, and a "
                   "green nobody re-earned is exactly what `BORN_FRESH`'s `.proof/` row forbids."),
)

#: (repo-relative path, WHY the destination grows its own instead of inheriting ours). A row here is
#: a DECISION not to copy — which is exactly what makes "it is not in the manifest" mean "we forgot
#: it" and nothing else.
BORN_FRESH: tuple[tuple[str, str], ...] = (
    ("plan/tree.json", "this repo's plan tree is this repo's memory; a destination starts its own."),
    ("docs/STATE.md", "truth-as-of-today ABOUT THIS REPO — a bounded snapshot of one repo's own "
                      "present, false in any other from the moment it is copied."),
    ("docs/LOG.md", "this repo's episode history, immutable and not transferable."),
    ("docs/work/", "per-increment governance docs of THIS repo's increments."),
    ("docs/decisions/", "this repo's ADRs. The destination cites them as ancestry, it does not "
                        "inherit them as its own law."),
    ("INDEX.md", "GENERATED by `v3/memory/docs_manifest.py` — a derived view, never copied."),
    ("baseline_verdicts.json", "a promotion baseline is a fact about one repo's runs."),
    (".gen/", "the live slot manifest — per-invocation scratch, never a package member."),
    (".proof/", "re-derivable evidence. Copying it would import a green nobody re-earned."),
    (".metamem/", "cross-session auto-memory — a relationship with one engineer in one repo."),
)


#: (repo-relative ROOT-LEVEL file, WHY it stays behind). The third answer a root file can give.
#: The manifest is DIRECTORY-shaped, so a file sitting at the root is precisely what it cannot see:
#: `.gitignore` was tracked, load-bearing and in NEITHER table, and nothing noticed until someone
#: ran the extraction (V3-EXTRACT-CUTOVER). `root_disposition_problems` is the law; this is the only
#: legal way to be absent from both tables — by SAYING SO, with a reason.
STAYS: tuple[tuple[str, str], ...] = (
    ("compass_artifact_wf-132dbce3-4e7a-4e00-86d1-6d0011e22a13_text_markdown.md",
     "a research artifact of THIS repo's own investigation. The platform never reads it, no gate "
     "resolves it, and it is not part of what makes a factory run."),
)


def root_disposition(relpath: str) -> str | None:
    """'package' | 'born_fresh' | 'stays' | None (an UNDECIDED root file) — for root-level files only.

    Kept separate from `classify` on purpose: `classify` answers "does this path travel", which is a
    question about the PACKAGE, while this answers "was this root file DECIDED", which is a question
    about the manifest's own completeness. Folding them would let a `STAYS` row make a path look
    classified when what it really is, is deliberately absent.
    """
    if any(relpath == path for path, _reason in STAYS):
        return "stays"
    return classify(relpath)


def classify(relpath: str) -> str | None:
    """'package' | 'born_fresh' | 'ancestor' | None (a PACKING HOLE).

    Longest-prefix wins, so a specific BORN_FRESH row (`docs/work/`) overrides a broader PACKAGE row.

    'ancestor' exists so the manifest never has to LIE to stay green. A module that names `docs/` is
    naming a tree of which `docs/spec/` and `docs/reference/` travel and `docs/work/` does not — it
    is a prefix used for scanning, not a dependency on the whole subtree. Answering that with a
    `docs/` row in either list would assert something false in both directions; answering it by
    descent states exactly what is true: rows of the manifest live under this path.
    """
    best: tuple[int, str] | None = None
    for kind, rows in (("package", PACKAGE), ("born_fresh", BORN_FRESH)):
        for path, _reason in rows:
            if relpath == path.rstrip("/") or relpath.startswith(path):
                if best is None or len(path) > best[0]:
                    best = (len(path), kind)
    if best:
        return best[1]
    probe = relpath if relpath.endswith("/") else relpath + "/"
    if any(p.startswith(probe) for p, _ in PACKAGE):
        return "ancestor"
    return None
