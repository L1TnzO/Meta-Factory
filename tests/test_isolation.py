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
