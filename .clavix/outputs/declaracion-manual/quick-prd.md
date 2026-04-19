# Declaración Anual — Quick PRD (Entrada Manual + Fix Sesión)

**Goal:** Refactorizar la vista `/declaracion` de la webapp Tsolbiil (ya en prod en tsolbil.vercel.app) para (1) reemplazar la grid fija de años 2020-2026 por un **input manual** con validación (entero, 2015 ≤ año ≤ añoActual−1) + botón "Descargar", con una lista de reportes ya guardados debajo para acceso rápido, y (2) arreglar de raíz el bug de descarga que ocurre en producción. Causa raíz del bug: `server/session.ts` guarda sesiones en un `Map<>` en memoria, pero Vercel es serverless — cada request puede ir a un instance distinto → `getSession(token)` retorna null → 401. El mismo bug era el que "arreglamos" con el workaround del doble login; ahora lo resolvemos de verdad.

**Fix técnico:** mover a arquitectura stateless. `/api/login` retorna las cookies SEMS junto al sessionToken; el cliente las guarda cifradas en IndexedDB (tabla `sessions` con nuevo campo `semsCookies: string[]`, DB v4, mismo `deviceSecret` que cifra credenciales); cada request a los proxies (`/api/reporte-anual`, `/api/comprobantes`, `/api/download-pdf`, `/api/download-quincena`) envía las cookies en el body y el server las usa directamente sin tocar estado. Se elimina `Map<>`, `createSession`, `getSession` en `server/session.ts`. Se elimina también el workaround de doble login en `auth.service.ts` (parámetro `_isRetry` y warmup) — ya no hace falta. Stack: Nuxt 4.2, Vue 3, Dexie, Nuxt UI 4.4, Tailwind 4.1.

**Fuera de alcance:** no hay grid ni lista predefinida de años (se elimina); no hay descarga masiva de múltiples años; no validamos si SEMS tiene datos antes de intentar (confiamos en que el portal responda con error si no los tiene); no migramos a Supabase/Redis para sesiones (IndexedDB cliente es suficiente); no hay reintentos automáticos con backoff (el usuario vuelve a presionar). Prioridad crítica: el bug de descarga rompe la funcionalidad en producción. Ambos cambios van en el mismo commit/deploy porque comparten archivos. El refactor de sesión impacta también el flujo de descarga de comprobantes — tocar los 4 endpoints proxy juntos para mantener consistencia.

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-16T13:00:00Z*
