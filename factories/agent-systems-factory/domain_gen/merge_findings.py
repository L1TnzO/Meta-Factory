def merge_findings(findings: list[dict]) -> list[dict]:
    best_by_id: dict[str, dict] = {}
    for finding in findings:
        fid: str = finding["id"]
        current: dict | None = best_by_id.get(fid)
        if current is None or finding["confidence"] > current["confidence"]:
            best_by_id[fid] = finding
    return sorted(
        best_by_id.values(),
        key=lambda finding: finding["confidence"],
        reverse=True,
    )
