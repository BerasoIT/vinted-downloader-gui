#!/bin/bash

# Script di build locale per Vinted Downloader GUI
# Usage: ./build_local.sh

echo "🚀 Building Vinted Downloader GUI v0.1.0..."

# Pulizia directory precedenti
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec

# Build con PyInstaller includendo la cartella src
echo "📦 Building executable..."
python -m PyInstaller \
    --onefile \
    --windowed \
    --name=VintedDownloaderGUI-linux \
    --add-data "src:src" \
    --hidden-import=tkinter \
    --hidden-import=tkinter.ttk \
    --hidden-import=tkinter.filedialog \
    --hidden-import=tkinter.messagebox \
    --hidden-import=tkinter.scrolledtext \
    --hidden-import=queue \
    --hidden-import=json \
    --hidden-import=threading \
    --hidden-import=subprocess \
    --hidden-import=re \
    --hidden-import=datetime \
    --hidden-import=pathlib \
    vinted_gui.py

if [ $? -eq 0 ]; then
    echo "✅ Build completato con successo!"
    echo "📁 Eseguibile disponibile in: ./dist/VintedDownloaderGUI-linux"
    echo ""
    echo "🔧 Per testare:"
    echo "   ./dist/VintedDownloaderGUI-linux"
else
    echo "❌ Build fallito!"
    exit 1
fi
