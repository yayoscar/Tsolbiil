#!/usr/bin/env python3
"""
Script para descargar todos los PDFs de comprobantes de un rango de quincenas.

Integra:
1. Endpoint de consulta: /mvc/comprobantes/pago/
2. Endpoint de descarga: /mvc/jasper/repReciboPago/

Autor: Agente de pruebas
Fecha: 2025-12-04
"""

import requests
from datetime import datetime
from typing import List, Dict, Any
import os
import time


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
COMPROBANTES_URL = f"{BASE_URL}/mvc/comprobantes/pago/"
DESCARGA_URL = f"{BASE_URL}/mvc/jasper/repReciboPago"


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


# =====================================================
# CONFIGURACIÓN DE DESCARGA
# =====================================================

OUTPUT_DIR = "/media/Files/Repos/Tsolbiil/descargas"


def print_separator(title: str = ""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def crear_sesion_portal(rfc: str, password: str) -> requests.Session:
    """Crea una sesión autenticada en el portal SEMS."""
    print_separator("🔐 INICIANDO SESIÓN")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # GET inicial
    session.get(LOGIN_PAGE, timeout=30)
    print(f"   JSESSIONID inicial: {session.cookies.get('JSESSIONID', 'N/A')[:15]}...")
    
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
    
    print(f"   JSESSIONID final: {session.cookies.get('JSESSIONID', 'N/A')[:15]}...")
    print("✅ Sesión creada exitosamente")
    return session


def obtener_comprobantes_quincena(
    session: requests.Session,
    rfc: str,
    anio: int,
    quincena: int,
) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de comprobantes para una quincena específica.
    """
    headers = {
        "Accept": "application/json,application/javascript",
        "X-Requested-With": "XMLHttpRequest",
        "Range": "items=0-99",  # Obtener hasta 100 comprobantes
        "Referer": f"{BASE_URL}/",
    }
    
    url = f"{COMPROBANTES_URL}?rfc={rfc}&anio={anio}&quincena={quincena}"
    
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    
    return resp.json()


def descargar_comprobante_pdf(
    session: requests.Session,
    id_comprobante: int,
    num_comprobante: int,
    anio: int,
    quincena: int,
    cons_qna_proc: int = 0,
    output_dir: str = OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    Descarga el PDF de un comprobante específico.
    
    Args:
        session: Sesión autenticada
        id_comprobante: ID del comprobante (idComprobante) - ESTE ES EL CORRECTO
        num_comprobante: Número del comprobante (numComprobante) - solo para nombrar archivo
        anio: Año del comprobante
        quincena: Quincena del comprobante
        cons_qna_proc: Consecutivo de quincena proceso (del JSON)
        output_dir: Directorio de salida
        
    Returns:
        Diccionario con información de la descarga
    """
    # Generar timestamp actual (parece ser usado como identificador de request)
    timestamp = int(time.time() * 1000)
    
    # Construir qnaProc: año + quincena con padding
    qna_proc = f"{anio}{quincena:02d}"
    
    url = f"{DESCARGA_URL}/{timestamp}"
    params = {
        "consQnaProc": cons_qna_proc,
        "qnaProc": qna_proc,
        "nuComprobante": id_comprobante,  # ¡Usar idComprobante aquí!
    }
    
    headers = {
        "Accept": "application/pdf,text/html,application/xhtml+xml,*/*",
        "Referer": f"{BASE_URL}/",
    }
    
    resp = session.get(url, params=params, headers=headers, timeout=60)
    
    result = {
        "id_comprobante": id_comprobante,
        "num_comprobante": num_comprobante,
        "anio": anio,
        "quincena": quincena,
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "size": len(resp.content),
        "success": False,
        "filepath": None,
        "error": None,
    }
    
    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}"
        return result
    
    # Verificar que es PDF
    if not resp.content.startswith(b'%PDF'):
        result["error"] = "El contenido no es PDF"
        return result
    
    # Guardar archivo
    os.makedirs(output_dir, exist_ok=True)
    filename = f"comprobante_{anio}_Q{quincena:02d}_{num_comprobante}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(resp.content)
    
    result["success"] = True
    result["filepath"] = filepath
    
    return result


def descargar_comprobantes_rango_quincenas(
    session: requests.Session,
    rfc: str,
    anio: int,
    quincena_inicio: int,
    quincena_fin: int,
) -> Dict[str, Any]:
    """
    Descarga todos los PDFs de comprobantes en un rango de quincenas.
    
    Args:
        session: Sesión autenticada
        rfc: RFC del trabajador
        anio: Año de consulta
        quincena_inicio: Primera quincena (inclusive)
        quincena_fin: Última quincena (inclusive)
        
    Returns:
        Resumen de la operación
    """
    
    resumen = {
        "anio": anio,
        "quincena_inicio": quincena_inicio,
        "quincena_fin": quincena_fin,
        "total_quincenas": 0,
        "total_comprobantes": 0,
        "descargas_exitosas": 0,
        "descargas_fallidas": 0,
        "detalles": [],
    }
    
    for quincena in range(quincena_inicio, quincena_fin + 1):
        print_separator(f"📅 QUINCENA {anio}/{quincena:02d}")
        resumen["total_quincenas"] += 1
        
        # Obtener comprobantes de esta quincena
        try:
            comprobantes = obtener_comprobantes_quincena(session, rfc, anio, quincena)
            print(f"   📋 Comprobantes encontrados: {len(comprobantes)}")
        except Exception as e:
            print(f"   ❌ Error obteniendo comprobantes: {e}")
            resumen["detalles"].append({
                "quincena": quincena,
                "error": str(e),
                "comprobantes": []
            })
            continue
        
        if not comprobantes:
            print(f"   ⚠️ No hay comprobantes para esta quincena")
            resumen["detalles"].append({
                "quincena": quincena,
                "comprobantes_encontrados": 0,
                "descargas": []
            })
            continue
        
        quincena_detalle = {
            "quincena": quincena,
            "comprobantes_encontrados": len(comprobantes),
            "descargas": []
        }
        
        # Descargar cada comprobante
        for idx, comp in enumerate(comprobantes):
            resumen["total_comprobantes"] += 1
            
            # ¡IMPORTANTE! Usar idComprobante, NO numComprobante
            id_comprobante = comp.get("idComprobante")
            num_comprobante = comp.get("numComprobante")
            neto = comp.get("totNetoCheque", 0)
            cons_qna = comp.get("consQnaProc", 0)
            
            print(f"\n   [{idx+1}/{len(comprobantes)}] Comprobante")
            print(f"       idComprobante: {id_comprobante}")
            print(f"       numComprobante: {num_comprobante}")
            print(f"       Neto: ${neto:,.2f}")
            print(f"       consQnaProc: {cons_qna}")
            
            # Descargar PDF usando idComprobante (el correcto)
            try:
                resultado = descargar_comprobante_pdf(
                    session=session,
                    id_comprobante=id_comprobante,  # Cambiado a idComprobante
                    num_comprobante=num_comprobante,
                    anio=anio,
                    quincena=quincena,
                    cons_qna_proc=cons_qna,  # Usar el del JSON
                )
                
                if resultado["success"]:
                    print(f"       ✅ Descargado: {resultado['filepath']}")
                    print(f"       📦 Tamaño: {resultado['size']:,} bytes")
                    resumen["descargas_exitosas"] += 1
                else:
                    print(f"       ❌ Error: {resultado['error']}")
                    resumen["descargas_fallidas"] += 1
                
                quincena_detalle["descargas"].append(resultado)
                
            except Exception as e:
                print(f"       ❌ Excepción: {e}")
                resumen["descargas_fallidas"] += 1
                quincena_detalle["descargas"].append({
                    "num_comprobante": num_comprobante,
                    "success": False,
                    "error": str(e)
                })
            
            # Pequeña pausa para no sobrecargar el servidor
            time.sleep(0.5)
        
        resumen["detalles"].append(quincena_detalle)
    
    return resumen


def main():
    """Función principal de prueba."""
    
    print("\n" * 2)
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║   DESCARGA MASIVA DE COMPROBANTES PDF - PORTAL SEMS                  ║")
    print("║   Rango: 2025 Quincenas 10-13                                        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"\n⏰ Inicio: {datetime.now().isoformat()}")
    print(f"📁 Directorio de salida: {OUTPUT_DIR}")
    
    # Crear sesión
    try:
        session = crear_sesion_portal(RFC_TEST, PASSWORD_TEST)
    except Exception as e:
        print(f"\n❌ Error al crear sesión: {e}")
        return
    
    # Descargar comprobantes del rango 2025, quincenas 10-13
    resumen = descargar_comprobantes_rango_quincenas(
        session=session,
        rfc=RFC_TEST,
        anio=2025,
        quincena_inicio=10,
        quincena_fin=13,
    )
    
    # Mostrar resumen final
    print_separator("📊 RESUMEN FINAL")
    
    print(f"\n📅 Período: {resumen['anio']} / Quincenas {resumen['quincena_inicio']}-{resumen['quincena_fin']}")
    print(f"📋 Total quincenas procesadas: {resumen['total_quincenas']}")
    print(f"📄 Total comprobantes encontrados: {resumen['total_comprobantes']}")
    print(f"✅ Descargas exitosas: {resumen['descargas_exitosas']}")
    print(f"❌ Descargas fallidas: {resumen['descargas_fallidas']}")
    
    # Detalle por quincena
    print(f"\n📋 Detalle por quincena:")
    for det in resumen["detalles"]:
        qna = det["quincena"]
        encontrados = det.get("comprobantes_encontrados", 0)
        descargas = det.get("descargas", [])
        exitosas = sum(1 for d in descargas if d.get("success", False))
        
        print(f"   Q{qna:02d}: {encontrados} comprobantes, {exitosas} PDFs descargados")
    
    print(f"\n⏰ Fin: {datetime.now().isoformat()}")
    print(f"📁 Archivos en: {OUTPUT_DIR}")
    
    # Listar archivos descargados
    if os.path.exists(OUTPUT_DIR):
        archivos = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
        if archivos:
            print(f"\n📂 Archivos PDF descargados ({len(archivos)}):")
            for archivo in sorted(archivos):
                filepath = os.path.join(OUTPUT_DIR, archivo)
                size = os.path.getsize(filepath)
                print(f"   - {archivo} ({size:,} bytes)")


if __name__ == "__main__":
    main()
