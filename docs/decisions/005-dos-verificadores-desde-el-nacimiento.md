<!-- meta:doc sha=ca58be7729e536fce7aa5d78e4f82ffc86f64807 updated=2026-06-13T14:57Z -->
# ADR-005 — Dos verificadores (re-derivación sobre custodia) desde el nacimiento de cada fábrica

| Campo | Valor |
| --- | --- |
| Estado | Aprobado |
| Fecha | 2026-06-13T02:17Z |
| Referencia | ASF/ADR-022 (origen), reference/SELF-IMPROVEMENT.md §1–2, ASF-LESSONS §G-7 |

## Contexto

La columna (ADR-002) protege el PROCESO de construcción, pero su custodia local depende de que la
cadena de hooks esté activa DENTRO de Claude Code: un proof editado a mano fuera del harness no lo
detecta nadie. ASF resolvió esto con ADR-022 (CI externo que re-deriva) pero lo agregó **tarde** en
su vida. Además, es la defensa exacta contra el problema "trusting trust" del auto-mejoramiento
(SELF-IMPROVEMENT §1): un sistema comprometido no puede ser auditado por sí mismo.

## Decisión

**Toda fábrica producida nace (meta-estación M6) con la doctrina de los dos verificadores:**

1. **Re-derivación sobre custodia.** El verificador externo NO audita artefactos guardados: los
   RECONSTRUYE en un clon limpio (`ci --full` → rebuild del dummy desde su spec por la línea
   completa → gates frescas → RTM comparado contra el **veredicto honesto pineado**). Desvío en
   CUALQUIER dirección = rojo (un "COMPLETE" espontáneo sin gold set es fachada, no mejora).
2. **Dos verificadores, dos preguntas.** El CI de la fábrica responde "¿la máquina sigue sabiendo
   fabricar?" (suite + UN dummy, costo constante). El CI de cada producto graduado responde "¿este
   producto sigue sano?".
3. **Jerarquía de independencia.** hooks (mismo actor) < pre-push (otra hora) < **CI remoto (otra
   máquina, otro actor — la única capa intocable por modelo/hooks/ingeniero local; la autoridad del
   perímetro)**.
4. **Colocación.** Toda la lógica vive en `meta ci` (CLI testeable); el hook y el yaml son
   transportes de una línea. Cero lógica duplicable que diverja.

## Consecuencias

- Es la defensa trusting-trust: un Meta-Factory local comprometido produce un veredicto que el
  runner limpio NO reproduce → rojo. La confianza no está en el binario sino en la re-derivación.
- El veredicto pineado es una CONSTANTE en el código: cambia solo por diff revisado. Rojo ante
  "mejora espontánea" es comportamiento correcto.
- M6 no es opcional ni diferible: nace con la fábrica, no se retrofitea (la lección G-7 de ASF).
- Rechazado: versionar runs/ (churn de regenerables); GPG como prerequisito (endurecimiento futuro).
