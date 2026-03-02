#!/usr/bin/env python3
"""
Script para probar descarga de comprobantes del portal SEMS.

Endpoint: /mvc/jasper/repReciboPago/{timestamp}
Parámetros: consQnaProc, qnaProc, nuComprobante
"""

import requests
from datetime import datetime
import os


# =====================================================
# CONFIGURACIÓN - CREDENCIALES
# =====================================================

RFC_TEST = "PEOO820203MB1"
PASSWORD_TEST = "atlante3"


# =====================================================
# CONFIGURACIÓN - URLs DEL PORTAL
# =====================================================

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"


# =====================================================
# HEADERS
# =====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def print_separator(title: str = ""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def crear_sesion_portal(rfc: str, password: str) -> requests.Session:
    """Crea una sesión autenticada en el portal SEMS."""
    print_separator("🔐 INICIANDO SESIÓN")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # GET inicial
    session.get(LOGIN_PAGE, timeout=30)
    
    # POST login
    login_data = {"j_username": rfc, "j_password": password}
    post_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": LOGIN_PAGE,
        "Origin": BASE_URL,
    }
    
    resp = session.post(AUTH_ENDPOINT, data=login_data, headers=post_headers, 
                        allow_redirects=True, timeout=30)
    
    if "login.jsp" in resp.url:
        raise Exception("Login fallido")
    
    print("✅ Sesión creada exitosamente")
    return session


def probar_descarga_comprobante(session: requests.Session):
    """Prueba la descarga de un comprobante usando el endpoint de Jasper."""
    
    print_separator("📥 PROBANDO DESCARGA DE COMPROBANTE")
    
    # URL del ejemplo proporcionado
    timestamp = "1764892687195"
    url = f"{BASE_URL}/mvc/jasper/repReciboPago/{timestamp}"
    
    params = {
        "consQnaProc": "0",
        "qnaProc": "202516",
        "nuComprobante": "69065819"
    }
    
    print(f"📤 GET a: {url}")
    print(f"   Parámetros: {params}")
    
    # Headers para descarga
    download_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/pdf",
        "Referer": f"{BASE_URL}/",
    }
    
    resp = session.get(url, params=params, headers=download_headers, timeout=60)
    
    print(f"\n📥 Respuesta recibida:")
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"   Content-Length: {resp.headers.get('Content-Length', 'N/A')} bytes")
    print(f"   Content-Disposition: {resp.headers.get('Content-Disposition', 'N/A')}")
    
    # Mostrar todos los headers de respuesta
    print(f"\n   📋 Todos los headers de respuesta:")
    for key, value in resp.headers.items():
        print(f"      {key}: {value}")
    
    # Analizar el contenido
    content = resp.content
    content_type = resp.headers.get('Content-Type', '').lower()
    
    print(f"\n   📊 Análisis del contenido:")
    print(f"      Tamaño: {len(content)} bytes")
    
    # Detectar tipo de archivo por magic bytes
    file_type = "desconocido"
    extension = ".bin"
    
    if content[:4] == b'%PDF':
        file_type = "PDF"
        extension = ".pdf"
    elif content[:2] == b'PK':
        file_type = "ZIP/Office (XLSX, DOCX, etc.)"
        extension = ".zip"
    elif content[:5] == b'<?xml':
        file_type = "XML"
        extension = ".xml"
    elif b'<html' in content[:500].lower() or b'<!doctype' in content[:500].lower():
        file_type = "HTML"
        extension = ".html"
    elif content[:3] == b'\xef\xbb\xbf' or content[:5] == b'<?xml':
        file_type = "XML con BOM"
        extension = ".xml"
    
    print(f"      Tipo detectado (magic bytes): {file_type}")
    print(f"      Primeros 100 bytes (raw): {content[:100]}")
    
    # Si es texto, mostrar preview
    try:
        text_preview = content[:500].decode('utf-8', errors='replace')
        print(f"\n      Preview como texto (primeros 500 chars):")
        print(f"      {text_preview[:500]}")
    except:
        print(f"      (No se puede decodificar como texto)")
    
    # Guardar el archivo
    output_dir = "/media/Files/Repos/Tsolbiil/descargas"
    os.makedirs(output_dir, exist_ok=True)
    
    # Intentar obtener nombre del Content-Disposition
    content_disp = resp.headers.get('Content-Disposition', '')
    if 'filename=' in content_disp:
        # Extraer nombre del archivo
        import re
        match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disp)
        if match:
            filename = match.group(1).strip()
        else:
            filename = f"comprobante_69065819{extension}"
    else:
        filename = f"comprobante_69065819{extension}"
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    print(f"\n   💾 Archivo guardado:")
    print(f"      Ruta: {filepath}")
    print(f"      Tamaño: {len(content)} bytes")
    
    return {
        "status": resp.status_code,
        "content_type": content_type,
        "file_type": file_type,
        "size": len(content),
        "filepath": filepath,
    }


if __name__ == "__main__":
    print("\n" * 2)
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   PRUEBA DE DESCARGA DE COMPROBANTE - PORTAL SEMS          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n⏰ Timestamp: {datetime.now().isoformat()}")
    
    try:
        session = crear_sesion_portal(RFC_TEST, PASSWORD_TEST)
        resultado = probar_descarga_comprobante(session)
        
        print_separator("📊 RESUMEN")
        print(f"Status: {resultado['status']}")
        print(f"Tipo de contenido: {resultado['content_type']}")
        print(f"Tipo de archivo detectado: {resultado['file_type']}")
        print(f"Tamaño: {resultado['size']} bytes")
        print(f"Guardado en: {resultado['filepath']}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
