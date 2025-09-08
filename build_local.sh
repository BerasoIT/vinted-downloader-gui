#!/bin/bash

# Script di build locale per Vinted Downloader GUI
# Usage: ./build_local.sh

echo "🚀 Building Vinted Downloader GUI v0.1.0..."

# Pulizia directory precedenti
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec

# Build con PyInstaller
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
    src/gui/vinted_downloader_gui.py

if [ $? -eq 0 ]; then
    echo "✅ Build completato con successo!"
    echo "📁 Eseguibile disponibile in: ./dist/VintedDownloaderGUI-linux"
    echo ""
    echo "🔧 Per testare:"
    echo "   chmod +x ./dist/VintedDownloaderGUI-linux"
    echo "   ./dist/VintedDownloaderGUI-linux"
else
    echo "❌ Build fallito!"
    exit 1
fi
