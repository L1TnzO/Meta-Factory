# Incremento FSK-DEV-RUN — una forma FÁCIL de iniciar la app (DX, no-fragil)

> **Doc de gobierno de la FÁBRICA** (nivel `factories/full-stack-kotlin/`, ADR-016). Estado: **CERRADO**
> (2026-06-25T16:08Z; ver §Evidencia). Abierto 2026-06-25T15:51Z.
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

## Evidencia (cierre 2026-06-25T16:08Z, commit feat `0c3c509`)
**Construido** — `factories/full-stack-kotlin/tools/dev_run.sh` (bash) + skill `correr-app`. Sustrato `seed/`+
`src/metafactory/` = **0**. `tools/dev_run.sh [PRODUCTO|stop|status] [PRODUCTO]`:
- **`up`** (default `snipeit`): autodetecta `JAVA_HOME`; **puerto libre AUTO** para app y PG (via el SO, `python3
  socket`); PG docker propia (`fsk-dev-<p>`, digest pineado = el del proof s1/s7/s9); re-bundlea el frontend; lanza
  `<pkg>.endpoints.AppServerKt` con las env vars; espera `/health`; **imprime la URL**. Si falta el build →
  `./gradlew installDist` / `npm install` (self-heal). DATA-agnóstico: `package_name` del spec efectivo (ADR-012).
- **`stop`** mata SÓLO su PID + borra SÓLO su PG/url/pid · **`status`** muestra URL+vida.

**Decisión técnica clave (bug encontrado y corregido en vivo)**: el server se lanza con el idiom `( cd …; export …;
exec java ) >log 2>&1 & echo $! >app.pid; disown`. La 1ra versión usó `nohup env java` → `nohup` FORKEA (no exec) →
`app.pid` apuntaba al wrapper y `stop` dejaba el `java` HUÉRFANO (verificado: tras `stop`, el JVM seguía vivo). El
`exec` hace que el subshell SE CONVIERTA en java → `$!` (capturado en el padre) ES el PID de java → `stop` lo mata de
verdad. Lección reusable para cualquier launcher de proceso de fondo en esta fábrica.

**Verificado VIVO (con mis ojos, ciclo completo)**:
- `dev_run.sh snipeit` → PG en puerto libre + bundle + AppServer en puerto libre → **`/health` `{"status":"UP"}`** ·
  `app.pid` == el PID real del java (`pgrep -x java`) · `GET /assets` count=3.
- **camino completo launcher→app→browser**: `browser_check.ts` (Chromium REAL) contra la URL del launcher → la HOME
  muestra el **dashboard con conteos VIVOS** (`Asset: 3`), lista/form/detalle/edit/operations verdes.
- **`stop`**: `kill -0` confirma el java MUERTO + PG eliminada + url/pid borrados, sin huérfanos.
- **Seguridad**: el `java -jar app.jar` del ingeniero (PID 4020) queda **intacto** en todo el ciclo (el launcher usa
  puerto+PG+PID propios, jamás `pkill java`).

**Resultado**: el ingeniero corre la app con `factories/full-stack-kotlin/tools/dev_run.sh` (o el skill `correr-app` /
"corré la app"). Se eliminó la secuencia larga y frágil. **Siguiente**: ver `FSK-FRONTEND-DELETE-INCREMENT.md` (la
recomendación) o el fork de §3 del handoff de DASHBOARD (pulido frontend vs backend backlog) — decisión con el ingeniero.
