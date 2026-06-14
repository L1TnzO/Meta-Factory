"""clean_runner — M6's gate (I-11, PF-10): the two-verifier doctrine is NOT decorative.

Criterion 3 of M4-M7: a CLEAN runner reconstructs the factory's product line FROM SOURCE and
DEMANDS the pinned verdict. Match -> green; any deviation (un proof_sha re-derivado distinto O un
pin distinto) -> red. A spontaneous PASS without proof is a façade, not a win — and a compromised
local Meta-Factory yields a proof_sha the clean re-derivation does not reproduce (SELF-IMPROVEMENT
§1, trusting-trust defense of self-improvement).

It re-derives in a THROWAWAY CLONE of the factory (sin `.proof/`/`build/`, como un checkout fresco):
custody is never the root of trust — replicability is. The real factory's `.proof/` (its meta-station
proofs) is never touched, so this gate composes inside the meta line without wiping its predecessors.

Reuses the ONE re-derivation law (`cli.rederive_pinned` + `cli._compare_to_pinned`), so the gate
cannot diverge from `meta ci --rederive` or `seed/external_ci.yml` (ADR-005 §4). The negative is
NON-decorative: against the freshly re-derived proofs, a TAMPERED pinned must yield a mismatch — if
it does not, the comparison has no teeth and the gate is prosa (red).

Argv: <factory_root> <meta_root> [spec_path-rel]."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: clean_runner <factory_root> <meta_root> [spec_path]", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()
    spec_rel = argv[2] if len(argv) > 2 else "factory.spec.yml"

    from ...cli import _compare_to_pinned, rederive_pinned
    from ...engine import RunContext
    from ...spec.loader import load_spec

    pinned_path = factory_root / "pinned_verdict.json"
    if not pinned_path.exists():
        print(f"SIN PINEAR: no hay pinned_verdict.json en {factory_root.name} (corré `meta pin`)")
        return 1
    pinned = json.loads(pinned_path.read_text(encoding="utf-8"))
    if not pinned:
        print("PINEADO VACÍO: pinned_verdict.json no pinea ninguna estación (nada que re-derivar)")
        return 1

    slug = load_spec(factory_root / spec_rel).slug

    tmp = Path(tempfile.mkdtemp(prefix="clean_runner_"))
    try:
        # 1. CLON LIMPIO: copiá la fuente committeada (spec, stations, domain, generated, seed,
        #    pinned) SIN el estado re-derivable (.proof/, build/) — un checkout fresco no los trae.
        clone = tmp / "factory"
        shutil.copytree(factory_root, clone,
                        ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"))

        # 2. RE-DERIVACIÓN: reconstruí la línea de producto desde la fuente y exigí el pineado.
        #    record_active=False: la re-derivación hermética no contamina el active.json/journal meta.
        ok, mismatches, rc, has_pinned = rederive_pinned(clone, meta_root, slug, record_active=False)
        if not has_pinned:                      # defensivo: el clon SÍ trae el pinned (copytree)
            print("SIN PINEAR: el clon no preservó pinned_verdict.json")
            return 1
        if not ok:
            if rc != 0:
                print(f"RUNNER LIMPIO ROJO: la línea de producto NO reconstruye en árbol limpio (rc={rc}) "
                      f"— producto roto en la fuente")
            else:
                print("VEREDICTO DESVIADO: el re-derivado limpio NO coincide con el pineado: "
                      + "; ".join(mismatches[:3]) + " (desvío -> rojo)")
            return 1

        # 3. NEGATIVO (no decorativo): contra los proofs RECIÉN re-derivados del clon, un pinned
        #    TAMPEREADO debe producir un mismatch. Si no, la comparación no tiene dientes (prosa).
        v = RunContext(root=clone, meta_root=meta_root, slug=slug).verifier
        sid0 = next(iter(pinned))
        tampered = dict(pinned)
        tampered[sid0] = str(pinned[sid0]) + "-tampered"
        if not _compare_to_pinned(v, clone, tampered):
            print("GATE DECORATIVO: un pinned tampereado NO produjo mismatch "
                  "(la comparación no tiene dientes; el veredicto sería prosa)")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"OK dos verificadores: runner limpio re-deriva {len(pinned)} proof_sha == pineado; "
          f"un pin tampereado cae a rojo (desvío en cualquier dirección detectado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
