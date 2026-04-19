# Product Requirements Document: Declaración Anual — Entrada Manual + Fix de Sesión

## Problem & Goal

La versión 1 del módulo Declaración, ya desplegada, presenta dos problemas:

1. **UX equivocada:** muestra una grid fija de años 2020-2026. El usuario real solo necesita declarar cualquier año pasado específico cuando lo requiera, no navegar por todos. Se desperdicia espacio visual y confunde.
2. **Bug crítico en producción: la descarga no funciona.** Causa raíz identificada: el manejo de sesión en `server/session.ts` usa un `Map<>` en memoria. En **Vercel serverless** cada invocación puede aterrizar en un instance distinto, por lo que el `sessionToken` que genera `/api/login` en un instance **no existe** en el instance que atiende `/api/reporte-anual`. El resultado es un 401 silencioso. Esta misma causa raíz explicaba el bug original que mitigamos con el "doble login" — también es un workaround que debemos eliminar al hacer el fix definitivo.

**Goal:** Rediseñar la vista de Declaración para que el usuario ingrese manualmente un año con validación, y corregir de raíz el bug de sesión moviéndonos a una arquitectura **stateless-friendly** donde las cookies SEMS se guardan cifradas en IndexedDB del cliente y se envían en cada request al proxy. De paso, eliminar el workaround del doble login porque ya no será necesario.

---

## Requirements

### Must-Have Features

#### 1. Entrada manual de año en la página `/declaracion`
- Sustituir la grid de años por un formulario compacto:
  - Un `<UInput>` numérico **tipo year** con `min=2015` y `max=añoActual−1` (2015–2025 al día de hoy).
  - Botón **"Descargar reporte"** que dispara la descarga vía proxy.
  - **Validación en vivo:**
    - Entero (sin decimales ni texto).
    - `2015 ≤ año ≤ añoActual − 1`.
    - Mensaje de error claro al lado del input si está fuera de rango.
- El botón se deshabilita mientras `!esValido(año)` o mientras está descargando.

#### 2. Lista "Reportes guardados" debajo del input
- Tabla/lista compacta con los reportes ya descargados por el usuario (query a IndexedDB `reportesAnuales`).
- Cada fila: **año** · tamaño · fecha descarga · botones **Ver** (`/declaracion/[año]`) y **Re-descargar** (overwrite).
- Ordenada desc por año.
- Si no hay ninguno: placeholder "Aún no has descargado ningún reporte. Ingresa un año arriba para empezar."

#### 3. Fix de raíz: cookies SEMS en IndexedDB del cliente
Migrar del modelo stateful a stateless:

**Cambios backend:**
- `/api/login.post.ts`: además de `session_token` y `rfc`, retornar **`cookies: string[]`** (las cookies SEMS extraídas).
- `/api/reporte-anual.post.ts`, `/api/download-pdf.post.ts`, `/api/download-quincena.post.ts`, `/api/comprobantes.post.ts`: aceptar **`cookies: string[]`** en el body y usarlas directamente para hacer el request a SEMS. Ya no dependen del `Map<>` en memoria.
- `server/session.ts`: conservar solo como referencia de constantes/headers. Eliminar (o marcar como deprecated) `createSession`, `getSession`, `deleteSession`, y el `Map<>`. Mantener `authenticateWithSEMS`, `extractCookies`, `cookiesToString` que son puras.

**Cambios frontend:**
- `app/db/schema.ts`: agregar campo `semsCookies: string[]` a `Session` o crear tabla separada `semsSessions` (1:1 con `Session`).
- `app/services/auth.service.ts`: al recibir la respuesta del login, guardar `cookies` en la tabla.
- `app/services/http.service.ts` y `app/utils/declaracion.ts`: leer las cookies de IndexedDB y enviarlas en el body de cada request al proxy.
- Al hacer `reauthenticate()` por 401, actualizar las cookies con las nuevas.

**Beneficio colateral:** eliminar el workaround de **doble login transparente** en `auth.service.ts` (`login()` con `_isRetry`). Si el fix de cookies resuelve el bug de raíz, el segundo login ya no es necesario.

#### 4. Manejo de errores al descargar (mantener comportamiento actual)
- `sesion-expirada` (401) → toast/alert "Tu sesión expiró, vuelve a entrar" + redirige a `/login` tras confirmación.
- `sin-datos` (422) → alert inline "El portal no tiene información para el año X".
- `red` → "Error de conexión, intenta de nuevo".
- Otros → mensaje genérico con status.

#### 5. Mantener página detalle `/declaracion/[año]`
- Sin cambios estructurales mayores. Sigue renderizando PDF embebido + botones.
- Si el año en la URL no está guardado localmente, mostrar "No tienes este reporte descargado" con CTA para volver a `/declaracion`.

### Technical Requirements

- **Framework**: Nuxt 4.2 + Vue 3 Composition API. Sin cambios.
- **DB**: Dexie `tsolbiil_db`, bump a **version 4** si agregamos columna/tabla de cookies SEMS.
- **UI**: Nuxt UI 4.4 (`UInput`, `UButton`, `UAlert`, `UBadge`). Tailwind 4.1.
- **Validación**: Zod schema inline o vanilla JS (la validación de año es trivial, no necesita Zod).
- **Criterios de performance**: la descarga debe tardar < 3s (red + SEMS). El cache local es instantáneo.
- **Seguridad**: las cookies SEMS se guardan en la misma tabla/registro que la sesión y están detrás del `deviceSecret` igual que las credenciales. Nunca se exponen en localStorage ni logs.

### Architecture & Design

**Flujo nuevo (stateless):**
```
┌─────────────┐   1. login(rfc, pass)    ┌──────────────┐
│ login.vue   │ ────────────────────────▶│ /api/login   │
└─────────────┘                          │ + SEMS auth  │
       ▲                                 └──────┬───────┘
       │                                        │
       │  2. { sessionToken, rfc, cookies }     │
       │ ◀──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ IndexedDB.sessions       │
│  + semsCookies: string[] │  (cifrado con deviceSecret)
└──────────────────────────┘
       │
       │  3. descargar reporte
       ▼
┌──────────────┐  { cookies, anio }   ┌──────────────────┐
│  frontend    │ ────────────────────▶│ /api/reporte-anual│
└──────────────┘                      │  usa cookies     │
                                      │  → SEMS          │
                                      └────────┬─────────┘
                                               │ PDF binary
       ◀───────────────────────────────────────┘
```

**Decisiones de diseño:**
- **Stateless server** porque Vercel. Ningún endpoint almacena estado entre invocaciones.
- **Cookies en cliente cifradas** porque ya tenemos `deviceSecret` + `AES-GCM` para las credenciales; agregar cookies es trivial.
- **Una sola tabla `sessions` con campo `semsCookies`** (no tabla nueva) — es 1:1 y simplifica queries.
- **UI compacta** — el usuario no escanea años, ingresa el que necesita. Histórico abajo para acceso rápido a los ya bajados.

---

## Out of Scope

- ❌ **Grid/listado de años predefinidos** — se elimina en esta versión.
- ❌ **Descarga automática masiva de múltiples años** — solo uno a la vez.
- ❌ **Validar si SEMS tiene datos antes de descargar** — el portal mismo responderá con error si no hay.
- ❌ **Guardar el cálculo en otras tablas de IndexedDB** — seguimos en `reportesAnuales` con el PDF Blob.
- ❌ **Quitar el Supabase / usar cloud storage** — las cookies se quedan en IndexedDB cliente.
- ❌ **Soporte multi-RFC** — sigue siendo un usuario activo a la vez.
- ❌ **Reintentos automáticos con backoff** — si falla, el usuario vuelve a presionar.

---

## Additional Context

- **Fecha de generación:** 2026-04-16.
- **Estado actual en producción:** https://tsolbil.vercel.app/declaracion — muestra grid fija de años 2020-2026, descarga retorna error silencioso o mensaje genérico.
- **Diagnóstico del bug:** el stack trace esperado en los logs de Vercel debería mostrar que `/api/reporte-anual` retorna 401 con `"Sesión inválida o expirada"`, porque `getSession(session_token)` devuelve `null` al no encontrar el token en el `Map<>` del instance que está atendiendo la request. Confirmar en el inspector si hay tiempo.
- **Impacto del fix de sesión:** afecta también el flujo de descarga de comprobantes (`/descargar`) y los otros endpoints (`/api/comprobantes`, `/api/download-pdf`, `/api/download-quincena`). Tocar esos endpoints en la misma PR para mantener consistencia. **Este refactor es más grande de lo que se ve a primera vista.**
- **Deprecation del doble login:** una vez aplicado el fix, quitar el parámetro `_isRetry` y el warmup en `app/services/auth.service.ts:login()`.
- **Prioridad:** el bug de descarga es **crítico** (producción rota). La entrada manual es **alta** (UX). Ambos en el mismo commit/deploy porque están en el mismo archivo.

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-16T13:00:00Z*
