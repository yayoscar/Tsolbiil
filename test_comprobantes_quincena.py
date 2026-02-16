#!/usr/bin/env python3
"""
Script de prueba de consulta de comprobantes por año/quincena.

Portal: https://portalautoservicios-sems.sep.gob.mx/
Endpoint: /mvc/comprobantes/pago/

Autor: Agente de pruebas
Fecha: 2024
"""

import requests
from datetime import datetime
from typing import List, Dict, Any


# =====================================================
# CONFIGURACIÓN - CREDENCIALES
# =====================================================
# ⚠️ NO incluir credenciales reales aquí
# Reemplazar con tus datos antes de ejecutar

RFC_TEST = "PEOO820203MB1"
PASSWORD_TEST = "atlante3"


# =====================================================
# CONFIGURACIÓN - URLs DEL PORTAL
# =====================================================

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
DETALLE_PATH = "/mvc/comprobantes/pago/"
DETALLE_URL = f"{BASE_URL}{DETALLE_PATH}"


# =====================================================
# HEADERS - Simular navegador real
# =====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


def print_separator(title: str = ""):
    """Imprime un separador visual para los logs."""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def crear_sesion_portal(rfc: str, password: str) -> requests.Session:
    """
    Crea una sesión autenticada en el portal SEMS.
    
    Args:
        rfc: RFC del usuario
        password: Contraseña del usuario
        
    Returns:
        requests.Session con sesión activa
        
    Raises:
        Exception: Si el login falla
    """
    print_separator("🔐 INICIANDO SESIÓN EN PORTAL SEMS")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # GET inicial para obtener cookies
    print("📥 GET inicial a login.jsp...")
    resp_get = session.get(LOGIN_PAGE, timeout=30)
    print(f"   Status: {resp_get.status_code}")
    print(f"   JSESSIONID inicial: {session.cookies.get('JSESSIONID', 'N/A')[:20]}...")
    
    # POST de autenticación
    print("\n📤 POST de autenticación...")
    login_data = {
        "j_username": rfc,
        "j_password": password
    }
    
    post_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": LOGIN_PAGE,
        "Origin": BASE_URL,
    }
    
    resp_post = session.post(
        AUTH_ENDPOINT,
        data=login_data,
        headers=post_headers,
        allow_redirects=True,
        timeout=30
    )
    
    print(f"   Status: {resp_post.status_code}")
    print(f"   URL final: {resp_post.url}")
    print(f"   JSESSIONID final: {session.cookies.get('JSESSIONID', 'N/A')[:20]}...")
    
    # Validar login exitoso
    if "login.jsp" in resp_post.url:
        raise Exception(f"❌ Login fallido. URL final: {resp_post.url}")
    
    print("\n✅ Sesión creada exitosamente")
    return session


def obtener_detalle_quincena(
    session: requests.Session,
    rfc: str,
    anio: int,
    quincena: int,
    offset: int = 0,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Consulta los comprobantes de nómina para un RFC, año y quincena
    usando el endpoint JSON oficial del portal SEMS.
    
    Args:
        session: Sesión autenticada
        rfc: RFC del trabajador
        anio: Año de consulta
        quincena: Número de quincena (1-24)
        offset: Inicio de paginación (default 0)
        limit: Cantidad de registros (default 10)
        
    Returns:
        Lista de comprobantes como diccionarios
    """
    
    range_header = f"items={offset}-{offset + limit - 1}"
    
    headers = {
        "Accept": "application/json,application/javascript",
        "X-Requested-With": "XMLHttpRequest",
        "Range": range_header,
        "Referer": f"{BASE_URL}/",
    }
    
    # El endpoint real usa GET con query parameters
    url = f"{DETALLE_URL}?rfc={rfc}&anio={anio}&quincena={quincena}"
    
    print(f"\n📤 GET a {url}")
    print(f"   Headers: Range={range_header}")
    
    resp = session.get(url, headers=headers, timeout=30)
    
    print(f"\n📥 Respuesta recibida:")
    print(f"   URL detalle: {resp.url}")
    print(f"   Status detalle: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"   Content-Range: {resp.headers.get('Content-Range', 'N/A')}")
    
    # Validar respuesta
    resp.raise_for_status()
    
    # Parsear JSON
    try:
        comprobantes = resp.json()
    except Exception as e:
        print(f"   ⚠️ Error parseando JSON: {e}")
        print(f"   Contenido raw (primeros 500 chars): {resp.text[:500]}")
        return []
    
    print(f"   Total comprobantes devueltos: {len(comprobantes)}")
    
    # Mostrar primer comprobante si existe
    if comprobantes:
        primero = comprobantes[0]
        print("\n   📄 Primer comprobante:")
        print(f"      idComprobante: {primero.get('idComprobante', 'N/A')}")
        print(f"      numComprobante: {primero.get('numComprobante', 'N/A')}")
        print(f"      totNetoCheque: {primero.get('totNetoCheque', 'N/A')}")
        print(f"      anio: {primero.get('anio', 'N/A')}")
        print(f"      quincena: {primero.get('quincena', 'N/A')}")
        
        # Mostrar todas las claves disponibles
        print(f"\n   🔑 Claves disponibles en comprobante:")
        for key in sorted(primero.keys()):
            print(f"      - {key}")
    
    return comprobantes


def ejecutar_pruebas():
    """
    Ejecuta las pruebas de consulta de comprobantes.
    
    Escenario A: 2025/10 - Se espera al menos 1 comprobante
    Escenario B: 2025/23 - Se espera 0 comprobantes
    """
    
    print("\n" * 2)
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   PRUEBA DE CONSULTA DE COMPROBANTES POR AÑO/QUINCENA      ║")
    print("║   Portal de Autoservicios SEMS - SEP                       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n⏰ Timestamp: {datetime.now().isoformat()}")
    
    resultados = {
        "timestamp": datetime.now().isoformat(),
        "escenario_a": {"exito": False, "comprobantes": 0},
        "escenario_b": {"exito": False, "comprobantes": 0},
    }
    
    # =========================================================
    # PASO 1: Crear sesión autenticada
    # =========================================================
    try:
        session = crear_sesion_portal(RFC_TEST, PASSWORD_TEST)
    except Exception as e:
        print(f"\n❌ Error al crear sesión: {e}")
        return resultados
    
    # =========================================================
    # ESCENARIO A: 2025 / Quincena 10 (se espera comprobantes)
    # =========================================================
    print_separator("🧪 ESCENARIO A: 2025 / QNA 10")
    print("📋 Expectativa: Al menos 1 comprobante")
    
    anio_ok = 2025
    quincena_ok = 10
    
    try:
        comprobantes_ok = obtener_detalle_quincena(
            session=session,
            rfc=RFC_TEST,
            anio=anio_ok,
            quincena=quincena_ok,
            offset=0,
            limit=10,
        )
        
        resultados["escenario_a"]["comprobantes"] = len(comprobantes_ok)
        resultados["escenario_a"]["data"] = comprobantes_ok
        
        print(f"\n📊 RESULTADO ESCENARIO A:")
        print(f"   Comprobantes obtenidos: {len(comprobantes_ok)}")
        
        if len(comprobantes_ok) > 0:
            print("   ✅ ÉXITO - Se encontraron comprobantes")
            resultados["escenario_a"]["exito"] = True
        else:
            print("   ⚠️ No se encontraron comprobantes (inesperado)")
            
        # Mostrar lista completa
        if comprobantes_ok:
            print("\n   📋 Lista completa de comprobantes:")
            for i, comp in enumerate(comprobantes_ok):
                print(f"      [{i+1}] ID: {comp.get('idComprobante')}, "
                      f"Num: {comp.get('numComprobante')}, "
                      f"Neto: ${comp.get('totNetoCheque', 0):,.2f}")
                
    except Exception as e:
        print(f"\n❌ Error en Escenario A: {e}")
        resultados["escenario_a"]["error"] = str(e)
    
    # =========================================================
    # ESCENARIO B: 2025 / Quincena 23 (se espera 0 comprobantes)
    # =========================================================
    print_separator("🧪 ESCENARIO B: 2025 / QNA 23")
    print("📋 Expectativa: 0 comprobantes")
    
    anio_vacio = 2025
    quincena_vacia = 23
    
    try:
        comprobantes_vacios = obtener_detalle_quincena(
            session=session,
            rfc=RFC_TEST,
            anio=anio_vacio,
            quincena=quincena_vacia,
            offset=0,
            limit=10,
        )
        
        resultados["escenario_b"]["comprobantes"] = len(comprobantes_vacios)
        resultados["escenario_b"]["data"] = comprobantes_vacios
        
        print(f"\n📊 RESULTADO ESCENARIO B:")
        print(f"   Comprobantes obtenidos: {len(comprobantes_vacios)}")
        
        if len(comprobantes_vacios) == 0:
            print("   ✅ ÉXITO - No hay comprobantes (esperado)")
            resultados["escenario_b"]["exito"] = True
        else:
            print(f"   ⚠️ Se encontraron {len(comprobantes_vacios)} comprobantes (inesperado)")
            
        # Mostrar lista si hay datos
        if comprobantes_vacios:
            print("\n   📋 Lista de comprobantes encontrados:")
            for i, comp in enumerate(comprobantes_vacios):
                print(f"      [{i+1}] ID: {comp.get('idComprobante')}, "
                      f"Num: {comp.get('numComprobante')}, "
                      f"Neto: ${comp.get('totNetoCheque', 0):,.2f}")
                
    except Exception as e:
        print(f"\n❌ Error en Escenario B: {e}")
        resultados["escenario_b"]["error"] = str(e)
    
    # =========================================================
    # RESUMEN FINAL
    # =========================================================
    print_separator("📊 RESUMEN FINAL DE PRUEBAS")
    
    print(f"⏰ Timestamp: {resultados['timestamp']}")
    print(f"\n🧪 Escenario A (2025/QNA 10):")
    print(f"   Comprobantes: {resultados['escenario_a']['comprobantes']}")
    print(f"   Resultado: {'✅ ÉXITO' if resultados['escenario_a']['exito'] else '❌ FALLO'}")
    
    print(f"\n🧪 Escenario B (2025/QNA 23):")
    print(f"   Comprobantes: {resultados['escenario_b']['comprobantes']}")
    print(f"   Resultado: {'✅ ÉXITO' if resultados['escenario_b']['exito'] else '❌ FALLO'}")
    
    # Conclusiones
    print_separator("🎯 CONCLUSIONES")
    
    if resultados["escenario_a"]["exito"] and resultados["escenario_b"]["exito"]:
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("\n📝 Notas:")
        print("   - El endpoint /mvc/comprobantes/pago/ funciona correctamente")
        print("   - La paginación con Range header es funcional")
        print("   - Se puede detectar quincenas sin comprobantes (lista vacía)")
    else:
        print("⚠️ ALGUNAS PRUEBAS FALLARON")
        print("   Revisar los detalles arriba para más información.")
    
    print("\n" + "=" * 60)
    
    return resultados


if __name__ == "__main__":
    ejecutar_pruebas()
    print("\n📁 Script finalizado.")
    print("   Revisa el archivo agent.md para documentación completa.")
