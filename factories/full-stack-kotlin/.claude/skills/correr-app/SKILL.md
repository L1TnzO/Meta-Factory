---
name: correr-app
description: Iniciar/parar localmente la app de un producto Full-Stack Kotlin (AppServer CRUD + frontend + PG) con un comando.
---

# correr-app — levantá la app de un producto con UN comando
Para VER/usar la app (no para verificar la fábrica — eso es `verificar-fabrica`).

- **Arrancar**: `factories/full-stack-kotlin/tools/dev_run.sh [PRODUCTO]` (default `snipeit`). Levanta PG docker
  propia + bundlea el frontend + corre el `AppServerKt`, espera `/health` e **imprime la URL** (abrila en el browser:
  la HOME del dashboard con conteos vivos). Puerto y PG son AUTO/propios → no choca ni mata otros `java`/contenedores.
- **Parar**: `… tools/dev_run.sh stop [PRODUCTO]`  ·  **Estado**: `… tools/dev_run.sh status [PRODUCTO]`.

Notas: corré desde la raíz del repo (cwd en la raíz; el script resuelve sus rutas). Si el producto nunca se generó,
el script lo construye solo (`./gradlew installDist` / `npm install`, la 1ra vez tarda). Es una conveniencia de
DESARROLLO (sin diente); la prueba de que "la app corre" la tiene el gate `frontend_browser_render` (s9).
