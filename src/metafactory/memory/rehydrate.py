"""rehydrate — SessionStart: inyecta el contexto mínimo de alto valor al arrancar una sesión.

Cierra el problema VIVIDO esta sesión: reiniciar perdía TODO el contexto residente, y el próximo
orquestador arrancaba a oscuras. Inyecta: incremento abierto + proyección de hechos + STATE «Ahora»
+ últimos eventos del journal + frescura de docs (sello ADR-009). Registra qué inyectó (medición).
NO reemplaza leer: triaja y orienta hacia `meta recall`/`meta check` (re-verificar > recordar).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..docs_manifest import SEAL_RE, body_of, doc_set, split_seal
from . import journal
from .projection import current_block, open_increment


def _state_now(root: Path) -> list[str]:
    state = root / "docs" / "STATE.md"
    if not state.exists():
        return []
    body = body_of(state.read_text(encoding="utf-8"))
    m = re.search(r"^## Ahora.*?(?=\n## )", body, re.DOTALL | re.MULTILINE)
    sect = m.group(0) if m else ""
    return [ln for ln in sect.splitlines() if ln.strip()][:11]


def _fresh_docs(root: Path, n: int = 4) -> list[str]:
    items: list[tuple[str, str]] = []
    for d in doc_set(root):
        seal, _ = split_seal(d.read_text(encoding="utf-8"))
        m = SEAL_RE.match(seal) if seal else None
        if m:
            items.append((m.group(2), str(d.relative_to(root))))
    items.sort(reverse=True)
    return [f"{rel} ({ts})" for ts, rel in items[:n]]


def build_payload(root: Path, session: str = "") -> str:
    root = Path(root)
    lines = ["=== Meta-Factory · rehidratación de memoria (SessionStart) ==="]
    lines.append(f"Incremento abierto: {open_increment(root) or 'ninguno'}")
    blk = current_block(root)
    if blk:
        lines += ["Proyección " + ln for ln in blk.splitlines() if ln.startswith("- ")]
    now = _state_now(root)
    if now:
        lines.append("STATE «Ahora»:")
        lines += ["  " + ln for ln in now]
    evs = journal.read(root, limit=5)
    if evs:
        lines.append("Últimos hechos (journal):")
        for e in evs:
            tag = e.get("station") or e.get("query") or e.get("subagent_type") or ""
            lines.append(f"  {e['ts']} {e['kind']} {tag}")
    fresh = _fresh_docs(root)
    if fresh:
        lines.append("Docs frescos (sello ADR-009): " + " · ".join(fresh))
    lines.append("Orientación: `meta check` (re-verificar > recordar) · "
                 "`meta recall <tema>` (rebanada) · `meta checkpoint` (narrar hechos sin narrar)")
    payload = "\n".join(lines)
    journal.append(root, "session_start", session=session, injected=len(lines))
    return payload
