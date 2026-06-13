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

START = "<!-- meta:projection (generado de hechos; NO editar a mano, se refresca con `meta checkpoint`) -->"
END = "<!-- /meta:projection -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)


def open_increment(root: Path) -> str | None:
    workdir = Path(root) / "docs" / "work"
    if not workdir.exists():
        return None
    for p in sorted(workdir.glob("*.md")):
        m = re.search(r"Estado:\s*\*\*(ABIERTO|CERRADO)\*\*", p.read_text(encoding="utf-8"))
        if m and m.group(1) == "ABIERTO":
            return p.name
    return None


def rtm_status(root: Path) -> list[str]:
    """Re-deriva el RTM de cada fábrica producida desde artefactos (.proof) — cero narrativa."""
    from ..engine.run_context import RunContext
    from ..spec import load_spec

    out: list[str] = []
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
        out.append(f"{spec.slug}: {status} ({total - unsat}/{total})")
    return out


def build_block(root: Path) -> str:
    inc = open_increment(root) or "ninguno"
    rtm = rtm_status(root)
    return "\n".join([
        START,
        "> Proyección de hechos (Tier 0 → STATE). Fuente: artefactos re-derivables; no es narrativa.",
        f"- Incremento abierto: {inc}",
        f"- RTM por fábrica (re-derivado de `.proof/`): {' · '.join(rtm) if rtm else 'sin fábricas'}",
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
        return True, "docs/STATE.md:1: falta el bloque de proyección (corré `meta checkpoint`)"
    if cur.strip() != fresh.strip():
        return True, "docs/STATE.md:1: la proyección está vieja respecto de los hechos (corré `meta checkpoint`)"
    return False, "ok"


def refresh(root: Path) -> bool:
    """Reescribe el bloque en STATE.md (lo inserta antes del primer `## ` si falta).
    Devuelve True si cambió. NO re-sella (lo hace el caller con doc-sync)."""
    state = Path(root) / "docs" / "STATE.md"
    text = state.read_text(encoding="utf-8")
    fresh = build_block(root)
    if BLOCK_RE.search(text):
        new = BLOCK_RE.sub(lambda _m: fresh, text)
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
