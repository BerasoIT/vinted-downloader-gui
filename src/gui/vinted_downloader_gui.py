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

# Aggiungi il path per importare dai moduli utils
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.queue_manager import DownloadQueue
from utils.log_manager import LogManager

# DEBUG: Modulo per debugging con VS Code
import logging
from utils.log_manager import get_logger, enable_file_logging, is_debug_mode

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
        
        # Variabili per tracking progresso
        self.total_links = 0
        self.processed_links = 0
        self.total_images = 0
        self.downloaded_images = 0
        
        # Inizializza logging e queue manager
        self.log_manager = LogManager()
        self.download_queue = DownloadQueue()
        
        self.setup_ui()
        self.check_queue()
        self.refresh_queue_display()  # Carica eventuali elementi salvati
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
        
        add_btn = ttk.Button(url_frame, text="Aggiungi", command=self.add_url_to_queue, width=10)
        add_btn.grid(row=0, column=1)
        
        # Tooltip per il bottone aggiungi
        ToolTip(add_btn, "Aggiungi URL alla lista download\nMonitoraggio automatico clipboard sempre attivo\nScorciatoia: Ctrl+Shift+V")
        
        # Download Queue frame
        queue_frame = ttk.LabelFrame(main_frame, text="Lista Download", padding="10")
        queue_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)
        queue_frame.columnconfigure(0, weight=1)
        
        # Frame per la lista e i bottoni
        queue_list_frame = ttk.Frame(queue_frame)
        queue_list_frame.grid(row=0, column=0, sticky="ew")
        queue_list_frame.columnconfigure(0, weight=1)
        
        # Listbox per mostrare gli URL in coda
        self.queue_listbox = tk.Listbox(queue_list_frame, height=9, selectmode=tk.SINGLE)
        self.queue_listbox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Scrollbar per la listbox
        queue_scrollbar = ttk.Scrollbar(queue_list_frame, orient="vertical", command=self.queue_listbox.yview)
        queue_scrollbar.grid(row=0, column=1, sticky="ns")
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        # Frame per i bottoni della queue
        queue_buttons_frame = ttk.Frame(queue_frame)
        queue_buttons_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Button(queue_buttons_frame, text="Rimuovi Selezionato", 
                  command=self.remove_from_queue).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Svuota Lista", 
                  command=self.clear_queue).grid(row=0, column=1, padx=(0, 5))
        
        # Label per mostrare il conteggio
        self.queue_count_label = ttk.Label(queue_frame, text="Articoli in lista: 0")
        self.queue_count_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        # Options frame collassabile
        self.options_expanded = tk.BooleanVar(value=False)  # Inizialmente collassato
        options_header_frame = ttk.Frame(main_frame)
        options_header_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        options_header_frame.columnconfigure(1, weight=1)
        
        # Bottone expand/collapse per opzioni
        self.options_toggle_btn = ttk.Button(options_header_frame, text="▶", width=3, 
                                           command=self.toggle_options)
        self.options_toggle_btn.grid(row=0, column=0, padx=(0, 5))
        
        ttk.Label(options_header_frame, text="Opzioni Download", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=1, sticky="w")
        
        # Frame per le opzioni (inizialmente nascosto)
        self.options_frame = ttk.Frame(main_frame, padding="10")
        self.options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.options_frame.columnconfigure(0, weight=1)
        # Inizialmente nascosto
        self.options_frame.grid_remove()
        
        ttk.Checkbutton(self.options_frame, text="Scarica foto profilo venditore (--seller) [DISABILITATO]", 
                       variable=self.seller_var, state='disabled').grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(self.options_frame, text="Scarica tutti gli articoli del venditore (--all)", 
                       variable=self.all_items_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(self.options_frame, text="Salva in sottodirectory (--save-in-dir)", 
                       variable=self.save_in_dir_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(self.options_frame, text="Ignora articoli già scaricati (tracking duplicati)", 
                       variable=self.skip_duplicates_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Checkbox per abilitare il logging su file (per condivisione log con sviluppatore)
        file_logging_check = ttk.Checkbutton(self.options_frame, text="Salva log dettagliati su file (debug_gui.log)", 
                                            variable=self.file_logging_var, 
                                            command=self.toggle_file_logging)
        file_logging_check.grid(row=4, column=0, sticky=tk.W, pady=2)
        ToolTip(file_logging_check, "Abilita il salvataggio dei log dettagliati su file per condivisione con lo sviluppatore")
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Configurazione Funzionalità Automatiche", padding="10")
        info_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        
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
        buttons_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        self.download_btn = ttk.Button(buttons_frame, text="Avvia Download", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="Ferma", command=self.stop_download, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="Pulisci Output", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Progress bars container
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar 1: Links progress
        self.links_progress_label = ttk.Label(progress_frame, text="Articoli: 0/0 (0%)")
        self.links_progress_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.links_progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.links_progress.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        # Progress bar 2: Images progress  
        self.images_progress_label = ttk.Label(progress_frame, text="Immagini: 0/0 (0%)")
        self.images_progress_label.grid(row=2, column=0, sticky="w", pady=(0, 2))
        
        self.images_progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.images_progress.grid(row=3, column=0, sticky="ew")
        
        # Mantieni riferimento alla barra principale per compatibilità
        self.progress = self.links_progress
        
        # Output section con header collapsible
        output_header_frame = ttk.Frame(main_frame)
        output_header_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        output_header_frame.columnconfigure(1, weight=1)
        
        # Bottone expand/collapse per output
        self.output_toggle_btn = ttk.Button(output_header_frame, text="▶", width=3, 
                                          command=self.toggle_output)
        self.output_toggle_btn.grid(row=0, column=0, padx=(0, 5))
        
        ttk.Label(output_header_frame, text="Output Download", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=1, sticky="w")
        
        # Frame per l'output (inizialmente nascosto)
        self.output_frame = ttk.Frame(main_frame, padding="5")
        # Non fare grid inizialmente (nascosto)
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(self.output_frame, height=10, width=80, state='disabled')
        self.output_text.grid(row=0, column=0, sticky="nsew")
        
        # Stato del toggle output (inizialmente nascosto)
        self.output_expanded = False
        
        # Configurazione per finestra dinamica
        self.setup_dynamic_window()
        
        # Status bar con info fullscreen
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=0, column=0, sticky="ew")
        
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
        from utils.log_manager import enable_file_logging
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
    
    def toggle_options(self):
        """Espande/collassa la sezione opzioni"""
        if self.options_expanded.get():
            # Collassa le opzioni
            self.options_frame.grid_remove()
            self.options_toggle_btn.config(text="▶")
            self.options_expanded.set(False)
        else:
            # Espande le opzioni
            self.options_frame.grid()
            self.options_toggle_btn.config(text="▼")
            self.options_expanded.set(True)
            
        # Ridimensiona finestra dinamicamente
        self.root.after(10, self.resize_window_to_content)
    
    def toggle_output(self):
        """Espande/collassa la sezione output"""
        if self.output_expanded:
            # Collassa l'output
            self.output_frame.grid_remove()
            self.output_toggle_btn.config(text="▶")
            self.output_expanded = False
        else:
            # Espande l'output
            self.output_frame.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=5)
            # Configura il peso della riga per espandere
            self.output_frame.master.rowconfigure(9, weight=1)
            self.output_toggle_btn.config(text="▼")
            self.output_expanded = True
            
        # Ridimensiona finestra dinamicamente
        self.root.after(10, self.resize_window_to_content)
    
    def setup_dynamic_window(self):
        """Configura la finestra per il ridimensionamento dinamico"""
        # Disabilita completamente il ridimensionamento manuale
        self.root.resizable(False, False)
        
        # Ulteriore blocco per assicurarsi che non sia ridimensionabile
        self.root.maxsize(width=1200, height=1200)  # Limite massimo uguale alla dimensione massima
        self.root.minsize(width=850, height=600)    # Dimensione minima
        
        # Bind per intercettare tentativi di ridimensionamento
        self.root.bind('<Configure>', self.on_window_configure)
        
        # Variabile per tracciare lo stato fullscreen
        self.is_fullscreen = False
        self.normal_geometry = None
        
        # Calcola e imposta la dimensione iniziale
        self.resize_window_to_content()
    
    def on_window_configure(self, event):
        """Intercetta i tentativi di ridimensionamento manuale"""
        # Solo per eventi sulla finestra principale (non sui widget interni)
        if event.widget == self.root:
            # Se la geometria cambia per ragioni diverse dai nostri metodi,
            # forza il ripristino della geometria corretta
            if hasattr(self, 'normal_geometry') and self.normal_geometry:
                current_geom = self.root.geometry()
                if current_geom != self.normal_geometry and not self.is_fullscreen:
                    # Piccolo delay per evitare loop infiniti
                    self.root.after_idle(lambda: self.root.geometry(self.normal_geometry))
    
    def resize_window_to_content(self):
        """Ridimensiona la finestra in base al contenuto visibile preservando la posizione"""
        if self.is_fullscreen:
            return  # Non ridimensionare se in fullscreen
            
        # Forza l'aggiornamento del layout
        self.root.update_idletasks()
        
        # Salva la posizione corrente
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        
        # Calcola la dimensione necessaria
        req_width = self.root.winfo_reqwidth()
        req_height = self.root.winfo_reqheight()
        
        # Aggiungi un po' di padding
        padding_width = 50
        padding_height = 50
        
        # Dimensioni minime e massime più generose
        min_width = 850  # Aumentato da 800
        max_width = 1200
        min_height = 600  # Aumentato da 400
        
        # Ottieni dimensioni schermo per il massimo
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        max_height = int(screen_height * 0.9)  # 90% dello schermo
        
        # Calcola dimensioni finali
        final_width = max(min_width, min(req_width + padding_width, max_width))
        final_height = max(min_height, min(req_height + padding_height, max_height))
        
        # Usa la posizione corrente solo se è valida, altrimenti centra
        if current_x < 0 or current_y < 0 or (current_x == 0 and current_y == 0):
            # Centra solo se la posizione non è valida (prima volta)
            center_x = (screen_width - final_width) // 2
            center_y = (screen_height - final_height) // 2
            center_x = max(0, center_x)
            center_y = max(0, center_y)
            self.root.geometry(f"{final_width}x{final_height}+{center_x}+{center_y}")
            self.normal_geometry = f"{final_width}x{final_height}+{center_x}+{center_y}"
        else:
            # Mantieni la posizione corrente
            self.root.geometry(f"{final_width}x{final_height}+{current_x}+{current_y}")
            self.normal_geometry = f"{final_width}x{final_height}+{current_x}+{current_y}"
    
    # =====================
    # GESTIONE DOWNLOAD QUEUE
    # =====================
    
    def add_url_to_queue(self):
        """Aggiunge l'URL corrente alla coda di download"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("URL Vuoto", "Inserisci un URL prima di aggiungerlo alla lista.")
            return
        
        # Verifica che sia un URL Vinted valido
        if not re.search(r'vinted\.[a-z.]+', url):
            messagebox.showwarning("URL Non Valido", "L'URL inserito non sembra essere un link Vinted valido.")
            return
        
        # Aggiungi alla queue
        added_item = self.download_queue.add(url)
        if added_item:
            self.refresh_queue_display()
            self.url_var.set("")  # Pulisci il campo
            if self.debug_enabled:
                logger.debug(f"🔗 URL aggiunto alla lista: {url}")
    
    def remove_from_queue(self):
        """Rimuove l'elemento selezionato dalla coda"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Nessuna Selezione", "Seleziona un elemento dalla lista da rimuovere.")
            return
        
        # Ottieni l'URL dell'elemento selezionato
        index = selection[0]
        queue_items = self.download_queue.get_all()
        if index < len(queue_items):
            url = queue_items[index]['url']
            self.download_queue.remove(url)
            self.refresh_queue_display()
            if self.debug_enabled:
                logger.debug(f"🗑️ URL rimosso dalla lista: {url}")
    
    def clear_queue(self):
        """Svuota completamente la coda"""
        if self.download_queue.count() == 0:
            messagebox.showinfo("Lista Vuota", "La lista è già vuota.")
            return
        
        result = messagebox.askyesno("Conferma", "Vuoi davvero svuotare tutta la lista?")
        if result:
            self.download_queue.clear()
            self.refresh_queue_display()
            if self.debug_enabled:
                logger.debug("🧹 Lista download svuotata")
    
    def refresh_queue_display(self):
        """Aggiorna la visualizzazione della coda"""
        # Pulisci la listbox
        self.queue_listbox.delete(0, tk.END)
        
        # Riempi con gli elementi della coda
        queue_items = self.download_queue.get_all()
        for item in queue_items:
            url = item['url']
            status = item.get('status', 'pending')
            # Mostra solo il titolo dell'articolo o ID dall'URL
            display_text = self.extract_title_from_url(url)
            if status == 'completed':
                display_text += " [✓ completato]"
            elif status == 'downloaded':
                display_text += " [↓ scaricato]"
            elif status == 'processing':
                display_text += " [⟳ in corso]"
            elif status == 'failed':
                display_text += " [✗ fallito]"
            # pending non ha indicatore
            self.queue_listbox.insert(tk.END, display_text)
        
        # Aggiorna il conteggio
        count = self.download_queue.count()
        pending_count = self.download_queue.count_pending()
        self.queue_count_label.config(text=f"Articoli in lista: {count} (pending: {pending_count})")
    
    def extract_title_from_url(self, url):
        """Estrae il titolo dell'articolo dall'URL per la visualizzazione"""
        try:
            # Estrae la parte dopo l'ultimo slash e prima del primo parametro
            parts = url.split('/')
            if len(parts) > 0:
                title_part = parts[-1].split('?')[0]
                # Rimuove l'ID e mantiene solo il titolo
                if '-' in title_part:
                    return title_part.split('-', 1)[1].replace('-', ' ').title()
            return url[-50:]  # Fallback: ultimi 50 caratteri
        except:
            return url[-50:]  # Fallback in caso di errore
    
    def process_download_queue(self):
        """Processa la coda di download in sequenza (da eseguire in thread separato)"""
        try:
            pending_items = self.download_queue.get_pending()
            total_items = len(pending_items)
            
            self.output_queue.put(f"\nAvvio download di {total_items} articoli dalla lista...\n")
            
            # Imposta progress bar
            self.root.after(0, lambda: self.progress.config(maximum=total_items, value=0, mode='determinate'))
            
            for i, item in enumerate(pending_items, 1):
                url = item['url']
                
                # Aggiorna status a 'processing'
                self.download_queue.update_status(url, 'processing')
                self.root.after(0, self.refresh_queue_display)  # Aggiorna UI nel thread principale
                
                self.output_queue.put(f"\n[{i}/{total_items}] Download: {self.extract_title_from_url(url)}")
                
                # Simula il download singolo impostando l'URL e chiamando start_download
                self.root.after(0, lambda u=url: self.url_var.set(u))
                
                # Avvia il download e attendi che finisca
                success = self.download_single_item_from_queue(url)
                
                # Aggiorna progress bar
                self.root.after(0, lambda v=i: self.progress.config(value=v))
                
                # Aggiorna status in base al risultato
                if success:
                    # Solo se organizzazione è abilitata, segna come completed
                    if self.auto_organize_enabled.get():
                        self.download_queue.update_status(url, 'completed')
                        self.output_queue.put(f"[{i}/{total_items}] Completato e organizzato")
                    else:
                        # Senza organizzazione, rimane come downloaded ma non completed
                        self.download_queue.update_status(url, 'downloaded')
                        self.output_queue.put(f"[{i}/{total_items}] Download completato")
                else:
                    self.download_queue.update_status(url, 'failed')
                    self.output_queue.put(f"[{i}/{total_items}] Download fallito")
                
                self.root.after(0, self.refresh_queue_display)  # Aggiorna UI
            
            self.output_queue.put(f"\nDownload lista completato! {total_items} articoli processati.")
            self.root.after(0, lambda: self.url_var.set(""))  # Pulisci URL field
            
            # Pulizia finale file temporanei
            self.cleanup_temp_files()
            
        finally:
            # IMPORTANTE: Resetta sempre lo stato dell'UI alla fine
            self.root.after(0, self.reset_ui_state)
    
    def reset_ui_state(self):
        """Resetta lo stato dell'UI dopo il completamento del download"""
        self.process_running = False
        self.download_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress.stop()
        self.progress.config(mode='indeterminate', value=0)  # Reset a indeterminato
        self.status_var.set("Pronto")
    
    def download_single_item_from_queue(self, url):
        """Scarica un singolo articolo dalla coda eseguendo il download reale"""
        try:
            # Costruisci il comando per il download con organizzazione
            if self.auto_organize_enabled.get():
                core_organized_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "vinted_downloader_organized.py")
                cmd = ["python3", core_organized_path]
            else:
                core_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "vinted_downloader.py")
                cmd = ["python3", core_path]
            
            # Aggiungi parametro debug se siamo in modalità debug
            if is_debug_mode():
                cmd.append("--debug")
            
            # Aggiungi URL
            cmd.append(url)
            
            # Esegui il comando di download
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=os.path.dirname(os.path.dirname(__file__)))
            
            # Controlla se il download è andato a buon fine
            success = result.returncode == 0
            
            if not success and self.debug_enabled:
                logger.debug(f"❌ Errore download {url}: {result.stderr}")
            
            # Pulizia file temporanei di sicurezza
            self.cleanup_temp_files()
            
            return success
            
        except Exception as e:
            if self.debug_enabled:
                logger.debug(f"❌ Errore download {url}: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Rimuove i file temporanei creati durante il download"""
        temp_files = ["item.json", "item_summary"]
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        for temp_file in temp_files:
            try:
                temp_path = os.path.join(project_root, temp_file)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    if self.debug_enabled:
                        logger.debug(f"🗑️ Rimosso file temporaneo: {temp_file}")
            except Exception as e:
                if self.debug_enabled:
                    logger.debug(f"⚠️ Errore rimozione {temp_file}: {e}")
    
    def reset_progress_bars(self):
        """Resetta entrambe le progress bar"""
        self.total_links = 0
        self.processed_links = 0
        self.total_images = 0
        self.downloaded_images = 0
        self.update_links_progress()
        self.update_images_progress()
    
    def update_links_progress(self):
        """Aggiorna la progress bar dei link"""
        if self.total_links > 0:
            percentage = (self.processed_links / self.total_links) * 100
            self.links_progress.config(value=percentage)
            self.links_progress_label.config(text=f"Articoli: {self.processed_links}/{self.total_links} ({percentage:.0f}%)")
        else:
            self.links_progress.config(value=0)
            self.links_progress_label.config(text="Articoli: 0/0 (0%)")
    
    def update_images_progress(self):
        """Aggiorna la progress bar delle immagini"""
        if self.total_images > 0:
            percentage = (self.downloaded_images / self.total_images) * 100
            self.images_progress.config(value=percentage)
            self.images_progress_label.config(text=f"Immagini: {self.downloaded_images}/{self.total_images} ({percentage:.0f}%)")
        else:
            self.images_progress.config(value=0)
            self.images_progress_label.config(text="Immagini: 0/0 (0%)")
    
    def set_total_links(self, total):
        """Imposta il numero totale di link da processare"""
        self.total_links = total
        self.processed_links = 0
        self.root.after(0, self.update_links_progress)
    
    def increment_processed_links(self):
        """Incrementa il contatore dei link processati"""
        self.processed_links += 1
        self.root.after(0, self.update_links_progress)
    
    def set_total_images(self, total):
        """Imposta il numero totale di immagini da scaricare"""
        self.total_images = total
        self.downloaded_images = 0
        self.root.after(0, self.update_images_progress)
    
    def increment_downloaded_images(self):
        """Incrementa il contatore delle immagini scaricate"""
        self.downloaded_images += 1
        self.root.after(0, self.update_images_progress)
    
    def parse_download_output(self, line):
        """Analizza l'output del download per aggiornare le progress bar"""
        import re
        
        line_lower = line.lower().strip()
        
        # Rileva il numero totale di immagini da "Found data: X images"
        found_data_match = re.search(r'found data:?\s*(\d+)\s*images?', line_lower)
        if found_data_match:
            total_images = int(found_data_match.group(1))
            self.set_total_images(total_images)
            return
        
        # Rileva quando inizia un nuovo articolo
        if "downloading details" in line_lower:
            if self.total_links == 0:
                # Prima volta: imposta total_links a 1 (singolo articolo)
                self.set_total_links(1)
            return
        
        # Rileva quando un'immagine viene scaricata
        if "downloading resource" in line_lower:
            self.increment_downloaded_images()
            return
        
        # Rileva completamento articolo
        if "organizzazione" in line_lower or "download completato" in line_lower:
            if self.processed_links < self.total_links:
                self.increment_processed_links()
            return
        
    def monitor_clipboard(self):
        """Monitora la clipboard per URL Vinted e li aggiunge automaticamente alla lista"""
        
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
                
                # Log per URL Vinted validi rilevati
                if self.debug_enabled:
                    logger.debug(f"✅ URL Vinted rilevato: {current_clipboard}")
                
                # Aggiungi automaticamente alla queue
                added_item = self.download_queue.add(current_clipboard)
                if added_item:
                    self.refresh_queue_display()
                    title = self.extract_title_from_url(current_clipboard)
                    self.status_var.set(f"URL aggiunto automaticamente alla lista: {title}")
                    if self.debug_enabled:
                        logger.debug(f"🔗 URL aggiunto automaticamente alla lista: {current_clipboard}")
                else:
                    self.status_var.set("URL già presente nella lista")
                
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
        core_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "vinted_downloader.py")
        cmd = [sys.executable, core_path]
        
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
        """Avvia il processo di download: prima la coda, poi singolo URL"""
        # DEBUG BREAKPOINT 4: Inizio Download
        logger.debug("🚀 DEBUG: Avvio download")
        
        # Reset delle progress bar
        self.reset_progress_bars()
        
        if self.process_running:
            messagebox.showwarning("Avviso", "Un download è già in corso")
            return
        
        # Prima controlla se ci sono elementi in coda
        pending_items = self.download_queue.get_pending()
        
        if pending_items:
            # Se ci sono elementi in coda, avvia il download della coda
            logger.debug(f"📋 DEBUG: Trovati {len(pending_items)} elementi in coda")
            self.start_queue_processing()
        else:
            # Se non ci sono elementi in coda, controlla l'URL singolo
            logger.debug("🎯 DEBUG: Nessun elemento in coda, controllo URL singolo")
            logger.debug(f"🔧 DEBUG: Organizzazione abilitata: {self.auto_organize_enabled.get()}")
            logger.debug(f"📂 DEBUG: Directory closet: {self.closet_directory.get()}")
            logger.debug(f"🎯 DEBUG: URL: {self.url_var.get()}")
            
            if not self.validate_inputs():
                logger.debug("❌ DEBUG: Validazione input fallita")
                return
                
            self.start_single_download()
    
    def start_queue_processing(self):
        """Avvia il download sequenziale della coda"""
        # Imposta il numero totale di link da processare
        pending_items = self.download_queue.get_pending()
        self.set_total_links(len(pending_items))
        
        self.process_running = True
        self.download_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.progress.start()
        
        # Avvia il download della coda in un thread separato
        self.queue_thread = threading.Thread(target=self.process_download_queue, daemon=True)
        self.queue_thread.start()
    
    def start_single_download(self):
        """Avvia il download di un singolo URL"""
        self.process_running = True
        self.download_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Imposta progress bar determinata per download singolo (5 fasi)
        self.progress.config(mode='determinate', maximum=100, value=0)
        self.status_var.set("Download in corso...")
        
        # Avvia download in thread separato
        self.download_thread = threading.Thread(target=self.run_download, daemon=True)
        self.download_thread.start()
        
    def run_download(self):
        """Esegue il download nel thread separato"""
        # DEBUG BREAKPOINT 5: Esecuzione Download
        logger.debug("⚡ DEBUG: Esecuzione download nel thread")
        
        try:
            # Fase 1: Preparazione comando (10%)
            self.root.after(0, lambda: self.progress.config(value=10))
            self.root.after(0, lambda: self.status_var.set("Preparazione comando..."))
            
            # Scegli il comando in base alle impostazioni
            if self.auto_organize_enabled.get():
                # DEBUG: Wrapper con organizzazione
                logger.debug("📁 DEBUG: Usando wrapper con organizzazione")
                
                # Usa il wrapper con organizzazione
                core_organized_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "vinted_downloader_organized.py")
                cmd = ["python3", core_organized_path]
                
                # Aggiungi parametro debug se siamo in modalità debug
                if is_debug_mode():
                    cmd.append("--debug")
                
                # Aggiungi URL
                url = self.url_var.get().strip()
                cmd.append(url)
                
                # Fase 2: Preparazione parametri (20%)
                self.root.after(0, lambda: self.progress.config(value=20))
                self.root.after(0, lambda: self.status_var.set("Configurazione parametri..."))
                
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
            
            # Fase 3: Avvio download (30%)
            self.root.after(0, lambda: self.progress.config(value=30))
            self.root.after(0, lambda: self.status_var.set("Avvio download..."))
            
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
            
            # Fase 4: Download in corso (da 40% a 80%)
            self.root.after(0, lambda: self.progress.config(value=40))
            self.root.after(0, lambda: self.status_var.set("Download in corso..."))
            
            # Conta le righe di output per simulare progresso
            line_count = 0
            # Leggi output in tempo reale solo se stdout è disponibile
            if self.current_process.stdout:
                for line in iter(self.current_process.stdout.readline, ''):
                    if not self.process_running:
                        break
                    
                    # Parse dell'output per aggiornare le progress bar
                    self.parse_download_output(line)
                    
                    # Aggiorna progresso basato sul contenuto dell'output
                    line_count += 1
                    if line_count % 3 == 0:  # Aggiorna ogni 3 righe
                        # Progresso da 40% a 80% basato sul numero di righe
                        progress_value = min(40 + (line_count * 2), 80)
                        self.root.after(0, lambda v=progress_value: self.progress.config(value=v))
                    
                    # Aggiorna status basato sul contenuto della riga
                    if "downloading details" in line.lower():
                        self.root.after(0, lambda: self.status_var.set("Scaricamento dettagli articolo..."))
                    elif "downloading resource" in line.lower():
                        self.root.after(0, lambda: self.status_var.set("Scaricamento immagini..."))
                    elif "organizzazione" in line.lower():
                        self.root.after(0, lambda: self.status_var.set("Organizzazione file..."))
                    
                    self.output_queue.put(("output", line))
                
            # Fase 5: Finalizzazione (90%)
            self.root.after(0, lambda: self.progress.config(value=90))
            self.root.after(0, lambda: self.status_var.set("Finalizzazione..."))
            
            # Aspetta che il processo termini
            return_code = self.current_process.wait()
            
            # Fase 6: Completamento (100%)
            self.root.after(0, lambda: self.progress.config(value=100))
            
            if return_code == 0:
                self.root.after(0, lambda: self.status_var.set("Download completato!"))
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
                self.root.after(0, lambda: self.status_var.set("Download fallito"))
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
                item = self.output_queue.get_nowait()
                
                # Controlla se è una tupla con 2 elementi
                if isinstance(item, tuple) and len(item) == 2:
                    msg_type, content = item
                elif isinstance(item, str):
                    # Se è solo una stringa, trattala come output
                    msg_type, content = "output", item
                else:
                    # Skip elementi non validi
                    continue
                
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
    core_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core")
    required_files = [
        os.path.join(core_dir, "vinted_downloader.py"),
        os.path.join(core_dir, "vinted_downloader_organized.py"), 
        os.path.join(core_dir, "vinted_organizer.py")
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ File mancanti: {', '.join(missing_files)}")
        return
        
    root = tk.Tk()
    root.title("Vinted Downloader GUI")
    # Rimuoviamo la geometria fissa - sarà gestita dinamicamente
    # root.geometry("900x750")  # Sarà calcolata automaticamente
    
    # SOLUZIONE DEFINITIVA: Forza la finestra ad apparire
    root.state('normal')  # Assicura che non sia minimizzata
    root.deiconify()      # Forza la visualizzazione se era iconificata
    root.lift()           # Porta in primo piano
    root.attributes('-topmost', True)  # Temporaneamente sempre in primo piano
    root.focus_force()    # Forza il focus
    
    # Centra la finestra sul monitor primario (gestione multi-monitor)
    # Il sistema dinamico gestirà automaticamente le dimensioni
    root.update_idletasks()
    
    # Posiziona temporaneamente la finestra per il calcolo
    root.geometry("+100+100")
    
    # Crea l'istanza GUI che gestirà le dimensioni dinamicamente
    app = VintedDownloaderGUI(root)
    
    # Disattiva topmost dopo 1 secondo per permettere normale utilizzo
    root.after(1000, lambda: root.attributes('-topmost', False))
    
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
