# Migración de FastAPI a Nuxt Server-Side

## Resumen

Se ha completado la migración de los endpoints del backend FastAPI (Python) a Nuxt server-side (Nitro/TypeScript). Esto elimina la dependencia del backend Python y simplifica la arquitectura del proyecto.

## Cambios Realizados

### 1. Estructura del Servidor

#### Nuevo archivo: `webapp/server/session.ts`
- Gestión de sesiones en memoria con cookies de SEMS
- Funciones para crear, obtener, eliminar y limpiar sesiones
- Autenticación con el portal SEMS
- Limpieza automática de sesiones expiradas (cada 5 minutos)
- Timeout de sesión: 30 minutos de inactividad

#### Nuevos endpoints en `webapp/server/api/`:

1. **`login.post.ts`** - POST `/api/login`
   - Autentica al usuario contra SEMS
   - Crea sesión del servidor
   - Retorna session_token

2. **`comprobantes.post.ts`** - POST `/api/comprobantes`
   - Obtiene lista de comprobantes para año y quincena
   - Valida sesión activa
   - Retorna array de comprobantes

3. **`download-pdf.post.ts`** - POST `/api/download-pdf`
   - Descarga PDF individual de comprobante
   - Retorna PDF como binary data

4. **`download-quincena.post.ts`** - POST `/api/download-quincena`
   - Descarga todos los PDFs de una quincena
   - Retorna array con comprobantes y PDFs en base64

5. **`logout.post.ts`** - POST `/api/logout`
   - Cierra sesión del usuario
   - Elimina sesión de memoria

### 2. Actualizaciones del Cliente

#### Modificado: `webapp/app/services/api.ts`
- Cambiado `API_BASE_URL` de `http://localhost:8000` a `/api`
- Agregados tipos TypeScript para todos los requests/responses
- Implementados métodos: `getComprobantes`, `downloadPdf`, `downloadQuincena`
- Mantenido método `login` y `logout`

#### Modificado: `webapp/app/services/auth.service.ts`
- Cambiado `getBackendUrl()` para retornar `/api` en lugar de usar `runtimeConfig`
- Eliminada dependencia de `NUXT_PUBLIC_API_URL`

#### Modificado: `webapp/nuxt.config.ts`
- Eliminada configuración `runtimeConfig.public.apiUrl`
- Eliminada dependencia de `NUXT_PUBLIC_API_URL`

### 3. Nuevos Componentes

#### Nuevo archivo: `webapp/app/composables/useApi.ts`
- Composable para acceder al cliente API
- Exporta `apiClient` singleton

#### Modificado: `webapp/app/pages/descargar.vue`
- Implementada lógica real de descarga usando API client
- Integración con IndexedDB para guardar comprobantes
- Barra de progreso de descarga
- Iteración sobre rango de quincenas
- Guardado de comprobantes, PDFs y conceptos en IndexedDB

## Cómo Eliminar la Dependencia de FastAPI

### 1. Eliminar el directorio del backend

```bash
# Eliminar el directorio backend_api
rm -rf backend_api/
```

### 2. Actualizar archivos de configuración

#### Eliminar de `.env` y `.env.production`:
```bash
# Eliminar o comentar estas líneas
# NUXT_PUBLIC_API_URL=http://localhost:8000
```

#### Eliminar de `.env.example`:
```bash
# Eliminar esta línea
NUXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Actualizar documentación

#### Actualizar `README.md`:
- Eliminar referencias al backend FastAPI
- Actualizar instrucciones de inicio (solo `npm run dev`)
- Actualizar diagramas de arquitectura

#### Actualizar `DEPLOY.md`:
- Eliminar pasos de despliegue del backend FastAPI
- Simplificar a solo despliegue de Nuxt

### 4. Actualizar scripts de inicio

#### Eliminar de `iniciar.sh` (si existe):
- Eliminar comandos para iniciar el backend FastAPI

### 5. Limpiar dependencias (si las hubiera)

El proyecto no tenía dependencias de Python en el package.json de Nuxt, pero si se agregaron scripts auxiliares:

```bash
# Eliminar scripts de Python si existen
# Eliminar requirements.txt del backend si ya no se necesita
```

## Arquitectura Final

```
┌─────────────────────────────────────────────────────────────┐
│                   Nuxt App (Frontend)                  │
│                                                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Páginas Vue (login.vue, descargar.vue, etc.)    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                │
│                          ▼                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Composables (useAuth, useSession, useApi)       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                │
│                          ▼                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Servicios (api.ts, auth.service.ts)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                │
│                          ▼                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  IndexedDB (usuarios, sesiones, comprobantes)     │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Internal API calls
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Nuxt Server (Nitro)                        │
│                                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  server/session.ts (Gestión de sesiones)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                │
│                          ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  server/api/*.post.ts (Endpoints)                │  │
│  │  • login.post.ts                               │  │
│  │  • comprobantes.post.ts                        │  │
│  │  • download-pdf.post.ts                         │  │
│  │  • download-quincena.post.ts                    │  │
│  │  • logout.post.ts                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP requests
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Portal SEMS (Externo)                      │
│  • login.jsp                                          │
│  • comprobantes endpoint                                │
│  • PDF download endpoint                                │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Pruebas recomendadas antes de eliminar FastAPI:

1. **Login**
   - Abrir la aplicación
   - Iniciar sesión con credenciales válidas
   - Verificar que se crea sesión correctamente

2. **Obtener Comprobantes**
   - Navegar a la página de descarga
   - Seleccionar una quincena específica
   - Verificar que se muestran los comprobantes

3. **Descargar PDF Individual**
   - Hacer clic en un comprobante
   - Verificar que se descarga el PDF correctamente

4. **Descargar Quincena Completa**
   - Seleccionar un rango de quincenas
   - Iniciar descarga masiva
   - Verificar que se descargan todos los PDFs
   - Verificar que se guardan en IndexedDB

5. **Logout**
   - Cerrar sesión
   - Verificar que se elimina la sesión del servidor

## Beneficios de la Migración

1. **Simplificación**: Un solo stack (TypeScript/JavaScript)
2. **Menos Infraestructura**: Solo un servidor Nuxt
3. **Mejor Performance**: Comunicación interna más rápida que HTTP
4. **Mantenimiento**: Menos código y tecnologías que mantener
5. **Deployment**: Más simple (solo Nuxt)
6. **Costos**: Menos recursos de servidor
7. **Type Safety**: TypeScript en todo el stack

## Consideraciones de Producción

### Sesiones en Memoria
- Actualmente las sesiones se almacenan en memoria
- Para producción con múltiples instancias, considerar:
  - **Redis**: Para compartir sesiones entre instancias
  - **Database**: Para persistencia de sesiones

### Timeout de Sesión
- Configurado a 30 minutos de inactividad
- Ajustar según necesidades del negocio

### Limpieza de Sesiones
- Ejecuta automáticamente cada 5 minutos
- Elimina sesiones expiradas para liberar memoria

### Manejo de Errores
- Todos los endpoints tienen manejo de errores robusto
- Códigos HTTP apropiados (401, 500, etc.)
- Mensajes descriptivos en español

## Archivos Eliminados (Opcionales)

Después de validar que todo funciona correctamente, puedes eliminar:

```bash
# Directorio del backend FastAPI
rm -rf backend_api/

# Scripts de Python (si existen)
rm -f *.py
rm -f requirements.txt

# Archivos de configuración del backend
rm -f backend_api/README.md
rm -f backend_api/requirements.txt
```

## Archivos Modificados

- `webapp/server/session.ts` (NUEVO)
- `webapp/server/api/login.post.ts` (NUEVO)
- `webapp/server/api/comprobantes.post.ts` (NUEVO)
- `webapp/server/api/download-pdf.post.ts` (NUEVO)
- `webapp/server/api/download-quincena.post.ts` (NUEVO)
- `webapp/server/api/logout.post.ts` (NUEVO)
- `webapp/app/services/api.ts` (MODIFICADO)
- `webapp/app/services/auth.service.ts` (MODIFICADO)
- `webapp/app/composables/useApi.ts` (NUEVO)
- `webapp/app/pages/descargar.vue` (MODIFICADO)
- `webapp/nuxt.config.ts` (MODIFICADO)

## Próximos Pasos

1. ✅ Implementar endpoints del servidor
2. ✅ Actualizar servicios del cliente
3. ✅ Implementar lógica de descarga
4. ⏳ Probar migración completa
5. ⏳ Documentar cambios
6. ⏳ Eliminar dependencia de FastAPI

## Soporte

Si encuentras problemas durante la migración:

1. Verifica que el servidor Nuxt está corriendo: `npm run dev`
2. Revisa la consola del navegador para errores
3. Revisa la terminal del servidor para logs
4. Verifica que IndexedDB se inicializa correctamente
5. Prueba cada endpoint individualmente con herramientas como Postman
