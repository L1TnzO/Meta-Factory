"""tests/test_overlap.py — suite Tier 0 for metafactory.memory.overlap (ADR-019 §5/§Consec., M6).

The OBSERVER of the third memory (auto-memory note-store vs the `docs/` wiki). Invariant: ZERO model
calls (file-IO + arithmetic). These tests are the two-sided TOOTH (in the suite, not a gate — the
note-store is out-of-tree): the containment metric MUST bite on a note copied from docs/ (HIGH band)
and MUST NOT bite on an unrelated note (LOW band); the locator MUST degrade gracefully (return None)
when the note-store is absent, so `meta metrics --overlap` stays portable on a clean clone. Uses
tmp_path; never touches the real `~/.claude` store.
"""
from __future__ import annotations

from pathlib import Path

from metafactory.memory import overlap


# ---------------------------------------------------------------------------
# shingles / containment — the deterministic core
# ---------------------------------------------------------------------------
class TestShingles:
    def test_kgrams_count(self):
        # 6 words, k=5 → 2 shingles.
        assert len(overlap.shingles("a b c d e f", k=5)) == 2

    def test_too_short_is_empty(self):
        assert overlap.shingles("a b c", k=5) == set()

    def test_case_and_whitespace_folded(self):
        assert overlap.shingles("The  Quick\nBROWN fox jumps", k=5) == {"the quick brown fox jumps"}


class TestContainment:
    def test_verbatim_copy_is_high(self):
        docs = overlap.shingles("the meta factory regenerates the agent systems factory from its spec", 5)
        note = "---\ntype: project\n---\nthe meta factory regenerates the agent systems factory from its spec"
        score = overlap.containment(note, docs)
        assert score == 1.0
        assert overlap.band_of(score) == "HIGH"

    def test_unrelated_is_low(self):
        docs = overlap.shingles("the meta factory regenerates the agent systems factory from its spec", 5)
        note = "---\ntype: feedback\n---\nplease prove everything by blocking and never fake a green check"
        score = overlap.containment(note, docs)
        assert score == 0.0
        assert overlap.band_of(score) == "LOW"

    def test_frontmatter_excluded(self):
        # The frontmatter words must not count toward containment (they're metadata, not content).
        docs = overlap.shingles("alpha beta gamma delta epsilon zeta eta", 5)
        note = "---\nname: x\ntype: project\ndescription: alpha beta gamma delta epsilon\n---\nunrelated body words here now"
        assert overlap.containment(note, docs) == 0.0

    def test_band_boundaries(self):
        assert overlap.band_of(overlap.BAND_HIGH) == "HIGH"
        assert overlap.band_of(overlap.BAND_LOW) == "MID"
        assert overlap.band_of(overlap.BAND_LOW - 0.001) == "LOW"


# ---------------------------------------------------------------------------
# measure — per-note rows over a synthetic store + docs tree
# ---------------------------------------------------------------------------
def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """A tiny repo with docs/ + a synthetic note-store; returns (root, memdir)."""
    root = tmp_path / "repo"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "LOG.md").write_text(
        "the meta factory regenerates the agent systems factory from its frozen spec by blocking",
        encoding="utf-8")
    memdir = tmp_path / "store"
    memdir.mkdir()
    (memdir / "MEMORY.md").write_text("- [dup](dup.md)\n- [uniq](uniq.md)\n", encoding="utf-8")
    (memdir / "dup.md").write_text(
        "---\ntype: project\n---\nthe meta factory regenerates the agent systems factory from its frozen spec by blocking",
        encoding="utf-8")
    (memdir / "uniq.md").write_text(
        "---\ntype: feedback\n---\nthe engineer wants determinism over prose and token economy in the orchestrator loop",
        encoding="utf-8")
    return root, memdir


class TestMeasure:
    def test_two_sided_classification(self, tmp_path):
        root, memdir = _make_project(tmp_path)
        docs_sh = overlap.docs_corpus_shingles(root)
        rows = {r["name"]: r for r in overlap.measure(memdir, docs_sh)}
        assert rows["dup.md"]["band"] == "HIGH" and rows["dup.md"]["type"] == "project"
        assert rows["uniq.md"]["band"] == "LOW" and rows["uniq.md"]["type"] == "feedback"
        # sorted worst-duplicator first
        assert overlap.measure(memdir, docs_sh)[0]["name"] == "dup.md"

    def test_memory_index_excluded_from_rows(self, tmp_path):
        root, memdir = _make_project(tmp_path)
        names = {r["name"] for r in overlap.measure(memdir, overlap.docs_corpus_shingles(root))}
        assert "MEMORY.md" not in names

    def test_index_tokens_positive(self, tmp_path):
        _, memdir = _make_project(tmp_path)
        assert overlap.memory_index_tokens(memdir) > 0


# ---------------------------------------------------------------------------
# portability — absent note-store must degrade gracefully (not raise)
# ---------------------------------------------------------------------------
class TestPortability:
    def test_find_memdir_absent_is_none(self, tmp_path):
        assert overlap.find_memdir(tmp_path / "nonexistent") is None

    def test_explicit_override_resolves(self, tmp_path):
        _, memdir = _make_project(tmp_path)
        assert overlap.find_memdir(tmp_path, explicit=str(memdir)) == memdir

    def test_explicit_without_index_is_none(self, tmp_path):
        empty = tmp_path / "empty"; empty.mkdir()
        assert overlap.find_memdir(tmp_path, explicit=str(empty)) is None

    def test_summarize_absent_is_one_honest_line(self, tmp_path):
        out = overlap.summarize(tmp_path / "no-store-here")
        assert len(out) == 1 and "ausente" in out[0]

    def test_summarize_present_is_bounded(self, tmp_path):
        root, memdir = _make_project(tmp_path)
        out = overlap.summarize(root, explicit=str(memdir))
        assert 1 < len(out) <= 6
        assert any("SOLAPAMIENTO" in ln for ln in out)
