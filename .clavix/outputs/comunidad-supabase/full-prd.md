# Product Requirements Document: Comunidad Supabase Migration

## Problem & Goal

**Problema:** El módulo de Comunidad en `https://tsolbil.vercel.app/comunidad` actualmente almacena comentarios en Upstash Redis (producción) o en un archivo JSON local (desarrollo). Esta arquitectura limita la capacidad de consulta, no permite SQL relacional, y depende de un servicio adicional que no es la base de datos principal del proyecto.

**Goal:** Migrar el almacenamiento de comentarios de la Comunidad a Supabase PostgreSQL para tener una única base de datos relacional, queries más potentes, y una arquitectura más simple. Reemplazar completamente Redis y el archivo local.

## Requirements

### Must-Have Features

1. **Tabla `comunidad_entries` en Supabase** — Almacena `id` (UUID), `nombre` (text), `mensaje` (text), `fecha` (timestamptz)
2. **Insertar comentario nuevo** — Endpoint `POST /api/comunidad` escribe a Supabase
3. **Listar comentarios recientes** — Endpoint `POST /api/comunidad-list` lee de Supabase ordenado por fecha DESC
4. **Validación server-side** — Mantener validación actual (nombre y mensaje requeridos, trim, longitud)
5. **Reemplazo total de Redis/archivo local** — Eliminar lógica de fallback Redis y archivo, dejar solo Supabase

### Technical Requirements

**Stack:**
- Supabase PostgreSQL (project: `tsolbil`, ID: `dtiimtpjpvdasbpulddm`)
- `@supabase/supabase-js` (nueva dependencia)
- Acceso desde Nuxt server/api usando `anon public` key (RLS activado con políticas explícitas para `select` e `insert` públicas)

**Variables de entorno necesarias en Vercel:**
```bash
SUPABASE_URL=https://dtiimtpjpvdasbpulddm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0aWltdHBqcHZkYXNicHVsZGRtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyODI5NjAsImV4cCI6MjA5MTg1ODk2MH0.K96DWPwMT4QGluXVqcT_UfXXVwPYKN4kZIbJfwkcUpg
```

> ℹ️ La `anon public` key es segura para exponer (está diseñada para ello). La seguridad real vive en las políticas RLS de Supabase: solo permitimos `select` e `insert`, nunca `update` ni `delete` desde anon.

### Architecture & Design

- **Cliente Supabase singleton** en `webapp/server/utils/supabase.ts`
- **Reescribir** `webapp/server/utils/community-store.ts` para usar Supabase en lugar de Redis/file
- **Mantener la interfaz pública** (`listCommunityEntries`, `createCommunityEntry`) sin cambios — los endpoints no requieren modificación
- **Eliminar** dependencia `@upstash/redis` del `package.json` (si no se usa en otros módulos)

### SQL Scripts (Para ejecutar manualmente en Supabase)

**Ubicación:** Supabase Dashboard → SQL Editor → New query

#### Script 1: Crear extensión, tabla y constraints (idempotente)

```sql
-- Extensión para generar UUIDs (normalmente ya viene activada en Supabase)
create extension if not exists "pgcrypto";

-- Tabla principal
create table if not exists public.comunidad_entries (
  id          uuid          primary key default gen_random_uuid(),
  nombre      text          not null,
  mensaje     text          not null,
  fecha       timestamptz   not null default now(),
  created_at  timestamptz   not null default now()
);

-- Constraints de longitud (drop + add para que el script sea re-ejecutable)
alter table public.comunidad_entries
  drop constraint if exists comunidad_entries_nombre_check;
alter table public.comunidad_entries
  add  constraint comunidad_entries_nombre_check
       check (char_length(trim(nombre)) between 1 and 80);

alter table public.comunidad_entries
  drop constraint if exists comunidad_entries_mensaje_check;
alter table public.comunidad_entries
  add  constraint comunidad_entries_mensaje_check
       check (char_length(trim(mensaje)) between 1 and 1500);

-- Índice para ordenar rápido por fecha
create index if not exists comunidad_entries_fecha_desc_idx
  on public.comunidad_entries (fecha desc);

comment on table public.comunidad_entries is
  'Comentarios públicos del módulo Comunidad de Tsolbiil';
```

#### Script 2: Row Level Security (RLS) con políticas para anon (idempotente)

Como usamos la `anon public` key, RLS debe estar activado **con políticas explícitas** que permitan solo lo que necesitamos: leer e insertar. NUNCA permitimos update ni delete desde anon.

```sql
-- Activar RLS
alter table public.comunidad_entries enable row level security;

-- Política de lectura: cualquiera puede leer todos los comentarios
drop policy if exists "comunidad_select_anon" on public.comunidad_entries;
create policy "comunidad_select_anon"
  on public.comunidad_entries
  for select
  to anon
  using (true);

-- Política de inserción: cualquiera puede crear comentarios
-- with check valida longitudes (los CHECK constraints de la tabla refuerzan esto a nivel DB)
drop policy if exists "comunidad_insert_anon" on public.comunidad_entries;
create policy "comunidad_insert_anon"
  on public.comunidad_entries
  for insert
  to anon
  with check (
    char_length(trim(nombre)) between 1 and 80
    and char_length(trim(mensaje)) between 1 and 1500
  );

-- NO se crean políticas para UPDATE ni DELETE → quedan bloqueadas para anon
```

#### Script 3: Verificación

```sql
-- Verificar que la tabla existe y tiene la estructura correcta
select column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name = 'comunidad_entries'
order by ordinal_position;

-- Verificar RLS activado
select tablename, rowsecurity
from pg_tables
where schemaname = 'public' and tablename = 'comunidad_entries';

-- Verificar políticas creadas (deberían aparecer 2: select y insert)
select policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'comunidad_entries';

-- Test insert (luego borra el row de prueba)
insert into public.comunidad_entries (nombre, mensaje)
values ('Test', 'Comentario de prueba')
returning *;

-- Borrar el test (esto solo funcionará desde el SQL Editor, no desde anon)
delete from public.comunidad_entries where nombre = 'Test';
```

#### Script 4 (opcional): Migrar datos existentes desde Redis/JSON

Si quieres conservar los comentarios actuales:

```sql
-- Ejecuta esto DESPUÉS de exportar el JSON desde Redis/archivo local
-- Reemplaza los valores con los datos reales
insert into public.comunidad_entries (id, nombre, mensaje, fecha, created_at)
values
  ('uuid-existente-1', 'Nombre 1', 'Mensaje 1', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('uuid-existente-2', 'Nombre 2', 'Mensaje 2', '2025-01-02T00:00:00Z', '2025-01-02T00:00:00Z')
on conflict (id) do nothing;
```

## Out of Scope

- ❌ Autenticación de usuarios para comentar (sigue siendo público)
- ❌ Moderación, soft-delete, o campo `aprobado` (MVP estricto)
- ❌ Captura de IP, user_agent o metadata anti-spam
- ❌ Lectura directa desde el cliente con anon key (todo pasa por server)
- ❌ Realtime subscriptions de Supabase
- ❌ Edición o borrado de comentarios desde la UI
- ❌ Paginación o búsqueda (se carga todo el listado como hoy)
- ❌ Migración automática de datos Redis → Supabase (manual si se requiere)

## Additional Context

**Credenciales del proyecto Supabase (referencia):**
- Project name: `tsolbil`
- Project ID: `dtiimtpjpvdasbpulddm`
- URL: `https://dtiimtpjpvdasbpulddm.supabase.co`
- Anon public key: la del chat (segura para exponer, va en Vercel como `SUPABASE_ANON_KEY`)
- Service role key: **NO se usa en este flujo**

**⚠️ ALERTA DE SEGURIDAD:**
El password de la base de datos fue compartido en chat (`CxhYV19hCSCq8t3a`). **Debe rotarse de inmediato** en Supabase Dashboard → Project Settings → Database → Reset password. Asume que está comprometido.

**Archivos afectados en el código:**
- `webapp/server/utils/community-store.ts` — reescribir para usar Supabase
- `webapp/server/utils/supabase.ts` — crear nuevo (cliente singleton)
- `webapp/server/api/comunidad.post.ts` — sin cambios (la interfaz se mantiene)
- `webapp/server/api/comunidad-list.post.ts` — sin cambios
- `webapp/package.json` — agregar `@supabase/supabase-js`, evaluar quitar `@upstash/redis`
- `webapp/.env.example` (si existe) — documentar `SUPABASE_URL` y `SUPABASE_ANON_KEY`

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-15*
