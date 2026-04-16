# Declaración Anual — Quick PRD

**Goal:** Agregar módulo "Declaración" al menú lateral de Tsolbiil (Nuxt 3 + Vue 3 + Dexie/IndexedDB) que, para usuarios asalariados preparando su declaración anual ante el SAT, calcule automáticamente el ingreso a reportar de un año fiscal elegido (empezando por el año inmediato anterior al actual). Features core: (1) listado de años disponibles obtenido de la tabla `comprobantes`, cada uno con badge de `Completo` (24/24 quincenas) o `Incompleto (X/24)` mostrando qué quincenas faltan; (2) validación que **bloquea el cálculo para años incompletos** para evitar cifras erróneas; (3) vista de detalle con monto total reportable + tabla de desglose por quincena (total percepciones, conceptos descontados, ingreso reportable); (4) explicación del método de cálculo y fundamento legal en la UI.

**Fórmula:** por cada quincena `q` del 01 al 24: `ingresoReportable(q) = Σ percepciones − Σ monto(conceptos con clave ∈ {01,1L,2L,3L,4L,5L})`. Total anual = Σ de las 24 quincenas. Consultas directas a Dexie (`comprobantes` + `conceptos`) filtradas por `userId` activo + `anio`. Archivos: `app/pages/declaracion/index.vue`, `app/pages/declaracion/[anio].vue`, composable `useDeclaracion.ts` para lógica de cálculo pura/testable. UI consistente con componentes existentes (Nuxt UI, Tailwind, brand-*, slate-*, dark mode). Fundamento legal mostrado en UI con referencias a **Art. 93 LISR** (ingresos exentos), **Arts. 94–99** (ingresos por salarios) y **Arts. 150–152** (declaración anual), con enlaces a SAT, Cámara de Diputados y portales como Justia/Taxdown.

**Out of scope (v1):** NO envío al SAT, NO cálculo del ISR a pagar (solo ingreso a reportar), NO exportación PDF/Excel, NO deducciones personales (gastos médicos/colegiaturas), NO edición manual de conceptos, NO multi-RFC. Los años incompletos se listan pero tienen el botón de cálculo deshabilitado con tooltip explicativo. Incluir nota visible: "Monto estimado informativo; verifica con tu contador o con el visor del SAT antes de presentar."

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-16T00:00:00Z*
