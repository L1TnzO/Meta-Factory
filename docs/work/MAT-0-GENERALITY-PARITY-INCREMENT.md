<!-- meta:doc sha=64e32665160933ff22057f7489d5e6d00a668ab7 updated=2026-06-16T22:04Z -->
# Incremento MAT-0-GENERALITY-PARITY

> **Doc de gobierno.** Estado: **ABIERTO** (creado 2026-06-16T21:50Z). Cerralo con `meta increment close`
> (gateado: árbol limpio + estación activa verde). Todo cambio de código vive acá (ADR-010).

## Objetivo

Volver **diente** la ley anti-overfitting de ADR-014: un check `generality_parity` que RECHAZA (rojo) todo
mecanismo de sustrato que **CLAIMS** generalidad (`status: general`) sin estar probado verde en **≥2 fábricas
de dominios radicalmente distintos** (toolchain de producto disjunto Y mezcla de primitivas distinta, §3).
Cierra la deuda de código de MAT-0 (el ADR ya está; el diente no) y desbloquea el lockstep que MAT-1 necesita.

## Diseño (el porqué, no sólo el qué)

- **El manifiesto `docs/reference/parity.yml`** (espejo de `primitives.yml`) es el **libro de promoción** de
  mecanismos de sustrato. Cada entrada: `mechanism` (un `kind` de check del registry o una build `action`),
  `status` (`prototype` = exploración en un dominio, permitida §2, NO gatea · `general` = promovido, gateado)
  y `domains` (las fábricas que lo co-validan). El manifiesto declara el **claim**; el check lo **verifica**.
- **El check verifica un claim `general`** contra artefactos (no contra prosa): (a) cada `domain` declarado
  prueba el mecanismo **verde** en una estación real (`gate_recompute_ok` — un `passed:true` editado a mano
  NO cuela), y (b) existe un **par radicalmente distinto** entre ellos: lenguajes de producto disjuntos
  (canon de los `toolchain:` de `proof_checks` `runs_in: product_env`; `pytest`/`mypy`/`venv`→python) Y
  mezclas de primitivas (`capabilities[].primitive` DES-x) distintas.
- **Honesto hoy**: dummy y ASF son **ambos Python** → ningún mecanismo puede ser `general` aún. El manifiesto
  inicial deja todo en `prototype` → verde. El gate crea la presión hacia MAT-1 (el 2º toolchain, TS): recién
  ahí `product_env`/`generate`/… pueden promoverse. Es exactamente el lockstep de ADR-014 §6 / MATURITY-PLAN §6.

## Fases
| Fase | Contenido | Estado |
| --- | --- | --- |
| 1 | Manifiesto `parity.yml` + `verify/checks/generality_parity.py` (verifica claims `general`) | ✅ |
| 2 | Teeth deterministas (`tests/test_generality_parity.py`): verde 2-toolchain · borrar proof→rojo · mismo toolchain→rojo · proof rancio→rojo · prototype 1-dominio→verde | ✅ |
| 3 | Cableado a `meta check` (gate meta) + nota en el guard ADR-012 (test_isolation) | ✅ |
| 4 | Demo VIVO por bloqueo sobre fábricas reales: `product_env`→`general` cae a rojo (ambos Python); manifiesto honesto = verde | ✅ |
| 5 | Docs (STATE/ROADMAP/MATURITY-PLAN + esta evidencia) + cierre | ✅ |

## Evidencia (verificable, no narrada)
- **El diente, por bloqueo** (`tests/test_generality_parity.py`, 8 verdes): `general` con 2 dominios distintos
  (python ⟂ ts) → verde · borrar la proof del 2º → rojo · mismo lenguaje (pytest↔unittest) → rojo · misma
  mezcla de primitivas → rojo · proof rancio (`proof_sha` mentido) → rojo · `prototype` en 1 dominio → verde.
- **Demo vivo sobre fábricas REALES** (`generality_parity . <manifiesto>`): `product_env` general[dummy,
  agent-systems-factory] → `GENERALITY_PARITY ROJO … ningún par … es radicalmente distinto (§3): toolchain/
  primitivas no difieren` (exit 1) — porque dummy y ASF son **ambos Python**. Manifiesto honesto (todo
  `prototype`) → `OK … 4 en prototype` (exit 0).
- **Cableado**: `meta check` → `6 checks all green · … generality ok` (suite 443→**451**).
- **No rompe nada**: `ci --rederive` dummy **5/5** y agent-systems-factory **6/6** == pineado (clon limpio);
  congelado `@ b1fcb1f` intocado.
- **Hallazgo colateral** (no del increment): `specs/dummy.factory.spec.yml` (3 estaciones) está STALE vs la
  spec REGISTRADA `factories/dummy/factory.spec.yml` (5, con s03 infra / s04 mcp). El check audita la
  registrada (la que materializó los `.proof/`). El drift de `specs/` se aborda aparte (no es de paridad).

## Criterio de cierre (demostrable, no narrable)
1. `generality_parity` cae a **rojo** si un mecanismo `general` tiene <2 fábricas que lo prueban verde, o si
   las que lo prueban comparten lenguaje/primitivas (§3) — probado **por bloqueo** con fixtures herméticos.
2. **Demo vivo**: marcar `product_env` `general` con `[dummy, agent-systems-factory]` → **rojo** (ambos
   Python); revertir el manifiesto → **verde**.
3. `meta check` **corre** el check (cableado al gate meta); suite verde; árbol limpio.
4. No rompe nada: dummy+ASF M0–M8 / `ci` intactos; el manifiesto honesto deja todo `prototype` → verde.
