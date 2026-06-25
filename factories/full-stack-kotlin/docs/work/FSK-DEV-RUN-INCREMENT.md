# Incremento FSK-DEV-RUN — una forma FÁCIL de iniciar la app (DX, no-fragil)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **ABIERTO** (creado
> 2026-06-25T15:51Z). Cerralo flippeando este header a CERRADO.
> Editar `factories/full-stack-kotlin/**` no-`.md` exige ESTE incremento abierto.

---

## 0. POR QUÉ (pedido directo del ingeniero, 2026-06-25)
Tras cerrar el arco frontend (✅DASHBOARD), correr la app a mano requiere una secuencia **larga y frágil** (la del
§★ EMPEZÁ ACÁ de los handoffs del arco): levantar una PG docker con un digest pineado, autodetectar `JAVA_HOME`,
bundlear el frontend (`node build_bundle.mjs`), y lanzar `java -cp 'build/install/<p>/lib/*' <pkg>.endpoints.AppServerKt`
con **4 env vars** (`FSK_NOW`/`FSK_AC_PORT`/`FSK_PG_URL`/`FSK_WEB_DIR`), cuidando de **no** chocar puertos ni matar
otros `java`. Es el dolor que el ingeniero quiere eliminar: **un comando** que levanta la app y te da la URL.

**Ojo — NO lo cubre el Dockerfile generado (s11)**: ese corre `ObsServerKt` (observabilidad, PG-free, sólo `/health`),
NO el `AppServerKt` CRUD+frontend+PG. El launcher apunta al AppServer real (la app que se USA).

**SCOPE** — un launcher de DESARROLLO (DX), NO una capacidad verificada con diente. La verificación de que "la app
corre" YA tiene dientes: el check `frontend_browser_render` (s9) levanta server+PG+Chromium y lo prueba e2e. Este
incremento NO agrega un gate; es una conveniencia honesta (residual DX aceptado, como un script de `tools/`). El
sustrato (`seed/`, `src/metafactory/`) NO se toca: vive 100% en `factories/full-stack-kotlin/tools/` + un skill.

---

## 1. Diseño
**`factories/full-stack-kotlin/tools/dev_run.sh [PRODUCTO|stop|status] [PRODUCTO]`** (bash, committeado):
- **`up` (default)**: autodetecta `JAVA_HOME`; elige un **puerto libre** para la app y otro para PG (vía el SO, sin
  hardcodear); levanta una **PG docker propia** (nombre `fsk-dev-<producto>`, digest pineado — el MISMO que el proof);
  re-bundlea el frontend (`build_bundle.mjs`); lanza `AppServerKt` con las 4 env vars; espera `/health`; **imprime la
  URL**. Guarda el estado (PID, container, puertos, URL) en un dir de runtime para poder pararlo.
- **`stop`**: mata SÓLO su PID + borra SÓLO su container (nunca un `java`/docker ajeno).
- **`status`**: muestra la URL + si está vivo.
- **Robustez / no-fragilidad**: NO toca el `java -jar app.jar` del ingeniero ni daemons gradle (puerto+container
  propios, PID trackeado, jamás `pkill java`); falla con un mensaje+fix claro si falta el build (`build/install/<p>/lib`)
  o `node_modules` (→ corré `product-run` una vez). DATA-agnóstico: el `<pkg>`/entidad-dueño salen del spec efectivo.

**Skill `correr-app`** (`.claude/skills/correr-app/SKILL.md`): para que el ingeniero diga "corré la app" / `/correr-app
[producto]` y el orquestador invoque `tools/dev_run.sh`. `.md` → sin diente (a-demanda, ley de colocación).

---

## 2. Criterio de cierre
1. `tools/dev_run.sh snipeit` levanta la app de cero (PG + bundle + AppServer), espera `/health`, imprime la URL; abrir
   la URL en un browser muestra la HOME del dashboard con conteos VIVOS. `stop` desarma todo limpio.
2. NO toca otros procesos (el `java -jar app.jar` del ingeniero sigue vivo). Sustrato `seed/`+`src/metafactory/` = 0.
3. STATE/LOG (fábrica) actualizados. Abrí/decidí el siguiente con el ingeniero (pulido frontend vs backend backlog).

## Evidencia (cierre — se completa al terminar)
