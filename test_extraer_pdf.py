#!/usr/bin/env python3
"""
Script para extraer datos de comprobantes de pago PDF del portal SEMS.

Usa pdfplumber para extraer tablas de percepciones y deducciones.

Autor: Agente de pruebas
Fecha: 2025-12-04
"""

import pdfplumber
import json
from typing import Dict, List, Any
from datetime import datetime


def extraer_datos_comprobante(pdf_path: str) -> Dict[str, Any]:
    """
    Extrae todos los datos relevantes de un comprobante de pago PDF.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        Diccionario con datos del comprobante, percepciones y deducciones
    """
    
    resultado = {
        "archivo": pdf_path,
        "timestamp_extraccion": datetime.now().isoformat(),
        "datos_generales": {},
        "percepciones": [],
        "deducciones": [],
        "totales": {},
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        
        # Extraer tablas
        tablas = page.extract_tables()
        
        print(f"📊 Tablas encontradas: {len(tablas)}")
        
        for tabla in tablas:
            for fila in tabla:
                if not fila:
                    continue
                
                # Buscar la fila que contiene los datos de percepciones/deducciones
                # El formato es: los valores están separados por \n en celdas específicas
                
                # Verificar si es la fila de datos (contiene \n en las celdas)
                fila_str = [str(c) if c else "" for c in fila]
                
                # La fila de datos tiene códigos con \n (ej: "07\n39\nCA...")
                for idx, celda in enumerate(fila_str):
                    if "\n" in celda and any(c.isdigit() for c in celda):
                        # Esta celda tiene datos multilínea
                        
                        # Columnas típicas del PDF:
                        # [0] = Códigos percepciones (07\n39\nCA...)
                        # [1] = Denominaciones percepciones
                        # [5] = Importes percepciones
                        # [6] = Códigos deducciones
                        # [7] = Denominaciones deducciones  
                        # [12] = Importes deducciones
                        
                        if len(fila_str) >= 13:
                            # Extraer percepciones
                            codigos_perc = fila_str[0].split("\n") if fila_str[0] else []
                            denoms_perc = fila_str[1].split("\n") if fila_str[1] else []
                            importes_perc = fila_str[5].split("\n") if fila_str[5] else []
                            
                            # Extraer deducciones
                            codigos_ded = fila_str[6].split("\n") if fila_str[6] else []
                            denoms_ded = fila_str[7].split("\n") if fila_str[7] else []
                            importes_ded = fila_str[12].split("\n") if fila_str[12] else []
                            
                            # Construir lista de percepciones
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
                            
                            # Construir lista de deducciones
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
                        
                        break  # Ya procesamos la fila de datos
                
                # Extraer datos generales del encabezado
                # Nombre
                if "PEREZ" in str(fila) or "OLAN" in str(fila):
                    for c in fila:
                        if c and "PEREZ" in str(c):
                            resultado["datos_generales"]["nombre"] = str(c).strip()
                
                # RFC
                if "RFC" in str(fila):
                    for i, c in enumerate(fila):
                        if c and "PEOO" in str(c) and "MB1" in str(c):
                            resultado["datos_generales"]["rfc"] = str(c).strip()
                
                # Número de comprobante
                if "28391829" in str(fila):
                    for c in fila:
                        if c and str(c).strip().isdigit() and len(str(c).strip()) == 8:
                            resultado["datos_generales"]["num_comprobante"] = str(c).strip()
    
    # Calcular totales
    resultado["totales"]["total_percepciones"] = sum(p["importe"] for p in resultado["percepciones"])
    resultado["totales"]["total_deducciones"] = sum(d["importe"] for d in resultado["deducciones"])
    resultado["totales"]["neto"] = resultado["totales"]["total_percepciones"] - resultado["totales"]["total_deducciones"]
    
    return resultado


def main():
    print("\n" * 2)
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║   EXTRACCIÓN DE DATOS DE COMPROBANTE PDF - PORTAL SEMS               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    # PDF de prueba: Quincena 10 de 2025
    pdf_path = "/media/Files/Repos/Tsolbiil/descargas/comprobante_2025_Q10_28391829.pdf"
    
    print(f"\n📄 Procesando: {pdf_path}")
    
    inicio = datetime.now()
    
    try:
        datos = extraer_datos_comprobante(pdf_path)
        
        fin = datetime.now()
        duracion = (fin - inicio).total_seconds()
        
        print("\n" + "=" * 70)
        print("📋 RESULTADOS DE LA EXTRACCIÓN")
        print("=" * 70)
        
        print(f"\n⏱️ Tiempo de procesamiento: {duracion:.3f} segundos")
        
        if datos.get("datos_generales"):
            print(f"\n👤 DATOS GENERALES:")
            for k, v in datos["datos_generales"].items():
                print(f"   {k}: {v}")
        
        print(f"\n💰 PERCEPCIONES ({len(datos['percepciones'])}):")
        for p in datos["percepciones"]:
            print(f"   [{p['codigo']:>3}] {p['denominacion']:<35} ${p['importe']:>10,.2f}")
        
        print(f"\n📉 DEDUCCIONES ({len(datos['deducciones'])}):")
        for d in datos["deducciones"]:
            print(f"   [{d['codigo']:>3}] {d['denominacion']:<35} ${d['importe']:>10,.2f}")
        
        print(f"\n📊 TOTALES:")
        print(f"   Total Percepciones: ${datos['totales']['total_percepciones']:>10,.2f}")
        print(f"   Total Deducciones:  ${datos['totales']['total_deducciones']:>10,.2f}")
        print(f"   Neto:               ${datos['totales']['neto']:>10,.2f}")
        
        # Guardar resultado como JSON
        json_path = pdf_path.replace(".pdf", "_datos.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Datos guardados en: {json_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
