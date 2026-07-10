# Nomenclatura y Bibliografía

## Nomenclatura

| Símbolo / término | Descripción | Unidades |
|---|---|---|
| SRS | Especificación de Requisitos de Software | — |
| NFR | Requisito no funcional | — |
| LLM | Modelo de lenguaje grande | — |
| HITL | Human-in-the-loop (humano en el ciclo) | — |
| MAD | Debate multi-agente | — |
| NLP4RE | PLN aplicado a ingeniería de requisitos | — |
| T2SA | Text-to-Story Alignment (alineación texto↔historia) | — |
| Fidelidad | Proporción de requisitos producidos con sustento en la transcripción | [0,1] |
| Cobertura | Proporción de chunks con carga de requisito modelados en algún requisito | [0,1] |
| CCI | Índice de calibración de cardinalidad = producidos / golden | adimensional (1,0 = calibrado) |
| IRE | Tasa de elicitación de requisitos implícitos (ReqElicitGym) | [0,1] |
| chunk 3s1 | Ventana deslizante de 3 turnos de conversación, stride 1 | — |
| K_max | Presupuesto máximo de rondas de deliberación (= 4) | rondas |
| ε | Umbral de plateau de cobertura (= 0,01) | Δcobertura |
| τ_dup | Umbral de similitud coseno para deduplicación semántica | [0,1] |

## Bibliografía

> Formato (Apellido, año) en el texto; lista alfabética. Entradas con campos pendientes marcadas —
> completar antes de la entrega (regla: ninguna cita inventada).

- Dente, F., Dalpiaz, F. y Papotti, P. (2025). *Automated Alignment between Elicitation Interviews
  and Requirements*. arXiv:2510.08622 [cs.CL]. DOI: 10.48550/arXiv.2510.08622. (Paquete de
  reproducibilidad Inter2US/Text2Stories: Zenodo, DOI 10.5281/zenodo.20596692.) *Nota: el título del
  paquete de datos dice "Automatic Alignment…"; el título del paper (fuente autoritativa) es
  "Automated Alignment…" — se cita el del paper.*
- Voria, G., Casillo, F., Gravino, C., Catolino, G. y Palomba, F. (2024). *RECOVER: Toward
  Requirements Generation from Stakeholders' Conversations*. arXiv:2411.19552 [cs.SE].
  DOI: 10.48550/arXiv.2411.19552. (Con Online Appendix público.)
- Almeida, C., Copque, I., Oliveira, A., Arouca, M. G. et al. (2025). *From Elicitation Interviews
  to Software Requirements: Evaluating LLM Performance in Requirement Generation*. Workshop em
  Engenharia de Requisitos (WER 2025). DOI: 10.29327/1588952.28-12. Material suplementario
  (WEPGCOMP/+Lugar): Zenodo, DOI 10.5281/zenodo.15080374. *Nota: la ficha pública (ResearchGate)
  lista 8 autores; solo 4 son visibles sin acceso de pago (Federal University of Bahia) — cita
  parcial declarada honesta, "et al." cubre los 4 restantes no identificados.*
- Jin, D., Jin, Z., Fang, Z., Li, L., Yang, X., He, Y. y Chen, X. (2026).
  *ReqElicitGym: An Evaluation Environment for Interview Competence in Conversational Requirements
  Elicitation*. arXiv:2602.18306 [cs.SE]. DOI: 10.48550/arXiv.2602.18306. Repositorio:
  github.com/jdm4pku/ReqElicitBench.
- ISO/IEC/IEEE (2018). *ISO/IEC/IEEE 29148:2018 — Systems and software engineering — Life cycle
  processes — Requirements engineering*.
- ISO/IEC (2023). *ISO/IEC 25010:2023 — Systems and software engineering — SQuaRE — Product
  quality model*.
- [FALTA DATO: cita de REConSum (RELabUU, Universidad de Utrecht) si se referencia en el texto
  final]
- [FALTA DATO: cita de OntoAgent si se mantiene la mención del +33% IRE en el Cap. 2]
- [FALTA DATO: cita primaria del estudio de segmentación de conversaciones Fit-Gap usado en 1.1
  (proporciones 8,6–12% de requisitos explícitos)]
- [FALTA DATO: cita de la plantilla Connextra / historias de usuario (p. ej. Cohn) si el tribunal
  la exige]
- [FALTA DATO: cita de la literatura de debate multi-agente y overhead de tokens usada en 2.1/3.5]

**Nota de método:** las cuatro primeras entradas provienen de los paquetes de datos incluidos en
`datasets/` (títulos extraídos de sus READMEs/apéndices); los campos de autoría/año/venue/DOI que
faltaban se completaron (2026-07-06) verificando cada paper contra su registro público (arXiv /
DOI de la conferencia) — ninguno inventado. **Quedan 5 citas secundarias sin resolver** (residual
honesto, sin bloquear el resto del informe): REConSum, OntoAgent, el estudio de segmentación
Fit-Gap, la plantilla Connextra/Cohn y la literatura de debate multi-agente/overhead de tokens —
solo se completan si el tribunal exige que cada mención puntual del Cap. 2 tenga cita propia.
