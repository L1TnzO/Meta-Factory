"""memory — el subsistema de memoria (3 tiers).

  Tier 0 (hechos, determinista, cero modelo): `journal` (eventos) + `metrics` (series).
  Tier 1 (significado): docs tipados (fuera de este paquete) + `projection` (proyección
          determinista de hechos a STATE) y `checkpoint` (el disparador no-discrecional).
  Tier 2 (recuperación medida): `recall` (rebanada dirigida) + `rehydrate` (SessionStart).

Frontera: la fuente de verdad son docs+git (portable). Todo lo de acá es caché derivado,
gitignored, regenerable; NUNCA la autoridad. La cura de la staleness es re-verificar, no recordar.
"""
from . import journal

__all__ = ["journal"]
