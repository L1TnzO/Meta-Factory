"""Dominio (HUMANO) de la fábrica full-stack: el módulo de producto que porta el marcador invariante.

Es la pieza que el ingeniero edita. La frontera I-5 la protege: rendererizada con skip_if_exists,
SOBREVIVE un re-scaffold (un `meta station m04` no la pisa). El sustrato (columna, gate, bus) la
rodea de garantías; si el marcador se corrompe, la columna lo detecta por bloqueo (no por prosa)."""

MARKER = "WEBAPP_OK"


def marker() -> str:
    return MARKER
