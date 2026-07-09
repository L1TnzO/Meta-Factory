#!/usr/bin/env python3
"""vendor_domain_gen.py — vendors the pinned Gradle wrapper into `domain_gen/` (s6, DES-8/MAT-2).

`domain_gen/` is a self-contained Gradle module DECOUPLED from `build/product/` (doesn't go through
`scaffold_product.py`) that exercises the LLM-generated domain logic under a contract test. It needs the
SAME vendored wrapper `build/product/` gets — single source `gradle_vendor.py` (FSK-S6-DOMAIN-GEN-VENDOR,
2026-07-09) — so `./gradlew run` exists once s6 activates for a product instance.

DETERMINISTIC (no LLM): the `via` of a `generate` build step whose sentinel is `domain_gen/gradlew`
(`skip_if_exists: true` ⇒ vendored ONCE, pinned; `ci --rederive` never re-copies, DES-1/I-3).

Uso: METAFACTORY_ROOT=<product root> python3 vendor_domain_gen.py
"""
from __future__ import annotations

import os
from pathlib import Path

from gradle_vendor import vendor_gradle_wrapper


def main() -> int:
    root = Path(os.environ.get("METAFACTORY_ROOT", ".")).resolve()
    out = root / "domain_gen"
    out.mkdir(parents=True, exist_ok=True)
    written = vendor_gradle_wrapper(out)
    print(f"vendor_domain_gen: {len(written)} archivos vendorizados en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
