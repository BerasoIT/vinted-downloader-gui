#!/usr/bin/env python3
"""
Build script per creare eseguibili con PyInstaller
"""

import os
import sys
import shutil
from pathlib import Path

def build_executable():
    """Crea l'eseguibile con PyInstaller"""
    
    # Path del progetto
    project_root = Path(__file__).parent
    main_script = project_root / "src" / "gui" / "vinted_downloader_gui.py"
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",                    # Un singolo file eseguibile
        "--windowed",                   # Nasconde la console su Windows
        "--name=VintedDownloaderGUI",   # Nome dell'eseguibile
        f"--icon={project_root}/docs/icon.ico" if (project_root / "docs" / "icon.ico").exists() else "",
        "--add-data", f"{project_root}/src:src",  # Include la cartella src
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        str(main_script)
    ]
    
    # Rimuovi parametri vuoti
    cmd = [arg for arg in cmd if arg]
    
    print("Comando PyInstaller:")
    print(" ".join(cmd))
    
    # Esegui PyInstaller
    os.system(" ".join(cmd))
    
    print("\n✅ Build completato!")
    print(f"📁 Eseguibile creato in: {project_root}/dist/")

if __name__ == "__main__":
    build_executable()
