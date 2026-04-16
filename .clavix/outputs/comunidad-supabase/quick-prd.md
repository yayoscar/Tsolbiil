# Comunidad Supabase Migration - Quick PRD

**Goal:** Migrar el almacenamiento de comentarios del módulo `/comunidad` desde Upstash Redis / archivo JSON local a Supabase PostgreSQL (proyecto `tsolbil`, ID `dtiimtpjpvdasbpulddm`). Reemplazo total — Redis se elimina del flujo. Mantener exactamente la misma funcionalidad: guardar `nombre`, `mensaje`, `fecha` y listarlos en orden cronológico inverso.

**Tech stack:** Nuxt 4 server API + `@supabase/supabase-js` con `anon public` key. RLS activado **con políticas explícitas**: `select` y `insert` permitidos para rol `anon`; `update` y `delete` bloqueados. Tabla `public.comunidad_entries` con `id uuid`, `nombre text` (1-80 chars), `mensaje text` (1-1500 chars), `fecha timestamptz`, `created_at timestamptz`, más CHECK constraints que refuerzan los límites a nivel DB. Variables de entorno: `SUPABASE_URL` y `SUPABASE_ANON_KEY` en Vercel. Reescribir `webapp/server/utils/community-store.ts` manteniendo la interfaz pública (`listCommunityEntries`, `createCommunityEntry`) para que los endpoints `POST /api/comunidad` y `POST /api/comunidad-list` no requieran cambios.

**Scope boundaries:** No autenticación, no moderación, no soft-delete, no metadata anti-spam, no realtime, no edición/borrado desde UI, no paginación, no búsqueda. Migración de datos existentes desde Redis es manual y opcional. ⚠️ El password de DB compartido en chat debe rotarse de inmediato en Supabase Dashboard (la anon key sí es segura para exponer).

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-15*
