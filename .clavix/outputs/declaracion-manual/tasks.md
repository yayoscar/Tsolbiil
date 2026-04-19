# Implementation Plan

**Project**: declaracion-manual
**Generated**: 2026-04-16T13:30:00Z

## Technical Context & Standards
*Detected Stack & Patterns*

- **Architecture**: Nuxt 4 flat structure + Nitro server (stateless serverless on Vercel).
- **Framework**: Nuxt 4.2 + Vue 3 Composition API (`<script setup lang="ts">`). Autoimports.
- **DB**: Dexie sobre IndexedDB, `tsolbiil_db` (actual: v3, a bumpear a v4). Cifrado con `deviceSecret` + AES-GCM.
- **Styling**: Tailwind 4.1 + Nuxt UI 4.4 (`UInput`, `UButton`, `UAlert`, `UBadge`).
- **Validación**: inline JS para cosas triviales; Zod solo donde ya está (login).
- **Conventions**: camelCase utils, PascalCase components, español para UI, `Intl.NumberFormat('es-MX', …)` para moneda.
- **Estado deploy**: https://tsolbil.vercel.app — descarga rota por sesiones en memoria en serverless.

**Refactor arquitectónico**:
Migrar de *stateful server* (`Map<>` de sesiones) a *stateless server* + cookies SEMS cifradas en IndexedDB del cliente. Afecta 4 endpoints proxy + schema DB + auth service.

**Orden de ejecución**: schema DB → login backend → endpoints proxy → auth service → utils frontend → UI → limpieza → verificación. Este orden minimiza el tiempo en que la app está rota durante la transición local.

---

## Phase 1: Schema IndexedDB (cookies cifradas) (ref: PRD §Fix de raíz)

- [x] **Agregar campo `semsCookies` cifrado en schema**
  Task ID: `phase-1-schema-01`
  > **Implementation**: Editar [webapp/app/db/schema.ts](webapp/app/db/schema.ts).
  > **Details**:
  > - En la interfaz `Session` agregar campo opcional: `semsCookies?: string[]`. Al ser array de strings (ej. `['JSESSIONID=abc', 'otra=xyz']`), lo guardamos **tal cual**, no cifrado individualmente. Toda la tabla IndexedDB ya es local; la protección real está al nivel de credentials (`authSecrets`), no sesiones (Sessions ya expone `sessionToken` en claro).
  > - Para consistencia: documentar en comentario que las cookies viven solo en el dispositivo del usuario y expiran con el logout (sesión marcada `isActive=false`). No es información sensible por sí sola (son cookies de sesión de una app que requiere auth para ser emitidas).
  > - No tocar `AuthSecret` (credenciales) — ese flujo no cambia.

- [x] **Bumpear DB a versión 4 con migración**
  Task ID: `phase-1-schema-02`
  > **Implementation**: Editar [webapp/app/db/db.ts](webapp/app/db/db.ts).
  > **Details**:
  > - Agregar `this.version(4).stores({...})` con el mismo shape que v3 (solo campos indexados cambian, y `semsCookies` **NO necesita índice** — queda como columna no indexada).
  > - Como Dexie solo requiere reindexación al agregar/cambiar índices, técnicamente v4 puede ser idéntica a v3 y el nuevo campo se suma implícitamente a cada registro. Sin embargo, bumpear la versión hace el cambio **explícito** y permite escribir una migración futura si hace falta.
  > - **Migración opcional** (recomendada): en v4, para sesiones existentes `isActive=true` sin `semsCookies`, marcarlas como inactivas para forzar re-login limpio. Hacerlo con `.upgrade(tx => tx.table('sessions').where('isActive').equals(1).modify({ isActive: false, lastError: 'migracion-v4' }))`. Esto evita el caso "sesión vieja sin cookies" que causaría descargas fallidas sin explicación.

---

## Phase 2: Backend stateless (ref: PRD §Architecture)

- [x] **Modificar `/api/login` para devolver cookies**
  Task ID: `phase-2-backend-01`
  > **Implementation**: Editar [webapp/server/api/login.post.ts](webapp/server/api/login.post.ts).
  > **Details**:
  > - Tras `authenticateWithSEMS(rfc, password)` que ya devuelve `cookies: string[]`, **eliminar** la llamada a `createSession` (ya no mantenemos estado server).
  > - Cambiar la respuesta exitosa a: `{ success: true, message: 'Autenticación exitosa', rfc: body.rfc, cookies }`.
  > - Dejar de retornar `session_token` (lo genera ahora el cliente vía `crypto.randomUUID()` en auth.service si hace falta ID local).
  > - Mantener el flujo de error actual.

- [x] **Reescribir `/api/reporte-anual` para leer cookies del body**
  Task ID: `phase-2-backend-02`
  > **Implementation**: Editar [webapp/server/api/reporte-anual.post.ts](webapp/server/api/reporte-anual.post.ts).
  > **Details**:
  > - Cambiar el body esperado a: `{ anio: number, cookies: string[], rfc: string }`.
  > - Remover `getSession(session_token)` y la validación asociada.
  > - Validar: `cookies` es array no vacío, `rfc` es string no vacío, `anio` entero razonable.
  > - Construir el request a `REPORTE_ANUAL_ENDPOINT` usando `cookiesToString(body.cookies)` en el header `Cookie` y `body.rfc` en `username`.
  > - Mantener el manejo de errores (HTML redirect → 401, no-PDF → 422, tamaño < 200 → 422).
  > - Si `cookies` está vacío o inválido, retornar 400 con mensaje "cookies requeridas".

- [x] **Reescribir `/api/download-pdf` para leer cookies del body**
  Task ID: `phase-2-backend-03`
  > **Implementation**: Editar [webapp/server/api/download-pdf.post.ts](webapp/server/api/download-pdf.post.ts).
  > **Details**:
  > - Cambiar body esperado a: `{ cookies: string[], id_archivo: string, qna_proc: string }` (eliminar `session_token`).
  > - Remover `getSession`. Usar `cookiesToString(body.cookies)` directamente.
  > - Misma validación de campos requeridos.

- [x] **Reescribir `/api/download-quincena` para leer cookies del body**
  Task ID: `phase-2-backend-04`
  > **Implementation**: Editar [webapp/server/api/download-quincena.post.ts](webapp/server/api/download-quincena.post.ts).
  > **Details**:
  > - Mismo patrón: `{ cookies: string[], ...otros campos existentes }`.
  > - Remover `getSession`; usar cookies del body.

- [x] **Reescribir `/api/comprobantes` para leer cookies del body**
  Task ID: `phase-2-backend-05`
  > **Implementation**: Editar [webapp/server/api/comprobantes.post.ts](webapp/server/api/comprobantes.post.ts).
  > **Details**:
  > - Mismo patrón: `{ cookies: string[], ...otros }`.
  > - Remover `getSession`.

- [x] **Reescribir `/api/logout` como no-op server-side**
  Task ID: `phase-2-backend-06`
  > **Implementation**: Editar [webapp/server/api/logout.post.ts](webapp/server/api/logout.post.ts).
  > **Details**:
  > - Como ya no hay sesión en memoria, el endpoint solo retorna `{ success: true }` y el cliente limpia su propio estado. Opcionalmente, si el SEMS tiene un endpoint de logout explícito, se puede llamar ahí con las cookies, pero no es crítico.

- [x] **Limpiar `server/session.ts` eliminando el `Map` y helpers de estado**
  Task ID: `phase-2-backend-07`
  > **Implementation**: Editar [webapp/server/session.ts](webapp/server/session.ts).
  > **Details**:
  > - Eliminar: `sessions` (Map), `createSession`, `getSession`, `deleteSession`, `cleanupExpiredSessions`, `generateSessionToken`, `SESSION_TIMEOUT`, `setInterval`.
  > - Conservar: `BASE_URL`, `LOGIN_PAGE`, `AUTH_ENDPOINT`, `COMPROBANTES_ENDPOINT`, `DOWNLOAD_PDF_ENDPOINT`, `REPORTE_ANUAL_ENDPOINT`, `DEFAULT_HEADERS`, `cookiesToString`, `extractCookies`, `authenticateWithSEMS`, interface `ServerSession` (aún útil de tipo).
  > - Resultado: archivo puramente de utilidades puras + constantes, sin estado global.

---

## Phase 3: Auth service frontend (ref: PRD §Fix de raíz)

- [x] **Modificar `auth.service.ts:login()`**
  Task ID: `phase-3-auth-01`
  > **Implementation**: Editar [webapp/app/services/auth.service.ts](webapp/app/services/auth.service.ts).
  > **Details**:
  > - La respuesta del backend ahora es `{ success, rfc, cookies }` en vez de `{ success, session_token }`. Ajustar el tipo del `data`.
  > - Donde hoy se guarda la sesión en IndexedDB (línea ~163-173), además asignar `semsCookies: data.cookies` en el objeto `Session`.
  > - El `sessionToken` ya no viene del servidor. Generarlo local con `generateUUID()` (ya existe). Es solo un identificador local de la sesión para indexar registros; no viaja al backend.
  > - **Eliminar el workaround del doble login**: quitar el parámetro `_isRetry: boolean = false` y todo el bloque "8. Segundo login transparente" (líneas 176-186). Quitar también el comentario explicativo del warmup.

- [x] **Agregar helper para leer cookies de la sesión activa**
  Task ID: `phase-3-auth-02`
  > **Implementation**: Agregar al final de [webapp/app/services/auth.service.ts](webapp/app/services/auth.service.ts).
  > **Details**:
  > ```ts
  > export async function getSessionCookies(): Promise<{ cookies: string[], rfc: string } | null> {
  >   const active = await getActiveSession()
  >   if (!active?.session.semsCookies?.length) return null
  >   // RFC: podemos derivar de authSecrets o guardarlo en User.displayName (ya se hace).
  >   return { cookies: active.session.semsCookies, rfc: active.user.displayName ?? '' }
  > }
  > ```
  > - Usado por utils/declaracion.ts y cualquier otro call-site que arme requests a endpoints proxy.

- [x] **Actualizar `reauthenticate` para refrescar cookies**
  Task ID: `phase-3-auth-03`
  > **Implementation**: Editar función `reauthenticate` en [webapp/app/services/auth.service.ts](webapp/app/services/auth.service.ts).
  > **Details**:
  > - La función ya llama a `login(credentials.rfc, credentials.password)`. Con los cambios de phase-3-auth-01, automáticamente el nuevo login guardará las cookies frescas en IndexedDB. No requiere más cambios aquí — solo verificar que no quede referencia al parámetro `_isRetry` eliminado.

---

## Phase 4: Frontend calls (ref: PRD §Frontend)

- [x] **Actualizar `utils/declaracion.ts` para enviar cookies**
  Task ID: `phase-4-utils-01`
  > **Implementation**: Editar [webapp/app/utils/declaracion.ts](webapp/app/utils/declaracion.ts).
  > **Details**:
  > - Cambiar la firma: `descargarReporteAnual(userId: string, anio: number): Promise<DescargaResult>` — ya no recibe `sessionToken`, lo lee internamente.
  > - Dentro, llamar a `getSessionCookies()` (nuevo helper del auth.service). Si es `null`, devolver `{ ok: false, kind: 'sin-sesion', mensaje: 'No hay sesión activa' }`.
  > - Cambiar el body del fetch a: `{ anio, cookies: <array>, rfc: <string> }`.
  > - Resto igual: manejo de errores, caché en IndexedDB, etc.
  > - Remover `aniosDisponibles()` — ya no lo usamos (se elimina con la UI vieja).

- [x] **Actualizar composable `useDeclaracion`**
  Task ID: `phase-4-composable-01`
  > **Implementation**: Editar [webapp/app/composables/useDeclaracion.ts](webapp/app/composables/useDeclaracion.ts).
  > **Details**:
  > - Reescribir para el nuevo flujo:
  >   - Estado: `reportesGuardados = ref<ReporteAnual[]>([])`, `descargando = ref(false)`, `error = ref<string|null>(null)`.
  >   - `cargarGuardados()` → llama `listarReportesGuardados(userId)` y hidrata el array, ordenado desc por `anio`.
  >   - `descargar(anio: number): Promise<DescargaResult>` → llama `descargarReporteAnual(userId, anio)`; si ok, refresca `reportesGuardados`; si error, setea `error.value`.
  >   - `eliminar(anio)` sin cambios lógicos (usa nuevo helper).
  >   - `obtener(anio)` sin cambios.
  > - Eliminar: `AnioRow`, `EstadoAnio`, `setEstado`, `indexByAnio`, `anios` — no aplican al nuevo modelo.

- [x] **Revisar otros call-sites de endpoints refactorizados**
  Task ID: `phase-4-utils-02`
  > **Implementation**: Buscar usos de `/api/comprobantes`, `/api/download-pdf`, `/api/download-quincena` en todo `webapp/app/`.
  > **Details**:
  > - Comando sugerido: `grep -r "/api/comprobantes\|/api/download-pdf\|/api/download-quincena" webapp/app/`.
  > - Para cada call-site, cambiar el body para incluir `cookies` (via `getSessionCookies()`) y eliminar `session_token`.
  > - **Archivos esperados**: `app/pages/descargar.vue`, `app/pages/comprobantes/*.vue`, `app/services/*.ts`.
  > - Si un call-site usa `http.service.ts` (`http.post(...)`), ahí pasa el `Authorization: Bearer` que ahora es inútil. Dejarlo — no daña — o modificar `http.service.ts` para pre-inyectar cookies en el body (opcional, más invasivo).

---

## Phase 5: UI Declaración (ref: PRD §Entrada manual + Lista guardados)

- [x] **Crear componente `DeclaracionInputForm.vue`**
  Task ID: `phase-5-ui-01`
  > **Implementation**: Crear [webapp/app/components/DeclaracionInputForm.vue](webapp/app/components/DeclaracionInputForm.vue).
  > **Details**:
  > - Props: none. Emits: `descargar: [anio: number]`.
  > - Estado local: `anio = ref<number | null>(null)`, `descargando = ref<boolean>(false)` (prop también aceptable).
  > - Validación reactiva:
  >   ```ts
  >   const minAnio = 2015
  >   const maxAnio = computed(() => new Date().getFullYear() - 1)
  >   const esValido = computed(() => {
  >     if (anio.value === null) return false
  >     return Number.isInteger(anio.value) && anio.value >= minAnio && anio.value <= maxAnio.value
  >   })
  >   const mensajeValidacion = computed(() => {
  >     if (anio.value === null) return ''
  >     if (anio.value < minAnio) return `El año debe ser ${minAnio} o mayor`
  >     if (anio.value > maxAnio.value) return `El año debe ser ${maxAnio.value} o menor`
  >     return ''
  >   })
  >   ```
  > - UI: card con título "Descargar reporte", `<UInput type="number" :min="minAnio" :max="maxAnio" placeholder="Ej: 2024" v-model="anio" />` y `<UButton :disabled="!esValido || descargando" :loading="descargando" @click="$emit('descargar', anio)">Descargar reporte</UButton>`.
  > - Mensaje de validación inline debajo del input cuando `anio !== null && !esValido`.
  > - Hint: "Años aceptados: {{ minAnio }} – {{ maxAnio }}".

- [x] **Reescribir `DeclaracionAnoCard.vue` como "card de reporte guardado"**
  Task ID: `phase-5-ui-02`
  > **Implementation**: Editar [webapp/app/components/DeclaracionAnoCard.vue](webapp/app/components/DeclaracionAnoCard.vue). Renombrar lógicamente (conservar el nombre del archivo por simplicidad).
  > **Details**:
  > - Props cambia: `{ reporte: ReporteAnual; descargando?: boolean }`.
  > - Eliminar ramas `idle`/`descargando`/`error` que ya no aplican al contexto (siempre recibe un reporte guardado).
  > - UI: icono `i-lucide-file-check` verde, año destacado, meta de tamaño y fecha, botones **Ver** (`/declaracion/[año]`) y **Re-descargar** (emits `redescargar: [anio]`).
  > - Mantener estética consistente con resto del proyecto (`rounded-xl`, paleta brand/slate, dark mode).

- [x] **Reescribir `pages/declaracion/index.vue`**
  Task ID: `phase-5-ui-03`
  > **Implementation**: Editar [webapp/app/pages/declaracion/index.vue](webapp/app/pages/declaracion/index.vue).
  > **Details**:
  > - Estructura:
  >   - Header (título + descripción) — sin cambios.
  >   - `<DeclaracionInputForm @descargar="onDescargar" :descargando="descargando" />`.
  >   - `<UAlert v-if="error" color="error" variant="soft" :title="error" />` para mostrar errores de descarga.
  >   - Sección "Reportes guardados":
  >     - Si `reportesGuardados.length === 0`: placeholder con icono `i-lucide-folder-open` y texto "Aún no has descargado ningún reporte. Ingresa un año arriba para empezar."
  >     - Si hay: grid `md:grid-cols-2 lg:grid-cols-3` con `<DeclaracionAnoCard :reporte="r" @redescargar="onRedescargar" />`.
  >   - `<DeclaracionFundamentoLegal />` al final.
  >   - Disclaimer ámbar (mismo texto actual).
  > - `<script setup>`:
  >   - `const { reportesGuardados, descargando, error, cargarGuardados, descargar } = useDeclaracion()`.
  >   - `async function onDescargar(anio: number) { const r = await descargar(anio); if (r.ok) await cargarGuardados() }`.
  >   - `const onRedescargar = onDescargar` (mismo handler).
  >   - `onMounted(cargarGuardados)`.
  > - Eliminar código relacionado con `anios`, estados por año, etc.

- [x] **Actualizar `pages/declaracion/[anio].vue` para nuevo composable**
  Task ID: `phase-5-ui-04`
  > **Implementation**: Editar [webapp/app/pages/declaracion/[anio].vue](webapp/app/pages/declaracion/%5Banio%5D.vue).
  > **Details**:
  > - Mantener la estructura general (iframe + botones Actualizar/Descargar).
  > - Ajustar uso del composable: `const { obtener, descargar } = useDeclaracion()` ya disponible en la nueva API.
  > - `onRedescargar` sigue funcional.
  > - Verificar que los imports sigan válidos tras los cambios del composable.

---

## Phase 6: Limpieza (ref: PRD §Deprecation)

- [x] **Eliminar workaround de doble login de `auth.service.ts`**
  Task ID: `phase-6-cleanup-01`
  > **Implementation**: Editar [webapp/app/services/auth.service.ts](webapp/app/services/auth.service.ts).
  > **Details**:
  > - Ya se hizo implícitamente en `phase-3-auth-01`. Verificar que no queden referencias a `_isRetry` ni al console.warn "Warmup login falló".
  > - Actualizar comentario de docstring de `login()` para reflejar el nuevo flujo (sin warmup).

- [x] **Actualizar `AppSidebar.vue` si el item Declaración cambió**
  Task ID: `phase-6-cleanup-02`
  > **Implementation**: Revisar [webapp/app/components/AppSidebar.vue](webapp/app/components/AppSidebar.vue).
  > **Details**:
  > - Solo verificar que `to: '/declaracion'` sigue correcto. No hay cambios.

---

## Phase 7: Verificación y deploy (ref: PRD §Success criteria)

- [x] **Type-check completo**
  Task ID: `phase-7-verify-01`
  > **Implementation**: Ejecutar `cd webapp && pnpm typecheck` en terminal.
  > **Details**: Cero errores nuevos en los archivos tocados. Los errores pre-existentes documentados (crypto.ts, prestamos.ts, etc.) siguen siendo aceptables.

- [x] **Build local**
  Task ID: `phase-7-verify-02`
  > **Implementation**: `cd webapp && pnpm build`.
  > **Details**: Build exitoso. Verificar que el bundle output sigue cerca de ~14 MB (no se rompe nada gordo).

- [x] **Prueba manual en dev**
  Task ID: `phase-7-verify-03`
  > **Implementation**: `pnpm dev`, abrir localhost, logout completo, login limpio, ir a /declaracion.
  > **Details**:
  > 1. Input rechaza años fuera de 2015–2025 con mensaje claro.
  > 2. Con año válido (ej. 2024), botón descarga y guarda el PDF. Iframe se renderiza.
  > 3. Refresh de página: el reporte aparece en "Reportes guardados". Click "Ver" navega a `/declaracion/2024`.
  > 4. Click "Re-descargar" sobrescribe el cache.
  > 5. Probar año con posible error (ej. 2015 si no tienes datos) → debe mostrar mensaje del portal o genérico.
  > 6. Verificar en Network tab que el body del POST `/api/reporte-anual` incluye `cookies` y `rfc`.

- [x] **Commit y deploy a producción**
  Task ID: `phase-7-verify-04`
  > **Implementation**: `git add -A && git commit -m "refactor(declaracion): manual year input + stateless session" && npx vercel --prod --yes`.
  > **Details**: Commit message debe mencionar el fix del bug de sesión (causa raíz) y la eliminación del doble login workaround. Tras el deploy, probar inmediatamente en https://tsolbil.vercel.app/declaracion que la descarga funciona al primer intento.

---

*Generated by Clavix /clavix:plan*
