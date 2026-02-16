# 🤖 Agent.md - Documentación del Agente de Pruebas SEMS

> **Archivo de documentación automática**  
> Última actualización: 2025-12-04

---

## 1. 🎯 Propósito del Agente

**Misión actual:** Probar autenticación y consulta de comprobantes al portal SEMS usando Python + requests.

### Descripción
Este agente tiene como objetivo principal realizar pruebas de autenticación automatizadas y consulta de comprobantes de nómina contra el portal de autoservicios SEMS (Sistema de Educación Media Superior) de la SEP.

**Portal objetivo:**
- **URL Base:** `https://portalautoservicios-sems.sep.gob.mx/`
- **Tipo de autenticación:** Spring Security (formulario tradicional)
- **Endpoint de login:** `/j_spring_security_check`
- **Endpoint de comprobantes:** `/mvc/comprobantes/pago/`

---

## 2. 🔧 Decisiones Técnicas Tomadas

### 2.1 Uso de `requests.Session()`
- **Razón:** Mantener cookies y estado de sesión entre peticiones.
- **Beneficio:** Simula correctamente el comportamiento de un navegador que mantiene la sesión.

### 2.2 Encabezados Utilizados

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9...",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}
```

- **Razón:** Headers realistas para evitar bloqueos por detección de bots.
- **User-Agent:** Chrome 120 en Windows 10 (navegador común).

### 2.3 ¿Por qué no usar Playwright/Selenium?

| Criterio | requests | Playwright/Selenium |
|----------|----------|---------------------|
| Velocidad | ✅ Rápido | ❌ Lento |
| Recursos | ✅ Bajo consumo | ❌ Alto consumo |
| JavaScript | ❌ No soporta | ✅ Soporta |
| Complejidad | ✅ Simple | ❌ Complejo |

**Decisión:** El portal SEMS usa formulario tradicional sin JavaScript complejo, por lo que `requests` es suficiente y más eficiente.

### 2.4 Flujo de Spring Security Detectado

```
1. GET /login.jsp → Obtiene JSESSIONID inicial
2. POST /j_spring_security_check → Envía credenciales
3. Redirección 302 → Nueva sesión autenticada
4. GET / → Acceso a página principal (si login exitoso)
```

---

## 3. 📊 Resultados de Ejecuciones

### Ejecución #1 (Prueba con credenciales de ejemplo)
- **Fecha:** 2025-12-04 18:40:28
- **Estado:** ❌ Autenticación fallida (esperado - credenciales de prueba)
- **Nota:** Prueba inicial con placeholders

---

### Ejecución #2 (Prueba con credenciales reales) ⭐
- **Fecha:** 2025-12-04 18:42:00
- **Estado:** ✅ **AUTENTICACIÓN EXITOSA**

#### Cookies Iniciales
| Cookie | Valor |
|--------|-------|
| JSESSIONID | `bb86c8a357168be51095955aed60` |

#### Cookies Finales
| Cookie | Valor |
|--------|-------|
| JSESSIONID | `bb86e536a0e029495fb05c9dfbf6` ✅ **CAMBIÓ** |

#### Flujo de Redirecciones
```
POST /j_spring_security_check
  └── 302 Redirect → / (página principal)
```

#### Resultados
- **URL Final:** `https://portalautoservicios-sems.sep.gob.mx/` ✅
- **JSESSIONID cambió:** ✅ Sí (nuevo contexto de sesión)
- **Acceso interno:** ✅ Sí (Status 200, contenido válido)
- **Errores de conexión:** 0

#### Hallazgos Importantes
1. ✅ **Autenticación Spring Security funcional** - El flujo completo funciona
2. ✅ **Sesión establecida correctamente** - JSESSIONID nuevo asignado
3. ✅ **Redirección a página principal** - No regresa a `login.jsp`
4. ✅ **Acceso a contenido protegido** - Página interna accesible
5. ✅ **Headers de navegador aceptados** - No hubo bloqueo por User-Agent

#### Conclusión
🎉 **El script de autenticación funciona correctamente.**
El flujo de login con `requests.Session()` es válido para este portal.
Se puede proceder a implementar funcionalidades adicionales (descargas, scraping, etc.)

---

## 4. 📋 Consulta de Comprobantes por Año/Quincena

### Endpoint Real Descubierto

> ⚠️ **Nota importante:** El endpoint inicialmente especificado como POST resultó ser **GET con query parameters**.

| Propiedad | Valor |
|-----------|-------|
| **URL** | `https://portalautoservicios-sems.sep.gob.mx/mvc/comprobantes/pago/` |
| **Método** | `GET` (no POST) |
| **Content-Type respuesta** | `application/json` |

### Headers Utilizados

```python
headers = {
    "Accept": "application/json,application/javascript",
    "X-Requested-With": "XMLHttpRequest",
    "Range": "items=0-9",  # Paginación
    "Referer": "https://portalautoservicios-sems.sep.gob.mx/",
}
```

### Parámetros (Query String)

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `rfc` | RFC del trabajador | `XXXX000000XXX` |
| `anio` | Año de consulta | `2025` |
| `quincena` | Número de quincena (1-24) | `10` |

**Ejemplo de URL completa:**
```
GET /mvc/comprobantes/pago/?rfc=XXXX000000XXX&anio=2025&quincena=10
```

### Resultado Escenario A: 2025/Quincena 10 ✅

**Fecha de prueba:** 2025-12-04 18:55:02

| Métrica | Valor |
|---------|-------|
| Status HTTP | 200 |
| Content-Type | application/json |
| Comprobantes encontrados | **1** |

**Ejemplo de comprobante devuelto:**
```json
{
  "idComprobante": 67247894,
  "numComprobante": 28391829,
  "totNetoCheque": 3565.00,
  "anio": 2025,
  "quincena": 10
}
```

**Conclusión:** ✅ El endpoint devuelve correctamente los comprobantes existentes.

### Resultado Escenario B: 2025/Quincena 23 ✅

**Fecha de prueba:** 2025-12-04 18:55:02

| Métrica | Valor |
|---------|-------|
| Status HTTP | 200 |
| Content-Type | application/json |
| Comprobantes encontrados | **0** |

**Respuesta:**
```json
[]
```

**Conclusión:** ✅ El endpoint devuelve lista vacía `[]` para quincenas sin comprobantes.

### Cómo Detectar Quincenas Sin Comprobantes

```python
comprobantes = obtener_detalle_quincena(session, rfc, anio, quincena)

if len(comprobantes) == 0:
    print("No hay comprobantes para esta quincena")
else:
    print(f"Se encontraron {len(comprobantes)} comprobantes")
```

### Claves Disponibles en Cada Comprobante

El objeto JSON de cada comprobante incluye (entre otros):
- `idComprobante` - ID único del comprobante
- `numComprobante` - Número de comprobante
- `totNetoCheque` - Total neto a pagar
- `anio` - Año del comprobante
- `quincena` - Quincena del comprobante

---

## 5. 💻 Código Generado

### 5.1 `test_login_sems.py`

**Ubicación:** `/media/Files/Repos/Tsolbiil/test_login_sems.py`

**Propósito:** Prueba de autenticación básica al portal SEMS.

**Características implementadas:**
- ✅ Sesión persistente con `requests.Session()`
- ✅ Headers de navegador realistas
- ✅ GET inicial para obtener cookies
- ✅ POST con `allow_redirects=True`
- ✅ Captura de cookies iniciales y finales
- ✅ Verificación de URL final
- ✅ Prueba de acceso a página interna
- ✅ Logs claros y detallados

### 5.2 `test_comprobantes_quincena.py` ⭐ NUEVO

**Ubicación:** `/media/Files/Repos/Tsolbiil/test_comprobantes_quincena.py`

**Propósito:** Consulta de comprobantes de nómina por año/quincena.

**Funciones implementadas:**

```python
def crear_sesion_portal(rfc: str, password: str) -> requests.Session:
    """Crea una sesión autenticada en el portal SEMS."""
    
def obtener_detalle_quincena(
    session: requests.Session,
    rfc: str,
    anio: int,
    quincena: int,
    offset: int = 0,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Consulta comprobantes usando el endpoint JSON oficial."""
```

**Características:**
- ✅ Función reutilizable `crear_sesion_portal()`
- ✅ Función `obtener_detalle_quincena()` con paginación
- ✅ Soporte para header `Range` de paginación
- ✅ Parsing automático de respuesta JSON
- ✅ Logs detallados de cada paso
- ✅ Manejo de errores robusto

---

## 6. 🚀 Próximas Tareas Sugeridas

### Prioridad Alta
1. **[✅] Ejecutar script con credenciales válidas** - COMPLETADO
2. **[✅] Implementar consulta de comprobantes** - COMPLETADO
3. **[ ] Descargar PDF/XML de comprobantes**
   - Identificar endpoint de descarga
   - Implementar función `descargar_comprobante()`

### Prioridad Media
4. **[ ] Manejo robusto de errores**
   - Reintentos automáticos
   - Timeout configurables
   - Logging a archivo

5. **[ ] Obtener todos los comprobantes de un año**
   - Iterar quincenas 1-24
   - Agregar todos los comprobantes

### Prioridad Baja
6. **[ ] Construcción de módulo completo de scraping**
   - Clase `SEMSClient` reutilizable
   - Métodos para cada operación del portal

7. **[ ] Configuración externa**
   - Archivo `.env` para credenciales
   - Archivo de configuración YAML/JSON

---

## 7. 📝 Notas Adicionales

### Seguridad
- ⚠️ **NUNCA** incluir credenciales reales en el código
- Usar variables de entorno o archivos `.env` ignorados por git
- Las credenciales de ejemplo son placeholders

### Requisitos
```bash
pip install requests
```

### Ejecución
```bash
# Prueba de login
python test_login_sems.py

# Prueba de comprobantes
python test_comprobantes_quincena.py
```

---

## 8. 📚 Referencias

- [Portal SEMS](https://portalautoservicios-sems.sep.gob.mx/)
- [Documentación de requests](https://requests.readthedocs.io/)
- [Spring Security Reference](https://docs.spring.io/spring-security/)

---

*Este archivo es actualizado automáticamente por el agente de pruebas.*
