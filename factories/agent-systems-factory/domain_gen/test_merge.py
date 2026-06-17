from merge_findings import merge_findings


def test_dedup_keeps_highest_confidence_sorted_desc():
    findings = [
        {"id": "A", "confidence": 0.5, "text": "a1"},
        {"id": "B", "confidence": 0.9, "text": "b1"},
        {"id": "A", "confidence": 0.8, "text": "a2"},
    ]
    out = merge_findings(findings)
    assert [f["id"] for f in out] == ["B", "A"]
    assert [f["confidence"] for f in out] == [0.9, 0.8]
    assert out[1]["text"] == "a2"  # conservó el de MAYOR confianza, no el primero


def test_empty():
    assert merge_findings([]) == []
