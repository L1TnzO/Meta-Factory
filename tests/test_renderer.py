"""Unit tests for metafactory.codegen.renderer."""
from __future__ import annotations

from pathlib import Path

import pytest

from metafactory.codegen.renderer import apply_builds, render_text, _copy_seed
from metafactory.engine.run_context import RunContext
from metafactory.engine.station import Station

# ── repo root for copy_seed ───────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]


# ── helpers ───────────────────────────────────────────────────────────────────

def make_station(sid: str, builds: list[dict]) -> Station:
    return Station.from_dict({"id": sid, "name": sid, "builds": builds})


def make_ctx(root: Path, meta_root: Path | None = None) -> RunContext:
    return RunContext(root=root, meta_root=meta_root or _REPO_ROOT)


# ── render_text ───────────────────────────────────────────────────────────────

class TestRenderText:
    def test_substitutes_single_placeholder(self):
        assert render_text("Hello {{name}}!", {"name": "World"}) == "Hello World!"

    def test_substitutes_multiple_placeholders(self):
        result = render_text("{{a}} + {{b}}", {"a": "1", "b": "2"})
        assert result == "1 + 2"

    def test_placeholder_with_spaces(self):
        result = render_text("{{ slug }}", {"slug": "my-factory"})
        assert result == "my-factory"

    def test_non_str_value_coerced_to_str(self):
        result = render_text("count={{n}}", {"n": 42})
        assert result == "count=42"

    def test_no_placeholders_returns_text_unchanged(self):
        text = "plain text with no placeholders"
        assert render_text(text, {}) == text

    def test_unknown_placeholder_raises_key_error(self):
        with pytest.raises(KeyError, match="unknown"):
            render_text("{{unknown}}", {"known": "x"})

    def test_extra_subst_keys_are_ignored(self):
        result = render_text("{{a}}", {"a": "yes", "extra": "ignored"})
        assert result == "yes"

    def test_repeated_placeholder_substituted_everywhere(self):
        result = render_text("{{x}}-{{x}}", {"x": "val"})
        assert result == "val-val"

    def test_empty_template_returns_empty(self):
        assert render_text("", {"slug": "x"}) == ""


# ── apply_builds: mkdir ───────────────────────────────────────────────────────

class TestApplyBuildsActions:
    def test_mkdir_creates_directory(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [{"action": "mkdir", "path": "subdir/nested"}])
        msgs = apply_builds(ctx, station, {})
        assert (tmp_path / "subdir" / "nested").is_dir()
        assert any("mkdir" in m for m in msgs)

    def test_mkdir_with_substitution(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [{"action": "mkdir", "path": "{{slug}}/src"}])
        apply_builds(ctx, station, {"slug": "my-factory"})
        assert (tmp_path / "my-factory" / "src").is_dir()

    def test_mkdir_is_idempotent(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [{"action": "mkdir", "path": "out"}])
        apply_builds(ctx, station, {})
        apply_builds(ctx, station, {})  # should not raise
        assert (tmp_path / "out").is_dir()

    def test_write_creates_file_with_content(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [{"action": "write", "dest": "hello.txt", "content": "world"}])
        msgs = apply_builds(ctx, station, {})
        assert (tmp_path / "hello.txt").read_text() == "world"
        assert any("write" in m for m in msgs)

    def test_write_substitutes_content(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [
            {"action": "write", "dest": "out.txt", "content": "slug={{slug}}"}
        ])
        apply_builds(ctx, station, {"slug": "my-slug"})
        assert (tmp_path / "out.txt").read_text() == "slug=my-slug"

    def test_write_creates_parent_dirs(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [
            {"action": "write", "dest": "a/b/c.txt", "content": "hi"}
        ])
        apply_builds(ctx, station, {})
        assert (tmp_path / "a" / "b" / "c.txt").exists()

    def test_render_reads_from_meta_root(self, tmp_path):
        # Create a synthetic meta_root with a template
        meta = tmp_path / "meta"
        (meta / "templates").mkdir(parents=True)
        tpl = meta / "templates" / "hello.txt"
        tpl.write_text("Hello {{name}}!", encoding="utf-8")

        output = tmp_path / "out"
        output.mkdir()
        ctx = RunContext(root=output, meta_root=meta)
        station = make_station("s1", [
            {"action": "render", "src": "templates/hello.txt", "dest": "result.txt"}
        ])
        apply_builds(ctx, station, {"name": "World"})
        assert (output / "result.txt").read_text() == "Hello World!"

    def test_render_tree_copies_all_files(self, tmp_path):
        meta = tmp_path / "meta"
        (meta / "tpl").mkdir(parents=True)
        (meta / "tpl" / "a.txt").write_text("{{slug}}", encoding="utf-8")
        (meta / "tpl" / "b.txt").write_text("static", encoding="utf-8")

        output = tmp_path / "out"
        output.mkdir()
        ctx = RunContext(root=output, meta_root=meta)
        station = make_station("s1", [
            {"action": "render_tree", "src": "tpl", "dest": "rendered"}
        ])
        apply_builds(ctx, station, {"slug": "dummy"})
        assert (output / "rendered" / "a.txt").read_text() == "dummy"
        assert (output / "rendered" / "b.txt").read_text() == "static"

    def test_unknown_action_raises_value_error(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [{"action": "teleport"}])
        with pytest.raises(ValueError, match="unknown build action"):
            apply_builds(ctx, station, {})

    def test_multiple_builds_return_multiple_msgs(self, tmp_path):
        ctx = make_ctx(tmp_path)
        station = make_station("s1", [
            {"action": "mkdir", "path": "a"},
            {"action": "mkdir", "path": "b"},
        ])
        msgs = apply_builds(ctx, station, {})
        assert len(msgs) == 2


# ── copy_seed ─────────────────────────────────────────────────────────────────

class TestCopySeed:
    def test_copy_seed_copies_verifier(self, tmp_path):
        ctx = make_ctx(tmp_path, meta_root=_REPO_ROOT)
        msgs = _copy_seed(ctx)
        seed_dest = tmp_path / "seed"
        assert seed_dest.is_dir()
        # verifier.py must have been copied
        assert (seed_dest / "verifier.py").exists()

    def test_copy_seed_returns_messages(self, tmp_path):
        ctx = make_ctx(tmp_path, meta_root=_REPO_ROOT)
        msgs = _copy_seed(ctx)
        assert len(msgs) >= 1
        assert all("copy_seed" in m for m in msgs)

    def test_copy_seed_via_apply_builds(self, tmp_path):
        ctx = make_ctx(tmp_path, meta_root=_REPO_ROOT)
        station = make_station("m1", [{"action": "copy_seed"}])
        msgs = apply_builds(ctx, station, {})
        assert any("copy_seed" in m for m in msgs)
        assert (tmp_path / "seed" / "verifier.py").exists()

    def test_copy_seed_idempotent(self, tmp_path):
        ctx = make_ctx(tmp_path, meta_root=_REPO_ROOT)
        _copy_seed(ctx)
        _copy_seed(ctx)  # second call should not raise
        assert (tmp_path / "seed" / "verifier.py").exists()
