<!-- meta:doc sha=bb9262ca1c7154aeab912091e69b84bae66edfa3 updated=2026-06-15T12:47Z -->
# Incremento A1-GRAMMAR-V2

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-15T12:47Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo
La factory-spec describe **cualquier** fábrica en 6 capas (L0 identidad · L1 dominio/capabilities ·
L2 línea/stations · L3 maquinaria · L4 sustrato · L5 requisitos) y **M0 rehúsa** lo incompleto o
deshonesto — con **cero tecnología hardcodeada en el validator** (ADR-012). Extiende
`spec/{model,loader,validator}.py` + `factory.schema.json`; los specs viejos (dummy, ASF) siguen verdes.

## Alcance / no-alcance
- **SÍ**: gramática v2 + sus dientes (validador) + schema espejo + tests (positivo rico + un negativo por
  regla). El dummy y el ASF quedan verdes sin tocarse (las secciones nuevas son OPCIONALES).
- **NO** (es A2): harvest del ASF COMPLETO a v2 + skeletons Full-Stack/Mobile/IoT. A1 sólo fija la gramática.

## Capas (v2) y los dientes que agregan
| Capa | Campo nuevo | Diente (negativo que BLOQUEA) |
| --- | --- | --- |
| L1 dominio | `capabilities[].{invariant,artifact,proof,primitive,tech,status}` | cap `status: built` sin `proof`; `tech` sin `primitive`; `primitive` mal formado (no `DES-N`) |
| L2 línea | `stations[].{depends_on, proof_checks[].{cmd,runs_in,toolchain,status}}` | `depends_on` a estación inexistente/inactiva; ciclo; `runs_in` fuera de enum |
| L3 maquinaria | `machinery.{harness,mcp,infra}` (DATO que el plan eligió) | `tech` sin `primitive` (misma regla, reusada) |
| L5 requisitos | `requirements[].{acceptance, verified_by}` | `verified_by` a un verificador FANTASMA (proof_check inexistente) |
| transversal | `status` enum | cualquier `status` ∉ {built, declared-deferred, planned} |

> **Regla madre (ADR-012)**: el validator chequea **forma** (`primitive` ~ `^DES-\d+$`, `tech`⇒`primitive`),
> NUNCA nombres de tecnología. `tech`/`toolchain` son DATO libre; whitelistearlos sería hornear herramientas.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | `model.py` + `loader.py`: dataclasses v2 (Capability, ProofCheck, Machinery; campos nuevos en Station/Requirement) + parse tolerante (lee `capabilities` o legacy `product_capabilities`) | ⏳ |
| 2 | `validator.py`: familia `validate_grammar_v2` (status enum · cap-sin-proof · tech-sin-primitiva · depends_on/ciclo · verifier-fantasma · runs_in) agregada a `validate()` | ⏳ |
| 3 | `factory.schema.json`: espejo declarativo de los campos nuevos (todos opcionales/aditivos) | ⏳ |
| 4 | tests: positivo rico v2 + un negativo por regla + regresión dummy/ASF verdes + tech-agnóstico | ⏳ |

## Criterio de cierre (demostrable, no narrable)
1. `meta station m00 --factory dummy` y `--factory agent-systems-factory` → PASS (specs viejos verdes).
2. Suite verde (`tests/test_spec.py` extendido) y `meta check` verde.
3. **Prueba por bloqueo**: un spec v2 con cada defecto (cap sin proof · tech sin primitiva · depends_on roto ·
   ciclo · verifier fantasma · status inválido) es RECHAZADO por `validate()` con `field: reason`; el spec
   rico bien-formado pasa con 0 problemas.
4. Tech-agnóstico: una `tech` arbitraria (string inventado) con `primitive: DES-N` válido PASA — el validator
   no whitelistea ninguna herramienta (ADR-012). `grep` de nombres de tech en `validator.py` = 0.
