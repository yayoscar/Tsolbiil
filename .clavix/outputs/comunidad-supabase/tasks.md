# Implementation Plan

**Project**: comunidad-supabase
**Generated**: 2026-04-15

## Technical Context & Standards

*Detected Stack & Patterns*
- **Architecture**: Nuxt 4 monolito (full-stack) — `app/` (cliente Vue) + `server/` (Nitro API)
- **Framework**: Nuxt 4 (compatibilityDate `2025-01-15`), Vue 3 Composition API
- **UI**: `@nuxt/ui` v4 (`UButton`, `UInput`, `UTextarea`, `UAlert`, `UIcon`) + Tailwind v4
- **State**: Composables en `app/composables/` (sin Pinia/Vuex)
- **API client**: `app/services/api.ts` + `useApi()` composable
- **Backend pattern**: `server/api/<endpoint>.post.ts` delega a `server/utils/<store>.ts` (función pura)
- **Validación**: server-side manual (no Zod en este flujo, aunque está disponible)
- **Env vars**: `.env` cargado por Nuxt; `NUXT_PUBLIC_*` para cliente, sin prefijo para server-only
- **Package manager**: pnpm 10.28.1
- **Linting**: ESLint con `commaDangle: 'never'`, `braceStyle: '1tbs'`
- **Conventions**: nombres de variables/funciones en inglés, strings UI en español, archivos kebab-case

---

## Phase 1: Setup & Dependencies

- [x] **Instalar SDK de Supabase** (ref: PRD § Technical Requirements)
  Task ID: phase-1-setup-01
  > **Implementation**: Ejecutar en `webapp/` el comando `pnpm add @supabase/supabase-js`.
  > **Details**: Verifica que la versión instalada sea ≥ `2.x`. No instales `@supabase/ssr` ni `@nuxtjs/supabase` — no los necesitamos porque solo accedemos desde Nitro server. Confirma que se actualiza `webapp/package.json` y `webapp/pnpm-lock.yaml`.

- [x] **Declarar runtimeConfig en nuxt.config.ts** (ref: PRD § Architecture & Design)
  Task ID: phase-1-setup-02
  > **Implementation**: Editar [webapp/nuxt.config.ts](webapp/nuxt.config.ts) agregando bloque `runtimeConfig` antes de `eslint`:
  > ```ts
  > runtimeConfig: {
  >   supabaseUrl: '',
  >   supabaseAnonKey: ''
  > },
  > ```
  > **Details**: Aunque el anon key es seguro de exponer, lo ponemos como server-only (sin `public:`) porque el flujo es 100% server-side. Nuxt mapea estos valores a `NUXT_SUPABASE_URL` y `NUXT_SUPABASE_ANON_KEY` automáticamente. NO uses `NUXT_PUBLIC_` ya que no se necesita en el cliente.

- [x] **Agregar variables al .env local y .env.example** (ref: PRD § Variables de entorno)
  Task ID: phase-1-setup-03
  > **Implementation**: Editar [webapp/.env](webapp/.env) y [webapp/.env.example](webapp/.env.example) agregando:
  > ```bash
  > # Supabase (módulo Comunidad)
  > NUXT_SUPABASE_URL=https://dtiimtpjpvdasbpulddm.supabase.co
  > NUXT_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # del Dashboard Supabase
  > ```
  > **Details**: En `.env.example` deja el valor del key como placeholder (ej. `your-anon-key-here`). En `.env` local pon el valor real. Verifica que `.env` esté en `.gitignore` (debería estarlo ya).

- [x] **Documentar las nuevas variables en ENV_CONFIG.md** (ref: PRD § Architecture & Design)
  Task ID: phase-1-setup-04
  > **Implementation**: Editar [webapp/ENV_CONFIG.md](webapp/ENV_CONFIG.md). Agregar después de la sección `NODE_ENV` una nueva sección "## Supabase (Comunidad)" documentando `NUXT_SUPABASE_URL` y `NUXT_SUPABASE_ANON_KEY`.
  > **Details**: Sigue el formato existente del archivo (subsección con título, descripción, ejemplo de valor, nota de en qué módulo se usa). Aclara que aunque la anon key es pública por diseño, queda como variable server-side porque el módulo Comunidad accede solo desde Nitro.

---

## Phase 2: Supabase Client Layer

- [x] **Crear cliente Supabase singleton** (ref: PRD § Architecture & Design)
  Task ID: phase-2-supabase-01
  > **Implementation**: Crear nuevo archivo `webapp/server/utils/supabase.ts` exportando `getSupabaseClient(): SupabaseClient`.
  > **Details**:
  > - Importar `createClient, type SupabaseClient` desde `@supabase/supabase-js`
  > - Patrón singleton con variable `let client: SupabaseClient | null = null` a nivel módulo
  > - Leer credenciales con `useRuntimeConfig().supabaseUrl` y `.supabaseAnonKey` (Nitro provee `useRuntimeConfig` global)
  > - Si faltan credenciales, lanzar `Error('Supabase no configurado: define NUXT_SUPABASE_URL y NUXT_SUPABASE_ANON_KEY')`
  > - Configurar el client con `{ auth: { persistSession: false, autoRefreshToken: false } }` (no necesitamos sesión)
  > - Respetar el estilo del codebase: `commaDangle: 'never'`, brace `1tbs`, sin punto y coma final si el resto del proyecto no los usa (revisar `community-store.ts` actual: NO usa punto y coma final)

---

## Phase 3: Migrate Community Store

- [x] **Definir tipo y constantes para la fila de Supabase** (ref: PRD § Must-Have Features)
  Task ID: phase-3-store-01
  > **Implementation**: En el nuevo `webapp/server/utils/community-store.ts` (reescrito), agregar al inicio:
  > ```ts
  > const TABLE = 'comunidad_entries'
  > interface CommunityEntryRow {
  >   id: string
  >   nombre: string
  >   mensaje: string
  >   fecha: string
  >   created_at: string
  > }
  > ```
  > **Details**: La interface `CommunityEntry` pública (con `id, nombre, mensaje, fecha`) se mantiene SIN cambios para no romper consumidores. `CommunityEntryRow` es interna, solo para tipar las queries de Supabase.

- [x] **Reescribir `listCommunityEntries()` para usar Supabase** (ref: PRD § Must-Have Features #3)
  Task ID: phase-3-store-02
  > **Implementation**: Reemplazar el cuerpo actual de `listCommunityEntries` en [webapp/server/utils/community-store.ts](webapp/server/utils/community-store.ts) con:
  > - `const supabase = getSupabaseClient()`
  > - Query: `supabase.from(TABLE).select('id, nombre, mensaje, fecha').order('fecha', { ascending: false })`
  > - Si `error` no es null, hacer `console.error('[Supabase] list error:', error)` y retornar `[]` (mismo comportamiento de fallback que tenía con Redis)
  > - Mapear `data ?? []` al tipo `CommunityEntry` (los campos coinciden 1:1)
  > **Details**: Mantener la misma signatura `Promise<CommunityEntry[]>`. La ordenación que antes hacía `localeCompare` ahora la hace Postgres con el índice `comunidad_entries_fecha_desc_idx`.

- [x] **Reescribir `createCommunityEntry()` para usar Supabase** (ref: PRD § Must-Have Features #2)
  Task ID: phase-3-store-03
  > **Implementation**: Reemplazar el cuerpo de `createCommunityEntry` con:
  > - Mantener validación inicial (`nombre.trim()`, `mensaje.trim()`, throws si vacío) — no la borres
  > - `const supabase = getSupabaseClient()`
  > - Insert: `supabase.from(TABLE).insert({ nombre, mensaje }).select('id, nombre, mensaje, fecha').single()`
  > - El `id`, `fecha` y `created_at` los genera Postgres por defecto, no los mandes
  > - Si `error`, lanzar `new Error(error.message || 'No se pudo guardar el comentario')` (el handler de la API lo captura)
  > - Retornar `data` (ya cumple `CommunityEntry`)
  > **Details**: Mantener signatura `Promise<CommunityEntry>`. Eliminar `randomUUID()` import — ya no se necesita.

- [x] **Eliminar código muerto del store** (ref: PRD § Out of Scope — eliminar Redis)
  Task ID: phase-3-store-04
  > **Implementation**: En el `community-store.ts` reescrito, BORRAR completamente:
  > - Imports de `node:crypto`, `node:fs/constants`, `node:fs/promises`, `node:path`
  > - Import de `@upstash/redis`
  > - Función `parseRedisUrl`, `getRedisClient`
  > - Constantes `LOCAL_DATA_PATH`, `REDIS_KEY`, `DEFAULT_STORE`
  > - Variable `redis`
  > - Funciones `ensureDataFile`, `readLocalStore`, `writeLocalStore`, `readRedisStore`, `writeRedisStore`, `readStore`, `writeStore`, `isRedisAvailable`, `sanitizeEntries`
  > - Interface interna `CommunityStore`
  > **Details**: El archivo final solo debe contener: imports de Supabase + getSupabaseClient, constante TABLE, interface `CommunityEntry` (export), interface `CommunityEntryRow` (interna), y las dos funciones públicas `listCommunityEntries` y `createCommunityEntry`. Apunta a un archivo de ~50 líneas vs. las 274 actuales.

---

## Phase 4: Cleanup

- [x] **Borrar archivo de datos local obsoleto** (ref: PRD § Out of Scope)
  Task ID: phase-4-cleanup-01
  > **Implementation**: Borrar `webapp/server/data/community.json` si existe (`rm webapp/server/data/community.json`). Si la carpeta `webapp/server/data/` queda vacía, borrarla también.
  > **Details**: Este archivo era el fallback cuando no había Redis. Ya no se usa. Si tiene comentarios viejos que quieras conservar, primero exporta su contenido y migra manualmente con el Script 4 del PRD (insert SQL).

- [x] **Remover dependencia @upstash/redis del package.json** (ref: PRD § Out of Scope)
  Task ID: phase-4-cleanup-02
  > **Implementation**: Ejecutar en `webapp/`: `pnpm remove @upstash/redis`.
  > **Details**: Confirmé que `@upstash/redis` SOLO se usa en `community-store.ts` (no aparece en otros archivos del codebase). Es seguro removerlo. Verifica que `webapp/package.json` ya no lo lista y que `pnpm-lock.yaml` se actualizó.

---

## Phase 5: Verification

- [x] **Type-check del proyecto** (ref: PRD § Must-Have Features)
  Task ID: phase-5-verify-01
  > **Implementation**: Ejecutar en `webapp/`: `pnpm typecheck`.
  > **Details**: Debe pasar sin errores. Si hay errores en `community-store.ts` o en consumidores, ajustar. Los endpoints `comunidad.post.ts` y `comunidad-list.post.ts` NO deberían cambiar — la interfaz pública del store es la misma.

- [x] **Lint del proyecto** (ref: PRD § Conventions)
  Task ID: phase-5-verify-02
  > **Implementation**: Ejecutar en `webapp/`: `pnpm lint`.
  > **Details**: Aplicar `pnpm lint --fix` si hay errores cosméticos. Atender errores reales (imports faltantes, vars sin usar).

- [x] **Smoke test local** (ref: PRD § Must-Have Features #2 y #3)
  Task ID: phase-5-verify-03
  > **Implementation**: Ejecutar `pnpm dev` en `webapp/`. Abrir `http://localhost:3000/comunidad`.
  > **Details**: Validar manualmente:
  > 1. La lista carga (puede estar vacía, no debe haber error en consola)
  > 2. Enviar un comentario con nombre + mensaje → aparece arriba de la lista inmediatamente
  > 3. Recargar la página → el comentario persiste (esto confirma que está en Supabase, no en memoria)
  > 4. En el SQL Editor de Supabase: `select * from comunidad_entries order by fecha desc limit 5;` → debe mostrar el row insertado
  > 5. Probar enviar con campos vacíos → debe mostrar error de validación (no debe llegar a Supabase)

- [x] **Configurar variables en Vercel** (ref: PRD § Variables de entorno)
  Task ID: phase-5-verify-04
  > **Implementation**: En el dashboard de Vercel del proyecto Tsolbiil → Settings → Environment Variables. Agregar:
  > - `NUXT_SUPABASE_URL` = `https://dtiimtpjpvdasbpulddm.supabase.co` (Production + Preview + Development)
  > - `NUXT_SUPABASE_ANON_KEY` = el anon key (Production + Preview + Development)
  > **Details**: Después de agregar las vars, hacer un nuevo deploy (push a main o redeploy manual). NO se requiere secret encryption porque la anon key está diseñada para ser pública. Opcional: remover las vars viejas `UPSTASH_REDIS_REST_*` o `REDIS_URL` si ya no se usan en otro módulo.

- [x] **Smoke test en producción** (ref: PRD § Must-Have Features)
  Task ID: phase-5-verify-05
  > **Implementation**: Una vez deployado, abrir `https://tsolbil.vercel.app/comunidad` y repetir los pasos del smoke test local (insert + reload + verificar en Supabase Dashboard).
  > **Details**: Si falla, revisar logs de Vercel: Functions → comunidad.post → ver si el error es de credenciales (`Supabase no configurado`) o de red (RLS bloqueando, política mal escrita, etc.). Si RLS bloquea: re-correr el Script 2 del PRD.

---

*Generated by Clavix /clavix:plan*
