#!/usr/bin/env python3
"""
GUI per Vinted Downloader
Interfaccia grafica che wrappa il modulo vinted_downloader esistente
senza modificarne il codice core.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import sys
import os
from pathlib import Path
import queue
import re

# DEBUG: Modulo per debugging con VS Code
import logging
from log_manager import get_logger, enable_file_logging, is_debug_mode

# Usa il nuovo sistema di logging centralizzato
debug_enabled = is_debug_mode()
logger = get_logger(__name__)


class ToolTip:
    """Semplice tooltip per widget tkinter"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.tooltip = None

    def on_enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="lightyellow",
                        relief="solid", borderwidth=1, font=("Arial", 9))
        label.pack()

    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class VintedDownloaderGUI:
    """Interfaccia grafica per il downloader Vinted"""
    
    def __init__(self, root):
        # Inizializzazione GUI
        if debug_enabled:
            logger.debug("🔧 DEBUG: Inizializzazione GUI")
        
        self.root = root
        self.debug_enabled = debug_enabled  # Rende accessibile la modalità debug
        
        # Queue per comunicazione tra thread
        self.output_queue = queue.Queue()
        
        # Variabili tkinter
        self.url_var = tk.StringVar()
        self.seller_var = tk.BooleanVar()
        self.all_items_var = tk.BooleanVar()
        self.save_in_dir_var = tk.BooleanVar()
        self.skip_duplicates_var = tk.BooleanVar(value=True)  # Attivo di default
        self.file_logging_var = tk.BooleanVar()  # Controllo logging su file
        
        # Flag per controllare il processo
        self.process_running = False
        self.current_process = None
        
        # Monitoraggio clipboard automatico
        self.last_clipboard_content = ""
        self.clipboard_monitor_active = True
        
        # Variabili per configurazione avanzata
        self.auto_organize_enabled = tk.BooleanVar(value=True)
        self.auto_clipboard_enabled = tk.BooleanVar(value=True)
        self.custom_closet_dir = tk.BooleanVar(value=False)
        # Directory di default sicura
        self.closet_directory = tk.StringVar(value=str(Path.cwd() / "closet"))
        
        self.setup_ui()
        self.check_queue()
        self.start_clipboard_monitoring()
        
    def setup_ui(self):
        """Configura l'interfaccia utente"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configura il ridimensionamento
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL Input
        ttk.Label(main_frame, text="URL Articolo Vinted:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Frame per URL entry e bottone grab
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=(10, 0))
        url_frame.columnconfigure(0, weight=1)
        
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Binding per Ctrl+Shift+V che fa paste smart (oltre al normale Ctrl+V)
        url_entry.bind('<Control-Shift-V>', lambda e: self.paste_from_clipboard())
        
        paste_btn = ttk.Button(url_frame, text="Incolla", command=self.paste_from_clipboard, width=10)
        paste_btn.grid(row=0, column=1)
        
        # Tooltip per il bottone incolla
        ToolTip(paste_btn, "Incolla manualmente dalla clipboard\nMonitoraggio automatico sempre attivo\nScorciatoia: Ctrl+Shift+V")
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Opzioni", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        options_frame.columnconfigure(0, weight=1)
        
        ttk.Checkbutton(options_frame, text="Scarica foto profilo venditore (--seller) [DISABILITATO]", 
                       variable=self.seller_var, state='disabled').grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Scarica tutti gli articoli del venditore (--all)", 
                       variable=self.all_items_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Salva in sottodirectory (--save-in-dir)", 
                       variable=self.save_in_dir_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="Ignora articoli già scaricati (tracking duplicati)", 
                       variable=self.skip_duplicates_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Checkbox per abilitare il logging su file (per condivisione log con sviluppatore)
        file_logging_check = ttk.Checkbutton(options_frame, text="Salva log dettagliati su file (debug_gui.log)", 
                                            variable=self.file_logging_var, 
                                            command=self.toggle_file_logging)
        file_logging_check.grid(row=4, column=0, sticky=tk.W, pady=2)
        ToolTip(file_logging_check, "Abilita il salvataggio dei log dettagliati su file per condivisione con lo sviluppatore")
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Configurazione Funzionalità Automatiche", padding="10")
        info_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Checkbox organizzazione automatica
        self.org_check = ttk.Checkbutton(info_frame, text="Organizzazione automatica: closet/nome_utente/titolo_001.webp", 
                                        variable=self.auto_organize_enabled)
        self.org_check.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Frame per directory closet personalizzata
        closet_frame = ttk.Frame(info_frame)
        closet_frame.grid(row=1, column=0, sticky="ew", pady=2)
        
        self.custom_dir_check = ttk.Checkbutton(closet_frame, text="Directory closet personalizzata:", 
                                               variable=self.custom_closet_dir, 
                                               command=self.toggle_custom_directory)
        self.custom_dir_check.grid(row=0, column=0, sticky=tk.W)
        
        self.closet_dir_label = ttk.Label(closet_frame, textvariable=self.closet_directory, 
                                         foreground="blue", width=50)
        self.closet_dir_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        self.closet_dir_button = ttk.Button(closet_frame, text="Scegli...", 
                                           command=self.choose_closet_directory, state="disabled")
        self.closet_dir_button.grid(row=0, column=2, padx=(5, 0))
        
        # Checkbox clipboard automatico
        self.clipboard_check = ttk.Checkbutton(info_frame, text="Monitoraggio automatico clipboard URL Vinted", 
                                              variable=self.auto_clipboard_enabled,
                                              command=self.toggle_clipboard_monitoring)
        self.clipboard_check.grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.download_btn = ttk.Button(buttons_frame, text="Avvia Download", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="Ferma", command=self.stop_download, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="Pulisci Output", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Output text area
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, width=80, state='disabled')
        self.output_text.grid(row=0, column=0, sticky="nsew")
        
        # Status bar
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        
    def paste_from_clipboard(self):
        """Incolla URL dalla clipboard (metodo manuale, ora principalmente per il bottone)"""
        try:
            # Ottieni il contenuto della clipboard
            clipboard_content = self.root.clipboard_get()
            clipboard_content = clipboard_content.strip()
            
            # Incolla il contenuto senza popup
            if clipboard_content:
                self.url_var.set(clipboard_content)
                if re.search(r'vinted\.[a-z.]+', clipboard_content):
                    self.status_var.set("URL Vinted incollato dalla clipboard")
                else:
                    self.status_var.set("Contenuto incollato - verifica che sia un URL Vinted")
                
        except tk.TclError:
            self.status_var.set("Clipboard vuota o inaccessibile")
        except Exception as e:
            self.status_var.set(f"Errore clipboard: {str(e)}")
            
    def start_clipboard_monitoring(self):
        """Avvia il monitoraggio automatico della clipboard"""
        self.monitor_clipboard()
        
    def toggle_custom_directory(self):
        """Abilita/disabilita selezione directory personalizzata"""
        if self.custom_closet_dir.get():
            self.closet_dir_button.config(state="normal")
        else:
            self.closet_dir_button.config(state="disabled")
            # Ripristina directory default
            self.closet_directory.set(str(Path.cwd() / "closet"))
    
    def choose_closet_directory(self):
        """Apre dialog per scegliere directory closet"""
        directory = filedialog.askdirectory(
            title="Scegli directory per cartella closet",
            initialdir=self.closet_directory.get()
        )
        if directory:
            self.closet_directory.set(str(Path(directory) / "closet"))
    
    def toggle_clipboard_monitoring(self):
        """Abilita/disabilita monitoraggio clipboard"""
        self.clipboard_monitor_active = self.auto_clipboard_enabled.get()
        if self.clipboard_monitor_active:
            # Riavvia monitoraggio se era disabilitato
            self.monitor_clipboard()
    
    def toggle_file_logging(self):
        """Abilita/disabilita il logging su file"""
        from log_manager import enable_file_logging
        enabled = self.file_logging_var.get()
        enable_file_logging(enabled)
        
        if enabled:
            logger.debug("📝 Logging su file abilitato")
            messagebox.showinfo("Logging Abilitato", 
                               "Il logging dettagliato è stato abilitato.\n"
                               "I log verranno salvati in 'debug_gui.log'.\n"
                               "Questo file può essere condiviso per il debug.")
        else:
            logger.debug("📝 Logging su file disabilitato")
            messagebox.showinfo("Logging Disabilitato", 
                               "Il logging su file è stato disabilitato.\n"
                               "I log non verranno più salvati su file.")
        
    def monitor_clipboard(self):
        """Monitora la clipboard per URL Vinted e li incolla automaticamente"""
        
        if not self.clipboard_monitor_active or not self.auto_clipboard_enabled.get():
            # Se disabilitato, controlla di nuovo tra 1 secondo
            self.root.after(1000, self.monitor_clipboard)
            return
            
        try:
            current_clipboard = self.root.clipboard_get().strip()
            
            # Se il contenuto è cambiato e è un URL Vinted
            if (current_clipboard != self.last_clipboard_content and 
                current_clipboard and 
                re.search(r'vinted\.[a-z.]+', current_clipboard)):
                
                # Log solo per URL Vinted validi rilevati
                if self.debug_enabled:
                    logger.debug(f"✅ URL Vinted rilevato: {current_clipboard}")
                
                # Incolla automaticamente senza popup
                self.url_var.set(current_clipboard)
                self.status_var.set("URL Vinted rilevato e incollato automaticamente")
                
            # Aggiorna l'ultimo contenuto
            self.last_clipboard_content = current_clipboard
            
        except (tk.TclError, Exception) as e:
            # Ignora errori di clipboard silenziosamente (sono normali)
            pass
            
        # Riprogramma il controllo ogni 500ms
        if self.clipboard_monitor_active:
            self.root.after(500, self.monitor_clipboard)
            
    def validate_inputs(self):
        """Valida gli input dell'utente"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Errore", "Inserisci l'URL dell'articolo Vinted")
            return False
            
        if not re.search(r'vinted\.[a-z.]+', url):
            messagebox.showerror("Errore", "L'URL non sembra essere un link Vinted valido")
            return False
            
        return True
        
    def build_command(self):
        """Costruisce il comando per il downloader ORIGINALE (core)"""
        # Usa il core originale senza modifiche
        cmd = [sys.executable, "vinted_downloader.py"]
        
        # URL (argomento posizionale)
        cmd.append(self.url_var.get().strip())
        
        # Directory output (sempre directory corrente)
        cmd.extend(["-o", str(Path.cwd())])
        
        # Opzioni
        if self.seller_var.get():
            cmd.append("--seller")
        if self.all_items_var.get():
            cmd.append("--all")
        if self.save_in_dir_var.get():
            cmd.append("--save-in-dir")
            
        return cmd
        
    def append_output(self, text, tag=None):
        """Aggiunge testo all'area di output"""
        self.output_text.config(state='normal')
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')
        
    def clear_output(self):
        """Pulisce l'area di output"""
        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state='disabled')
        
    def start_download(self):
        """Avvia il processo di download in un thread separato"""
        # DEBUG BREAKPOINT 4: Inizio Download
        logger.debug("🚀 DEBUG: Avvio download")
        logger.debug(f"🔧 DEBUG: Organizzazione abilitata: {self.auto_organize_enabled.get()}")
        logger.debug(f"📂 DEBUG: Directory closet: {self.closet_directory.get()}")
        logger.debug(f"🎯 DEBUG: URL: {self.url_var.get()}")
        
        if not self.validate_inputs():
            logger.debug("❌ DEBUG: Validazione input fallita")
            return
            
        if self.process_running:
            messagebox.showwarning("Avviso", "Un download è già in corso")
            return
            
        self.process_running = True
        self.download_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.progress.start()
        self.status_var.set("Download in corso...")
        
        # Avvia download in thread separato
        self.download_thread = threading.Thread(target=self.run_download, daemon=True)
        self.download_thread.start()
        
    def run_download(self):
        """Esegue il download nel thread separato"""
        # DEBUG BREAKPOINT 5: Esecuzione Download
        logger.debug("⚡ DEBUG: Esecuzione download nel thread")
        
        try:
            # Scegli il comando in base alle impostazioni
            if self.auto_organize_enabled.get():
                # DEBUG: Wrapper con organizzazione
                logger.debug("📁 DEBUG: Usando wrapper con organizzazione")
                
                # Usa il wrapper con organizzazione
                cmd = ["python3", "vinted_downloader_organized.py"]
                
                # Aggiungi parametro debug se siamo in modalità debug
                if is_debug_mode():
                    cmd.append("--debug")
                
                # Aggiungi URL
                url = self.url_var.get().strip()
                cmd.append(url)
                
                # Opzioni
                if self.seller_var.get():
                    cmd.append("--seller")
                if self.all_items_var.get():
                    cmd.append("--all")
                
                # Controllo duplicati (solo per wrapper con organizzazione)
                if not self.skip_duplicates_var.get():
                    cmd.append("--force-download")
                
                # Directory di base sempre directory corrente
                cmd.extend(["-o", str(Path.cwd())])
                
                # Aggiungi parametro per directory closet se personalizzata
                if self.custom_closet_dir.get() and self.closet_directory.get():
                    cmd.extend(["--closet-dir", self.closet_directory.get()])
                else:
                    # Usa directory closet predefinita
                    cmd.extend(["--closet-dir", str(Path.cwd() / "closet")])
                
            else:
                # DEBUG: Core originale
                logger.debug("🔧 DEBUG: Usando core originale")
                
                # Usa il comando originale
                cmd = self.build_command()
            
            # Log comando finale per troubleshooting
            logger.info(f"💻 Comando eseguito: {' '.join(cmd)}")
            
            self.output_queue.put(("info", f"Comando: {' '.join(cmd)}\n\n"))
            
            # Esegui il comando
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=os.getcwd()
            )
            
            # Leggi output in tempo reale solo se stdout è disponibile
            if self.current_process.stdout:
                for line in iter(self.current_process.stdout.readline, ''):
                    if not self.process_running:
                        break
                    self.output_queue.put(("output", line))
                
            # Aspetta che il processo termini
            return_code = self.current_process.wait()
            
            if return_code == 0:
                self.output_queue.put(("success", "\nDownload completato con successo!\n"))
                # Determina dove sono stati salvati i file basandosi sulla configurazione
                if self.auto_organize_enabled.get():
                    if self.custom_closet_dir.get() and self.closet_directory.get():
                        save_location = self.closet_directory.get()
                    else:
                        save_location = str(Path.cwd() / "closet")
                else:
                    save_location = str(Path.cwd())
                self.output_queue.put(("info", f"File salvati in: {save_location}\n"))
            else:
                self.output_queue.put(("error", f"\nDownload fallito (codice: {return_code})\n"))
                
        except Exception as e:
            self.output_queue.put(("error", f"\nErrore durante il download: {str(e)}\n"))
        finally:
            self.output_queue.put(("done", None))
            
    def stop_download(self):
        """Ferma il processo di download"""
        if self.current_process:
            self.current_process.terminate()
            self.output_queue.put(("warning", "\nDownload interrotto dall'utente\n"))
        self.process_running = False
        
    def check_queue(self):
        """Controlla la queue per messaggi dai thread"""
        try:
            while True:
                msg_type, content = self.output_queue.get_nowait()
                
                if msg_type == "done":
                    self.process_running = False
                    self.download_btn.config(state='normal')
                    self.stop_btn.config(state='disabled')
                    self.progress.stop()
                    self.status_var.set("Pronto")
                elif msg_type == "output":
                    self.append_output(content)
                elif msg_type == "error":
                    self.append_output(content)
                    self.status_var.set("Errore durante il download")
                elif msg_type == "success":
                    self.append_output(content)
                    self.status_var.set("Download completato")
                elif msg_type == "warning":
                    self.append_output(content)
                    self.status_var.set("Download interrotto")
                elif msg_type == "info":
                    self.append_output(content)
                    
        except queue.Empty:
            pass
        finally:
            # Ricontrolla dopo 100ms
            self.root.after(100, self.check_queue)


def main():
    """Funzione principale per avviare la GUI"""
    # Verifica che i file necessari esistano
    required_files = [
        "vinted_downloader.py",
        "vinted_downloader_organized.py", 
        "vinted_organizer.py"
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ File mancanti: {', '.join(missing_files)}")
        return
        
    root = tk.Tk()
    root.title("Vinted Downloader GUI")
    root.geometry("800x600")
    root.resizable(True, True)
    
    # SOLUZIONE DEFINITIVA: Forza la finestra ad apparire
    root.state('normal')  # Assicura che non sia minimizzata
    root.deiconify()      # Forza la visualizzazione se era iconificata
    root.lift()           # Porta in primo piano
    root.attributes('-topmost', True)  # Temporaneamente sempre in primo piano
    root.focus_force()    # Forza il focus
    
    # Centra la finestra sullo schermo
    root.update_idletasks()
    width = 800
    height = 600
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Disattiva topmost dopo 1 secondo per permettere normale utilizzo
    root.after(1000, lambda: root.attributes('-topmost', False))
    
    app = VintedDownloaderGUI(root)
    
    # Gestione chiusura finestra
    def on_closing():
        app.clipboard_monitor_active = False
        if app.process_running:
            if messagebox.askokcancel("Uscita", "Un download è in corso. Vuoi interromperlo e uscire?"):
                app.stop_download()
                root.destroy()
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
