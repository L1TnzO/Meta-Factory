"""products_rederive — R1's gate (ADR-015): every PRODUCT INSTANCE re-derives to its OWN pin, isolated.

A factory is a reusable target: 1 factory : N products (the lifecycle, ADR-015). This gate makes that
NON-decorative, the multi-product analogue of `clean_runner` (M6): in a THROWAWAY CLONE of the factory
(sin `.proof/`/`build/`, como un checkout fresco) it re-derives EACH instance under `products/<p>/` from
its committed source (`product.yml` + its pin) and demands every re-derived proof_sha equal the pinned
constant. Each instance has its OWN evidence root, so re-deriving B never reads A's `.proof/` — the
products are ISOLATED by construction (delete A's proof, B's gate is untouched). Custody is never the
root of trust; replicability is (PF-10).

Reuses the ONE re-derivation law (`cli.rederive_pinned` + `cli._compare_to_pinned`), so the gate cannot
diverge from `meta ci --rederive --product` (ADR-005 §4). The negative is NON-decorative (like
clean_runner): against each instance's freshly re-derived proofs, a TAMPERED pin must yield a mismatch —
if it does not, the comparison has no teeth and the verdict is prosa (red).

A factory with NO instances reports N/A (honest, not faked green) — like `boundary_survives` opt-out.

Argv: <factory_root> <meta_root>."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: products_rederive <factory_root> <meta_root>", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()

    from ...cli import _compare_to_pinned, rederive_pinned
    from ...engine import RunContext
    from ...spec.loader import load_spec

    products_dir = factory_root / "products"
    instances = (sorted(p.name for p in products_dir.iterdir() if (p / "product.yml").is_file())
                 if products_dir.is_dir() else [])
    if not instances:
        print("N/A: la fábrica no declara instancias de producto (products/<p>/) — products_rederive no aplica")
        return 0

    slug = load_spec(factory_root / "factory.spec.yml").slug
    tmp = Path(tempfile.mkdtemp(prefix="products_rederive_"))
    try:
        # CLON LIMPIO: la fuente committeada (spec, codegen, seed, products/<p>/{product.yml,pin,domain_gen})
        # SIN el estado re-derivable (.proof/, build/ a cualquier nivel) — un checkout fresco no los trae.
        clone = tmp / "factory"
        shutil.copytree(factory_root, clone,
                        ignore=shutil.ignore_patterns(".proof", "build", "__pycache__"))
        proven = []
        for name in instances:
            proot = clone / "products" / name
            # 1. RE-DERIVACIÓN aislada: cada instancia desde su PROPIO product.yml + pin, en su PROPIA raíz
            #    (chassis = la fábrica clonada). record_active=False: hermética, no contamina el journal meta.
            ok, mismatches, rc, has_pinned = rederive_pinned(proot, meta_root, slug,
                                                             record_active=False, chassis=clone)
            if not has_pinned:
                print(f"SIN PINEAR: {name} no trae pinned_verdict.json (corré `meta pin --product {name}`)")
                return 1
            if not ok:
                if rc != 0:
                    print(f"RUNNER LIMPIO ROJO: la instancia {name} NO reconstruye en árbol limpio (rc={rc})")
                else:
                    print(f"VEREDICTO DESVIADO ({name}): re-derivado != pineado: " + "; ".join(mismatches[:3]))
                return 1
            # 2. NEGATIVO (no decorativo): contra los proofs RECIÉN re-derivados, un pin TAMPEREADO debe
            #    producir un mismatch. Si no, la comparación no tiene dientes (prosa).
            pinned = json.loads((proot / "pinned_verdict.json").read_text(encoding="utf-8"))
            v = RunContext(root=proot, meta_root=meta_root, slug=slug, chassis=clone).verifier
            sid0 = next(iter(pinned))
            tampered = dict(pinned)
            tampered[sid0] = str(pinned[sid0]) + "-tampered"
            if not _compare_to_pinned(v, proot, tampered):
                print(f"GATE DECORATIVO ({name}): un pin tampereado NO produjo mismatch (sin dientes)")
                return 1
            proven.append((name, len(pinned)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    detail = " · ".join(f"{n}:{k}/{k}" for n, k in proven)
    print(f"OK products_rederive: {len(proven)} instancia(s) re-derivan == su pin en árbol limpio, "
          f"aisladas (raíz propia) y con diente (pin tampereado → rojo) — {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
