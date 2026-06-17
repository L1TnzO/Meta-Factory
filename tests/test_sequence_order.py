"""La línea ordena las estaciones por orden NATURAL (numérico), no lexicográfico — así una línea con ≥10
estaciones corre s9 ANTES de s10 (lexicográfico encajaría s10 entre s1 y s2 y lo correría antes de su
requires_prev). Idéntico para s0..s9 y m00..m08 (no cambia ninguna línea existente). I-2: el orden sigue
siendo función determinista de los ids en disco. Surfaceado por MAT-5 (ASF gana una 10ª estación, s10)."""
from __future__ import annotations

from metafactory.engine.sequence import Sequence, _natural_key, load_sequence
from metafactory.engine.station import Station


def _seq(*ids: str) -> Sequence:
    return Sequence([Station.from_dict({"id": i}) for i in ids])


def test_two_digit_station_sorts_after_single_digits():
    seq = Sequence(sorted([Station.from_dict({"id": i}) for i in ["s10", "s1", "s2", "s9", "s0"]],
                          key=lambda s: _natural_key(s.id)))
    assert seq.ids() == ["s0", "s1", "s2", "s9", "s10"]


def test_single_digit_lines_are_unchanged():
    """s0..s9 order identically under natural and lexicographic — existing factories don't move."""
    key = lambda s: _natural_key(s.id)  # noqa: E731
    sts = [Station.from_dict({"id": f"s{n}"}) for n in (3, 0, 7, 1)]
    assert [s.id for s in sorted(sts, key=key)] == ["s0", "s1", "s3", "s7"]


def test_zero_padded_meta_stations_unchanged():
    sts = [Station.from_dict({"id": i}) for i in ["m08", "m00", "m02", "m07"]]
    assert [s.id for s in sorted(sts, key=lambda s: _natural_key(s.id))] == ["m00", "m02", "m07", "m08"]


def test_load_sequence_orders_naturally(tmp_path):
    for i in ["s0", "s1", "s2", "s10", "s4"]:
        (tmp_path / f"{i}.yml").write_text(f"id: {i}\nactivation: always\n", encoding="utf-8")
    assert load_sequence(tmp_path).ids() == ["s0", "s1", "s2", "s4", "s10"]
