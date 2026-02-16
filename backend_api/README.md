# Backend API para SEMS Comprobantes

Servidor FastAPI que actúa como proxy entre la aplicación Flutter y el portal SEMS.

## Instalación

```bash
cd backend_api
python -m venv venv
source venv/bin/activate  # En Linux/Mac
pip install -r requirements.txt
```

## Ejecutar

```bash
python main.py
```

O usando uvicorn directamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /` - Información de la API
- `POST /login` - Autenticar usuario
- `POST /comprobantes` - Obtener comprobantes
- `POST /download-pdf` - Descargar PDF
- `POST /logout` - Cerrar sesión

## Documentación Interactiva

Una vez ejecutando, visita:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
