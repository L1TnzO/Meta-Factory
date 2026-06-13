"""Unit tests for metafactory.docs_manifest."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from metafactory.docs_manifest import (
    SEAL_RE,
    body_of,
    build_index,
    check,
    git_blob_sha,
    split_seal,
    stamp,
    sync,
)

# ── git availability ──────────────────────────────────────────────────────────

def _git_available() -> bool:
    try:
        r = subprocess.run(["git", "--version"], capture_output=True)
        return r.returncode == 0
    except OSError:
        return False


_GIT = _git_available()


# ── helpers ───────────────────────────────────────────────────────────────────

def _sealed_md(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    stamp(p)
    return p


def _make_tiny_repo(tmp_path: Path) -> Path:
    """Create the minimal layout that docs_manifest.check() and doc_set() expect."""
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    # A properly stamped doc under docs/
    d = repo / "docs" / "STATE.md"
    d.write_text("# State\nsome content\n", encoding="utf-8")
    stamp(d)
    # START-HERE.md at repo root
    sh = repo / "START-HERE.md"
    sh.write_text("# Start Here\n", encoding="utf-8")
    stamp(sh)
    return repo


# ── git_blob_sha ─────────────────────────────────────────────────────────────

class TestGitBlobSha:
    @pytest.mark.skipif(not _GIT, reason="git not available")
    def test_matches_git_hash_object(self, tmp_path):
        data = b"hello, git\n"
        expected = git_blob_sha(data)
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=data, capture_output=True,
        )
        actual = result.stdout.strip().decode()
        assert expected == actual

    def test_different_bytes_give_different_sha(self):
        assert git_blob_sha(b"abc") != git_blob_sha(b"xyz")

    def test_empty_bytes_sha_is_deterministic(self):
        s1 = git_blob_sha(b"")
        s2 = git_blob_sha(b"")
        assert s1 == s2

    def test_sha_is_40_hex_chars(self):
        sha = git_blob_sha(b"some content")
        assert re.fullmatch(r"[0-9a-f]{40}", sha)


# ── split_seal / body_of ─────────────────────────────────────────────────────

class TestSplitSeal:
    def test_no_seal_returns_none_and_full_text(self):
        text = "# Title\nsome body\n"
        seal, body = split_seal(text)
        assert seal is None
        assert body == text

    def test_with_seal_parses_correctly(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Title\nbody here\n", encoding="utf-8")
        stamp(p)
        text = p.read_text(encoding="utf-8")
        seal, body = split_seal(text)
        assert seal is not None
        assert SEAL_RE.match(seal)
        assert "# Title" in body

    def test_seal_line_not_in_body(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\ncontent\n", encoding="utf-8")
        stamp(p)
        text = p.read_text(encoding="utf-8")
        _, body = split_seal(text)
        assert "meta:doc" not in body

    def test_body_of_excludes_seal_line(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\nsome body\n", encoding="utf-8")
        stamp(p)
        text = p.read_text(encoding="utf-8")
        body = body_of(text)
        assert "meta:doc" not in body
        assert "# Doc" in body


# ── stamp idempotency ─────────────────────────────────────────────────────────

class TestStampIdempotency:
    def test_first_stamp_returns_true(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\ncontent\n", encoding="utf-8")
        changed = stamp(p)
        assert changed is True

    def test_second_stamp_returns_false(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\ncontent\n", encoding="utf-8")
        stamp(p)  # first stamp
        changed = stamp(p)  # second stamp, same body
        assert changed is False

    def test_second_stamp_does_not_modify_file(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\ncontent\n", encoding="utf-8")
        stamp(p)
        text_after_first = p.read_text(encoding="utf-8")
        stamp(p)
        text_after_second = p.read_text(encoding="utf-8")
        assert text_after_first == text_after_second

    def test_editing_body_triggers_restamp(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\ncontent\n", encoding="utf-8")
        stamp(p)
        # modify body only
        _, body = split_seal(p.read_text(encoding="utf-8"))
        p.write_text(f"<!-- placeholder -->\n{body}new line\n", encoding="utf-8")
        # write without seal so stamp treats it as new
        p.write_text(f"{body}new line\n", encoding="utf-8")
        changed = stamp(p)
        assert changed is True


# ── build_index / check ───────────────────────────────────────────────────────

class TestBuildIndex:
    def test_build_index_lists_stamped_docs(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        index_text = build_index(repo)
        assert "docs/STATE.md" in index_text
        assert "START-HERE.md" in index_text

    def test_build_index_excludes_INDEX_md(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        # create an INDEX.md (which should be excluded)
        (repo / "INDEX.md").write_text("# INDEX\n", encoding="utf-8")
        index_text = build_index(repo)
        assert "INDEX.md" not in index_text

    def test_build_index_has_header(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        index_text = build_index(repo)
        assert "generated by metafactory.docs_manifest" in index_text


class TestCheck:
    def test_clean_repo_has_no_problems(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        # sync to write INDEX.md
        sync(repo)
        problems = check(repo)
        assert problems == []

    def test_missing_index_is_a_problem(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        # do NOT create INDEX.md
        problems = check(repo)
        assert any("INDEX.md" in p for p in problems)

    def test_unstamped_doc_is_a_problem(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        sync(repo)
        # add a new unstamped doc
        d = repo / "docs" / "NEW.md"
        d.write_text("# New\ncontent\n", encoding="utf-8")
        # don't stamp it; rebuild index to include it
        sync(repo)  # this stamps it, so let's manually break the seal
        text = d.read_text(encoding="utf-8")
        _, body = split_seal(text)
        # Write back with a wrong sha seal
        d.write_text("<!-- meta:doc sha=0000000000000000000000000000000000000000 updated=2026-01-01T00:00Z -->\n" + body, encoding="utf-8")
        problems = check(repo)
        assert any("NEW.md" in p or "stale" in p for p in problems)

    def test_dangling_index_entry_is_a_problem(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        sync(repo)
        # manually add a nonexistent doc to INDEX.md
        index = repo / "INDEX.md"
        text = index.read_text(encoding="utf-8")
        text += "| `docs/GHOST.md` | `abcdef012345` | 2026-01-01T00:00Z | Ghost |\n"
        index.write_text(text, encoding="utf-8")
        problems = check(repo)
        assert any("GHOST.md" in p and "dangling" in p for p in problems)

    def test_doc_missing_from_index_is_a_problem(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        sync(repo)
        # add a new doc and stamp it but don't update INDEX
        d = repo / "docs" / "EXTRA.md"
        d.write_text("# Extra\ncontent\n", encoding="utf-8")
        stamp(d)
        # rebuild index but then remove the entry manually
        index_text = build_index(repo)
        lines = [ln for ln in index_text.splitlines() if "EXTRA.md" not in ln]
        (repo / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        problems = check(repo)
        assert any("EXTRA.md" in p for p in problems)

    def test_dangling_link_in_start_here_is_a_problem(self, tmp_path):
        repo = _make_tiny_repo(tmp_path)
        sync(repo)
        # write a dangling link into START-HERE.md
        sh = repo / "START-HERE.md"
        _, body = split_seal(sh.read_text(encoding="utf-8"))
        sh.write_text(body + "\nSee [nonexistent](docs/NONEXISTENT.md).\n", encoding="utf-8")
        stamp(sh)
        sync(repo)
        problems = check(repo)
        assert any("NONEXISTENT.md" in p for p in problems)
