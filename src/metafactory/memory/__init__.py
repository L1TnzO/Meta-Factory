"""memory — el subsistema de memoria (3 tiers).

  Tier 0 (hechos, determinista, cero modelo): `journal` (eventos) + `metrics` (series).
  Tier 1 (significado): docs tipados (fuera de este paquete) + `projection` (proyección
          determinista de hechos a STATE) y `checkpoint` (el disparador no-discrecional).
  Tier 2 (recuperación): `rehydrate` (SessionStart). `recall` se RETIRÓ (ADR-019 §2, M2): se midió
          1×/0-hit — redundante con Grep/Read, que ES la superficie de retrieval (Letta). La cura de
          la staleness es re-verificar (`meta check`), no recordar; el retrieval directo es Grep/Read.

Frontera: la fuente de verdad son docs+git (portable). Todo lo de acá es caché derivado,
gitignored, regenerable; NUNCA la autoridad. La cura de la staleness es re-verificar, no recordar.
"""
from . import journal

__all__ = ["journal"]
