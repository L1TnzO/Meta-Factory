"""codegen — the deterministic build side of a meta-station (renders the template
chassis into a factory). Lo creativo (qué fabrica) es dato del spec; lo invariante
(cómo se cablea) es este código (I-3, frontera del determinismo)."""
from .renderer import apply_builds, render_text

__all__ = ["apply_builds", "render_text"]
