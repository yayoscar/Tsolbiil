"""
Backend FastAPI para SEMS Comprobantes App
Actúa como proxy entre la app Flutter y el portal SEMS
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from datetime import datetime
import secrets

app = FastAPI(title="SEMS Comprobantes API", version="1.0.0")

# Configurar CORS para permitir peticiones desde Flutter Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar el dominio exacto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenamiento de sesiones en memoria (en producción usar Redis)
# Estructura: {session_token: {"session": requests.Session, "rfc": str}}
sessions = {}

# Constantes del portal SEMS
BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
COMPROBANTES_ENDPOINT = f"{BASE_URL}/mvc/comprobantes/pago/"
DOWNLOAD_PDF_ENDPOINT = f"{BASE_URL}/mvc/comprobantes/pago/descargar/pdf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Modelos Pydantic
class LoginRequest(BaseModel):
    rfc: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None

class ComprobanteRequest(BaseModel):
    session_token: str
    anio: int
    quincena: int

class Concepto(BaseModel):
    tipoConcepto: str
    claveConcepto: str
    concepto: str
    importe: float

class Comprobante(BaseModel):
    idArchivo: int
    nombre: str
    plaza: str
    folioRecibo: str
    fechaInicialPago: str
    fechaFinalPago: str
    quincena: int
    anio: int
    totalPercepciones: float
    totalDeducciones: float
    totalNeto: float
    conceptos: List[Concepto]

class DownloadPdfRequest(BaseModel):
    session_token: str
    id_archivo: int
    qna_proc: str  # Formato: "20241" para quincena 1 del 2024


def get_session(session_token: str) -> requests.Session:
    """Obtiene una sesión almacenada o lanza error"""
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return sessions[session_token]["session"]

def get_rfc(session_token: str) -> str:
    """Obtiene el RFC asociado a una sesión"""
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return sessions[session_token]["rfc"]


@app.get("/")
async def root():
    """Endpoint de prueba"""
    return {
        "message": "SEMS Comprobantes API",
        "version": "1.0.0",
        "endpoints": ["/login", "/comprobantes", "/download-pdf", "/logout"]
    }


@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Autentica al usuario en el portal SEMS y crea una sesión
    """
    try:
        # Crear sesión de requests
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Paso 1: GET a la página de login
        print(f"[Login] Iniciando autenticación para RFC: {credentials.rfc}")
        session.get(LOGIN_PAGE)
        
        # Paso 2: POST con credenciales
        auth_response = session.post(
            AUTH_ENDPOINT,
            data={
                "j_username": credentials.rfc,
                "j_password": credentials.password,
            },
            headers={
                "Referer": LOGIN_PAGE,
                "Origin": BASE_URL,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=True,
        )
        
        # Validar autenticación exitosa
        is_success = "login.jsp" not in auth_response.url
        
        if is_success:
            # Generar token de sesión único
            session_token = secrets.token_urlsafe(32)
            sessions[session_token] = {
                "session": session,
                "rfc": credentials.rfc
            }
            
            print(f"[Login] ✓ Autenticación exitosa para {credentials.rfc}")
            return LoginResponse(
                success=True,
                message="Autenticación exitosa",
                session_token=session_token
            )
        else:
            print(f"[Login] ✗ Autenticación fallida para {credentials.rfc}")
            return LoginResponse(
                success=False,
                message="RFC o contraseña incorrectos"
            )
            
    except Exception as e:
        print(f"[Login] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")


@app.post("/comprobantes", response_model=List[Comprobante])
async def get_comprobantes(request: ComprobanteRequest):
    """
    Obtiene los comprobantes para un año y quincena específicos
    """
    session = get_session(request.session_token)
    rfc = get_rfc(request.session_token)
    
    try:
        quincena_str = str(request.quincena).zfill(2)
        
        # Construir URL con parámetros en query string
        url = f"{COMPROBANTES_ENDPOINT}?rfc={rfc}&anio={request.anio}&quincena={quincena_str}"
        
        response = session.get(
            url,
            headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Range": "items=0-99",
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al obtener comprobantes: {response.status_code}"
            )
        
        comprobantes = response.json()
        print(f"[Comprobantes] Encontrados {len(comprobantes)} comprobantes")
        
        return comprobantes
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Comprobantes] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener comprobantes: {str(e)}")


@app.post("/download-pdf")
async def download_pdf(request: DownloadPdfRequest):
    """
    Descarga un PDF de comprobante
    """
    session = get_session(request.session_token)
    
    try:
        response = session.get(
            DOWNLOAD_PDF_ENDPOINT,
            params={
                "idArchivo": request.id_archivo,
                "qnaProc": request.qna_proc,
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al descargar PDF: {response.status_code}"
            )
        
        # Retornar el PDF como bytes
        from fastapi.responses import Response
        return Response(
            content=response.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=comprobante_{request.id_archivo}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Download] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al descargar PDF: {str(e)}")


class DownloadQuincenaRequest(BaseModel):
    session_token: str
    anio: int
    quincena: int

class ComprobanteConPdf(BaseModel):
    comprobante: Comprobante
    pdf_base64: str  # PDF codificado en base64

@app.post("/download-quincena", response_model=List[ComprobanteConPdf])
async def download_quincena(request: DownloadQuincenaRequest):
    """
    Descarga todos los comprobantes de una quincena con sus PDFs
    """
    session = get_session(request.session_token)
    rfc = get_rfc(request.session_token)
    
    try:
        import base64
        
        # Paso 1: Obtener lista de comprobantes
        quincena_str = str(request.quincena).zfill(2)
        
        print(f"[Download Quincena] Obteniendo comprobantes: {request.anio}/{quincena_str} para RFC: {rfc}")
        
        # Construir URL con parámetros en query string
        url = f"{COMPROBANTES_ENDPOINT}?rfc={rfc}&anio={request.anio}&quincena={quincena_str}"
        
        response = session.get(
            url,
            headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Range": "items=0-99",
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al obtener comprobantes: {response.status_code}"
            )
        
        comprobantes = response.json()
        print(f"[Download Quincena] Encontrados {len(comprobantes)} comprobantes")
        
        # Paso 2: Descargar PDF de cada comprobante
        resultado = []
        qna_proc = f"{request.anio}{request.quincena}"  # Sin padding
        
        for comp in comprobantes:
            try:
                id_archivo = comp['idArchivo']
                print(f"[Download Quincena] Descargando PDF: {id_archivo}")
                
                pdf_response = session.get(
                    DOWNLOAD_PDF_ENDPOINT,
                    params={
                        "idArchivo": id_archivo,
                        "qnaProc": qna_proc,
                    }
                )
                
                if pdf_response.status_code == 200:
                    # Codificar PDF en base64
                    pdf_base64 = base64.b64encode(pdf_response.content).decode('utf-8')
                    
                    resultado.append({
                        "comprobante": comp,
                        "pdf_base64": pdf_base64
                    })
                    print(f"[Download Quincena] ✓ PDF descargado: {id_archivo}")
                else:
                    print(f"[Download Quincena] ✗ Error descargando PDF {id_archivo}: {pdf_response.status_code}")
                    
            except Exception as e:
                print(f"[Download Quincena] Error con comprobante {comp.get('idArchivo')}: {str(e)}")
                continue
        
        print(f"[Download Quincena] Completado: {len(resultado)}/{len(comprobantes)} comprobantes descargados")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Download Quincena] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al descargar quincena: {str(e)}")


class LogoutRequest(BaseModel):
    session_token: str

@app.post("/logout")
async def logout(request: LogoutRequest):
    """
    Cierra una sesión
    """
    if request.session_token in sessions:
        del sessions[request.session_token]
        return {"success": True, "message": "Sesión cerrada"}
    return {"success": False, "message": "Sesión no encontrada"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
