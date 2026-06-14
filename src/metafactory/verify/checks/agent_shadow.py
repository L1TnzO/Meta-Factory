"""agent_shadow — M7's gate (I-12): toda prohibición que declara un agent de delegación tiene una
SOMBRA determinista (un hook/seed/CLI) que EXISTE y está CABLEADA, y el presupuesto de residencia
(CLAUDE.md ≤ N) es medible. Un contrato HUECO —un agent que dice apoyarse en una sombra que no está
instalada o es un hook muerto— es rojo. El juicio nunca se hard-blocka: solo se exige la PRESENCIA del
impedimento determinista (ADR-023, I-12). Espeja a M4/M5/M6: la ley/contenido lo instala M1; M7 agrega
el diente que lo hace no-decorativo.

Convención (la declara este gate). Cada `.claude/agents/<rol>.md` lleva en su frontmatter YAML:

    ---
    name: writer
    model: sonnet
    shadows:
      - prohibits: "no escribe veredictos en .proof/"
        shadow: ".claude/hooks/proof_protect.py"
      - prohibits: "no declara verde sin que el verifier compute passed"
        shadow: "seed/verifier.py"
    ---

El gate exige, por cada shadow: (1) el `shadow` (path relativo a la raíz de la fábrica) EXISTE; (2) si
es un hook (`.claude/hooks/*.py`) está referenciado en `.claude/settings.json` (cableado, no muerto).
Además: `CLAUDE.md` existe y mide ≤ `context_budget.claude_md_max_lines` de la factory-spec. El negativo
NO es decorativo: borrar el target de una sombra debe tirar el gate a rojo (si no, sería prosa).

Argv: <factory_root> <meta_root> [spec_path-rel]."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


def _parse_frontmatter(text: str) -> dict:
    """Extrae el frontmatter YAML (entre los dos primeros `---`). {} si no hay o no parsea."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    import yaml
    try:
        data = yaml.safe_load(text[3:end])
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _wired_hook_files(factory_root: Path) -> set[str]:
    """Nombres de archivo de hook referenciados en .claude/settings.json (los cableados)."""
    settings = factory_root / ".claude" / "settings.json"
    if not settings.exists():
        return set()
    try:
        blob = settings.read_text(encoding="utf-8")
        json.loads(blob)  # valida que sea JSON; la búsqueda es textual sobre el blob
    except (json.JSONDecodeError, OSError):
        return set()
    hooks_dir = factory_root / ".claude" / "hooks"
    return {p.name for p in hooks_dir.glob("*.py") if p.name in blob} if hooks_dir.exists() else set()


def _violations(factory_root: Path, claude_md_max: int) -> list[str]:
    """La ley del gate (única fuente): junta los problemas de sombras + presupuesto. Vacío == verde."""
    problems: list[str] = []
    agents_dir = factory_root / ".claude" / "agents"
    agents = sorted(agents_dir.glob("*.md")) if agents_dir.exists() else []
    if not agents:
        problems.append("harness sin agents: no hay .claude/agents/*.md (M7 hornea los contratos)")
        return problems

    wired = _wired_hook_files(factory_root)
    declared = 0
    for agent in agents:
        fm = _parse_frontmatter(agent.read_text(encoding="utf-8"))
        for entry in fm.get("shadows", []) or []:
            if not isinstance(entry, dict) or "shadow" not in entry:
                problems.append(f"{agent.name}: entrada de shadow malformada (falta `shadow`)")
                continue
            declared += 1
            shadow = str(entry["shadow"])
            target = factory_root / shadow
            if not target.exists():
                problems.append(f"{agent.name}: sombra inexistente para «{entry.get('prohibits', '?')}»: {shadow}")
                continue
            if shadow.replace("\\", "/").startswith(".claude/hooks/") and shadow.endswith(".py"):
                if Path(shadow).name not in wired:
                    problems.append(f"{agent.name}: la sombra {shadow} es un hook MUERTO (no está cableado en settings.json)")
    if declared == 0:
        problems.append("ningún agent declara `shadows`: el contrato I-12 no se puede verificar (sería prosa)")

    claude_md = factory_root / "CLAUDE.md"
    if not claude_md.exists():
        problems.append("falta CLAUDE.md (la residencia ≤ presupuesto, I-6)")
    else:
        n = len(claude_md.read_text(encoding="utf-8").splitlines())
        if n > claude_md_max:
            problems.append(f"CLAUDE.md mide {n} líneas > presupuesto {claude_md_max} (residencia, I-6)")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: agent_shadow <factory_root> <meta_root> [spec_path]", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()
    spec_rel = argv[2] if len(argv) > 2 else "factory.spec.yml"

    from ...spec.loader import load_spec

    spec = load_spec(factory_root / spec_rel)
    budget = int((spec.substrate.get("context_budget", {}) or {}).get("claude_md_max_lines", 120))

    # 1. la ley sobre la fábrica real: cero violaciones == verde.
    problems = _violations(factory_root, budget)
    if problems:
        print(f"HARNESS INCOMPLETO ({len(problems)}):")
        for p in problems[:6]:
            print(f"  - {p}")
        return 1

    # 2. NEGATIVO (no decorativo): en un clon hermético, borrar el target de UNA sombra debe tirar
    #    el gate a rojo. Si no cambia, la verificación de sombras no tiene dientes (sería prosa).
    tmp = Path(tempfile.mkdtemp(prefix="agent_shadow_"))
    try:
        clone = tmp / "f"
        shutil.copytree(factory_root, clone, ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"))
        # primera sombra declarada en el primer agent con sombras
        victim = None
        for agent in sorted((clone / ".claude" / "agents").glob("*.md")):
            fm = _parse_frontmatter(agent.read_text(encoding="utf-8"))
            shadows = [e for e in (fm.get("shadows", []) or []) if isinstance(e, dict) and e.get("shadow")]
            if shadows:
                victim = clone / str(shadows[0]["shadow"])
                break
        if victim is None or not victim.exists():
            print("NO VERIFICABLE: ningún agent declara una sombra con target existente para el negativo")
            return 1
        victim.unlink()
        if not _violations(clone, budget):
            print(f"GATE DECORATIVO: borrar la sombra {victim.name} NO tiró el gate a rojo (sin dientes)")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n_agents = len(list((factory_root / ".claude" / "agents").glob("*.md")))
    print(f"OK harness I-12: {n_agents} agent(s), toda sombra declarada existe y (si es hook) está "
          f"cableada; CLAUDE.md ≤ {budget}; borrar una sombra cae a rojo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
