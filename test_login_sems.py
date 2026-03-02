#!/usr/bin/env python3
"""
Script de prueba de autenticación contra el portal SEMS.

Portal: https://portalautoservicios-sems.sep.gob.mx/
Método: Spring Security (formulario tradicional POST)

Autor: Agente de pruebas
Fecha: 2024
"""

import requests
from datetime import datetime


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
INTERNAL_PAGE = f"{BASE_URL}/"


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


def print_cookies(cookies: requests.cookies.RequestsCookieJar, label: str):
    """Imprime las cookies de forma legible."""
    print(f"\n📋 {label}:")
    if not cookies:
        print("   (Sin cookies)")
    for cookie in cookies:
        print(f"   - {cookie.name}: {cookie.value[:50]}..." if len(cookie.value) > 50 else f"   - {cookie.name}: {cookie.value}")


def test_sems_login():
    """
    Ejecuta la prueba completa de autenticación al portal SEMS.
    
    Pasos:
    1. Crear sesión con headers realistas
    2. GET inicial a login.jsp para obtener cookies
    3. POST al endpoint de autenticación
    4. Validar redirección y cookies
    5. Probar acceso a página interna
    """
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "initial_cookies": None,
        "final_cookies": None,
        "final_url": None,
        "login_success": False,
        "internal_access": False,
        "errors": []
    }
    
    print_separator("🚀 INICIANDO PRUEBA DE AUTENTICACIÓN - PORTAL SEMS")
    print(f"⏰ Timestamp: {results['timestamp']}")
    print(f"🔗 URL Base: {BASE_URL}")
    print(f"👤 Usuario: {RFC_TEST[:4]}****" if len(RFC_TEST) > 4 else f"👤 Usuario: {RFC_TEST}")
    
    # =========================================================
    # PASO 1: Crear sesión
    # =========================================================
    print_separator("PASO 1: Creando sesión")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    print("✅ Sesión creada con headers realistas")
    print(f"   User-Agent: {HEADERS['User-Agent'][:50]}...")
    
    # =========================================================
    # PASO 2: GET inicial a login.jsp
    # =========================================================
    print_separator("PASO 2: GET inicial a login.jsp")
    
    try:
        resp_get = session.get(LOGIN_PAGE, timeout=30)
        print(f"✅ GET exitoso")
        print(f"   Status Code: {resp_get.status_code}")
        print(f"   URL: {resp_get.url}")
        
        # Guardar cookies iniciales
        results["initial_cookies"] = dict(session.cookies)
        print_cookies(session.cookies, "Cookies iniciales")
        
        # Verificar que la página de login cargó correctamente
        if "login" in resp_get.text.lower() or "j_username" in resp_get.text:
            print("✅ Formulario de login detectado en la respuesta")
        else:
            print("⚠️ No se detectó formulario de login en la respuesta")
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Error en GET inicial: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results
    
    # =========================================================
    # PASO 3: POST al endpoint de autenticación
    # =========================================================
    print_separator("PASO 3: POST de autenticación")
    
    # Datos del formulario
    login_data = {
        "j_username": RFC_TEST,
        "j_password": PASSWORD_TEST
    }
    
    # Headers adicionales para el POST
    post_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": LOGIN_PAGE,
        "Origin": BASE_URL,
    }
    
    print(f"📤 Enviando POST a: {AUTH_ENDPOINT}")
    print(f"   Campos: j_username, j_password")
    print(f"   Content-Type: application/x-www-form-urlencoded")
    
    try:
        resp_post = session.post(
            AUTH_ENDPOINT,
            data=login_data,
            headers=post_headers,
            allow_redirects=True,
            timeout=30
        )
        
        print(f"\n📥 Respuesta recibida:")
        print(f"   Status Code: {resp_post.status_code}")
        print(f"   URL Final: {resp_post.url}")
        print(f"   History (redirecciones): {len(resp_post.history)} redirección(es)")
        
        for i, r in enumerate(resp_post.history):
            print(f"      [{i+1}] {r.status_code} -> {r.url}")
        
        results["final_url"] = resp_post.url
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error en POST de login: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results
    
    # =========================================================
    # PASO 4: Validar autenticación
    # =========================================================
    print_separator("PASO 4: Validación de autenticación")
    
    # Guardar cookies finales
    results["final_cookies"] = dict(session.cookies)
    print_cookies(session.cookies, "Cookies finales")
    
    # Comparar JSESSIONID
    initial_jsessionid = results["initial_cookies"].get("JSESSIONID", "")
    final_jsessionid = results["final_cookies"].get("JSESSIONID", "")
    
    print(f"\n🔑 Análisis de JSESSIONID:")
    print(f"   Inicial: {initial_jsessionid[:20]}..." if len(initial_jsessionid) > 20 else f"   Inicial: {initial_jsessionid}")
    print(f"   Final:   {final_jsessionid[:20]}..." if len(final_jsessionid) > 20 else f"   Final:   {final_jsessionid}")
    
    if initial_jsessionid != final_jsessionid:
        print("   ✅ JSESSIONID cambió (indica nuevo contexto de sesión)")
    else:
        print("   ⚠️ JSESSIONID no cambió")
    
    # Verificar URL final
    print(f"\n🔗 Verificación de URL final:")
    if "login.jsp" in resp_post.url.lower():
        print(f"   ❌ La URL final contiene 'login.jsp' - Autenticación fallida")
        print(f"   URL: {resp_post.url}")
        results["login_success"] = False
        
        # Buscar mensaje de error en la página
        if "error" in resp_post.text.lower() or "invalid" in resp_post.text.lower():
            print("   ⚠️ Se detectó posible mensaje de error en la respuesta")
    else:
        print(f"   ✅ La URL final NO es login.jsp - Posible éxito")
        print(f"   URL: {resp_post.url}")
        results["login_success"] = True
    
    # =========================================================
    # PASO 5: Probar acceso a página interna
    # =========================================================
    print_separator("PASO 5: Acceso a página interna")
    
    try:
        resp_internal = session.get(INTERNAL_PAGE, timeout=30)
        print(f"📄 GET a página interna: {INTERNAL_PAGE}")
        print(f"   Status Code: {resp_internal.status_code}")
        print(f"   URL Final: {resp_internal.url}")
        
        # Mostrar primeros 300 caracteres
        content_preview = resp_internal.text[:300].replace("\n", " ").strip()
        print(f"\n📝 Preview del contenido (primeros 300 chars):")
        print(f"   {content_preview}...")
        
        # Verificar si es contenido de sesión activa o login
        if "login.jsp" in resp_internal.url or "j_username" in resp_internal.text:
            print("\n   ❌ Redirigido a login - No hay sesión activa")
            results["internal_access"] = False
        else:
            print("\n   ✅ Acceso a página interna exitoso")
            results["internal_access"] = True
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Error accediendo página interna: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
    
    # =========================================================
    # RESUMEN FINAL
    # =========================================================
    print_separator("📊 RESUMEN DE LA PRUEBA")
    
    print(f"⏰ Timestamp: {results['timestamp']}")
    print(f"🔗 URL Final: {results['final_url']}")
    print(f"🔐 Login exitoso: {'✅ SÍ' if results['login_success'] else '❌ NO'}")
    print(f"📄 Acceso interno: {'✅ SÍ' if results['internal_access'] else '❌ NO'}")
    print(f"❗ Errores: {len(results['errors'])}")
    
    if results["errors"]:
        print("\nDetalles de errores:")
        for err in results["errors"]:
            print(f"   - {err}")
    
    # Conclusión
    print_separator("🎯 CONCLUSIÓN")
    
    if results["login_success"] and results["internal_access"]:
        print("✅ AUTENTICACIÓN EXITOSA")
        print("   El flujo de login funciona correctamente.")
    elif results["login_success"]:
        print("⚠️ AUTENTICACIÓN PARCIAL")
        print("   El login parece exitoso pero hay problemas con acceso interno.")
    else:
        print("❌ AUTENTICACIÓN FALLIDA")
        print("   Posibles causas:")
        print("   - Credenciales incorrectas")
        print("   - El portal requiere campos adicionales (CSRF token, captcha)")
        print("   - Cambios en el flujo de autenticación")
        print("   - Bloqueo por IP o rate limiting")
    
    print("\n" + "=" * 60)
    
    return results


if __name__ == "__main__":
    print("\n" * 2)
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     SCRIPT DE PRUEBA - AUTENTICACIÓN PORTAL SEMS           ║")
    print("║     Portal de Autoservicios SEMS - SEP                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Ejecutar prueba
    results = test_sems_login()
    
    print("\n📁 Script finalizado.")
    print("   Revisa el archivo agent.md para documentación completa.")
