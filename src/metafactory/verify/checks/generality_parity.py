"""generality_parity — ADR-014's tooth: NINGÚN mecanismo de sustrato se promueve probado en un solo dominio.

Un *mecanismo de sustrato* (un `kind` de check del registry o una build `action`: capacidad de
generación/verificación/gating en `src/metafactory|seed`) declara su promoción en `docs/reference/parity.yml`
(el libro de promoción). `status: prototype` = exploración en un dominio (permitida, ADR-014 §2) -> NO gatea.
`status: general` = PROMOVIDO -> este check lo VERIFICA y cae a rojo si el claim no se sostiene:

  1. <2 fábricas declaradas prueban el mecanismo VERDE (proof recomputado con `gate_recompute_ok`, no un
     `passed:true` rancio/editado a mano), o
  2. ninguna pareja entre las que lo prueban es RADICALMENTE DISTINTA (ADR-014 §3): lenguaje de producto
     DISJUNTO (canon de los `toolchain:` de los `proof_checks` `runs_in: product_env`; pytest/mypy/venv ->
     python) Y mezcla de primitivas (`capabilities[].primitive`, DES-x) distinta.

Extiende —no reemplaza— el guard de ADR-012 (`tests/test_isolation.py`: cero tokens de tech de generación en
`src/`): aquél prohíbe hornear la tech; éste prohíbe DECLARAR general lo probado en un solo dominio. La
narrativa declara (el manifiesto), el código garantiza (este exit code) — SAFE-6.

El mapa lenguaje↔token de abajo son STRINGS de verificación, no imports: no viola ADR-012 (es config de
gating dominio-agnóstica, no una dependencia de stack). Token desconocido => él mismo (conservador).

Argv: [meta_root=.] [manifest=<meta_root>/docs/reference/parity.yml]."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# ADR-014 §3, operacional: dos dominios son "radicalmente distintos" sii NO comparten LENGUAJE de producto.
# Cada token de un `toolchain:` declarado se canoniza a un lenguaje con esta tabla (verificación, no
# generación). Sin ella, dummy{python,venv,unittest} y ASF{pytest,mypy} parecerían distintos siendo ambos
# Python — un falso verde. Una fábrica de un lenguaje nuevo agrega sus tokens acá (config, no `if` por-tech).
_LANG = {
    "python": "python", "pytest": "python", "unittest": "python", "mypy": "python",
    "pip": "python", "venv": "python", "poetry": "python", "ruff": "python", "tox": "python",
    "typescript": "ts", "tsc": "ts", "ts": "ts", "vitest": "ts", "jest": "ts", "vite": "ts",
    "npm": "ts", "npx": "ts", "node": "ts", "eslint": "ts", "playwright": "ts", "pnpm": "ts",
    "go": "go", "gofmt": "go", "cargo": "rust", "rust": "rust", "rustc": "rust",
    "gradle": "jvm", "maven": "jvm", "kotlin": "jvm", "swift": "swift",
    "flutter": "dart", "dart": "dart", "protoc": "proto", "qemu": "embedded",
}


def _canon_lang(token: str) -> str:
    return _LANG.get(token.lower(), token.lower())


def _stations(spec: dict) -> list[dict]:
    return ((spec.get("domain") or {}).get("station_sequence") or [])


def _language_set(spec: dict) -> set[str]:
    """Los lenguajes de PRODUCTO de la fábrica: canon de los tokens de cada `toolchain:` de los proof_checks
    que corren en el toolchain del producto (`runs_in: product_env`). Los `factory_env` (toolchain del
    sustrato, p.ej. `metafactory`) se excluyen — §3 habla del toolchain DEL PRODUCTO."""
    langs: set[str] = set()
    for st in _stations(spec):
        for pc in (st.get("proof_checks") or []):
            if pc.get("runs_in") != "product_env":
                continue
            for tok in re.split(r"[^A-Za-z0-9]+", str(pc.get("toolchain", ""))):
                if tok:
                    langs.add(_canon_lang(tok))
    return langs


def _primitive_set(spec: dict) -> set[str]:
    """La mezcla de primitivas de DISEÑO (DES-x) que la fábrica ejerce, de `capabilities[].primitive`."""
    caps = ((spec.get("domain") or {}).get("capabilities") or [])
    return {str(c["primitive"]) for c in caps if c.get("primitive")}


def _stations_using(spec: dict, mechanism: str) -> list[str]:
    """Ids de estaciones cuyo `checks[].kind` o `builds[].action` ES el mecanismo (lo EJERCEN)."""
    ids: list[str] = []
    for st in _stations(spec):
        kinds = {c.get("kind") for c in (st.get("checks") or [])}
        actions = {b.get("action") for b in (st.get("builds") or [])}
        if mechanism in kinds or mechanism in actions:
            ids.append(str(st.get("id")))
    return ids


def _proves_green(verifier, factory_root: Path, station_ids: list[str]) -> bool:
    """True sii alguna de esas estaciones tiene un proof que RECOMPONE verde (Lock #2: un passed:true
    editado a mano no cuela). No re-ejecuta los comandos (eso es el external_ci); recompone el veredicto."""
    for sid in station_ids:
        proof = verifier.load_proof(factory_root, sid)
        if proof is None:
            continue
        if verifier.gate_recompute_ok(proof)[0]:
            return True
    return False


def _radically_distinct(spec_a: dict, spec_b: dict) -> tuple[bool, str]:
    """ADR-014 §3: lenguaje de producto DISJUNTO Y mezcla de primitivas distinta. Ambas condiciones."""
    la, lb = _language_set(spec_a), _language_set(spec_b)
    if not la or not lb:
        return False, f"sin toolchain de producto declarado en alguna ({la or '∅'} / {lb or '∅'})"
    if la & lb:
        return False, f"mismo lenguaje de producto {sorted(la & lb)} (no ejerce la generalidad, §3)"
    pa, pb = _primitive_set(spec_a), _primitive_set(spec_b)
    if pa == pb:
        return False, f"misma mezcla de primitivas {sorted(pa) or '∅'} (§3 exige toolchain Y primitivas distintas)"
    return True, f"lenguajes {sorted(la)}≠{sorted(lb)} y primitivas distintas"


def _load_spec(meta_root: Path, slug: str) -> dict | None:
    """La spec AUTORITATIVA de una fábrica es la REGISTRADA (`factories/<slug>/factory.spec.yml`): es la
    que materializó la línea cuyos `.proof/` audita este check. La de `specs/` es la de autoría (puede
    quedar atrás de la registrada). Fallback a `specs/` si la fábrica no está registrada."""
    for path in (meta_root / "factories" / slug / "factory.spec.yml",
                 meta_root / "specs" / f"{slug}.factory.spec.yml"):
        if path.exists():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return None


def _audit_general(verifier, meta_root: Path, entry: dict) -> tuple[bool, str]:
    """Verifica un claim `general`. Devuelve (ok, razón). Rojo si <2 dominios verdes o ningún par distinto."""
    mech = entry.get("mechanism")
    domains = list(entry.get("domains") or [])
    specs: dict[str, dict] = {}
    green: list[str] = []
    for slug in domains:
        spec = _load_spec(meta_root, slug)
        if spec is None:
            continue
        specs[slug] = spec
        if _proves_green(verifier, meta_root / "factories" / slug, _stations_using(spec, mech)):
            green.append(slug)
    if len(green) < 2:
        return False, (f"mecanismo {mech!r} es `general` pero sólo {green or 'ninguna'} fábrica(s) lo "
                       f"prueban verde (ADR-014 §2 exige ≥2)")
    for i in range(len(green)):
        for j in range(i + 1, len(green)):
            ok, why = _radically_distinct(specs[green[i]], specs[green[j]])
            if ok:
                return True, f"{mech!r}: {green[i]} ⟂ {green[j]} ({why})"
    return False, (f"mecanismo {mech!r} es `general` pero ningún par entre {green} es radicalmente distinto "
                   f"(falso verde, ADR-014 §3): toolchain/primitivas no difieren")


def main(argv: list[str]) -> int:
    meta_root = Path(argv[0]).resolve() if argv else Path.cwd()
    manifest = Path(argv[1]) if len(argv) > 1 else meta_root / "docs" / "reference" / "parity.yml"
    if not manifest.exists():
        print(f"OK generality_parity: no hay manifiesto de paridad ({manifest}); nada que verificar (N/A)")
        return 0
    try:
        from ..._seed import load_seed_verifier
        verifier = load_seed_verifier(str(meta_root))
    except Exception as exc:  # pragma: no cover - el seed siempre está; defensivo
        print(f"generality_parity: no pude cargar el seed verifier: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    mechs = data.get("mechanisms") or []
    general = [m for m in mechs if m.get("status") == "general"]
    proto = [m for m in mechs if m.get("status") == "prototype"]

    problems: list[str] = []
    proven: list[str] = []
    for entry in general:
        ok, why = _audit_general(verifier, meta_root, entry)
        (proven if ok else problems).append(why)

    if problems:
        print(f"GENERALITY_PARITY ROJO ({len(problems)} claim(s) de generalidad sin sostén):")
        for p in problems:
            print(f"  ✗ {p}")
        print("  -> probalo en un 2º dominio radicalmente distinto, o devolvelo a `prototype` (ADR-014 §2).")
        return 1

    print(f"OK generality_parity: {len(general)} mecanismo(s) `general` con paridad de dos dominios verde, "
          f"{len(proto)} en `prototype` (exploración, ADR-014 §2).")
    for p in proven:
        print(f"  ✓ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
