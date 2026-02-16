#!/usr/bin/env python3
"""
Script para verificar qué quincenas tienen comprobantes disponibles.
Útil para diagnosticar si las quincenas 1-9 realmente no tienen datos o hay un problema.
"""

import requests
import json


# Cargar configuración
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
COMPROBANTES_URL = f"{BASE_URL}/mvc/comprobantes/pago/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def crear_sesion_portal(rfc: str, password: str) -> requests.Session:
    """Crea una sesión autenticada en el portal SEMS."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(LOGIN_PAGE, timeout=30)
    
    resp = session.post(
        AUTH_ENDPOINT,
        data={"j_username": rfc, "j_password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=True,
        timeout=30
    )
    
    if "login.jsp" in resp.url:
        raise Exception("Login fallido")
    
    return session


def verificar_quincenas(session: requests.Session, rfc: str, anio: int):
    """Verifica todas las quincenas de un año."""
    print(f"\n{'='*70}")
    print(f"  VERIFICACIÓN DE QUINCENAS - AÑO {anio}")
    print(f"{'='*70}\n")
    
    resultados = []
    
    for quincena in range(1, 25):
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Range": "items=0-99",
        }
        # Formatear quincena con dos dígitos (01, 02, etc.)
        url = f"{COMPROBANTES_URL}?rfc={rfc}&anio={anio}&quincena={quincena:02d}"
        
        try:
            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            comprobantes = resp.json()
            
            tiene_datos = len(comprobantes) > 0
            estado = "✅" if tiene_datos else "❌"
            
            resultados.append({
                "quincena": quincena,
                "tiene_datos": tiene_datos,
                "cantidad": len(comprobantes)
            })
            
            print(f"  Q{quincena:02d}: {estado} {'Comprobantes: ' + str(len(comprobantes)) if tiene_datos else 'Sin comprobantes'}")
            
        except Exception as e:
            print(f"  Q{quincena:02d}: ⚠️  Error: {e}")
            resultados.append({
                "quincena": quincena,
                "tiene_datos": False,
                "error": str(e)
            })
    
    # Resumen
    con_datos = sum(1 for r in resultados if r.get("tiene_datos", False))
    sin_datos = sum(1 for r in resultados if not r.get("tiene_datos", False))
    
    print(f"\n{'='*70}")
    print(f"  RESUMEN")
    print(f"{'='*70}")
    print(f"  ✅ Quincenas con comprobantes: {con_datos}")
    print(f"  ❌ Quincenas sin comprobantes: {sin_datos}")
    print(f"\n  Primera quincena con datos: Q{next((r['quincena'] for r in resultados if r.get('tiene_datos')), 'N/A'):02d}")
    
    return resultados


def main():
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║   VERIFICACIÓN DE QUINCENAS DISPONIBLES                              ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    print(f"\n📋 RFC: {config['rfc']}")
    print(f"📅 Años a verificar: {config['anio_inicio']} - {config['anio_final']}")
    
    # Login
    print("\n🔐 Iniciando sesión...")
    try:
        session = crear_sesion_portal(config["rfc"], config["password"])
        print("✅ Sesión creada exitosamente")
    except Exception as e:
        print(f"❌ Error de login: {e}")
        return
    
    # Verificar cada año
    for anio in range(config["anio_inicio"], config["anio_final"] + 1):
        verificar_quincenas(session, config["rfc"], anio)
    
    print("\n✅ Verificación completada\n")


if __name__ == "__main__":
    main()
