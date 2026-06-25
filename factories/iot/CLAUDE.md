# Fábrica iot — residencia (lo de-cada-turno)

> Presupuesto: este archivo es el ÚNICO siempre-residente (I-6). Se paga alquiler por línea — mínimo y
> medible en el diff. Lo determinista vive en el CLI/gates; lo histórico, en `docs/`. Acá solo lo que
> debe influir en CADA turno. La gate `agent_shadow` (M7) mide este presupuesto.

## Empezá acá
1. `docs/STATE.md` — estado actual de la fábrica (punto de entrada único).
2. La línea de producto vive en `stations/` (estaciones como dato); el contrato SDD, en `factory.spec.yml`.

## Reglas de cada turno (lo que el harness ya enforza, no repetir en prosa)
- **El veredicto no se escribe a mano**: `passed` lo computa SOLO `seed/verifier.py` desde exit codes
  reales (Cerrojo 1). No toques `.proof/` — el hook `proof_protect` lo deniega.
- **No declares verde sin prueba**: corré la gate (`meta station`/`meta product-run`) y leé el bus de
  veredictos (≤N líneas), nunca el dump de tests.
- **Dos verificadores**: la custodia local no es la raíz de confianza; la re-derivación en runner limpio
  lo es (`seed/external_ci.yml` + el veredicto pineado).
- **Delegá por default**: el contrato de cada rol vive en `.claude/agents/` (cuesta ~0 líneas). Toda
  prohibición de un agent tiene SOMBRA determinista (I-12) — el orquestador no se apoya en prosa.
- **Lo que toca la cadena de confianza** (gate/verifier/hooks) lo lee el orquestador con sus propios ojos.
- **Multi-archivo por mantenibilidad**: el código nuevo (codegen y artefactos generados) se parte en archivos
  cohesivos, no en un monolito; no agregues archivos NUEVOS de miles de líneas (si uno tiende a ~800+, partilo).
  Los monolitos existentes son deuda conocida — no reescribir salvo pedido.

## Colocación (dónde va cada pieza)
CLI si debe ser garantizado · hook si debe impedirse aunque el modelo se porte mal · acá si influye cada
turno · skill si es a-demanda · agent si es un rol · `docs/` si es historia (residencia cero).
