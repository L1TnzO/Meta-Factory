#!/usr/bin/env python3
"""run_live.py — el DRIVER vivo de ASF: corre el PRODUCTO LangGraph contra un provider REAL (MAT-5).

Vive en la FÁBRICA (ADR-012): el sustrato del Meta-Factory no nombra ningún provider. Acá SÍ elegimos la
tech, pero MÍNIMA y sin sumar deps al venv del producto: el grafo llama `_get_llm().invoke([SystemMessage,
HumanMessage])` y lee `.content`, así que inyectamos (monkeypatch, como produce_output.py con el fake-LLM) un
adaptador stdlib `urllib` que habla el endpoint OpenAI-compatible declarado en el entorno (METAFACTORY_LLM_*).
NO se importa langchain-openai ni el SDK de ningún proveedor — el producto sigue provider-agnóstico (ADR-002).

Corre con el python del venv del PRODUCTO (langgraph + langchain-core ya instalados por s1). Lo llama el check
`live_run` SÓLO cuando el pin (live/live_output.json) NO existe y hay keys (§7). El output ACEPTADO se PINEA
(committeado) y `ci --rederive` lo re-verifica sin re-llamar al provider — el no-determinismo vive sólo acá.

MAT-6: el caso del gold trae una transcripción de entrevista REAL (dataset/example_conversation.txt) + una
instrucción de RE; el input del grafo es instrucción+transcripción y el producto RECUPERA los requisitos
funcionales (Agent_RE). El scorer mide el RECALL de esa recuperación contra los 28 requisitos que recuperaron
los expertos humanos (dataset/experts_final_requirements.txt) — un ground truth REAL.

Por cada caso del gold corre el grafo HASTA el interrupt (research+synthesize; human_review queda pendiente:
el HITL no-salteable a RUNTIME contra el modelo real), captura el draft y los findings, resume para el output
final, y construye los items de atribución vía el schema REAL del producto (OutputItem fuerza grounded=False
sin evidencia). Escribe live/live_output.json en el formato que leen el scorer y las propiedades."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # factory root
PRODUCT_SRC = ROOT / "build" / "product" / "src"
GOLD = ROOT / "live" / "gold.json"
OUT = Path(os.environ.get("METAFACTORY_LIVE_OUTPUT", str(ROOT / "live" / "live_output.json")))

BASE_URL = os.environ.get("METAFACTORY_LLM_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("METAFACTORY_LLM_API_KEY", "")
MODEL = os.environ.get("METAFACTORY_LLM_MODEL", "")

_ROLE = {"system": "system", "human": "user", "ai": "assistant"}


class _Resp:
    def __init__(self, content: str) -> None:
        self.content = content


class _DeepSeekLLM:
    """Adaptador stdlib: traduce los mensajes de LangChain a la API OpenAI-compatible y devuelve un objeto
    con `.content` (lo que el nodo del producto espera). Sin SDK de proveedor."""

    def invoke(self, messages: list) -> _Resp:
        msgs = [{"role": _ROLE.get(getattr(m, "type", "human"), "user"),
                 "content": getattr(m, "content", str(m))} for m in messages]
        body = json.dumps({"model": MODEL, "messages": msgs, "temperature": 0, "max_tokens": 3000}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
        return _Resp(data["choices"][0]["message"]["content"] or "")


def _content_tokens(text: str) -> set[str]:
    import re
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 4}


def _run_case(case: dict, graph_input: dict) -> dict:
    from agent_system.generated.attribution.schema import OutputItem
    from agent_system.generated.graph import nodes as _nodes
    from agent_system.generated.graph.topology import build_graph

    _nodes._get_llm.cache_clear()
    original = _nodes._get_llm
    setattr(_nodes, "_get_llm", lambda: _DeepSeekLLM())
    try:
        graph = build_graph()
        cfg = {"configurable": {"thread_id": f"live-{case['case_id']}"}}
        graph.invoke(graph_input, config=cfg)
        state = graph.get_state(cfg)
        reached_interrupt = "human_review" in (state.next or ())   # el grafo halló el interrupt no-salteable
        draft = str(state.values.get("draft", "") or "")
        findings = [str(f) for f in (state.values.get("findings", []) or [])]
        final = graph.invoke(None, config=cfg)                     # resume (aprobación humana simulada)
        answer = str(final.get("output", "") or "") or draft
    finally:
        setattr(_nodes, "_get_llm", original)

    # items de atribución vía el schema REAL: cada finding es su propia evidencia (grounded); el draft se
    # ancla a los findings que comparten tokens de contenido — si no comparte ninguno, el schema fuerza
    # grounded=False (el contrato de grounding ejercido sobre el output del modelo REAL).
    items: list[dict] = []
    for i, f in enumerate(findings):
        oi = OutputItem(content=f, grounded=True, confidence=0.8, evidence_ids=[f"finding-{i}"])
        items.append(oi.model_dump())
    draft_tokens = _content_tokens(answer)
    support = [f"finding-{i}" for i, f in enumerate(findings) if _content_tokens(f) & draft_tokens]
    draft_item = OutputItem(content=answer, grounded=True, confidence=0.7, evidence_ids=support)
    items.append(draft_item.model_dump())

    return {"case_id": str(case["case_id"]), "answer": answer, "draft": draft,
            "status": "DRAFT FOR VALIDATION", "reached_interrupt": bool(reached_interrupt),
            "findings": findings, "grounded_items": items}


def main() -> int:
    if not (BASE_URL and API_KEY and MODEL):
        print("run_live: faltan METAFACTORY_LLM_BASE_URL/API_KEY/MODEL en el entorno", file=sys.stderr)
        return 2
    if str(PRODUCT_SRC) not in sys.path:
        sys.path.insert(0, str(PRODUCT_SRC))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    results = []
    for case in gold:
        # MAT-6: el input del grafo se arma desde la instrucción de RE + la transcripción REAL (dataset/,
        # relativa al gold). El producto recupera los requisitos funcionales de la transcripción.
        transcript = (GOLD.parent / case["transcript_file"]).read_text(encoding="utf-8")
        graph_input = {"input_text": f"{case['instruction']}\n\nTRANSCRIPT:\n{transcript}"}
        try:
            results.append(_run_case(case, graph_input))
        except urllib.error.URLError as exc:
            print(f"run_live: error de red al provider en {case['case_id']}: {exc}", file=sys.stderr)
            return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"run_live: {len(results)} casos corridos VIVOS vs {MODEL} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
