#!/usr/bin/env python3
"""
Launcher principale per Vinted Downloader GUI
Avvia l'interfaccia grafica dalla nuova struttura organizzata
"""

import sys
import os
from pathlib import Path

# Aggiungi il path src al PYTHONPATH
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Importa e avvia la GUI
from gui.vinted_downloader_gui import main

if __name__ == "__main__":
    main()
