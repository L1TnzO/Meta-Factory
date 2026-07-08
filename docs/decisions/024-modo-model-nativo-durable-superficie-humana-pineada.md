<!-- meta:doc sha=0f68fc4045f11b40a60905f3e6c9ac057a41c3b9 updated=2026-07-08T15:53Z -->
<!-- meta:doc sha=PENDING updated=2026-07-08T15:53Z -->
# ADR-024 — Modo model-nativo durable: la superficie humana como override pineado (concreta ADR-023 §4)

| Campo | Valor |
| --- | --- |
| Estado | Propuesto |
| Fecha | 2026-07-08T15:53Z |
| Decide | el ingeniero (2026-07-08, «terminá snipe-it model-nativo, el frontend es horrible»); analiza, diseña y propone el orquestador |
| Concreta / revisa | ADR-023 §4 (el moat pasa a spec+gates+artefacto PINEADO — este ADR le da MECANISMO durable) · ADR-023 §3 (freeze-con-pin del codegen de templates — este ADR crece el PERFIL DE VERIFICACIÓN + un override, NO alimenta templates) · ADR-012 (tech=plan: el opt-in es DATO en product.yml) |
| Referencia | `factories/full-stack-kotlin/tools/modelgen_ab_gate.sh` (la mitad VERIFICAR ya construida por el A/B) · `factories/full-stack-kotlin/docs/work/FSK-FRONTEND-MODELGEN-AB-INCREMENT.md` (el experimento que lo validó) |

## Contexto (medido, no narrado)
1. **El A/B construyó sólo la mitad VERIFICAR.** `modelgen_ab_gate.sh` corre s8+s9 vía el engine SIN
   re-derivar s0 (el artefacto model-nativo en `build/` no se clobberea) + design-floor. Pero es un gate
   de experimento, no la línea estándar.
2. **Nada durable está commiteado.** La superficie model-nativa que ganó el A/B (`app.ts`+`app.css`) vive
   en `build/product/frontend/src/` — que está **gitignored**. En un clone limpio no existe.
3. **`ci --rederive --all-products` clobbea.** Re-emite el frontend de TEMPLATES; pisaría cualquier
   superficie model-nativa. El perfil estándar de s9 NO corre `design_floor` (vive en `tools/`).
4. **snipe-it sería el PRIMER producto durablemente model-nativo.** Falta el mecanismo de coexistencia:
   commitear la superficie, no re-derivarla, verificarla, pinearla — sin romper los productos-template
   pineados (`assets`), que por ADR-023 §3 siguen verdes gratis.

## Decisión
1. **Superficie model-nativa = subconjunto ACOTADO.** Sólo la capa de presentación humana
   (`frontend/src/app.ts` + `frontend/src/app.css`). El cliente tipado (`frontend/src/client.ts`,
   `frontend/gen/api.ts`) y los checks (`browser_check.ts`, `consume_check.ts`) siguen
   TEMPLATE-generados y type-checked → preserva el moat de type-safety (DES-6) y reusa el perfil de
   verificación tal cual. Es exactamente lo que el brazo B del A/B generó.
2. **Override pineado (DATO, ADR-012).** La superficie se commitea a una ubicación TRACKED per-producto
   (`products/<p>/frontend/app.ts` + `products/<p>/frontend/app.css`). La línea de codegen, para un
   producto que declara el opt-in, **COPIA el override** en `build/` en vez de emitir el template. La
   presencia del override + el flag en `product.yml` (`frontend_surface: model-native`) es el opt-in.
3. **`design_floor` se promueve al perfil s9 OPT-IN.** Corre SÓLO para productos con superficie
   model-nativa. Los productos-template (`assets`) no lo corren → siguen verdes en su pin (ADR-023 §3
   intacto). El diente vive como check estándar, no como script de experimento.
4. **Verificar-no-re-derivar es el pin.** Para un producto model-nativo, `ci` re-VERIFICA el artefacto
   (s8/s9 + design_floor sobre la superficie commiteada), NO re-deriva la superficie. El pin ES el
   artefacto verificado (ADR-023 §4, ahora con mecanismo).
5. **Diente two-sided.** Un producto opt-in cuya superficie fue clobbereada por el template (o falta) →
   ROJO; un producto-template sin opt-in que igual corre design_floor → error de config → ROJO. La
   promoción no debe poder romper `assets` en silencio.

## Consecuencias
- **F1/ASF hereda el modo.** «Regenerar model-nativo bajo el perfil de verificación» (ADR-023) ahora
  tiene una forma concreta y durable, reusable por cualquier fábrica.
- **El codegen de templates sigue CONGELADO.** Este ADR NO lo alimenta: agrega un mecanismo de OVERRIDE
  (copiar en vez de emitir) + crece el PERFIL DE VERIFICACIÓN (design_floor opt-in). Ambos son la parte
  viva de una fábrica bajo ADR-023 §1.
- **El costo por producto sube a tokens-de-Sonnet-bajo-gates** (ADR-023): la superficie se genera una vez
  por slot y se pinea; re-verificar sigue 0-modelo.
- **snipe-it (19 entidades) es grande:** su superficie se genera SPLIT en varios slots (INC-B), no en uno
  — el A/B midió UN slot para 5 entidades del sweet-spot.
