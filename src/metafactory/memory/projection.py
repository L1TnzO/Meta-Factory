"""projection — el FIX de G-M1: proyección determinista de HECHOS a STATE.

La lección vivida: el disparador discrecional se saltea. La cura (ADR-007 §3, ADR-023):
- Achicar la superficie de JUICIO: cuanto más de STATE sea proyección de hechos (regenerable),
  menos prosa escribe el modelo y menos puede quedar vieja.
- Lo determinista se ENFORZA (este bloque debe estar fresco: `meta check` lo verifica, hard);
  el SIGNIFICADO (qué episodio escribir) se SURFACE-ea, no se hard-blockea.

El bloque proyecta HECHOS LENTOS (incremento abierto, RTM por fábrica) que cambian en fronteras
de fase, no en cada turno → churn mínimo. Los hechos rápidos viven en el journal (vista en vivo).
NUNCA editar el bloque a mano: se regenera con `meta checkpoint`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

START = "<!-- meta:projection (generated from facts; do NOT hand-edit, refreshed by `meta checkpoint`) -->"
_LEGACY_START = "<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->"
END = "<!-- /meta:projection -->"
# Dual-accept the START marker (ADR-026 migration): a STATE.md written before this constant's English
# translation still has the legacy Spanish marker on disk. `refresh()` must FIND that old block to replace
# it in place, not leave it stranded and insert a second one — same lesson as the Estado/Status header
# grammar (ENGLISH-CLI-STRINGS Slot B). `END` never had Spanish words, so it needs no legacy variant.
BLOCK_RE = re.compile(r"(?:" + re.escape(START) + "|" + re.escape(_LEGACY_START) + r")" + r".*?" + re.escape(END),
                      re.DOTALL)


def open_increment(root: Path) -> str | None:
    """Delegates to the seed's lifecycle LAW (`seed/lifecycle.py`) — single source shared with a
    produced factory's inherited `increment_guard`, so the meta and the factory never diverge."""
    from .._seed import load_seed_lifecycle
    return load_seed_lifecycle().open_increment(Path(root))


def rtm_statuses(root: Path) -> dict[str, tuple[str, int, int]]:
    """Re-deriva el RTM de cada fábrica producida desde artefactos (.proof) — cero narrativa. Fuente
    ESTRUCTURADA `{slug: (status, satisfechos, total)}` (orden = fábricas ordenadas). `rtm_status` la
    formatea; `state_fidelity` (M3) la lee como ORÁCULO determinista. Single-source: una sola lectura
    del proof alimenta la proyección y el gate de fidelidad."""
    from ..engine.run_context import RunContext
    from ..spec import load_spec

    out: dict[str, tuple[str, int, int]] = {}
    facdir = Path(root) / "factories"
    if not facdir.exists():
        return out
    for fdir in sorted(p for p in facdir.iterdir() if p.is_dir()):
        spec_path = fdir / "factory.spec.yml"
        if not spec_path.exists():
            continue
        spec = load_spec(spec_path)
        ctx = RunContext(root=fdir, meta_root=root, slug=spec.slug)
        total = len(spec.requirements)
        unsat = 0
        for req in spec.requirements:
            ok = bool(req.satisfied_by)
            for sid in req.satisfied_by:
                proof = ctx.verifier.load_proof(fdir, sid)
                ok = ok and proof is not None and ctx.verifier.gate_recompute_ok(proof)[0]
            if not ok:
                unsat += 1
        status = "COMPLETE" if (unsat == 0 and total > 0) else ("INCOMPLETE" if total > 0 else "—")
        out[spec.slug] = (status, total - unsat, total)
    return out


def rtm_status(root: Path) -> list[str]:
    """El RTM por fábrica como líneas formateadas (vista de la proyección). Deriva de `rtm_statuses`."""
    return [f"{slug}: {st} ({sat}/{tot})" for slug, (st, sat, tot) in rtm_statuses(root).items()]


def build_block(root: Path) -> str:
    inc = open_increment(root) or "none"
    rtm = rtm_status(root)
    return "\n".join([
        START,
        "> Fact projection (Tier 0 → STATE). Source: re-derivable artifacts; not narrative.",
        f"- Open increment: {inc}",
        f"- RTM by factory (re-derived from `.proof/`): {' · '.join(rtm) if rtm else 'no factories'}",
        END,
    ])


def current_block(root: Path) -> str | None:
    state = Path(root) / "docs" / "STATE.md"
    if not state.exists():
        return None
    m = BLOCK_RE.search(state.read_text(encoding="utf-8"))
    return m.group(0) if m else None


def is_stale(root: Path) -> tuple[bool, str]:
    cur = current_block(root)
    fresh = build_block(root)
    if cur is None:
        return True, "docs/STATE.md:1: missing the projection block (run `meta checkpoint`)"
    if cur.strip() != fresh.strip():
        return True, "docs/STATE.md:1: the projection is stale vs. the facts (run `meta checkpoint`)"
    return False, "ok"


def refresh(root: Path) -> bool:
    """Reescribe el bloque en STATE.md (lo inserta antes del primer `## ` si falta).
    Devuelve True si cambió. NO re-sella (lo hace el caller con doc-sync)."""
    state = Path(root) / "docs" / "STATE.md"
    text = state.read_text(encoding="utf-8")
    fresh = build_block(root)
    matches = list(BLOCK_RE.finditer(text))
    if matches:
        # Replace the FIRST block in place; drop any further block(s) entirely. Handles the common
        # case (exactly one match) unchanged, and self-heals a stray duplicate — e.g. the legacy
        # Spanish marker and a fresh English one briefly coexisting across the START-text migration.
        pieces = [text[: matches[0].start()], fresh]
        prev_end = matches[0].end()
        for m in matches[1:]:
            pieces.append(text[prev_end: m.start()].rstrip("\n"))
            prev_end = m.end()
        pieces.append(text[prev_end:])
        new = re.sub(r"\n{3,}", "\n\n", "".join(pieces))
    else:
        m = re.search(r"^## ", text, re.MULTILINE)
        if m:
            new = text[: m.start()] + fresh + "\n\n" + text[m.start():]
        else:
            new = text.rstrip() + "\n\n" + fresh + "\n"
    if new == text:
        return False
    state.write_text(new, encoding="utf-8")
    return True


def _main(argv: list[str]) -> int:
    from .._seed import repo_root
    root = repo_root()
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        stale, reason = is_stale(root)
        print(reason)
        return 1 if stale else 0
    if cmd == "refresh":
        print("projection refreshed" if refresh(root) else "projection unchanged")
        return 0
    print("usage: projection [check|refresh]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
