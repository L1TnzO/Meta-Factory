"""journal — Tier 0 memoria de HECHOS (eventos). Append-only JSONL, gitignored, regenerable.

Cero modelo: file-IO + aritmética. Lo escribe el ENGINE al-momento (captura continua at-source),
no un checkpoint discrecional — la lección vivida: los checkpoints se saltean, los hechos no deben.
Es la RED DE SEGURIDAD: si la generación se corta, los hechos quedan aunque la narrativa esté vieja.

Eventos (kind):
  station_run  {station, slug, passed, gate_open, proof_sha}   ← el engine, en cada gate
  delegation   {subagent_type, model, description}              ← captura de subagentes
  recall       {query, n, refs}                                 ← RETIRADO (ADR-019 §2): ya no se escribe;
                                                                  la serie histórica se LEE (la medición vive, T0)
  session_start{session, injected}                              ← qué inyectó la rehidratación
  note         {text}                                           ← anotación manual ocasional
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

MEMDIR = ".metamem"


def now() -> str:
    # segundo de precisión: es telemetría de máquina, no marca narrativa (que es al minuto)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal_path(root: Path) -> Path:
    return Path(root) / MEMDIR / "journal.jsonl"


def append(root: Path, kind: str, **fields) -> dict:
    """Anexa un evento. Best-effort: la captura de memoria nunca debe romper la línea (si el
    disco falla, el gate ya es la autoridad). Devuelve el registro escrito."""
    rec = {"ts": now(), "kind": kind, **fields}
    try:
        p = journal_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return rec


def read(root: Path, *, kinds: set[str] | None = None, limit: int | None = None) -> list[dict]:
    p = journal_path(root)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if kinds and rec.get("kind") not in kinds:
            continue
        out.append(rec)
    return out[-limit:] if limit else out


def latest(root: Path, kind: str) -> dict | None:
    evs = read(root, kinds={kind})
    return evs[-1] if evs else None
