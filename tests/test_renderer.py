"""Unit tests for metafactory.codegen.renderer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from metafactory.codegen.renderer import apply_builds, render_text, _copy_seed
from metafactory.engine.run_context import RunContext
from metafactory.engine.station import Station

PY = sys.executable
# A generator that reads its brief and EMITS the artifact (the substrate never writes dest itself).
# Declared in DATA (`via`) — the substrate names no tech (ADR-012/013). This stand-in is deterministic
# so the gate proof is reproducible; a live `claude -p` would be the same seam with different data.
_GEN_FROM_BRIEF = ("import os; "
                   "b=open(os.environ['METAFACTORY_BRIEF']).read(); "
                   "open(os.environ['METAFACTORY_DEST'],'w').write(b)")

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

    # ── skip_if_exists: la frontera generado/dominio (I-5, M4) ──────────────────
    def _meta_with_tpl(self, tmp_path, body="domain {{slug}}"):
        meta = tmp_path / "meta"
        (meta / "tpl").mkdir(parents=True)
        (meta / "tpl" / "d.txt").write_text(body, encoding="utf-8")
        return meta

    def test_render_skip_if_exists_preserves_domain(self, tmp_path):
        """Un archivo de dominio editado a mano SOBREVIVE un re-render (skip_if_exists)."""
        meta = self._meta_with_tpl(tmp_path)
        out = tmp_path / "out"; out.mkdir()
        ctx = RunContext(root=out, meta_root=meta)
        st = make_station("m4", [{"action": "render", "src": "tpl/d.txt", "dest": "domain/d.txt",
                                  "skip_if_exists": True}])
        apply_builds(ctx, st, {"slug": "dummy"})           # primer scaffold
        (out / "domain" / "d.txt").write_text("EDITADO A MANO", encoding="utf-8")
        msgs = apply_builds(ctx, st, {"slug": "dummy"})    # re-scaffold
        assert (out / "domain" / "d.txt").read_text() == "EDITADO A MANO"
        assert any("skip(exists)" in m for m in msgs)

    def test_render_without_flag_overwrites_generated(self, tmp_path):
        """Sin el flag, generado/ SÍ se regenera (la otra cara de la frontera)."""
        meta = self._meta_with_tpl(tmp_path, body="generated {{slug}}")
        out = tmp_path / "out"; out.mkdir()
        ctx = RunContext(root=out, meta_root=meta)
        st = make_station("m4", [{"action": "render", "src": "tpl/d.txt", "dest": "generated/g.txt"}])
        apply_builds(ctx, st, {"slug": "dummy"})
        (out / "generated" / "g.txt").write_text("BASURA", encoding="utf-8")
        apply_builds(ctx, st, {"slug": "dummy"})
        assert (out / "generated" / "g.txt").read_text() == "generated dummy"

    def test_render_tree_skip_if_exists_preserves_existing(self, tmp_path):
        meta = tmp_path / "meta"
        (meta / "tpl").mkdir(parents=True)
        (meta / "tpl" / "a.txt").write_text("{{slug}}", encoding="utf-8")
        out = tmp_path / "out"; out.mkdir()
        ctx = RunContext(root=out, meta_root=meta)
        st = make_station("m4", [{"action": "render_tree", "src": "tpl", "dest": "domain",
                                  "skip_if_exists": True}])
        apply_builds(ctx, st, {"slug": "dummy"})
        (out / "domain" / "a.txt").write_text("MANUAL", encoding="utf-8")
        msgs = apply_builds(ctx, st, {"slug": "dummy"})
        assert (out / "domain" / "a.txt").read_text() == "MANUAL"
        assert any("skip(exists)" in m for m in msgs)

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


# ── generate: the creative slot (C1, ADR-013) ──────────────────────────────────

class TestGenerateAction:
    def test_generator_declared_in_data_produces_artifact(self, tmp_path):
        """The substrate runs the generator from `via` (data); the generator writes dest."""
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [{"action": "generate", "dest": "build/out.py",
                                  "brief": "MARK={{marker}}", "via": [PY, "-c", _GEN_FROM_BRIEF]}])
        msgs = apply_builds(ctx, st, {"marker": "OK_1"})
        assert (tmp_path / "build" / "out.py").read_text() == "MARK=OK_1"
        assert any("generate build/out.py" in m and "produced=True" in m for m in msgs)

    def test_brief_written_to_default_gen_location(self, tmp_path):
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [{"action": "generate", "dest": "build/x.py",
                                  "brief": "blueprint {{slug}}", "via": [PY, "-c", _GEN_FROM_BRIEF]}])
        msgs = apply_builds(ctx, st, {"slug": "demo"})
        assert (tmp_path / ".gen" / "x.py.brief.md").read_text() == "blueprint demo"
        assert any("brief .gen/x.py.brief.md" in m for m in msgs)

    def test_substrate_does_not_fake_artifact_when_generator_produces_nothing(self, tmp_path):
        """The honest seam: a generator that writes nothing leaves dest ABSENT — the substrate
        never writes the artifact itself (the column will then render the honest red)."""
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [{"action": "generate", "dest": "build/none.py",
                                  "brief": "x", "via": [PY, "-c", "pass"]}])
        msgs = apply_builds(ctx, st, {})
        assert not (tmp_path / "build" / "none.py").exists()
        assert any("produced=False" in m for m in msgs)

    def test_generator_that_cannot_launch_does_not_raise(self, tmp_path):
        """Fail-safe: a generator binary that can't even launch never throws past the build —
        dest stays absent and the column gates it red."""
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [{"action": "generate", "dest": "build/n.py",
                                  "via": ["metafactory-no-such-binary-xyz"]}])
        msgs = apply_builds(ctx, st, {})  # must not raise
        assert not (tmp_path / "build" / "n.py").exists()
        assert any("rc=127" in m and "produced=False" in m for m in msgs)

    def test_stale_artifact_removed_before_generation(self, tmp_path):
        """A failing generator must NOT pass on a stale artifact from a prior run."""
        ctx = make_ctx(tmp_path)
        dest = tmp_path / "build" / "s.py"
        dest.parent.mkdir(parents=True)
        dest.write_text("STALE-FROM-PRIOR-RUN")
        st = make_station("c1", [{"action": "generate", "dest": "build/s.py",
                                  "via": [PY, "-c", "pass"]}])  # produces nothing this run
        apply_builds(ctx, st, {})
        assert not dest.exists()  # stale removed, generator wrote nothing -> absent

    def test_skip_if_exists_preserves_filled_slot(self, tmp_path):
        """skip_if_exists: don't re-invoke the generator if the slot is already filled
        (e.g. a non-deterministic LLM run)."""
        ctx = make_ctx(tmp_path)
        dest = tmp_path / "build" / "k.py"
        dest.parent.mkdir(parents=True)
        dest.write_text("ALREADY-GENERATED")
        st = make_station("c1", [{"action": "generate", "dest": "build/k.py", "skip_if_exists": True,
                                  "brief": "x", "via": [PY, "-c", _GEN_FROM_BRIEF]}])
        msgs = apply_builds(ctx, st, {})
        assert dest.read_text() == "ALREADY-GENERATED"
        assert any("skip(exists)" in m for m in msgs)

    def test_via_argv_receives_substitution(self, tmp_path):
        """`via` argv gets {{var}} subst, so the design can parametrize the generator call."""
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [{"action": "generate", "dest": "build/v.txt",
                                  "via": [PY, "-c", "import os;open(os.environ['METAFACTORY_DEST'],'w').write('{{payload}}')"]}])
        apply_builds(ctx, st, {"payload": "FROM_ARGV"})
        assert (tmp_path / "build" / "v.txt").read_text() == "FROM_ARGV"

    def test_same_seam_is_domain_agnostic(self, tmp_path):
        """principle #6 (ADR-012): the SAME action runs radically different generators with NO
        per-tech branch — one emits Python, the other emits TypeScript."""
        ctx = make_ctx(tmp_path)
        st = make_station("c1", [
            {"action": "generate", "dest": "build/mod.py",
             "brief": "def greet(): return {{marker}}", "via": [PY, "-c", _GEN_FROM_BRIEF]},
            {"action": "generate", "dest": "build/mod.ts",
             "brief": "export const greet = () => {{marker}};", "via": [PY, "-c", _GEN_FROM_BRIEF]},
        ])
        apply_builds(ctx, st, {"marker": '"X"'})
        assert (tmp_path / "build" / "mod.py").read_text() == 'def greet(): return "X"'
        assert (tmp_path / "build" / "mod.ts").read_text() == 'export const greet = () => "X";'


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
