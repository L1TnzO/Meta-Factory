"""metafactory — Stage 1 machinery (auto-mejorable bajo la columna).

Domain-agnostic engine that runs a line of stations-as-data (I-2) under the frozen
seed's anti-rubber-stamp column (Stage 0). Builds factories from a factory-spec (SDD).
The trust root is `seed/verifier.py`, loaded via `metafactory._seed`; this package
never re-implements the verdict computation.
"""

__all__ = ["__version__"]
__version__ = "0.1.0-bootstrap"
