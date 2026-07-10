"""Diente dos-lados de codegen_freeze (ADR-023 §3, CODEGEN-FREEZE-TOOTH): el freeze del codegen de
templates tiene sombra determinista. Se testea la LEY PURA (`evaluate`/`parse_waivers`) con entradas
sintéticas — sin git, sin IO: los mismos escenarios que el lado RED in-process del check, más los
bordes (waiver malformado, alcance inválido, sin-incremento)."""
from __future__ import annotations

import metafactory.verify.checks.codegen_freeze as CF

_DIFF = ["factories/x/codegen/emit.py"]
_WAIVER_VERIF = ("Codegen-freeze-waiver: alcance=verificacion · motivo: cablear cobertura del proof · "
                 "cita: ADR-023 §1")
_WAIVER_SUP = ("Codegen-freeze-waiver: alcance=superficie · motivo: evolución deliberada del template · "
               "cita: ADR-031")


class TestLaw:
    def test_clean_no_diff_no_waiver(self):
        assert CF.evaluate([], "X-INCREMENT.md", "# doc normal") == []
        assert CF.evaluate([], None, None) == []

    def test_diff_without_open_increment_flags(self):
        probs = CF.evaluate(_DIFF, None, None)
        assert len(probs) == 1 and "SIN incremento abierto" in probs[0]

    def test_diff_without_waiver_flags(self):
        probs = CF.evaluate(_DIFF, "X-INCREMENT.md", "# doc sin waiver")
        assert len(probs) == 1 and "SIN waiver" in probs[0] and "ADR-023" in probs[0]

    def test_diff_with_valid_waiver_passes_both_alcances(self):
        assert CF.evaluate(_DIFF, "X-INCREMENT.md", _WAIVER_VERIF) == []
        assert CF.evaluate(_DIFF, "X-INCREMENT.md", _WAIVER_SUP) == []

    def test_waiver_without_diff_flags_decorative(self):
        probs = CF.evaluate([], "X-INCREMENT.md", _WAIVER_VERIF)
        assert len(probs) == 1 and "decorativo" in probs[0]


class TestWaiverForm:
    def test_malformed_missing_cita_flags(self):
        probs = CF.evaluate(_DIFF, "X.md", "Codegen-freeze-waiver: alcance=verificacion · motivo: x")
        assert len(probs) == 1 and "MALFORMADO" in probs[0] and "cita" in probs[0]

    def test_malformed_bad_alcance_flags_even_without_diff(self):
        # Un waiver malformado nunca se ignora en silencio (ni siquiera con ventana limpia).
        probs = CF.evaluate([], "X.md", "codegen-freeze-waiver: alcance=todo · motivo: x · cita: ADR-023")
        assert len(probs) == 1 and "MALFORMADO" in probs[0] and "alcance" in probs[0]

    def test_parse_counts_and_case_insensitive(self):
        text = _WAIVER_VERIF + "\nprosa normal\n" + _WAIVER_SUP.upper()
        valid, problems = CF.parse_waivers(text)
        assert valid == 2 and problems == []


class TestToothAlive:
    def test_red_side_scenarios_bite(self):
        # El mismo invariante que corre in-process en el gate: si esto falla, el diente es decorativo.
        assert CF._tooth_alive() == []
