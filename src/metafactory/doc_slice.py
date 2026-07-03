"""doc_slice — pull ONE section of a long `.md` doc instead of loading it whole.

Context-economy tool (INC-3 CONTEXT-LEAN-TEETH): a reader who only needs "§2.3" or
"the RBAC section" of a long spec/roadmap can ask for just that slice, or a bounded
2-line abstract + section map, instead of paying the full-doc token cost.

Convention assumed of the input markdown: the FIRST line MAY be an in-band seal
(`docs_manifest.SEAL_RE`, e.g. `<!-- meta:doc sha=... updated=... -->`) — always
excluded here. The `#` line is the doc TITLE, not a section. Sections are ATX
headings `##`/`###`/... and carry their number IN the heading text itself (e.g.
`## §1 · First`, `### 1.1 Sub one`) — there is no separate frontmatter for it.

Public API:
  section_map(text) -> str        one line per heading (## and deeper), indented
                                   by level.
  abstract(text) -> str           `#` title + first prose paragraph (<=2 lines) +
                                   the section map appended.
  slice(text, selector) -> str | None
                                   raw text of ONE matched section, from its heading
                                   up to (not incl.) the next heading of the SAME OR
                                   HIGHER level. Match order: (1) exact section
                                   number (leading `§` optional), (2) case-insensitive
                                   title substring. `None` if neither matches.
"""
from __future__ import annotations

import re

SEAL_RE = re.compile(r"^<!--\s*meta:doc\b.*-->\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
NUMBER_RE = re.compile(r"^§?\s*(\d+(?:\.\d+)*)\s*[·:\-]?\s*(.*)$")


def _parse_heading_text(rest: str) -> tuple[str | None, str]:
    """`rest` is the heading text after the `#`s. Returns (number|None, title)."""
    m = NUMBER_RE.match(rest)
    if m:
        return m.group(1), m.group(2).strip()
    return None, rest.strip()


def _headings(text: str) -> list[dict]:
    """All ATX headings of level >= 2 (sections), in document order. Each entry:
    {idx, level, number, title}. The seal line never matches (it isn't a `#` line);
    the `#` title line is level 1 and is filtered out here (not a section)."""
    heads: list[dict] = []
    for idx, line in enumerate(text.splitlines()):
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        if level < 2:
            continue
        number, title = _parse_heading_text(m.group(2))
        heads.append({"idx": idx, "level": level, "number": number, "title": title})
    return heads


def section_map(text: str) -> str:
    """One line per section heading, indented by level (deeper heading = more
    leading whitespace than its parent). Excludes the `#` title and the seal."""
    lines = []
    for h in _headings(text):
        indent = "  " * (h["level"] - 2)
        label = f"§{h['number']} {h['title']}" if h["number"] else h["title"]
        lines.append(f"{indent}{label}")
    return "\n".join(lines)


def abstract(text: str) -> str:
    """`#` title + first prose paragraph (non-empty, non-heading, non-seal text,
    capped at 2 lines) + the section map appended. Never includes the seal line."""
    lines = text.splitlines()
    title = ""
    title_idx = -1
    for idx, line in enumerate(lines):
        if SEAL_RE.match(line):
            continue
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            title = m.group(2).strip()
            title_idx = idx
            break

    prose: list[str] = []
    collecting = False
    for line in lines[title_idx + 1 :]:
        if SEAL_RE.match(line):
            continue
        if HEADING_RE.match(line):
            if collecting:
                break
            continue
        if not line.strip():
            if collecting:
                break
            continue
        collecting = True
        prose.append(line.strip())
        if len(prose) >= 2:
            break

    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    if prose:
        parts.append("")
        parts.extend(prose)
    parts.append("")
    parts.append(section_map(text))
    return "\n".join(parts)


def slice(text: str, selector: str) -> str | None:
    """Raw text of the ONE section matched by `selector`, from its heading line up
    to (not including) the next heading of the same-or-higher level. `selector` is
    tried first as a section number (leading `§` optional, exact match), then as a
    case-insensitive substring of the heading title. `None` if neither matches."""
    heads = _headings(text)
    sel = selector.strip()
    sel = sel[1:].strip() if sel.startswith("§") else sel

    matched = None
    for h in heads:
        if h["number"] is not None and h["number"] == sel:
            matched = h
            break
    if matched is None:
        sel_lower = sel.lower()
        for h in heads:
            if sel_lower in h["title"].lower():
                matched = h
                break
    if matched is None:
        return None

    lines = text.splitlines(keepends=True)
    start = matched["idx"]
    end = len(lines)
    for h in heads:
        if h["idx"] > start and h["level"] <= matched["level"]:
            end = h["idx"]
            break
    return "".join(lines[start:end])
