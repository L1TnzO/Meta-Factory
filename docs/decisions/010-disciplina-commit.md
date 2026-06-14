<!-- meta:doc sha=50f2c2eb9606705d3f186f60170562b3a60553e0 updated=2026-06-14T01:55Z -->
# ADR-010 — Disciplina de commit: todo código vive en un incremento; cadencia por fase

| Campo | Valor |
| --- | --- |
| Estado | **Aprobado + Implementado** (2026-06-14, sesión opus-4.8, incremento CADENCE): `memory/cadence.py` + `meta increment {open,close,status}` + hook `increment_guard` + cadencia en `gate_guard`/`stop_proof` + surface en `meta check`. Cero modelo. |
| Fecha | 2026-06-14T00:55Z |
| Referencia | `work/CADENCE-INCREMENT.md` (evidencia), STATE #5 (origen), ADR-007 (Tier 0 — `cadence` es file-IO+git como el journal), ADR-023/ASF (no forzar el juicio), I-10 (commits con trailers) |

## Contexto

El pecado central del bootstrap fue **0 commits en toda la construcción** (M0→M8 como un build largo sin
estructura): sin evidencia-por-requisito en vivo, el RTM re-derivaba pero la mitad de la traza faltaba
(`HONEST-STATE §5`). Mi default genérico de asistente —"commitear sólo cuando me lo piden"— choca con la
doctrina del repo. STATE #5 lo dejó como diseño abierto: ¿cómo forzar la cadencia de commit?

Al diseñar, el ingeniero **reencuadró el problema**: el agujero no era "no commitear DENTRO de un incremento"
sino que **se podía tocar código FUERA de todo incremento**. La cura no es razonar casos borde dentro/fuera,
sino **disolver la frontera**: todo cambio de código exige un incremento abierto. Hasta un fix menor es un
incremento menor — para no pensar en bordes y que SIEMPRE que se toca código, haya un incremento.

`commit_guard` ya existía pero gatea **calidad** (no commitees una estación roja), no **cadencia** (no te
obliga a commitear). El pecado no fue commitear rojo; fue no commitear. El mecanismo faltante es otro.

## Decisión

Una doctrina de commit en dos capas, determinista y re-derivable (cero modelo: git + file-IO + aritmética).
La verdad es git (working tree) + docs (incremento abierto, vía `projection.open_increment`); la maquinaria
sólo la LEE y la proyecta. **Bloquea, NO auto-commitea**: el mensaje (con trailers I-10) lo escribe el modelo.

1. **Capa 1 — Increment-gate.** Editar cualquier archivo **no-`.md` bajo el repo** exige un incremento
   abierto. `.md` siempre permitido (es como se ABRE un incremento y la modalidad normal de docs → sin
   chicken-egg). Hook `increment_guard` (PreToolUse Write|Edit|MultiEdit); la decisión vive en
   `cadence.edit_allowed` (pura, testeada); el hook sólo transporta (ley de colocación).

2. **Capa 2 — Cadencia por fase.** Deuda = incremento abierto + código no-`.md` sin commitear. Dientes:
   - **advance-time** (`gate_guard`): no avanzás a la estación N+1 si la N está verde sin commitear — cae
     justo en el antipatrón del bootstrap (build largo de un turno);
   - **close-time** (`stop_proof`): el turno no cierra si hay un gate verde sin commitear (backstop); no
     molesta el WIP de desarrollo (sin gate nuevo desde el último commit, no dispara);
   - **close-increment** (`meta increment close`): rehúsa cerrar con deuda o estación activa roja;
   - **surface** (`meta check`): muestra la deuda como aviso temprano (no-block, ADR-023).

3. **Lifecycle barato**: `meta increment open/close/status` para que "incremento menor" sea un comando,
   no fricción que se rodee.

## Consecuencias / límites honestos

- **Construir una fábrica vía estaciones** sin incremento abierto NO está gateado todavía (el increment-gate
  cubre EDITAR código, no ejecutar la línea). Refinamiento posible; fuera de alcance acá.
- **`increment_guard` se carga al inicio de sesión**: enforza EN VIVO recién tras reiniciar (como los otros
  hooks en la sesión 2). Durante la construcción se probó por exit-code y unit tests; lo live es el capstone.
- **Propagación al sustrato (`template/factory/harness`) diferida**: el núcleo vive en el harness de la
  meta-factory; hornearlo para que toda fábrica generada lo herede es follow-up (G-8). Validar antes de invertir.

## Descartado (y por qué)

- **Auto-commit por cadencia** → mensajes basura + atribución de trabajo no narrado (viola I-10). Se bloquea.
- **Gatear sólo DENTRO del incremento** (mi diseño inicial) → deja el agujero real (codificar fuera). El
  reencuadro lo cierra.
- **Umbral/recordatorio discrecional** → el disparador discrecional se saltea (la lección del bootstrap). Hard.

## Addendum 2026-06-14 — capstone cerrado + residual aceptado

Hechos posteriores al cierre del incremento CADENCE, registrados SIN mutar la decisión (decisions/ inmutable):

- **Capstone live-verify cerrado** (resuelve el límite «`increment_guard` se carga al inicio de sesión»):
  verificado EN VIVO en sesión nueva — sin incremento abierto, `Write` de un `.py` → DENEGADO por el harness
  con el mensaje ADR-010; `.md` y fuera-del-repo permitidos; árbol limpio antes/después (sin fuga del scratch).
  Las dos capas quedan probadas en vivo (`gate_guard` ya había bloqueado avance con deuda). Evidencia: commit
  `5ed511a`, STATE §Agujeros.

- **Residual ACEPTADO — docs `.md` fuera de un incremento NO tienen cadencia de commit (no se endurece).**
  `dirty_code` excluye `.md` y `stop_block` sólo mira dentro de un incremento abierto, así que un doc suelto
  sin commitear no dispara dientes. Decisión deliberada: **no construir maquinaria para taparlo**, por
  proporcionalidad — (a) el daño es chico: un `.md` sin commitear no rompe código, gate ni cadena de pruebas;
  (b) la rebanada PELIGROSA de los docs (la proyección de hechos de STATE) YA está enforced en duro por
  `meta check`; (c) el cortafuegos contra el derrame «se me hace hábito en código» está puesto en la frontera
  del CÓDIGO (Capas 1/2), no de los docs — el hábito no puede cruzar; (d) un backstop que nag-uee por cada
  `.md` sin commitear dispararía casi siempre (estás a mitad de un doc) → ruido que entrena a IGNORAR los
  dientes que sí importan. Cambiar ruido barato por debilitar la columna es mal trueque (ADR-023: no forzar
  lo de bajo riesgo). Mitigación proporcional —no-máquina, sin ruido en runtime—: una instrucción en
  `CLAUDE.md` (commit como parte del trabajo, que OVERRIDE el default genérico). Es un parche que REDUCE lo
  no-commiteado, no lo elimina; aceptado como tal.
