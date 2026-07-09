#!/usr/bin/env python3
"""gradle_vendor.py — single source for vendoring the PINNED Gradle wrapper (`codegen/assets/gradle/`,
DES-1) into a destination tree. Extracted from `scaffold_product.py` (FSK-S6-DOMAIN-GEN-VENDOR,
2026-07-09) so a SECOND self-contained Gradle module — `domain_gen/` (s6, DES-8/MAT-2) — can vendor the
SAME pinned wrapper without duplicating the copy loop (single source, no drift between consumers).

Lives in the FACTORY (ADR-012): the substrate `src/metafactory/` names no Gradle/Kotlin."""
from __future__ import annotations

import shutil
from pathlib import Path


def assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / "gradle"


def vendor_gradle_wrapper(out: Path) -> list[str]:
    """Copy the pinned wrapper (binary + scripts) VERBATIM into `out`. Returns the sorted list of
    paths written (relative to `out`). `gradlew` gets +x (the script itself, not `gradlew.bat`)."""
    assets = assets_dir()
    written: list[str] = []
    for src in sorted(assets.rglob("*")):
        if src.is_file():
            rel = "/".join(src.relative_to(assets).parts)
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            if dest.name == "gradlew":
                dest.chmod(0o755)
            written.append(rel)
    return sorted(written)
