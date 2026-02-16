#!/usr/bin/env python3
"""
Script de verificación del entorno y configuración.

Verifica que:
- Python 3 está instalado
- Todas las dependencias están disponibles
- El archivo de configuración existe y es válido
- Puede conectarse al portal SEMS

Autor: Sistema automatizado
Fecha: 2026-01-16
"""

import sys
import os
import json


def verificar_python():
    """Verifica la versión de Python."""
    print("🐍 Verificando Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor} (se requiere 3.8+)")
        return False


def verificar_dependencias():
    """Verifica que todas las dependencias estén instaladas."""
    print("\n📦 Verificando dependencias...")
    dependencias = {
        "requests": "requests",
        "pdfplumber": "pdfplumber",
        "openpyxl": "openpyxl",
    }
    
    todas_ok = True
    for nombre, modulo in dependencias.items():
        try:
            __import__(modulo)
            print(f"   ✅ {nombre}")
        except ImportError:
            print(f"   ❌ {nombre} (no instalado)")
            todas_ok = False
    
    return todas_ok


def verificar_config():
    """Verifica que el archivo de configuración exista y sea válido."""
    print("\n⚙️  Verificando configuración...")
    
    if not os.path.exists("config.json"):
        print("   ❌ config.json no encontrado")
        print("   💡 Crea el archivo: cp config.json.ejemplo config.json")
        return False
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        campos_requeridos = ["rfc", "password", "anio_inicio", "quincena_inicio"]
        faltantes = []
        
        for campo in campos_requeridos:
            if campo not in config:
                faltantes.append(campo)
        
        if faltantes:
            print(f"   ❌ Campos faltantes: {', '.join(faltantes)}")
            return False
        
        # Verificar que no sean valores de ejemplo
        if "TU_RFC" in config["rfc"] or "TU_CONTRASEÑA" in config["password"]:
            print("   ⚠️  config.json contiene valores de ejemplo")
            print("   💡 Edita config.json con tus datos reales")
            return False
        
        print("   ✅ config.json válido")
        print(f"      RFC: {config['rfc']}")
        print(f"      Año: {config['anio_inicio']}")
        print(f"      Quincena inicio: {config['quincena_inicio']}")
        quincena_final = config.get('quincena_final')
        if quincena_final is None:
            print(f"      Quincena final: automática (quincena actual)")
        else:
            print(f"      Quincena final: {quincena_final}")
        return True
        
    except json.JSONDecodeError:
        print("   ❌ config.json tiene formato JSON inválido")
        return False
    except Exception as e:
        print(f"   ❌ Error leyendo config.json: {e}")
        return False


def verificar_conexion():
    """Verifica la conexión al portal SEMS."""
    print("\n🌐 Verificando conexión al portal SEMS...")
    
    try:
        import requests
        url = "https://portalautoservicios-sems.sep.gob.mx/login.jsp"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            print("   ✅ Portal SEMS accesible")
            return True
        else:
            print(f"   ⚠️  Portal respondió con código {resp.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ No se pudo conectar al portal (verifica tu conexión a internet)")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Timeout conectando al portal")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("  VERIFICACIÓN DEL SISTEMA DE DESCARGA DE COMPROBANTES SEMS")
    print("=" * 70 + "\n")
    
    resultados = []
    
    # Ejecutar verificaciones
    resultados.append(("Python", verificar_python()))
    resultados.append(("Dependencias", verificar_dependencias()))
    resultados.append(("Configuración", verificar_config()))
    resultados.append(("Conexión", verificar_conexion()))
    
    # Resumen
    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70 + "\n")
    
    todos_ok = all(resultado for _, resultado in resultados)
    
    for nombre, ok in resultados:
        estado = "✅" if ok else "❌"
        print(f"   {estado} {nombre}")
    
    print()
    
    if todos_ok:
        print("✅ Sistema listo para usar")
        print("\n💡 Ejecuta: ./iniciar.sh")
    else:
        print("❌ Hay problemas que resolver antes de continuar")
        print("\n💡 Revisa los errores anteriores y corrígelos")
    
    print()
    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
