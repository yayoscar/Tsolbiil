# Sistema de Persistencia Local con IndexedDB

## Resumen

Se ha implementado un sistema completo de persistencia local multiusuario con cifrado de credenciales, manejo automático de re-autenticación en 401, y preparación de tablas para comprobantes.

## Arquitectura

### Componentes Principales

1. **Base de Datos (IndexedDB)**
   - `app/db/schema.ts` - Interfaces TypeScript para todas las entidades
   - `app/db/db.ts` - Instancia Dexie con configuración de tablas e índices

2. **Utilidades de Cifrado**
   - `app/utils/crypto.ts` - Web Crypto API (PBKDF2 + AES-GCM)

3. **Servicios**
   - `app/services/auth.service.ts` - Lógica de autenticación y gestión de usuarios
   - `app/services/http.service.ts` - Cliente HTTP con interceptor para 401

4. **Composables**
   - `app/composables/useSession.ts` - Estado reactivo de sesión
   - `app/composables/useAuth.ts` - API compatible hacia atrás

5. **Middleware**
   - `app/middleware/auth.global.ts` - Protección de rutas

## Base de Datos

### Nombre
`tsolbiil_db` (versión 1)

### Tablas

#### 1. `users`
Almacena usuarios locales (multiusuario).

**Campos:**
- `id`: string (UUID, PK)
- `rfcHash`: string (SHA-256 del RFC normalizado)
- `displayName`: string (opcional)
- `createdAt`: number
- `lastLoginAt`: number
- `active`: boolean

**Índices:**
- `rfcHash` (unique)
- `active`

#### 2. `authSecrets`
Credenciales cifradas (1:1 con users).

**Campos:**
- `userId`: string (PK)
- `ciphertext`: string (base64)
- `iv`: string (base64)
- `salt`: string (base64)
- `kdf`: { name, iterations, hash }
- `updatedAt`: number

#### 3. `sessions`
Sesiones de usuario.

**Campos:**
- `id`: string (UUID, PK)
- `userId`: string
- `sessionToken`: string
- `createdAt`: number
- `updatedAt`: number
- `isActive`: boolean
- `expiresAt`: number (opcional)
- `last401At`: number (opcional)
- `lastError`: string (opcional)

**Índices:**
- `userId`
- `isActive`
- `[userId+isActive]` (compuesto)

#### 4. `deviceSecrets`
Master key local para cifrado.

**Campos:**
- `id`: string ('master', PK único)
- `secret`: string (base64)
- `createdAt`: number

#### 5. `comprobantes` (preparado)
Documentos de pago.

**Campos:**
- `id`: string (PK)
- `userId`: string
- `uuidFiscal`: string (opcional)
- `folio`: string (opcional)
- `fechaPago`: number
- `periodoInicio`: number (opcional)
- `periodoFin`: number (opcional)
- `totalPercepciones`: number (opcional)
- `totalDeducciones`: number (opcional)
- `neto`: number (opcional)
- `createdAt`: number
- `updatedAt`: number
- `deletedAt`: number (opcional)

**Índices:**
- `userId`
- `[userId+fechaPago]`
- `[userId+uuidFiscal]`

#### 6. `comprobanteFiles` (preparado)
Archivos PDF/XML de comprobantes.

**Campos:**
- `id`: string (PK)
- `userId`: string
- `comprobanteId`: string
- `tipo`: 'PDF' | 'XML' | 'ORIGINAL'
- `mimeType`: string
- `blob`: Blob
- `hash`: string (opcional)
- `sizeBytes`: number (opcional)
- `createdAt`: number

**Índices:**
- `[userId+comprobanteId]`
- `[userId+tipo]`

#### 7. `conceptos` (preparado)
Percepciones/Deducciones.

**Campos:**
- `id`: string (PK)
- `userId`: string
- `comprobanteId`: string
- `categoria`: 'PERCEPCION' | 'DEDUCCION' | 'OTRO'
- `clave`: string (opcional)
- `descripcion`: string
- `monto`: number
- `orden`: number (opcional)
- `createdAt`: number

**Índices:**
- `[userId+comprobanteId]`
- `[userId+categoria]`

#### 8. `outbox` (preparado para sync futura)
Cola de sincronización.

**Campos:**
- `id`: string (PK)
- `userId`: string
- `entity`: string
- `entityId`: string
- `op`: 'UPSERT' | 'DELETE'
- `payload`: any
- `createdAt`: number
- `sentAt`: number (opcional)

## Cifrado

### Estrategia
- **Algoritmo**: AES-GCM (256 bits)
- **Derivación**: PBKDF2 con 100,000 iteraciones
- **Hash**: SHA-256

### Device Secret
Se genera un "master key" local de 32 bytes aleatorios que se guarda en `deviceSecrets`. Este secreto se usa como base para derivar las claves de cifrado.

**Nota:** En futuras versiones se puede evolucionar a:
- PIN local del usuario
- WebAuthn / biometría
- Sin romper el esquema actual

### Flujo de Cifrado
1. Obtener/crear `deviceSecret`
2. Generar `salt` aleatorio (16 bytes)
3. Derivar clave: `PBKDF2(deviceSecret, salt, 100000)`
4. Generar `iv` aleatorio (12 bytes)
5. Cifrar datos: `AES-GCM(clave, iv, datos)`
6. Guardar `{ ciphertext, iv, salt, kdf }`

### Datos Cifrados
Solo se cifran las credenciales:
```typescript
{
  rfc: string,
  password: string
}
```

**Nunca se guarda RFC o password en texto plano.**

## Flujos

### Login (Primer Inicio)
1. Usuario ingresa RFC + password
2. `authService.login()` llama a `POST /login` del backend
3. Si success:
   - Calcular `rfcHash = SHA-256(RFC normalizado)`
   - Buscar/crear usuario en `users`
   - Cifrar `{ rfc, password }` con `deviceSecret`
   - Guardar en `authSecrets`
   - Crear sesión en `sessions` con `sessionToken`
   - Actualizar estado reactivo
4. Si error: mostrar mensaje

### Login (Recurrente)
1. Middleware `auth.global.ts` ejecuta `checkSession()`
2. `authService.getActiveSession()` busca sesión activa en IndexedDB
3. Si existe: restaurar estado reactivo
4. Si no: redirigir a `/login`

### Re-autenticación Automática (401)
1. Request al backend responde 401
2. `httpService` intercepta el 401
3. Obtiene sesión activa y `userId`
4. Descifra credenciales desde `authSecrets`
5. Ejecuta `authService.login()` para obtener nuevo token
6. Reintenta request original (1 sola vez)
7. Si falla:
   - Marca error en `sessions`
   - Ejecuta `logout()`
   - Redirige a `/login`

### Control de Concurrencia
Si múltiples requests reciben 401 simultáneamente:
- Solo el primero ejecuta re-autenticación
- Los demás esperan con una Promise compartida (`reauthPromise`)
- Todos reintintan con el nuevo token

### Logout
1. Usuario hace clic en logout
2. `authService.logout()`:
   - Marca sesión como `isActive=false`
   - Marca usuario como `active=false`
3. Limpia estado reactivo
4. Redirige a `/login`

**Nota:** Las credenciales cifradas permanecen en IndexedDB para futuros logins.

## API de Servicios

### auth.service.ts

```typescript
// Login contra backend y guardar local
login(rfc: string, password: string): Promise<LoginResult>

// Obtener sesión activa
getActiveSession(): Promise<{ session, user } | null>

// Obtener credenciales descifradas
getDecryptedCredentials(userId: string): Promise<DecryptedCredentials | null>

// Logout local
logout(): Promise<void>

// Marcar error 401
mark401Error(error?: string): Promise<void>

// Re-autenticar con credenciales guardadas
reauthenticate(): Promise<LoginResult>
```

### http.service.ts

```typescript
// Request con auto-retry en 401
httpRequest<T>(endpoint: string, options?: HttpOptions): Promise<T>

// Métodos HTTP
http.get<T>(endpoint, options?)
http.post<T>(endpoint, body?, options?)
http.put<T>(endpoint, body?, options?)
http.patch<T>(endpoint, body?, options?)
http.delete<T>(endpoint, options?)

// Cliente API específico
apiClient.login(rfc, password)
apiClient.logout()
apiClient.getComprobantes() // preparado
apiClient.downloadPDF(id) // preparado
```

### crypto.ts

```typescript
// Cifrado/descifrado
encrypt(data: any, password: string): Promise<{ ciphertext, iv, salt, iterations }>
decrypt<T>(ciphertext, iv, salt, password, iterations): Promise<T>

// Hashing
sha256Hash(text: string): Promise<string>
hashRFC(rfc: string): Promise<string>

// Utilidades
generateUUID(): string
normalizeRFC(rfc: string): string
generateSalt(): string
generateIV(): string
arrayBufferToBase64(buffer: ArrayBuffer): string
base64ToArrayBuffer(base64: string): ArrayBuffer
```

## Composables

### useSession()

```typescript
// Estado reactivo
isAuthenticated: ComputedRef<boolean>
user: ComputedRef<User | null>
session: ComputedRef<Session | null>
loading: ComputedRef<boolean>
error: ComputedRef<string | null>

// Métodos
checkSession(): Promise<void>
loginUser(rfc, password): Promise<{ success, error? }>
logoutUser(): Promise<void>
getSessionToken(): string | null
setError(error: string | null): void
clearSession(): void
```

### useAuth()

```typescript
// API compatible hacia atrás
isAuthenticated: ComputedRef<boolean>
user: ComputedRef<User | null>
sessionToken: ComputedRef<string | null>

// Métodos
login(rfc, password, rememberMe): Promise<{ success, error? }>
logout(): Promise<void>
checkSession(): Promise<void>
```

## Seguridad

### ✅ Implementado
- Cifrado de credenciales con AES-GCM
- Derivación de claves con PBKDF2 (100,000 iteraciones)
- RFC solo guardado como hash SHA-256
- Device secret aleatorio único por equipo
- Sesiones con tokens del backend
- Re-autenticación automática

### ⚠️ Consideraciones
- Device secret en IndexedDB es "seguridad razonable"
- NO es infalible contra acceso físico al dispositivo
- Para mayor seguridad futuro: PIN local + WebAuthn

### 🔒 Buenas Prácticas
- Nunca exponer RFC/password en logs
- Nunca enviar device secret al backend
- Session tokens del backend son la autoridad
- IndexedDB solo para recuperación automática

## Debug

En desarrollo, la instancia de Dexie está disponible en:
```javascript
window.tsolbiilDb
```

Puedes inspeccionar tablas:
```javascript
await window.tsolbiilDb.users.toArray()
await window.tsolbiilDb.sessions.toArray()
```

## Próximos Pasos

1. **Descargar comprobantes** desde el backend
2. **Guardar PDFs/XMLs** en `comprobanteFiles`
3. **Parsear conceptos** y guardar en `conceptos`
4. **Búsqueda offline** en comprobantes guardados
5. **Sync selectivo** con `outbox`
6. **PWA offline** completo
7. **PIN local** opcional para mayor seguridad
8. **WebAuthn** para autenticación biométrica

## Estructura de Archivos

```
webapp/app/
├── db/
│   ├── db.ts          # Instancia Dexie
│   └── schema.ts      # Tipos e interfaces
├── utils/
│   └── crypto.ts      # Web Crypto API
├── services/
│   ├── auth.service.ts  # Autenticación
│   └── http.service.ts  # Cliente HTTP
├── composables/
│   ├── useSession.ts    # Estado de sesión
│   └── useAuth.ts       # API compatible
├── middleware/
│   └── auth.global.ts   # Protección de rutas
└── pages/
    └── login.vue        # Página de login
```

## Dependencias

- `dexie` - Cliente IndexedDB con tipos
- Web Crypto API (nativa del navegador)

No se requieren librerías adicionales de cifrado.
