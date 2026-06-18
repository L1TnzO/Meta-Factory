# La columna anti-sello-de-goma — doctrina de los tres cerrojos (INMUTABLE)

> STAGE 0 · trust-chain · R3. Esta doctrina es la raíz de confianza de TODA fábrica.
> Se hereda sin cambios (M1). Modificarla = gate R3 (SELF-IMPROVEMENT §3/§5).
> El corazón: **es imposible marcar una compuerta sin prueba real.**

Una compuerta (gate) abre solo si un veredicto `passed=true` lo respalda. Estos tres cerrojos,
independientes, vuelven imposible producir ese `passed=true` sin que los checks reales hayan
salido en exit 0. Cada uno cubre una vía distinta de fraude; los tres juntos no dejan hueco.

## Cerrojo 1 — El veredicto no es escribible por el modelo
`passed` lo computa EXCLUSIVAMENTE `seed/verifier.py` desde exit codes reales de subprocesos
(`recompute_passed`: todo check existe y todo check salió 0). El verifier es el ÚNICO escritor de
`proof.json` y del ledger. El modelo no puede escribir esos artefactos:
- `permissions.deny` niega `Write`/`Edit` sobre `**/.proof/**`.
- el hook `PreToolUse` (`proof_protect`) niega además todo `Bash` que redirija/edite `.proof/`
  (`> .proof/…`, `tee`, `sed -i`, `cp … .proof/…`).
El verifier escribe vía file-IO DENTRO de `meta station`/`meta verify` (no es una tool call del
modelo), así que el camino legítimo funciona y el fraudulento no existe.

## Cerrojo 2 — La compuerta recomputa el hash
Antes de abrir, la gate recomputa `passed` y `proof_sha` desde los checks del propio `proof.json`
(`gate_recompute_ok`) y rechaza si:
- el `proof_sha` almacenado ≠ el recomputado (artefacto editado a mano), o
- el `passed` almacenado ≠ el recomputado (un `passed=true` pegado a mano se cae acá), o
- el recomputado no es `passed`.
`proof_sha` se computa sobre `(station, sorted[(name, exit)])` — sin timestamps ni salida
específica de máquina — para que un runner independiente que re-derive el MISMO resultado compute
el MISMO sha (doctrina de los dos verificadores, PF-10). Un exit distinto ⇒ un sha distinto.

## Cerrojo 3 — El hook `Stop` re-corre verify
Al cierre de cada turno, el hook `Stop` (`stop_proof`) re-corre el verify de la estación activa
(registrada en `.proof/active.json` por el runner) y, si no pasa, imprime el motivo y bloquea el
turno (exit 2). No se puede "declarar listo" un trabajo cuyo verify falla: el cierre lo re-verifica.

## Por qué los tres y no uno
- Solo el cerrojo 1 → un proof viejo válido podría reusarse, o el ledger editarse fuera del harness.
- Solo el cerrojo 2 → nada obliga a recomputar al cierre; el turno cierra con un proof rojo intacto.
- Solo el cerrojo 3 → re-correr sin proteger el artefacto deja editar el proof entre corrida y gate.
Juntos: el artefacto es intocable (1), su contenido se valida por recómputo (2), y el cierre
re-deriva el hecho (3). La custodia local NO es la raíz: encima está el CI externo, que re-deriva
en una máquina limpia y compara contra el veredicto pineado (`external_ci.yml`, M6).

## La prueba de bloqueo (capstone, insalteable)
Corromper el invariante de un producto (p.ej. cambiar su marcador) debe producir: `verify`
`passed=false` → la gate NO abre → el hook `Stop` bloquea (exit 2) → el CI externo computa un
`proof_sha` distinto al pineado → rojo. Si ALGUNO de esos pasos no ocurre, la columna está hueca
y el cambio no se promueve. Render verde con producto roto DEBE poder fallar (lección de ASF).
