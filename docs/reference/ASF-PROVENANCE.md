<!-- meta:doc sha=f33e14885e42b68ab2d5ab9a3707ab677663c346 updated=2026-07-04T20:10Z -->
# ASF — pin de provenance de la referencia congelada

> tipo: reference (estable) · creado: 2026-06-15T02:48Z
> Pin content-addressed del ASF original (fuente cosechada + oráculo de paridad). Decisión del
> ingeniero (2026-06-14, tras cerrar ASF-REGEN): **pinear identidad, NO copiar el árbol**. Hace que
> "qué exactamente se cosechó/comparó" sea inmutable y verificable sin arrastrar 60M/1.1G al repo.
> Consistente con ADR-006 (ASF congelado, no se toca) y el content-addressing de ADR-009 / `proof_sha`.

## El pin

| Campo | Valor |
| --- | --- |
| commit | `b1fcb1ff26ac7c960361042bac7dd9ae82bc6a2f` |
| tree | `1a47adc816abaeae068bea2f0d42bbab91ac6ca9` |
| branch | `feat/v2-source-grounding` |
| HEAD msg | `build(s08): s08 — gate opened` |
| ubicación | `../../Agent_Systems_Factory/` (repo git HERMANO, FUERA del Meta-Factory) |
| sucio al pinear | sólo `.claude/memory/journal.jsonl` (efímero, journal de sesión — NO material para la cosecha) |
| tamaño | 60M sin `.git`/`.venv` · 1.1G con |

## Verificar el pin (dos verificadores; aritmética, sin modelo)

```
git -C ../../Agent_Systems_Factory rev-parse HEAD        # → b1fcb1ff26ac7c960361042bac7dd9ae82bc6a2f
git -C ../../Agent_Systems_Factory rev-parse 'HEAD^{tree}'# → 1a47adc816abaeae068bea2f0d42bbab91ac6ca9
```

Si difieren, la referencia cambió desde la cosecha: re-leer el delta antes de confiar en cualquier
juicio de paridad o en `reference/ASF-LESSONS.md` / `reference/REGEN-AUDIT.md`.

## Por qué pin y no copia (la decisión, registrada)

- **El SHA YA es la identidad inmutable**: git hashea el árbol+historia. Copiar adentro o anida un
  segundo `.git` (sucio) o lo aplana y **pierde el historial** → quedaría *menos* congelado.
- **Su valor es ser referencia INDEPENDIENTE** (dos-verificadores, oráculo de paridad). Meterlo al
  repo lo mete en la misma custodia que debía auditar desde afuera.
- **Redundante**: el chasis regenerado ya vive in-repo en `factories/agent-systems-factory/`.
- **La cosecha ya terminó** (`ASF-LESSONS.md` extrajo el sustrato; `factory.spec.yml` descendió las
  opiniones; la paridad se redefinió y demostró por re-derivación, que no necesita ASF). El rol
  restante de ASF es archival → un pin basta.

## Si algún día hay que portar los bytes

(p.ej. clonar Meta_Factory a una máquina sin ASF al lado): `git submodule add` apuntando al repo de
ASF @ este SHA, o un `git bundle` archivado como artefacto. **No es necesario hoy** — el pin cubre la
provenance; los bytes están a un `git clone` del repo hermano.
