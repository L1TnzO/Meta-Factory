"""PF-6 isolation (criterion 7): the Meta-Factory machinery must not depend on any
produced factory. A factory is a product; the platform never imports its products."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "metafactory"


def test_no_static_import_of_factories():
    bad = []
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if re.search(r"^\s*(from|import)\s+factories(\.|\s|$)", text, re.MULTILINE):
            bad.append(str(py))
    assert not bad, f"metafactory statically imports factories: {bad}"


def test_no_generation_tech_in_substrate():
    """ADR-012/013 guard: the substrate names NO generation/domain tech. Generation happens via
    a generator DECLARED IN DATA (`generate`'s `via`), never an `import` baked into `src/`. If a
    stack package is imported here, the platform got opinionated to a stack (the G-2 of ASF, a
    level up). New domains add data (a `via`), not a substrate dependency."""
    techs = ("copier", "cookiecutter", "jinja2", "mako", "genshi",
             "langgraph", "langchain", "llama_index", "openai", "anthropic")
    pat = re.compile(rf"^\s*(from|import)\s+({'|'.join(techs)})(\.|\s|$)", re.MULTILINE)
    bad = [str(py) for py in SRC.rglob("*.py") if pat.search(py.read_text(encoding="utf-8"))]
    assert not bad, f"substrate imports generation/domain tech (must be `via` data, ADR-012): {bad}"


def test_importing_metafactory_does_not_load_a_factory():
    for name in (
        "metafactory", "metafactory.cli", "metafactory.engine",
        "metafactory.spec", "metafactory.verify", "metafactory.codegen",
        "metafactory.docs_manifest",
    ):
        __import__(name)
    leaked = [
        (n, getattr(m, "__file__", ""))
        for n, m in list(sys.modules.items())
        if getattr(m, "__file__", None) and "/factories/" in m.__file__.replace("\\", "/")
    ]
    assert not leaked, f"metafactory imported factory modules: {leaked}"
