---
name: correr-app
description: Start/stop a Full-Stack Kotlin product's app locally (CRUD AppServer
  + frontend + PG) with one command.
---

# correr-app — launch a product's app with ONE command
For SEEING/using the app (not for verifying the factory — that is `verificar-fabrica`).

- **Start**: `factories/full-stack-kotlin/tools/dev_run.sh [PRODUCT]` (default `snipeit`). Brings up its own
  docker PG + bundles the frontend + runs `AppServerKt`, waits for `/health` and **prints the URL**
  (open it in the browser: the dashboard HOME with live counts). Port and PG are AUTO/own → it never
  clashes with or kills other `java` processes/containers.
- **Stop**: `… tools/dev_run.sh stop [PRODUCT]`  ·  **Status**: `… tools/dev_run.sh status [PRODUCT]`.

Notes: run from the repo root (cwd at root; the script resolves its paths). If the product was never
generated, the script builds it itself (`./gradlew installDist` / `npm install`, slow the 1st time).
It is a DEVELOPMENT convenience (no tooth); the proof that "the app runs" belongs to the
`frontend_browser_render` gate (s9).
