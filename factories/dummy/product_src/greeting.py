"""Producto trivial de la fábrica dummy: un módulo que DEBE portar el marcador invariante.

Es la pieza de dominio que la fábrica fabrica. El sustrato (columna, gate, bus) la rodea de
garantías. Si el marcador se corrompe, la columna lo detecta por bloqueo (no por prosa)."""

MARKER = "DUMMY_OK"


def greet() -> str:
    return MARKER
