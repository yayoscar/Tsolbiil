#!/bin/bash
# Script de inicio rápido para descarga de comprobantes SEMS

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   SISTEMA DE DESCARGA DE COMPROBANTES SEMS                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "⚠️  No se encontró el entorno virtual."
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    
    echo "📥 Instalando dependencias..."
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Entorno configurado correctamente"
else
    echo "✅ Entorno virtual encontrado"
    source venv/bin/activate
fi

echo ""

# Verificar si existe config.json
if [ ! -f "config.json" ]; then
    echo "⚠️  No se encontró config.json"
    echo "📝 Por favor, crea el archivo config.json con tu configuración:"
    echo ""
    echo '{'
    echo '  "rfc": "TU_RFC_AQUI",'
    echo '  "password": "TU_CONTRASEÑA",'
    echo '  "anio_inicio": 2024,'
    echo '  "quincena_inicio": 1'
    echo '}'
    echo ""
    echo "Ejecuta: nano config.json"
    exit 1
fi

echo "🚀 Iniciando descarga de comprobantes..."
echo ""

# Ejecutar el script principal
python descarga_comprobantes.py

echo ""
echo "✅ Proceso completado"
echo "💡 Para desactivar el entorno virtual: deactivate"
