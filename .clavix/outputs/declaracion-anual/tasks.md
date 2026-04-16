# Implementation Plan

**Project**: declaracion-anual
**Generated**: 2026-04-16T00:00:00Z

## Technical Context & Standards
*Detected Stack & Patterns*

- **Architecture**: Nuxt 4 flat structure — `pages/` (rutas file-based), `composables/` (estado reactivo), `utils/` (lógica pura), `components/` (UI), `db/` (Dexie).
- **Framework**: Nuxt 4.2 + Vue 3 (Composition API, `<script setup lang="ts">`). Autoimports habilitados (`ref`, `computed`, `onMounted`, `useAuth`, `useRoute`).
- **Styling**: Tailwind CSS 4.1 + Nuxt UI 4.4 (`UButton`, `UIcon`, `UBadge`, `UTooltip`). Paleta `brand-*` y `slate-*`; dark mode vía `dark:`; clases custom `animate-fade-in`, `gradient-brand`, `hover-lift`, `transition-smooth` ya definidas en `assets/`.
- **Icons**: `@iconify-json/lucide` (prefijo `i-lucide-*`).
- **State/Data**: Sin store global; estado vía composables (`useAuth`, `useSession`). Persistencia en Dexie (`~/db/db.ts`, tablas `comprobantes`, `conceptos`). Índices relevantes: `[userId+anio]`, `[userId+anio+quincena]`, `[userId+comprobanteId]`, `[userId+categoria]`.
- **API**: Lógica local (no backend para esta feature). Import de DB en páginas vía `const { db } = await import('~/db/db')`; en utils import directo.
- **Conventions**:
  - Archivos: camelCase para utils/composables (`analisis.ts`, `useAnalisisSueldo.ts`), kebab/snake para pages (`descargar.vue`, `comprobantes/[anio].vue`), PascalCase para componentes (`AppSidebar.vue`, `ComprobanteCard.vue`).
  - Textos UI en español.
  - Moneda con `Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })`.
  - Obtener `userId` con `useAuth().user.value?.id`; guard temprano si null.
  - Validación con Zod cuando aplique.
- **Formateo de quincena**: dos dígitos con leading zero (ej. `01`, `07`, `24`). Ya usado en `comprobantes/`.

---

## Phase 1: Lógica de negocio pura (utils) (ref: PRD §Fórmula, §Validación de completitud)

- [x] **Definir tipos y constantes del módulo Declaración**
  Task ID: `phase-1-utils-01`
  > **Implementation**: Crear `app/utils/declaracion.ts`.
  > **Details**: Al tope del archivo exportar:
  > - `export const CLAVES_DESCONTADAS = ['01', '1L', '2L', '3L', '4L', '5L'] as const` (coincidencia exacta contra `Concepto.clave`).
  > - `export const QUINCENAS_ESPERADAS = 24` y helper `export const QUINCENAS_TOTALES: number[] = Array.from({length: 24}, (_, i) => i + 1)`.
  > - Interfaces exportadas:
  >   - `AnioResumenDeclaracion { anio: number; quincenasCubiertas: number[]; quincenasFaltantes: number[]; totalComprobantes: number; completo: boolean }`
  >   - `QuincenaDesglose { quincena: number; totalPercepciones: number; montoDescontado: number; ingresoReportable: number; comprobantesCount: number }`
  >   - `CalculoAnual { anio: number; totalReportable: number; totalPercepcionesBruto: number; totalDescontado: number; desglose: QuincenaDesglose[]; generadoEn: number }`
  > - No contiene lógica todavía, solo tipos y constantes (mantener el archivo testable por partes).

- [x] **Implementar `listarAniosDisponibles` en utils**
  Task ID: `phase-1-utils-02`
  > **Implementation**: Añadir función en `app/utils/declaracion.ts` importando `db` desde `~/db/db`.
  > **Details**:
  > ```ts
  > export async function listarAniosDisponibles(userId: string): Promise<AnioResumenDeclaracion[]>
  > ```
  > - Query: `db.comprobantes.where('userId').equals(userId).toArray()` (no filtrar por `deletedAt` salvo que tenga valor truthy — replicar el patrón de `comprobantes/index.vue` que tampoco lo filtra; si se agrega filtro, excluir los que tengan `deletedAt != null`).
  > - Agrupar por `anio` en un `Map<number, Set<number>>` (quincenas únicas) y un `Map<number, number>` (count de comprobantes).
  > - Para cada año calcular `quincenasCubiertas` (array ordenado), `quincenasFaltantes` = `QUINCENAS_TOTALES.filter(q => !cubiertas.has(q))`, `completo = quincenasFaltantes.length === 0`.
  > - **Filtrado por año máximo**: mirar la fecha del sistema; el primer año mostrado debe ser `new Date().getFullYear() - 1`. Excluir años >= al año actual.
  > - Ordenar descendente por `anio`.
  > - Retornar array.

- [x] **Implementar `calcularIngresoAnual` en utils**
  Task ID: `phase-1-utils-03`
  > **Implementation**: Añadir función en `app/utils/declaracion.ts`.
  > **Details**:
  > ```ts
  > export async function calcularIngresoAnual(userId: string, anio: number): Promise<CalculoAnual>
  > ```
  > - Obtener comprobantes del año: `db.comprobantes.where('[userId+anio]').equals([userId, anio]).toArray()` (usa el índice compuesto ya definido en `db.ts:42`).
  > - Recolectar todos los `comprobanteId` del año.
  > - Obtener conceptos asociados en UNA sola query batcheada: usar `db.conceptos.where('[userId+comprobanteId]').anyOf(comprobanteIds.map(id => [userId, id])).toArray()` para evitar N+1.
  > - Construir un `Map<string, Concepto[]>` por `comprobanteId`.
  > - Para cada `Comprobante` del año:
  >   - Acumular en un `Map<number, QuincenaDesglose>` keyed por `comprobante.quincena` (1-24).
  >   - `totalPercepciones(q)`: suma de `monto` de conceptos con `categoria === 'PERCEPCION'` de todos los comprobantes de esa quincena.
  >   - `montoDescontado(q)`: suma de `monto` de conceptos con `CLAVES_DESCONTADAS.includes(concepto.clave ?? '')` **independientemente de categoría** (el requisito dice "descontar los conceptos 01, 1L, 2L, 3L, 4L, 5L" sin limitarlo a percepción).
  >   - `ingresoReportable(q) = totalPercepciones(q) − montoDescontado(q)`.
  > - Generar `desglose` como array ordenado por quincena (01 → 24). Para quincenas sin datos (no debería pasar si el llamador valida `completo`, pero por defensivo) devolver zeros.
  > - `totalReportable` = Σ `ingresoReportable`. `totalPercepcionesBruto` = Σ `totalPercepciones`. `totalDescontado` = Σ `montoDescontado`.
  > - `generadoEn = Date.now()`.
  > - **NO lanzar excepción si año incompleto**; es responsabilidad del llamador. Solo calcular con lo disponible.

- [x] **Helper de formato: `formatMoneda` + `formatQuincena`**
  Task ID: `phase-1-utils-04`
  > **Implementation**: Añadir al final de `app/utils/declaracion.ts`.
  > **Details**:
  > - `export function formatMoneda(n: number): string` usando `Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', minimumFractionDigits: 2, maximumFractionDigits: 2 })`. Nota: decimales sí (a diferencia de `comprobantes/index.vue` que usa 0), porque para declaración el usuario necesita ver centavos.
  > - `export function formatQuincena(q: number): string` → `String(q).padStart(2, '0')`.
  > - `export function formatListaQuincenas(qs: number[]): string` → `qs.map(formatQuincena).join(', ')` (para el tooltip "Faltan: 07, 15, 22").

---

## Phase 2: Composable reactivo (ref: PRD §Technical Requirements — Estructura de archivos)

- [x] **Crear `useDeclaracion` composable**
  Task ID: `phase-2-composable-01`
  > **Implementation**: Crear `app/composables/useDeclaracion.ts`.
  > **Details**:
  > - Mirror del patrón de `useAnalisisSueldo.ts:14-82`.
  > - Estado reactivo: `aniosDisponibles = ref<AnioResumenDeclaracion[]>([])`, `calculoActual = ref<CalculoAnual | null>(null)`, `cargando = ref(false)`, `error = ref<string | null>(null)`.
  > - Obtener `userId` con `const auth = useAuth()` y `computed(() => auth.user.value?.id)`.
  > - Exponer funciones:
  >   - `cargarAnios(): Promise<void>` → llama `listarAniosDisponibles(userId)`.
  >   - `calcularAnio(anio: number): Promise<void>` → valida que el año existe y está `completo` en `aniosDisponibles.value`; si no, setear `error = 'Año incompleto, no se puede calcular'` y salir. Si ok, llama `calcularIngresoAnual`.
  >   - `limpiarCalculo(): void` → resetea `calculoActual`.
  > - Try/catch en cada función async; log `console.error` + mensaje amigable en `error.value`.
  > - Retornar `{ aniosDisponibles, calculoActual, cargando, error, cargarAnios, calcularAnio, limpiarCalculo }` tipado con `readonly`/`Readonly` donde aplique (opcional, mantener simple).

---

## Phase 3: Página listado (ref: PRD §Listado de años disponibles)

- [x] **Crear página index de Declaración**
  Task ID: `phase-3-pages-01`
  > **Implementation**: Crear `app/pages/declaracion/index.vue`.
  > **Details**:
  > - Estructura basada en `app/pages/comprobantes/index.vue` (misma animación `animate-fade-in`, mismo header con `<h1>` y `<p>`, mismos estados `cargando` / `empty` / `grid`).
  > - `<script setup lang="ts">`: `const { aniosDisponibles, cargando, error, cargarAnios } = useDeclaracion(); onMounted(cargarAnios)`.
  > - Header:
  >   - Título: `Declaración anual`.
  >   - Subtítulo: `Calcula el ingreso que debes reportar en tu declaración anual de ISR a partir de tus comprobantes.`
  > - Estado `cargando`: spinner `i-lucide-loader-2 animate-spin text-brand-600` (idéntico a comprobantes).
  > - Estado vacío (`aniosDisponibles.length === 0`): mismo patrón con CTA a `/descargar`.
  > - Grid responsivo `md:grid-cols-2 lg:grid-cols-3`; iterar `aniosDisponibles` usando `<DeclaracionAnoCard :anio="a" />` (ver Phase 5).
  > - Al final, nota discreta: "Los años incompletos se listan pero no permiten cálculo hasta que descargues todas las quincenas faltantes."
  > - `definePageMeta({ layout: 'default' })` — omitir si layout default es automático (verificar con `comprobantes/index.vue`; no lo declara, entonces omitir).

---

## Phase 4: Página detalle (ref: PRD §Vista de detalle del cálculo)

- [x] **Crear página dinámica `/declaracion/[anio].vue`**
  Task ID: `phase-4-pages-01`
  > **Implementation**: Crear `app/pages/declaracion/[anio].vue`.
  > **Details**:
  > - `const route = useRoute()` → `const anio = computed(() => Number(route.params.anio))`.
  > - Validar que `anio` sea número y <= año actual − 1; si no, redirigir a `/declaracion` con `navigateTo('/declaracion')`.
  > - `const { calculoActual, cargando, error, calcularAnio, aniosDisponibles, cargarAnios } = useDeclaracion()`.
  > - `onMounted(async () => { await cargarAnios(); await calcularAnio(anio.value) })`.
  > - Layout de la página:
  >   - Breadcrumb/back link: `<NuxtLink to="/declaracion">` con `i-lucide-chevron-left` (mirar `comprobantes/[anio]/index.vue` para el patrón exacto).
  >   - Header con título `Declaración anual {{ anio }}` + subtítulo.
  >   - **Card destacada** (si `calculoActual`): fondo `gradient-brand`, texto blanco, muestra `formatMoneda(calculoActual.totalReportable)` en `text-4xl font-bold`, label "Monto a reportar en declaración".
  >   - **Sección método de cálculo**: componente `<DeclaracionMetodo :calculo="calculoActual" />` (ver Phase 5).
  >   - **Sección desglose**: `<DeclaracionDesgloseTable :desglose="calculoActual.desglose" />`.
  >   - **Sección fundamento legal**: `<DeclaracionFundamentoLegal />`.
  >   - **Disclaimer**: cuadro amarillo/ámbar (`bg-amber-50 dark:bg-amber-950/30 border-amber-200`) con texto "El monto mostrado es una estimación informativa basada en tus comprobantes de nómina. Verifica con tu contador o con el visor del SAT antes de presentar tu declaración."
  > - Estado de error: si `error.value` truthy, mostrar alerta roja con el mensaje y botón "Volver al listado".

---

## Phase 5: Componentes UI auxiliares (ref: PRD §Architecture & Design)

- [x] **Componente `DeclaracionAnoCard`**
  Task ID: `phase-5-components-01`
  > **Implementation**: Crear `app/components/DeclaracionAnoCard.vue`.
  > **Details**:
  > - Props: `{ anio: AnioResumenDeclaracion }`.
  > - Import tipo: `import type { AnioResumenDeclaracion } from '~/utils/declaracion'`.
  > - Estructura:
  >   - Si `anio.completo`: envolver en `<NuxtLink :to="\`/declaracion/${anio.anio}\`">` reutilizando las clases de `comprobantes/index.vue:37-68` (hover-lift, border, rounded-xl).
  >   - Si incompleto: usar `<div>` con opacidad `opacity-75 cursor-not-allowed` y `<UTooltip :text="\`Faltan quincenas: ${formatListaQuincenas(anio.quincenasFaltantes)}\`">` envolviéndolo.
  > - Contenido:
  >   - Icono grande: `i-lucide-file-text` en círculo `bg-brand-100`.
  >   - Título: `{{ anio.anio }}`.
  >   - Subtítulo: `{{ anio.quincenasCubiertas.length }}/24 quincenas · {{ anio.totalComprobantes }} comprobantes`.
  >   - Badge de estado: si completo, `<UBadge color="success" variant="subtle">Completo</UBadge>`; si incompleto, `<UBadge color="warning" variant="subtle">Incompleto</UBadge>`.
  >   - Si incompleto: línea adicional con texto gris `Faltan: {{ formatListaQuincenas(anio.quincenasFaltantes) }}` (truncar a 5 quincenas + "..." si son más).
  >   - Chevron derecha: `i-lucide-chevron-right` (solo si `completo`).

- [x] **Componente `DeclaracionMetodo`**
  Task ID: `phase-5-components-02`
  > **Implementation**: Crear `app/components/DeclaracionMetodo.vue`.
  > **Details**:
  > - Props: `{ calculo: CalculoAnual }`.
  > - Card blanca con `rounded-xl border`. Título: "Cómo se calculó" con icono `i-lucide-calculator`.
  > - Lista numerada (1-4) explicando:
  >   1. Se obtuvieron los comprobantes del año {{ calculo.anio }} ({{ 24 }} quincenas completas).
  >   2. Por cada quincena se sumó el total de percepciones: `{{ formatMoneda(calculo.totalPercepcionesBruto) }}`.
  >   3. Se descontaron los conceptos con clave **01, 1L, 2L, 3L, 4L y 5L** (sueldo base y percepciones ya contempladas): `-{{ formatMoneda(calculo.totalDescontado) }}`.
  >   4. El resultado es el ingreso reportable anual: **{{ formatMoneda(calculo.totalReportable) }}**.
  > - Detalle mostrando la fórmula en bloque `<code>` con background `slate-100 dark:slate-800`:
  >   ```
  >   ingresoReportable = Σ percepciones(quincena) − Σ conceptos(01,1L..5L)
  >   ```

- [x] **Componente `DeclaracionDesgloseTable`**
  Task ID: `phase-5-components-03`
  > **Implementation**: Crear `app/components/DeclaracionDesgloseTable.vue`.
  > **Details**:
  > - Props: `{ desglose: QuincenaDesglose[] }`.
  > - Usar `<UTable>` de Nuxt UI **si ya está en uso** en otra parte del proyecto; si no, tabla HTML con clases Tailwind (inspeccionar `app/pages/prestamos/` antes de escribir; si no hay patrón, usar `<table>` plano con `divide-y`).
  > - Columnas:
  >   - Quincena (formateada `01`, `02`...)
  >   - Percepciones (derecha, `text-green-600`)
  >   - Descontado (derecha, `text-slate-500`, prefijo `-`)
  >   - Ingreso reportable (derecha, `font-semibold text-brand-600`)
  > - Fila totales al final con `font-bold border-t-2`.
  > - Responsive: en mobile (`md:hidden`) colapsar a lista de cards por quincena; en desktop tabla.

- [x] **Componente `DeclaracionFundamentoLegal`**
  Task ID: `phase-5-components-04`
  > **Implementation**: Crear `app/components/DeclaracionFundamentoLegal.vue`.
  > **Details**:
  > - Sin props.
  > - Card con icono `i-lucide-scale` y título "Fundamento legal".
  > - Párrafo introductorio: "Este cálculo se basa en el marco de la Ley del Impuesto Sobre la Renta (LISR) vigente en México."
  > - Lista con 3 items, cada uno con el artículo en negrita y un enlace externo (abrir en nueva pestaña `target="_blank" rel="noopener noreferrer"`):
  >   - **Art. 93 LISR** — Ingresos exentos del ISR. [SAT: articulo/15199/articulo-93](https://www.sat.gob.mx/articulo/15199/articulo-93)
  >   - **Arts. 94–99 LISR** — Ingresos por salarios y servicios personales subordinados. [Justia MX](https://mexico.justia.com/federales/leyes/ley-del-impuesto-sobre-la-renta/titulo-iv/capitulo-i/)
  >   - **Arts. 150–152 LISR** — Declaración anual de personas físicas. [Justia MX](https://mexico.justia.com/federales/leyes/ley-del-impuesto-sobre-la-renta/titulo-iv/capitulo-xi/)
  > - Nota al pie con enlace a la ley completa: [LISR — Cámara de Diputados (PDF)](http://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf).
  > - Icono `i-lucide-external-link` junto a cada link.

---

## Phase 6: Integración con navegación (ref: PRD §Nueva entrada de menú)

- [x] **Agregar "Declaración" al sidebar**
  Task ID: `phase-6-nav-01`
  > **Implementation**: Editar `app/components/AppSidebar.vue`, array `navItems` (líneas 67-93).
  > **Details**:
  > - Insertar el nuevo item **entre** "Comprobantes" y "Préstamos":
  >   ```ts
  >   {
  >     label: 'Declaración',
  >     icon: 'i-lucide-file-text',
  >     to: '/declaracion'
  >   }
  >   ```
  > - No tocar estilos ni template; sólo el array.
  > - Verificar que no existe otra entrada en sidebars alternos (buscar también cualquier menú en `layouts/mobile.vue` o `layouts/desktop.vue`; si tienen su propio array, replicar el cambio).

---

## Phase 7: Verificación (ref: PRD §Quality)

- [x] **Type-check completo**
  Task ID: `phase-7-verify-01`
  > **Implementation**: Ejecutar `pnpm --filter webapp typecheck` (o `cd webapp && pnpm typecheck`).
  > **Details**: Resolver cualquier error de tipos, especialmente en `useDeclaracion`, imports de tipos y props de componentes. Zero errors antes de seguir.

- [ ] [BLOCKED: requiere navegador + sesión del usuario] **Prueba manual con datos reales**
  Task ID: `phase-7-verify-02`
  > **Implementation**: `cd webapp && pnpm dev`. Loguear con un usuario que tenga comprobantes.
  > **Details**: Verificar:
  > 1. El item "Declaración" aparece en sidebar.
  > 2. `/declaracion` lista los años descendiente desde el año anterior al actual (2025 hoy).
  > 3. Años incompletos muestran badge `Incompleto`, lista de quincenas faltantes, y no son clickeables.
  > 4. Al entrar a un año completo: monto total coincide con cálculo manual sobre 1-2 quincenas sample.
  > 5. Desglose por quincena muestra 24 filas.
  > 6. Fundamento legal abre los enlaces en nueva pestaña.
  > 7. Dark mode funciona en todas las vistas.
  > 8. Responsive mobile: la tabla colapsa correctamente.

- [ ] [BLOCKED: requiere consola del navegador con sesión activa] **Validación del cálculo con datos del usuario**
  Task ID: `phase-7-verify-03`
  > **Implementation**: Consola del navegador: ejecutar `await window.tsolbiilDb.conceptos.where('userId').equals('<id>').toArray()` (el `tsolbiilDb` global está expuesto en dev — ver `db.ts:63-65`).
  > **Details**: Filtrar conceptos por `clave` en `['01','1L','2L','3L','4L','5L']` y verificar que los montos descontados reportados por la UI coinciden con la suma de IndexedDB. Si discrepan, revisar `calcularIngresoAnual` (problema probable: batch query `anyOf` o filtro de categoría).

---

*Generated by Clavix /clavix:plan*
