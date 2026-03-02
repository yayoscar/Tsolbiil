#!/usr/bin/env python3
"""
Script para descargar todos los comprobantes de 2024 (Q01-Q24) y extraer sus datos.

Proceso completo:
1. Login al portal SEMS
2. Consultar comprobantes de cada quincena
3. Descargar PDFs
4. Extraer datos con pdfplumber
5. Generar JSON consolidado

Autor: Agente de pruebas
Fecha: 2025-12-04
"""

import requests
import pdfplumber
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any


# =====================================================
# CONFIGURACIÓN
# =====================================================

RFC_TEST = "PEOO820203MB1"
PASSWORD_TEST = "atlante3"

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
COMPROBANTES_URL = f"{BASE_URL}/mvc/comprobantes/pago/"
DESCARGA_URL = f"{BASE_URL}/mvc/jasper/repReciboPago"

OUTPUT_DIR = "/media/Files/Repos/Tsolbiil/descargas/2024"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# =====================================================
# FUNCIONES
# =====================================================

def print_separator(title: str = ""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


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


def obtener_comprobantes_quincena(session: requests.Session, rfc: str, anio: int, quincena: int) -> List[Dict]:
    """Obtiene la lista de comprobantes para una quincena."""
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Range": "items=0-99",
    }
    url = f"{COMPROBANTES_URL}?rfc={rfc}&anio={anio}&quincena={quincena}"
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def descargar_pdf(session: requests.Session, id_comprobante: int, anio: int, quincena: int, 
                  cons_qna_proc: int, output_dir: str) -> str:
    """Descarga el PDF de un comprobante y retorna la ruta del archivo."""
    timestamp = int(time.time() * 1000)
    qna_proc = f"{anio}{quincena:02d}"
    
    url = f"{DESCARGA_URL}/{timestamp}"
    params = {
        "consQnaProc": cons_qna_proc,
        "qnaProc": qna_proc,
        "nuComprobante": id_comprobante,
    }
    
    resp = session.get(url, params=params, timeout=60)
    
    if resp.status_code != 200 or not resp.content.startswith(b'%PDF'):
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    filename = f"comprobante_{anio}_Q{quincena:02d}_{id_comprobante}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(resp.content)
    
    return filepath


def extraer_datos_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extrae percepciones y deducciones del PDF."""
    resultado = {
        "percepciones": [],
        "deducciones": [],
        "totales": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            tablas = page.extract_tables()
            
            for tabla in tablas:
                for fila in tabla:
                    if not fila:
                        continue
                    
                    fila_str = [str(c) if c else "" for c in fila]
                    
                    # Buscar fila con datos multilínea
                    for celda in fila_str:
                        if "\n" in celda and any(c.isdigit() for c in celda):
                            if len(fila_str) >= 13:
                                # Percepciones
                                codigos_perc = fila_str[0].split("\n") if fila_str[0] else []
                                denoms_perc = fila_str[1].split("\n") if fila_str[1] else []
                                importes_perc = fila_str[5].split("\n") if fila_str[5] else []
                                
                                # Deducciones
                                codigos_ded = fila_str[6].split("\n") if fila_str[6] else []
                                denoms_ded = fila_str[7].split("\n") if fila_str[7] else []
                                importes_ded = fila_str[12].split("\n") if fila_str[12] else []
                                
                                for i in range(len(codigos_perc)):
                                    codigo = codigos_perc[i].strip() if i < len(codigos_perc) else ""
                                    denom = denoms_perc[i].strip() if i < len(denoms_perc) else ""
                                    importe_str = importes_perc[i].strip() if i < len(importes_perc) else "0"
                                    
                                    if codigo and importe_str:
                                        try:
                                            importe = float(importe_str.replace(",", "").replace("$", ""))
                                            resultado["percepciones"].append({
                                                "codigo": codigo,
                                                "denominacion": denom,
                                                "importe": importe
                                            })
                                        except ValueError:
                                            pass
                                
                                for i in range(len(codigos_ded)):
                                    codigo = codigos_ded[i].strip() if i < len(codigos_ded) else ""
                                    denom = denoms_ded[i].strip() if i < len(denoms_ded) else ""
                                    importe_str = importes_ded[i].strip() if i < len(importes_ded) else "0"
                                    
                                    if codigo and importe_str:
                                        try:
                                            importe = float(importe_str.replace(",", "").replace("$", ""))
                                            resultado["deducciones"].append({
                                                "codigo": codigo,
                                                "denominacion": denom,
                                                "importe": importe
                                            })
                                        except ValueError:
                                            pass
                            break
        
        resultado["totales"]["total_percepciones"] = sum(p["importe"] for p in resultado["percepciones"])
        resultado["totales"]["total_deducciones"] = sum(d["importe"] for d in resultado["deducciones"])
        resultado["totales"]["neto"] = resultado["totales"]["total_percepciones"] - resultado["totales"]["total_deducciones"]
        
    except Exception as e:
        resultado["error"] = str(e)
    
    return resultado


def main():
    print("\n" * 2)
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║   DESCARGA Y EXTRACCIÓN DE COMPROBANTES 2024 (Q01-Q24)               ║")
    print("║   Portal de Autoservicios SEMS - SEP                                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    inicio_total = datetime.now()
    print(f"\n⏰ Inicio: {inicio_total.isoformat()}")
    print(f"📁 Directorio de salida: {OUTPUT_DIR}")
    
    # Resultado consolidado
    resultado_anual = {
        "anio": 2024,
        "rfc": RFC_TEST,
        "timestamp_proceso": inicio_total.isoformat(),
        "quincenas": [],
        "resumen": {
            "total_quincenas_con_comprobantes": 0,
            "total_comprobantes": 0,
            "total_percepciones_anual": 0.0,
            "total_deducciones_anual": 0.0,
            "total_neto_anual": 0.0,
        }
    }
    
    # Login
    print_separator("🔐 INICIANDO SESIÓN")
    try:
        session = crear_sesion_portal(RFC_TEST, PASSWORD_TEST)
        print("✅ Sesión creada exitosamente")
    except Exception as e:
        print(f"❌ Error de login: {e}")
        return
    
    # Procesar cada quincena
    for quincena in range(1, 25):
        print_separator(f"📅 QUINCENA 2024/{quincena:02d}")
        
        quincena_data = {
            "quincena": quincena,
            "comprobantes": []
        }
        
        # Obtener comprobantes
        try:
            comprobantes = obtener_comprobantes_quincena(session, RFC_TEST, 2024, quincena)
            print(f"   📋 Comprobantes encontrados: {len(comprobantes)}")
        except Exception as e:
            print(f"   ❌ Error consultando: {e}")
            resultado_anual["quincenas"].append(quincena_data)
            continue
        
        if not comprobantes:
            print(f"   ⚠️ Sin comprobantes")
            resultado_anual["quincenas"].append(quincena_data)
            continue
        
        resultado_anual["resumen"]["total_quincenas_con_comprobantes"] += 1
        
        # Procesar cada comprobante
        for idx, comp in enumerate(comprobantes):
            resultado_anual["resumen"]["total_comprobantes"] += 1
            
            id_comp = comp.get("idComprobante")
            num_comp = comp.get("numComprobante")
            neto_api = comp.get("totNetoCheque", 0)
            cons_qna = comp.get("consQnaProc", 0)
            
            print(f"\n   [{idx+1}] ID: {id_comp} | Neto: ${neto_api:,.2f}")
            
            # Descargar PDF
            pdf_path = descargar_pdf(session, id_comp, 2024, quincena, cons_qna, OUTPUT_DIR)
            
            if not pdf_path:
                print(f"       ❌ Error descargando PDF")
                quincena_data["comprobantes"].append({
                    "id_comprobante": id_comp,
                    "num_comprobante": num_comp,
                    "neto_api": neto_api,
                    "error": "Descarga fallida"
                })
                continue
            
            print(f"       ✅ PDF descargado")
            
            # Extraer datos
            datos_pdf = extraer_datos_pdf(pdf_path)
            
            comprobante_data = {
                "id_comprobante": id_comp,
                "num_comprobante": num_comp,
                "pdf_path": pdf_path,
                "percepciones": datos_pdf["percepciones"],
                "deducciones": datos_pdf["deducciones"],
                "totales": datos_pdf["totales"]
            }
            
            quincena_data["comprobantes"].append(comprobante_data)
            
            # Acumular totales anuales
            resultado_anual["resumen"]["total_percepciones_anual"] += datos_pdf["totales"].get("total_percepciones", 0)
            resultado_anual["resumen"]["total_deducciones_anual"] += datos_pdf["totales"].get("total_deducciones", 0)
            resultado_anual["resumen"]["total_neto_anual"] += datos_pdf["totales"].get("neto", 0)
            
            print(f"       📊 Percepciones: {len(datos_pdf['percepciones'])} | Deducciones: {len(datos_pdf['deducciones'])}")
            print(f"       💰 Neto: ${datos_pdf['totales'].get('neto', 0):,.2f}")
            
            # Pequeña pausa
            time.sleep(0.3)
        
        resultado_anual["quincenas"].append(quincena_data)
    
    # Guardar JSON consolidado
    print_separator("💾 GUARDANDO RESULTADOS")
    
    json_path = os.path.join(OUTPUT_DIR, "comprobantes_2024_completo.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(resultado_anual, f, ensure_ascii=False, indent=2)
    
    print(f"   Archivo: {json_path}")
    
    # Resumen final
    fin_total = datetime.now()
    duracion = (fin_total - inicio_total).total_seconds()
    
    print_separator("📊 RESUMEN FINAL - AÑO 2024")
    
    print(f"\n⏱️ Tiempo total: {duracion:.1f} segundos ({duracion/60:.1f} minutos)")
    print(f"\n📅 Quincenas con comprobantes: {resultado_anual['resumen']['total_quincenas_con_comprobantes']} de 24")
    print(f"📄 Total comprobantes: {resultado_anual['resumen']['total_comprobantes']}")
    print(f"\n💰 TOTALES ANUALES:")
    print(f"   Percepciones: ${resultado_anual['resumen']['total_percepciones_anual']:>12,.2f}")
    print(f"   Deducciones:  ${resultado_anual['resumen']['total_deducciones_anual']:>12,.2f}")
    print(f"   Neto:         ${resultado_anual['resumen']['total_neto_anual']:>12,.2f}")
    
    print(f"\n📁 Archivos guardados en: {OUTPUT_DIR}")
    
    # Listar PDFs
    if os.path.exists(OUTPUT_DIR):
        pdfs = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
        print(f"   PDFs descargados: {len(pdfs)}")


if __name__ == "__main__":
    main()
