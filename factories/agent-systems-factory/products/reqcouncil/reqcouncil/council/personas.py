"""Persona prompt loader (docs/design/01 §5): versioned files, referenced by sha.

An analyst's system prompt = its charter file + the SHARED output contract
(`personas/_output_contract.md`) — one contract, zero drift between analysts. Every
loaded prompt returns its sha12 so `run.json` pins exactly what each persona saw.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PERSONAS_DIR = Path(__file__).with_name("personas")
OUTPUT_CONTRACT = "_output_contract.md"
OBJECTION_CONTRACT = "_objection_contract.md"
REBUTTAL_CONTRACT = "_rebuttal_contract.md"
GAP_HUNTER = "gap_hunter"  # the one critic that emits CANDIDATES (design/01 §1.2)


@dataclass(frozen=True)
class Persona:
    name: str
    system_prompt: str
    sha: str  # sha256[:12] of the FULL system prompt (charter + shared contract)


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def load_analyst(name: str, personas_dir: Path | None = None) -> Persona:
    base = personas_dir or PERSONAS_DIR
    charter = (base / f"{name}.md").read_text(encoding="utf-8").strip()
    contract = (base / OUTPUT_CONTRACT).read_text(encoding="utf-8").strip()
    prompt = f"{charter}\n\n{contract}"
    return Persona(name=name, system_prompt=prompt, sha=_sha12(prompt))


def load_synthesizer(personas_dir: Path | None = None) -> Persona:
    base = personas_dir or PERSONAS_DIR
    prompt = (base / "synthesizer.md").read_text(encoding="utf-8").strip()
    return Persona(name="synthesizer", system_prompt=prompt, sha=_sha12(prompt))


def load_analysts(names: list[str], personas_dir: Path | None = None) -> list[Persona]:
    return [load_analyst(n, personas_dir) for n in names]


def load_critic(name: str, personas_dir: Path | None = None) -> Persona:
    """Critic = charter + the contract its OUTPUT obeys (design/01 §1.2).

    gap_hunter emits candidates, so it shares the analysts' output contract; the
    objection critics share the objection contract. One contract each, zero drift.
    """
    base = personas_dir or PERSONAS_DIR
    charter = (base / f"{name}.md").read_text(encoding="utf-8").strip()
    contract_file = OUTPUT_CONTRACT if name == GAP_HUNTER else OBJECTION_CONTRACT
    contract = (base / contract_file).read_text(encoding="utf-8").strip()
    prompt = f"{charter}\n\n{contract}"
    return Persona(name=name, system_prompt=prompt, sha=_sha12(prompt))


def load_critics(names: list[str], personas_dir: Path | None = None) -> list[Persona]:
    return [load_critic(n, personas_dir) for n in names]


def load_rebuttal(owner: str, personas_dir: Path | None = None) -> Persona:
    """The owning persona answering objections: its charter + the rebuttal contract."""
    base = personas_dir or PERSONAS_DIR
    charter = (base / f"{owner}.md").read_text(encoding="utf-8").strip()
    contract = (base / REBUTTAL_CONTRACT).read_text(encoding="utf-8").strip()
    prompt = f"{charter}\n\n{contract}"
    return Persona(name=f"{owner}:rebuttal", system_prompt=prompt, sha=_sha12(prompt))
