#!/usr/bin/env python3
"""
Script para investigar la estructura correcta de descarga de comprobantes.
"""

import requests
import json


# Configuración
RFC_TEST = "PEOO820203MB1"
PASSWORD_TEST = "atlante3"
BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def crear_sesion():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(f"{BASE_URL}/login.jsp", timeout=30)
    resp = session.post(
        f"{BASE_URL}/j_spring_security_check",
        data={"j_username": RFC_TEST, "j_password": PASSWORD_TEST},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=True,
        timeout=30
    )
    if "login.jsp" in resp.url:
        raise Exception("Login fallido")
    return session


def main():
    print("=" * 70)
    print("INVESTIGACIÓN DE ESTRUCTURA DE COMPROBANTES")
    print("=" * 70)
    
    session = crear_sesion()
    print("✅ Sesión creada\n")
    
    # Obtener comprobantes de quincena 16 (el de la URL original)
    print("📋 Obteniendo comprobantes de 2025/Q16...")
    
    url = f"{BASE_URL}/mvc/comprobantes/pago/?rfc={RFC_TEST}&anio=2025&quincena=16"
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Range": "items=0-99",
    }
    
    resp = session.get(url, headers=headers, timeout=30)
    comprobantes = resp.json()
    
    print(f"   Encontrados: {len(comprobantes)}")
    
    if comprobantes:
        print("\n📄 Estructura completa del primer comprobante:")
        print(json.dumps(comprobantes[0], indent=2, ensure_ascii=False))
        
        print("\n🔑 Todas las claves disponibles:")
        for key in sorted(comprobantes[0].keys()):
            value = comprobantes[0][key]
            print(f"   {key}: {value}")
        
        # Buscar el número 69065819 de la URL original
        print("\n🔍 Buscando el valor 69065819 (de la URL original):")
        for key, value in comprobantes[0].items():
            if str(value) == "69065819" or value == 69065819:
                print(f"   ✅ Encontrado en campo: {key}")
    
    # También verificar quincena 10 para comparar
    print("\n" + "=" * 70)
    print("📋 Obteniendo comprobantes de 2025/Q10 para comparar...")
    
    url10 = f"{BASE_URL}/mvc/comprobantes/pago/?rfc={RFC_TEST}&anio=2025&quincena=10"
    resp10 = session.get(url10, headers=headers, timeout=30)
    comprobantes10 = resp10.json()
    
    if comprobantes10:
        print("\n📄 Estructura del comprobante Q10:")
        print(json.dumps(comprobantes10[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
