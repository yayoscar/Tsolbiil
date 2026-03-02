# Sistema de Descarga de Comprobantes SEMS

Sistema automatizado para descargar y procesar comprobantes de pago del Portal de Autoservicios SEMS-SEP.

## Características

- ✅ Lectura de configuración desde archivo JSON
- ✅ Organización automática de descargas por año
- ✅ Extracción de percepciones y deducciones de PDFs
- ✅ Generación de JSON único consolidado
- ✅ Exportación a Excel con formato profesional

## Requisitos

### Instalación con entorno virtual (recomendado)

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Editar el archivo `config.json` con tus datos:

```json
{
  "rfc": "TU_RFC_AQUI",
  "password": "TU_CONTRASEÑA",
  "anio_inicio": 2024,
  "quincena_inicio": 1
}
```

### Parámetros de configuración:

- **rfc**: RFC del trabajador (13 caracteres)
- **password**: Contraseña del portal SEMS
- **anio_inicio**: Año del cual descargar comprobantes
- **quincena_inicio**: Quincena desde la cual iniciar (1-24)

## Uso

### Verificación inicial

Antes de ejecutar el sistema, verifica que todo esté configurado:

```bash
source venv/bin/activate
python verificar.py
```

### Opción 1: Script de inicio rápido (recomendado)

```bash
./iniciar.sh
```

Este script automáticamente:
- Crea el entorno virtual si no existe
- Instala las dependencias si es necesario
- Ejecuta la descarga de comprobantes

### Opción 2: Ejecución manual

```bash
# Activar entorno virtual (si no está activo)
source venv/bin/activate

# Ejecutar script
python descarga_comprobantes.py

# Desactivar entorno virtual cuando termines
deactivate
```

## Estructura de Salida

```
descargas/
└── 2024/
    ├── comprobante_2024_Q01_12345.pdf
    ├── comprobante_2024_Q02_12346.pdf
    ├── ...
    ├── comprobantes_2024_completo.json
    └── comprobantes_2024_completo.xlsx
```

### Archivo JSON

Contiene todos los datos extraídos de los comprobantes:

```json
{
  "anio": 2024,
  "rfc": "PEOO820203MB1",
  "timestamp_proceso": "2026-01-16T10:30:00",
  "quincenas": [
    {
      "quincena": 1,
      "comprobantes": [
        {
          "id_comprobante": 12345,
          "num_comprobante": "ABC123",
          "percepciones": [
            {
              "codigo": "07",
              "denominacion": "SUELDO BASE",
              "importe": 15000.00
            }
          ],
          "deducciones": [
            {
              "codigo": "03",
              "denominacion": "ISSSTE",
              "importe": 1500.00
            }
          ],
          "totales": {
            "total_percepciones": 15000.00,
            "total_deducciones": 1500.00,
            "neto": 13500.00
          }
        }
      ]
    }
  ],
  "resumen": {
    "total_quincenas_con_comprobantes": 24,
    "total_comprobantes": 24,
    "total_percepciones_anual": 360000.00,
    "total_deducciones_anual": 36000.00,
    "total_neto_anual": 324000.00
  }
}
```

### Archivo Excel

Tabla con las siguientes columnas:

| Comprobante | Año  | Quincena | Tipo       | Concepto           | Monto     |
|-------------|------|----------|------------|--------------------|-----------|
| ABC123      | 2024 | 1        | Percepción | 07 - SUELDO BASE   | 15,000.00 |
| ABC123      | 2024 | 1        | Deducción  | 03 - ISSSTE        | 1,500.00  |

## Características Avanzadas

### Organización por Año

Las descargas se organizan automáticamente en carpetas por año:
- `descargas/2024/`
- `descargas/2025/`

### Procesamiento Configurable

Puedes configurar desde qué quincena iniciar la descarga. Por ejemplo, para descargar solo de Q12 a Q24:

```json
{
  "quincena_inicio": 12
}
```

### Datos Consolidados

- Un único archivo JSON con todos los datos del año
- Un único archivo Excel con todos los conceptos desglosados
- Resumen con totales anuales

## Seguridad

⚠️ **Importante**: El archivo `config.json` contiene información sensible.

### Primera vez:
```bash
# Copiar el archivo de ejemplo
cp config.json.ejemplo config.json

# Editar con tus datos reales
nano config.json
```

El archivo `config.json` ya está en `.gitignore` para proteger tus credenciales.

## Solución de Problemas

### Error de Login
- Verifica que el RFC y contraseña sean correctos
- Asegúrate de tener acceso al portal SEMS

### Error al Extraer PDF
- Algunos PDFs pueden tener formato diferente
- El script intentará extraer lo que pueda

### Error de Instalación de Dependencias

Si obtienes un error de "externally-managed-environment", usa un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Archivos del Proyecto

### Archivos principales
- **descarga_comprobantes.py** - Script principal de descarga
- **config.json** - Archivo de configuración (crear desde ejemplo)
- **config.json.ejemplo** - Plantilla de configuración
- **requirements.txt** - Dependencias del proyecto

### Scripts de utilidad
- **iniciar.sh** - Script de inicio rápido
- **verificar.py** - Verificación del sistema y configuración

### Directorios
- **descargas/** - Directorio de salida (se crea automáticamente)
- **venv/** - Entorno virtual de Python

## Inicio Rápido

1. Clonar o descargar el repositorio
2. Crear y activar entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Crear archivo de configuración:
```bash
cp config.json.ejemplo config.json
nano config.json  # Editar con tus datos
```

4. Verificar configuración:
```bash
python verificar.py
```

5. Ejecutar descarga:
```bash
./iniciar.sh
```

6. Verificar resultados:
```bash
ls -lh descargas/2024/
```

## Licencia

Uso interno - SEP SEMS

## Autor

Sistema automatizado - 2026
