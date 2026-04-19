#!/usr/bin/env python3
"""
Prueba aislada: login + GET al endpoint de reporte anual del portal SEMS.
Reporta status, content-type, content-disposition, tamaño, y preview.
"""

import requests
import sys
import time

RFC = "PEOO820203MB1"
PASSWORD = "atlante3"

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
REPORTE_ANUAL_ENDPOINT = f"{BASE_URL}/mvc/jasper/repReporteAnualIng"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def banner(msg: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {msg}")
    print("=" * 70)


def login() -> requests.Session:
    banner("Login al portal SEMS")
    session = requests.Session()
    session.headers.update(HEADERS)

    resp_get = session.get(LOGIN_PAGE, timeout=30)
    print(f"GET login.jsp → {resp_get.status_code}")

    resp_post = session.post(
        AUTH_ENDPOINT,
        data={"j_username": RFC, "j_password": PASSWORD},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE,
            "Origin": BASE_URL,
        },
        allow_redirects=True,
        timeout=30,
    )
    print(f"POST auth → {resp_post.status_code}, URL final: {resp_post.url}")
    if "login.jsp" in resp_post.url:
        print("❌ Login fallido (terminó en login.jsp)")
        sys.exit(1)

    print("✅ Login exitoso")
    print(f"   Cookies: {list(session.cookies.keys())}")
    return session


def probar_reporte_anual(session: requests.Session, anio: int) -> None:
    banner(f"GET reporte anual — anio={anio}")

    token = int(time.time() * 1000)
    params = {"token": str(token), "anio": str(anio), "username": RFC}
    print(f"URL: {REPORTE_ANUAL_ENDPOINT}")
    print(f"Params: {params}")

    resp = session.get(
        REPORTE_ANUAL_ENDPOINT,
        params=params,
        headers={"Referer": f"{BASE_URL}/"},
        allow_redirects=True,
        timeout=60,
    )

    print(f"\n📥 Respuesta:")
    print(f"   Status: {resp.status_code}")
    print(f"   URL final: {resp.url}")
    print(f"   History: {[(r.status_code, r.url) for r in resp.history]}")
    print(f"\n📋 Headers de respuesta relevantes:")
    for h in ("Content-Type", "Content-Disposition", "Content-Length", "Content-Encoding", "Location", "Set-Cookie"):
        v = resp.headers.get(h)
        if v:
            print(f"   {h}: {v}")

    ct = resp.headers.get("Content-Type", "").lower()
    size = len(resp.content)
    print(f"\n📦 Content recibido: {size} bytes, content-type={ct!r}")

    if size == 0:
        print("   ⚠️ Body vacío")
        return

    header_bytes = resp.content[:8]
    print(f"   Magic bytes (hex): {header_bytes.hex()}")
    print(f"   Magic bytes (ascii, prefix): {resp.content[:20]!r}")

    if resp.content.startswith(b"%PDF"):
        print("   ✅ Es un PDF (magic bytes %PDF)")
    elif resp.content[:4] == b"PK\x03\x04":
        print("   📄 Es un archivo ZIP (probablemente DOCX/XLSX moderno)")
    elif resp.content[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
        print("   📄 Es un archivo OLE2 (Word .doc / Excel .xls clásico)")
    elif "html" in ct or resp.content[:200].lower().find(b"<!doctype") != -1 or resp.content[:200].lower().find(b"<html") != -1:
        print("   🟡 Es HTML — preview:")
        try:
            preview = resp.content[:2000].decode("utf-8", errors="replace")
        except Exception:
            preview = str(resp.content[:2000])
        print("   " + "-" * 60)
        for line in preview.splitlines()[:40]:
            print(f"   {line}")
        print("   " + "-" * 60)
    else:
        print("   ❓ Formato desconocido — preview bytes:")
        print(f"   {resp.content[:200]!r}")


def main():
    session = login()
    # Probar varios años
    for anio in (2024, 2023, 2025):
        probar_reporte_anual(session, anio)


if __name__ == "__main__":
    main()
