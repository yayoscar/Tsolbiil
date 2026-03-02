# Implementación de Variables de Entorno - Resumen

## ✅ Cambios Realizados

### 1. Archivos de Configuración Creados

- **`.env`** - Variables de entorno locales (desarrollo)
- **`.env.example`** - Plantilla con valores de ejemplo
- **`.env.production.example`** - Plantilla para producción
- **`.gitignore`** - Ya configurado para excluir .env (no sube a Git)

### 2. Configuración de Nuxt

**Archivo:** `nuxt.config.ts`

Agregado `runtimeConfig` para exponer variables de entorno:

```typescript
runtimeConfig: {
  public: {
    apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8000'
  }
}
```

### 3. Servicios Actualizados

Se actualizaron 3 servicios para usar variables de entorno dinámicamente:

#### `app/services/http.service.ts`
- Función `getBackendUrl()` que lee la configuración
- Reemplaza constante hardcodeada `BACKEND_URL`

#### `app/services/auth.service.ts`
- Función `getBackendUrl()` para obtener URL dinámicamente
- Actualizado método `login()` para usar URL configurable

#### `app/services/api.ts`
- Función `getApiBaseUrl()` para configuración dinámica
- Reemplaza constante `API_BASE_URL`

### 4. Scripts y Herramientas

**Script `env.sh`:**
- `./env.sh dev` - Configurar para desarrollo
- `./env.sh prod` - Configurar para producción
- `./env.sh show` - Mostrar configuración actual

**Scripts npm (package.json):**
- `pnpm build:prod` - Build para producción
- `pnpm dev:prod` - Desarrollo con config de producción
- `pnpm env:dev` - Configurar entorno desarrollo
- `pnpm env:prod` - Configurar entorno producción
- `pnpm env:show` - Mostrar configuración

### 5. Documentación

- **`ENV_CONFIG.md`** - Guía completa de variables de entorno
- **`DEPLOY.md`** - Guía detallada de despliegue para múltiples plataformas
- **`README.md`** - Actualizado con instrucciones de configuración

## 📝 Variables de Entorno

### Variable Principal: `NUXT_PUBLIC_API_URL`

Esta variable controla la URL del backend API.

**Desarrollo:**
```env
NUXT_PUBLIC_API_URL=http://localhost:8000
```

**Producción:**
```env
NUXT_PUBLIC_API_URL=https://api.tudominio.com
```

> **Nota:** El prefijo `NUXT_PUBLIC_` hace que la variable esté disponible en el cliente (navegador).

## 🚀 Uso

### Desarrollo Local

```bash
# 1. Configurar variables (ya hecho)
cp .env.example .env

# 2. Iniciar en desarrollo
pnpm dev
```

### Producción

```bash
# 1. Configurar para producción
./env.sh prod
# o manualmente editar .env con URL de producción

# 2. Build
pnpm build

# 3. Preview
pnpm preview
```

### Cambiar entre Entornos

```bash
# Desarrollo
./env.sh dev
pnpm dev

# Producción
./env.sh prod
pnpm build
```

## 🔍 Verificación

Para verificar que la configuración está correcta:

```bash
# Ver variables actuales
./env.sh show
# o
pnpm env:show
```

En el navegador (consola de desarrollo):
```javascript
const config = useRuntimeConfig()
console.log('API URL:', config.public.apiUrl)
```

## 📦 Despliegue

### Vercel / Netlify

Configurar en el panel:
- Variable: `NUXT_PUBLIC_API_URL`
- Valor: `https://api.tudominio.com`

### Docker

```bash
docker run -e NUXT_PUBLIC_API_URL=https://api.tudominio.com tu-imagen
```

### VPS

```bash
# Editar .env.production
./env.sh prod
pnpm build
pm2 start .output/server/index.mjs
```

## ⚠️ Importante

1. **No subir `.env` a Git** - Ya está en `.gitignore`
2. **Usar `.env.example`** - Como plantilla para otros desarrolladores
3. **Prefijo `NUXT_PUBLIC_`** - Requerido para variables del cliente
4. **Rebuild necesario** - Al cambiar variables de entorno
5. **Configurar CORS** - En el backend para la URL de producción

## 📚 Documentación Adicional

- Ver `ENV_CONFIG.md` para detalles completos
- Ver `DEPLOY.md` para guías de despliegue específicas
- Ver `README.md` para información general

## ✨ Beneficios

- ✅ Configuración centralizada
- ✅ Diferentes URLs para dev/prod
- ✅ No hardcodear URLs en el código
- ✅ Fácil cambio entre entornos
- ✅ Seguro (no sube .env a Git)
- ✅ Compatible con todas las plataformas
- ✅ Scripts automatizados

---

**Fecha:** 22 de enero de 2026  
**Estado:** ✅ Implementado y probado
