# Product Requirements Document: Declaración Anual — Apoyo de Cálculo de Ingresos

## Problem & Goal

Los usuarios de Tsolbiil (empleados asalariados, probablemente de SEMS/UNAM) necesitan preparar su **declaración anual de ISR ante el SAT** cada año y actualmente deben calcular manualmente, sumando quincena por quincena de sus comprobantes de nómina, cuál es el ingreso que deben reportar. Este proceso es tedioso, propenso a errores y desincentiva que la persona haga su declaración correctamente.

**Goal:** Agregar un nuevo módulo **"Declaración"** en el menú lateral de la webapp que, con los comprobantes ya almacenados en IndexedDB, calcule automáticamente el monto de ingreso a reportar en la declaración anual de un año fiscal elegido, mostrando el desglose quincenal del cálculo y su fundamento legal, para dar al usuario una cifra verificable y un respaldo serio.

---

## Requirements

### Must-Have Features

#### 1. Nueva entrada de menú "Declaración"
- Agregar ítem **"Declaración"** al `AppSidebar.vue` (ícono sugerido: `i-lucide-file-text` o `i-lucide-calculator`), posicionado después de "Comprobantes" y antes de "Préstamos".
- Ruta: `/declaracion` (index) y `/declaracion/[anio]` (detalle por año).

#### 2. Listado de años disponibles (pantalla index)
- Mostrar los años fiscales disponibles, **comenzando por el año inmediato anterior al actual** (ej. si hoy es 2026 → primer año mostrado es 2025) hacia atrás.
- La lista se construye a partir de los `anios` presentes en la tabla `comprobantes` de IndexedDB para el `userId` activo.
- Cada entrada del listado debe mostrar:
  - **Año** (ej. "2025")
  - **Estado de completitud**: `Completo` (24 quincenas: 01–24) o `Incompleto (X/24)` con badge distintivo.
  - **Quincenas faltantes** (cuando está incompleto): lista concisa (ej. "Faltan: 07, 15, 22").
  - **Acción**: botón "Ver cálculo" **solo habilitado si el año está completo**; si está incompleto, el botón se muestra deshabilitado con tooltip explicativo.

#### 3. Validación de completitud quincenal
- Un año se considera **Completo** si existen comprobantes que cubran **todas las quincenas del 01 al 24** para ese `userId` y `anio` (consulta directa a IndexedDB agrupando por `quincena`).
- Los años incompletos **se muestran en el listado pero bloquean el cálculo** para evitar resultados parciales que confundan al usuario en su declaración.

#### 4. Vista de detalle del cálculo (al seleccionar un año)
Al seleccionar un año completo, mostrar:

- **Monto total reportable** (destacado como número grande).
- **Tabla de desglose por quincena** (24 filas) con columnas:
  - Quincena (01–24)
  - Total percepciones
  - Monto de conceptos descontados (suma de claves `01`, `1L`, `2L`, `3L`, `4L`, `5L`)
  - Ingreso reportable de la quincena
- **Explicación del método de cálculo** visible en la UI (acordeón o panel): texto claro describiendo paso a paso qué se hizo.
- **Fundamento legal**: sección con referencias a la Ley del ISR (Art. 93, 94–99, 150–152) y enlaces a fuentes oficiales (SAT, Diputados, o portales reconocidos como Justia, Taxdown). Debe dejar claro al usuario que el cálculo es serio y basado en ley vigente.

#### 5. Fórmula de cálculo
Para cada quincena `q` del año seleccionado:

```
totalPercepciones(q) = Σ monto de Conceptos donde categoria = 'PERCEPCION'
conceptosDescontados(q) = Σ monto de Conceptos donde clave ∈ {'01','1L','2L','3L','4L','5L'}
ingresoReportable(q) = totalPercepciones(q) − conceptosDescontados(q)
```

**Monto total a declarar** = Σ ingresoReportable(q) para q ∈ {01..24}

- Las consultas se hacen sobre la tabla `conceptos` de IndexedDB filtrando por `userId` y los `comprobanteId` que pertenecen al año objetivo.
- Considerar todos los comprobantes del año (incluyendo extraordinarios/retroactivos si existen en la misma quincena — se suman al `totalPercepciones` de esa quincena).

### Technical Requirements

- **Framework**: Nuxt 3 + Vue 3 (Composition API, `<script setup lang="ts">`).
- **UI**: Nuxt UI (`UIcon`, tablas, tarjetas), Tailwind CSS (coherente con el estilo existente en `comprobantes/`, `prestamos/`).
- **Persistencia**: Dexie sobre IndexedDB (`tsolbiil_db`), consultas a las tablas `comprobantes` y `conceptos` mediante los índices existentes (`[userId+anio]` implícito vía `userId` + filtro por `anio`, y `[userId+comprobanteId]` para conceptos).
- **Estado del usuario activo**: reusar `useSession` / `auth.service` para obtener `userId`.
- **Estructura de archivos**:
  - `app/pages/declaracion/index.vue` — listado de años
  - `app/pages/declaracion/[anio].vue` — detalle del cálculo
  - `app/composables/useDeclaracion.ts` — lógica de consulta IndexedDB y cálculo (pura, testable)
  - Opcional: `app/components/DeclaracionAnoCard.vue`, `DeclaracionDesgloseTable.vue`
- **Navegación**: agregar entrada a `navItems` en `app/components/AppSidebar.vue`.
- **Performance**: consultas deben ejecutarse en < 500ms para un año típico (~24–30 comprobantes, ~200–600 conceptos).
- **Internacionalización**: textos en español (coherente con el resto de la app); montos formateados como MXN (`Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })`).

### Architecture & Design

- **Capa de datos**: el composable `useDeclaracion` encapsula:
  - `listarAniosDisponibles(userId): Promise<AnioResumen[]>` — devuelve años + quincenas cubiertas + flag `completo`.
  - `calcularIngresoAnual(userId, anio): Promise<CalculoAnual>` — devuelve total + desglose quincenal.
- **Patrón**: lógica de negocio desacoplada del componente (Repository-style vía Dexie directo en composable, coherente con el resto del proyecto que no usa repositorios separados).
- **Estilo visual**: cards con bordes redondeados `rounded-xl`, paleta `brand-*` y `slate-*` ya usada, soporte dark mode.
- **Accesibilidad**: botones deshabilitados con `aria-disabled` y tooltip textual explicando por qué (ej. "Este año tiene quincenas faltantes: 07, 15").

### Fundamento Legal (a mostrar en la UI)

El cálculo se apoya en el marco de la **Ley del Impuesto Sobre la Renta (LISR)** vigente:

- **Art. 93 LISR** — Ingresos exentos de ISR (aguinaldo, prima vacacional, fondo de ahorro, previsión social, etc., medidos en UMA). Referencia: [Art. 93 LISR — SAT](https://www.sat.gob.mx/articulo/15199/articulo-93), [Taxdown](https://taxdown.com.mx/blog/articulo-93-lisr).
- **Arts. 94–99 LISR** — Ingresos por salarios y en general por la prestación de un servicio personal subordinado (determinación de ingreso gravable). Referencia: [Justia México](https://mexico.justia.com/federales/leyes/ley-del-impuesto-sobre-la-renta/titulo-iv/capitulo-i/).
- **Arts. 150–152 LISR** — Declaración Anual del ISR de personas físicas. Referencia: [Justia México](https://mexico.justia.com/federales/leyes/ley-del-impuesto-sobre-la-renta/titulo-iv/capitulo-xi/).
- **Ley oficial completa**: [LISR — Cámara de Diputados (PDF)](http://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf).

La UI debe incluir una **nota visible** tipo: *"El monto mostrado es una estimación informativa basada en tus comprobantes de nómina. Verifica con tu contador o con el visor del SAT antes de presentar tu declaración."*

---

## Out of Scope (v1)

Expresamente **NO** se incluye en esta primera versión:

- ❌ **Envío o presentación al SAT.** El módulo es puramente informativo; no se conecta con servicios del SAT ni genera archivos XML/declaración.
- ❌ **Cálculo del ISR a pagar o a favor.** Solo calculamos el ingreso a reportar, no aplicamos tarifas de ISR ni deducciones para determinar impuesto.
- ❌ **Exportación a PDF o Excel.** El desglose solo se muestra en pantalla.
- ❌ **Deducciones personales** (gastos médicos, colegiaturas, donativos, intereses hipotecarios). El usuario los capturará directamente en el aplicativo del SAT.
- ❌ **Años incompletos no permiten cálculo.** Se listan con el badge "Incompleto" pero el botón de cálculo está deshabilitado — decisión del usuario para evitar cifras erróneas.
- ❌ **Edición manual de conceptos o percepciones.** Los datos provienen tal cual de los comprobantes ya almacenados.
- ❌ **Multi-RFC / consolidación de empleadores.** Solo el RFC/usuario activo en sesión.

---

## Additional Context

- **Año actual (de referencia del sistema):** 2026 → primer año mostrado: 2025.
- **Contexto de los conceptos descontados (`01`, `1L`–`5L`):** son las claves internas que en los comprobantes del usuario representan el sueldo base y posibles percepciones tipo "licencia" o asimilables ya incorporadas al recibo normal. Restarlas aísla el ingreso adicional reportable. La documentación en la UI debe indicar esto en lenguaje claro.
- **Dependencia con el flujo de descarga:** requiere que el usuario ya haya descargado sus comprobantes del año (flujo en `/descargar`). El listado inicial cubre este caso natural porque se construye a partir de lo que exista en IndexedDB.
- **Riesgo documentado:** si un patrón/universidad utiliza claves distintas (no `01`/`1L`–`5L`) para esos mismos conceptos fiscales, el cálculo podría desviarse. Mitigar mostrando el desglose explícito por quincena para que el usuario lo verifique.
- **Estado del proyecto (2026-04-16):** estamos dentro de la temporada de declaración anual 2025 (vence 30 de abril 2026), por lo que esta feature tiene urgencia comercial: los usuarios la necesitan este mes.

---

*Generated with Clavix Planning Mode*
*Generated: 2026-04-16T00:00:00Z*
