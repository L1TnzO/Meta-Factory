"""Tooth for precompact (ADR-019 §5, M4): the minimum-fidelity, non-destructive writeback at the
COMPACTION boundary. Proven by behaviour on synthetic repos (tmp dirs) — no live hook, no model:

  - build_snapshot RE-DERIVES the open increment + a plan pointer/digest from disk;
  - the writeback is VALIDATED + NON-DESTRUCTIVE (a malformed snapshot never clobbers a good one);
  - re-injection is GUARDED: only on source==compact AND only for THIS session (stale → ignored);
  - the `compact` series (M5) is recorded, so the bet is READ against the observer;
  - rehydrate surfaces the preserved state end-to-end on compact and not otherwise.
"""
from __future__ import annotations

from pathlib import Path

from metafactory.memory import instrument, journal, precompact, rehydrate

INCREMENT = """<!-- meta:doc sha=x updated=2026-06-26T00:00Z -->
# Incremento FOO

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-26T00:00Z).

## Objetivo
Dejar TERMINADO el experimento foo con diente.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | a | ✅ |
| 2 | b | ✅ |
| 3 | c | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. algo
"""


def _repo_with_increment(tmp_path: Path) -> Path:
    wd = tmp_path / "docs" / "work"
    wd.mkdir(parents=True)
    (wd / "FOO-INCREMENT.md").write_text(INCREMENT, encoding="utf-8")
    return tmp_path


def test_build_snapshot_rederives_open_increment(tmp_path):
    """The snapshot picks up the open increment, points at its doc, extracts the objective, and counts
    phases (2/3 ✅) — a re-derived digest, not a copy of the conversation."""
    root = _repo_with_increment(tmp_path)
    snap = precompact.build_snapshot(root, session="S1", trigger="auto")
    assert snap["increment"] == "FOO-INCREMENT.md"
    assert snap["plan"]["doc"] == "docs/work/FOO-INCREMENT.md"
    assert "experimento foo" in snap["plan"]["objective"]
    assert (snap["plan"]["phases_done"], snap["plan"]["phases_total"]) == (2, 3)
    assert precompact.is_valid(snap)


def test_validated_writeback_is_nondestructive(tmp_path):
    """A good snapshot persists; a malformed one (empty / wrong schema) is REJECTED and never clobbers
    the good one on disk — the non-destructive half of the ClawVM writeback."""
    root = _repo_with_increment(tmp_path)
    good = precompact.build_snapshot(root, session="S1", trigger="manual")
    assert precompact.write_snapshot(root, good) is not None
    assert precompact.write_snapshot(root, {}) is None                       # malformed
    assert precompact.write_snapshot(root, {"schema": "wrong", "ts": "x"}) is None
    on_disk = precompact.read_snapshot(root)
    assert on_disk is not None and on_disk["session"] == "S1"               # the good one survives


def test_surface_guard_session_and_source(tmp_path):
    """Re-injection fires ONLY on a compaction AND only for THIS session: another session's snapshot is
    stale (would re-introduce drift) and a normal startup is not a compaction."""
    root = _repo_with_increment(tmp_path)
    precompact.write_snapshot(root, precompact.build_snapshot(root, session="S1", trigger="auto"))
    assert precompact.surface_for_rehydrate(root, session="S1", source="compact")        # this session
    assert precompact.surface_for_rehydrate(root, session="OTHER", source="compact") == []  # stale
    assert precompact.surface_for_rehydrate(root, session="S1", source="startup") == []   # not compact


def test_render_is_bounded_and_handles_no_increment(tmp_path):
    """The re-injection is bounded (≤7 lines) and degrades gracefully when no increment was open."""
    root = _repo_with_increment(tmp_path)
    snap = precompact.build_snapshot(root, session="S1", trigger="auto")
    lines = precompact.render_for_rehydrate(snap)
    assert lines and len(lines) <= 7 and any("POST-COMPACTACIÓN" in ln for ln in lines)
    empty = precompact.build_snapshot(tmp_path / "empty", session="S2", trigger="auto")  # no docs/work
    rendered = precompact.render_for_rehydrate(empty)
    assert rendered and any("No había incremento" in ln for ln in rendered)


def test_record_writes_compact_series(tmp_path):
    """record() feeds M5's `compact` series + journals the event, so the bet is measurable (correlate
    with thrashing). Both halves land under the tmp root's `.metamem`."""
    root = _repo_with_increment(tmp_path)
    snap = precompact.build_snapshot(root, session="S1", trigger="auto")
    precompact.record(root, snap, written=True)
    series = instrument.compact_series(root)
    assert len(series) == 1 and series[0]["increment"] == "FOO-INCREMENT.md" and series[0]["written"] is True
    assert any(e["kind"] == "compact" for e in journal.read(root))
    assert any("COMPACTACIÓN" in ln for ln in instrument.summarize(root))


def test_rehydrate_injects_on_compact_only(tmp_path):
    """End-to-end read half: rehydrate re-injects the preserved block on source==compact (same session)
    and does NOT on a normal startup — the payload is backward-compatible (source defaults to '')."""
    root = _repo_with_increment(tmp_path)
    precompact.write_snapshot(root, precompact.build_snapshot(root, session="S1", trigger="auto"))
    compact = rehydrate.build_payload(root, session="S1", source="compact")
    startup = rehydrate.build_payload(root, session="S1", source="startup")
    assert "POST-COMPACTACIÓN" in compact
    assert "POST-COMPACTACIÓN" not in startup
