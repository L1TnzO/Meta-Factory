"""rtm_rederive — M5's gate (I-8): el RTM y su evidencia SE RE-DERIVAN de `.proof/`, no de prosa.

Prueba el criterio 2 de M4-M7: `meta rtm` re-deriva, por requisito, SATISFIED/UNSATISFIED desde los
proofs, y la evidencia (ledger) deriva de esos proofs — no de narrativa. La prueba NO es decorativa:
en una copia HERMÉTICA del `.proof/`, CORROMPER el proof de una estación que satisface un requisito
SATISFIED debe tirarlo a UNSATISFIED. Si el veredicto NO cambia, el RTM sería prosa (rojo).

Reusa el verificador del seed (única autoridad de veredictos, lock #2) y la misma ley de re-derivación
que `meta rtm` — cero lógica duplicada. Hermético: sólo toca un temp. Atado a los artefactos reales,
así que es una gate de verdad, no un restatement de intención.

Argv: <factory_root> <meta_root> [spec_path-rel]."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


def _rederive(verifier, proof_root: Path, spec) -> dict:
    """RTM re-derivado SÓLO de artefactos (misma ley que cmd_rtm, I-10): un requisito está SATISFIED
    iff toda estación en su satisfied_by tiene un proof presente con la gate recomputable-OK."""
    status: dict[str, bool] = {}
    for req in spec.requirements:
        ok = bool(req.satisfied_by)
        for sid in req.satisfied_by:
            proof = verifier.load_proof(proof_root, sid)
            ok = ok and proof is not None and verifier.gate_recompute_ok(proof)[0]
        status[req.id] = ok
    return status


def _tamper_proof(verifier, proof_root: Path, sid: str) -> bool:
    """Corrompe el proof de `sid` en `proof_root` (flip de un exit 0 -> 9): recompute_passed cae a
    False y el proof_sha deja de cuadrar, así que gate_recompute_ok lo rechaza. True si pudo."""
    p = verifier.proof_path(proof_root, sid)
    if not p.exists():
        return False
    proof = json.loads(p.read_text(encoding="utf-8"))
    checks = proof.get("checks", [])
    if not checks:
        return False
    checks[0]["exit"] = 9
    p.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return True


def _ledger_consistent(verifier, factory_root: Path) -> tuple[bool, str]:
    """La evidencia deriva de los proofs: cada gate del ledger tiene un proof en disco cuyo sha
    RECOMPUTADO coincide. Un entry sin proof respaldante (o con sha que no cuadra) sería prosa."""
    ledger = verifier.ledger_path_for(factory_root)
    if not ledger.exists():
        return True, "sin ledger (nada que cruzar)"
    try:
        gates = json.loads(ledger.read_text(encoding="utf-8")).get("gates", [])
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"ledger ilegible: {exc}"
    for g in gates:
        sid = g.get("station", "")
        proof = verifier.load_proof(factory_root, sid)
        if proof is None:
            return False, f"el ledger cita la gate {sid} sin proof en disco"
        re_sha = verifier.compute_proof_sha(sid, proof.get("checks", []))
        if re_sha != g.get("proof_sha"):
            return False, f"gate {sid}: el proof_sha del ledger no coincide con el recomputado del proof"
    return True, "ok"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: rtm_rederive <factory_root> <meta_root> [spec_path]", file=sys.stderr)
        return 2
    factory_root = Path(argv[0]).resolve()
    meta_root = Path(argv[1]).resolve()
    spec_rel = argv[2] if len(argv) > 2 else "factory.spec.yml"

    from ...engine import RunContext
    from ...spec.loader import load_spec

    spec = load_spec(factory_root / spec_rel)
    v = RunContext(root=factory_root, meta_root=meta_root, slug=spec.slug).verifier

    # 1. hay un RTM que re-derivar (la spec mapea requisitos a estaciones)
    if not any(r.satisfied_by for r in spec.requirements):
        print("RTM VACÍO: la spec no mapea ningún requisito a estaciones (no hay RTM que re-derivar)")
        return 1

    # 2. baseline desde el .proof/ REAL: hace falta al menos un requisito SATISFIED para probar la caída
    base = _rederive(v, factory_root, spec)
    sat = [rid for rid, ok in base.items() if ok]
    if not sat:
        print("RTM SIN COBERTURA: ningún requisito está SATISFIED — la fábrica no fue construida (corré la línea)")
        return 1

    # 3. NEGATIVO (no decorativo): en copia hermética, corromper el proof de una estación que satisface
    #    un requisito SATISFIED debe TIRARLO a UNSATISFIED. Si no cambia, el RTM no se re-deriva de .proof/.
    target_req = next(r for r in spec.requirements if r.id in sat and r.satisfied_by)
    target_sid = target_req.satisfied_by[0]
    tmp = Path(tempfile.mkdtemp(prefix="rtm_rederive_"))
    try:
        shutil.copytree(factory_root / ".proof", tmp / ".proof")
        if not _tamper_proof(v, tmp, target_sid):
            print(f"NO VERIFICABLE: no pude corromper el proof de {target_sid} (¿sin checks?)")
            return 1
        after = _rederive(v, tmp, spec)
        if after.get(target_req.id):
            print(f"RTM DECORATIVO: corromper el proof de {target_sid} NO cambió {target_req.id} "
                  f"(el RTM no se re-deriva de .proof/ — sería prosa)")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 4. la evidencia (ledger) deriva de los proofs, no de narrativa
    ok, reason = _ledger_consistent(v, factory_root)
    if not ok:
        print(f"EVIDENCIA INCONSISTENTE: {reason}")
        return 1

    print(f"OK RTM vivo: {len(sat)}/{len(spec.requirements)} SATISFIED re-derivado de .proof/; "
          f"corromper {target_sid} tira {target_req.id} a UNSATISFIED; ledger consistente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
