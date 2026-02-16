#!/usr/bin/env python3
"""
Script para descargar comprobantes de pago del portal SEMS.

Características:
- Lee configuración desde config.json (RFC, contraseña, año y quincena de inicio)
- Organiza descargas en carpetas por año
- Genera un único JSON con todos los conceptos extraídos
- Genera archivo XLSX con las columnas: comprobante, año, quincena, concepto, monto

Autor: Sistema automatizado
Fecha: 2026-01-16
"""

import requests
import pdfplumber
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


# =====================================================
# CONFIGURACIÓN BASE
# =====================================================

BASE_URL = "https://portalautoservicios-sems.sep.gob.mx"
LOGIN_PAGE = f"{BASE_URL}/login.jsp"
AUTH_ENDPOINT = f"{BASE_URL}/j_spring_security_check"
COMPROBANTES_URL = f"{BASE_URL}/mvc/comprobantes/pago/"
DESCARGA_URL = f"{BASE_URL}/mvc/jasper/repReciboPago"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# =====================================================
# FUNCIONES DE CONFIGURACIÓN
# =====================================================

def calcular_quincena_actual() -> int:
    """Calcula la quincena actual basándose en la fecha."""
    hoy = datetime.now()
    mes = hoy.month
    dia = hoy.day
    
    # Cada mes tiene 2 quincenas
    # Si el día es 1-15: primera quincena del mes
    # Si el día es 16-31: segunda quincena del mes
    quincena = (mes - 1) * 2 + (1 if dia <= 15 else 2)
    return quincena


def cargar_configuracion(config_path: str = "config.json") -> Dict[str, Any]:
    """Carga la configuración desde el archivo JSON."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validar campos requeridos
    campos_requeridos = ["rfc", "password", "anio_inicio", "quincena_inicio"]
    for campo in campos_requeridos:
        if campo not in config:
            raise ValueError(f"Campo requerido faltante en config.json: {campo}")
    
    # Si no está definido anio_final o es null, usar anio_inicio
    if "anio_final" not in config or config["anio_final"] is None:
        config["anio_final"] = config["anio_inicio"]
    
    # Validar que anio_final >= anio_inicio
    if config["anio_final"] < config["anio_inicio"]:
        raise ValueError(f"anio_final ({config['anio_final']}) no puede ser menor que anio_inicio ({config['anio_inicio']})")
    
    # Si no está definida quincena_final o es null, usar la quincena actual
    if "quincena_final" not in config or config["quincena_final"] is None:
        config["quincena_final"] = calcular_quincena_actual()
    
    # Validar que quincena_final no exceda 24
    if config["quincena_final"] > 24:
        config["quincena_final"] = 24
    
    # Validar que quincena_final >= quincena_inicio (solo para el mismo año)
    if config["anio_inicio"] == config["anio_final"] and config["quincena_final"] < config["quincena_inicio"]:
        raise ValueError(f"quincena_final ({config['quincena_final']}) no puede ser menor que quincena_inicio ({config['quincena_inicio']}) para el mismo año")
    
    return config


# =====================================================
# FUNCIONES DE PORTAL
# =====================================================

def print_separator(title: str = ""):
    """Imprime un separador visual."""
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
        raise Exception("Login fallido - Verifique RFC y contraseña")
    
    return session


def obtener_comprobantes_quincena(session: requests.Session, rfc: str, anio: int, quincena: int) -> List[Dict]:
    """Obtiene la lista de comprobantes para una quincena."""
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Range": "items=0-99",
    }
    # Formatear quincena con dos dígitos (01, 02, etc.)
    url = f"{COMPROBANTES_URL}?rfc={rfc}&anio={anio}&quincena={quincena:02d}"
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def descargar_pdf(session: requests.Session, id_comprobante: int, anio: int, quincena: int, 
                  cons_qna_proc: int, output_dir: str) -> str:
    """Descarga el PDF de un comprobante y retorna la ruta del archivo."""
    timestamp = int(time.time() * 1000)
    # Usar formato con padding de ceros para el parámetro qnaProc
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


# =====================================================
# FUNCIONES DE EXTRACCIÓN
# =====================================================

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


# =====================================================
# FUNCIONES DE EXPORTACIÓN
# =====================================================

def generar_excel(datos: Dict[str, Any], output_path: str):
    """Genera un archivo XLSX con los datos de todos los comprobantes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comprobantes"
    
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    center_alignment = Alignment(horizontal="center", vertical="center")
    
    # Encabezados
    headers = ["Comprobante", "Año", "Quincena", "Tipo", "Concepto", "Monto"]
    ws.append(headers)
    
    # Aplicar estilo a encabezados
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment
    
    # Datos
    for quincena_data in datos.get("quincenas", []):
        anio = datos.get("anio")
        quincena = quincena_data.get("quincena")
        
        for comp in quincena_data.get("comprobantes", []):
            num_comp = comp.get("num_comprobante", comp.get("id_comprobante", ""))
            
            # Percepciones
            for perc in comp.get("percepciones", []):
                concepto = f"{perc['codigo']} - {perc['denominacion']}"
                monto = perc['importe']
                ws.append([num_comp, anio, quincena, "Percepción", concepto, monto])
            
            # Deducciones
            for ded in comp.get("deducciones", []):
                concepto = f"{ded['codigo']} - {ded['denominacion']}"
                monto = ded['importe']
                ws.append([num_comp, anio, quincena, "Deducción", concepto, monto])
    
    # Ajustar anchos de columna
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 8
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 50
    ws.column_dimensions['F'].width = 15
    
    # Formato de números
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=6, max_col=6):
        for cell in row:
            cell.number_format = '#,##0.00'
    
    wb.save(output_path)


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def main():
    print("\n" * 2)
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║   DESCARGA Y EXTRACCIÓN DE COMPROBANTES DE PAGO SEMS                 ║")
    print("║   Portal de Autoservicios SEMS - SEP                                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    inicio_total = datetime.now()
    print(f"\n⏰ Inicio: {inicio_total.isoformat()}")
    
    # Cargar configuración
    print_separator("📋 CARGANDO CONFIGURACIÓN")
    try:
        config = cargar_configuracion("config.json")
        print(f"   RFC: {config['rfc']}")
        print(f"   Año de inicio: {config['anio_inicio']}")
        print(f"   Año final: {config['anio_final']}")
        print(f"   Quincena de inicio: {config['quincena_inicio']}")
        print(f"   Quincena final: {config['quincena_final']}")
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return
    
    # Login
    print_separator("🔐 INICIANDO SESIÓN")
    try:
        session = crear_sesion_portal(config["rfc"], config["password"])
        print("✅ Sesión creada exitosamente")
    except Exception as e:
        print(f"❌ Error de login: {e}")
        return
    
    # Procesar cada año
    for anio in range(config["anio_inicio"], config["anio_final"] + 1):
        print_separator(f"📆 PROCESANDO AÑO {anio}")
        
        # Crear directorio de salida organizado por año
        output_dir = f"descargas/{anio}"
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 Directorio de salida: {output_dir}")
        
        # Resultado consolidado
        resultado_anual = {
            "anio": anio,
            "rfc": config["rfc"],
            "timestamp_proceso": datetime.now().isoformat(),
            "quincenas": [],
            "resumen": {
                "total_quincenas_con_comprobantes": 0,
                "total_comprobantes": 0,
                "total_percepciones_anual": 0.0,
                "total_deducciones_anual": 0.0,
                "total_neto_anual": 0.0,
            }
        }
        
        # Determinar rango de quincenas para este año
        # Si es el primer año, usar quincena_inicio; si no, desde la 1
        inicio_q = config["quincena_inicio"] if anio == config["anio_inicio"] else 1
        # Si es el último año, usar quincena_final; si no, hasta la 24
        fin_q = config["quincena_final"] if anio == config["anio_final"] else 24
        
        # Procesar quincenas
        for quincena in range(inicio_q, fin_q + 1):
            print_separator(f"📅 QUINCENA {anio}/{quincena:02d}")
            
            quincena_data = {
                "quincena": quincena,
                "comprobantes": []
            }
            
            # Obtener comprobantes
            try:
                comprobantes = obtener_comprobantes_quincena(
                    session, config["rfc"], anio, quincena
                )
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
                pdf_path = descargar_pdf(
                    session, id_comp, anio, quincena, cons_qna, output_dir
                )
                
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
        
        # Guardar JSON consolidado del año
        print_separator(f"💾 GUARDANDO RESULTADOS DEL AÑO {anio}")
        
        json_path = os.path.join(output_dir, f"comprobantes_{anio}_completo.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(resultado_anual, f, ensure_ascii=False, indent=2)
        
        print(f"   📄 JSON: {json_path}")
        
        # Generar Excel
        excel_path = os.path.join(output_dir, f"comprobantes_{anio}_completo.xlsx")
        try:
            generar_excel(resultado_anual, excel_path)
            print(f"   📊 Excel: {excel_path}")
        except Exception as e:
            print(f"   ❌ Error generando Excel: {e}")
        
        # Resumen del año
        print_separator(f"📊 RESUMEN AÑO {anio}")
        
        print(f"\n📅 Quincenas con comprobantes: {resultado_anual['resumen']['total_quincenas_con_comprobantes']}")
        print(f"📄 Total comprobantes: {resultado_anual['resumen']['total_comprobantes']}")
        print(f"\n💰 TOTALES DEL AÑO:")
        print(f"   Percepciones: ${resultado_anual['resumen']['total_percepciones_anual']:>12,.2f}")
        print(f"   Deducciones:  ${resultado_anual['resumen']['total_deducciones_anual']:>12,.2f}")
        print(f"   Neto:         ${resultado_anual['resumen']['total_neto_anual']:>12,.2f}")
        
        print(f"\n📁 Archivos guardados en: {output_dir}")
        
        # Listar PDFs
        if os.path.exists(output_dir):
            pdfs = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
            print(f"   PDFs descargados: {len(pdfs)}")
    
    # Resumen final de todo el proceso
    fin_total = datetime.now()
    duracion = (fin_total - inicio_total).total_seconds()
    
    print_separator("🎉 PROCESO COMPLETADO")
    print(f"\n⏱️ Tiempo total: {duracion:.1f} segundos ({duracion/60:.1f} minutos)")
    print(f"📆 Años procesados: {config['anio_inicio']} - {config['anio_final']}")
    print("\n✅ Todos los archivos han sido descargados y organizados por año")


if __name__ == "__main__":
    main()
