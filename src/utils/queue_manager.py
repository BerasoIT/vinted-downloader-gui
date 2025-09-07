#!/usr/bin/env python3
"""
Queue Manager per Vinted Downloader GUI
Gestisce la lista di download in modo semplice e persistente
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

QUEUE_FILE = Path(__file__).parent.parent.parent / "data" / "download_queue.json"


class DownloadQueue:
    """Gestisce la coda di download con persistenza su file"""
    
    def __init__(self, queue_file: Path = QUEUE_FILE):
        self.queue_file = Path(queue_file)
        self.data = {"queue": []}
        self.load()
    
    def load(self):
        """Carica la coda dal file JSON"""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                # Assicura che la struttura sia corretta
                if "queue" not in self.data:
                    self.data = {"queue": []}
            except (json.JSONDecodeError, IOError):
                self.data = {"queue": []}
    
    def save(self):
        """Salva la coda sul file JSON"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError:
            # Se non riesce a salvare, non è fatale
            pass
    
    def add(self, url: str) -> Dict:
        """Aggiunge un URL alla coda se non è già presente"""
        # Controlla se l'URL è già presente
        for item in self.data["queue"]:
            if item.get("url") == url:
                return item  # Già presente, non aggiungere duplicato
        
        # Crea nuovo elemento
        entry = {
            "url": url,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"  # pending, processing, completed, failed
        }
        
        self.data["queue"].append(entry)
        self.save()
        return entry
    
    def remove(self, url: str) -> bool:
        """Rimuove un URL dalla coda"""
        original_length = len(self.data["queue"])
        self.data["queue"] = [item for item in self.data["queue"] if item.get("url") != url]
        
        if len(self.data["queue"]) < original_length:
            self.save()
            return True
        return False
    
    def get_all(self) -> List[Dict]:
        """Restituisce tutti gli elementi della coda"""
        return list(self.data.get("queue", []))
    
    def update_status(self, url: str, status: str) -> bool:
        """Aggiorna lo status di un elemento della coda"""
        for item in self.data["queue"]:
            if item.get("url") == url:
                item["status"] = status
                self.save()
                return True
        return False
    
    def clear(self):
        """Svuota completamente la coda"""
        self.data = {"queue": []}
        self.save()
    
    def get_pending(self) -> List[Dict]:
        """Restituisce solo gli elementi con status 'pending'"""
        return [item for item in self.data.get("queue", []) if item.get("status") == "pending"]
    
    def count(self) -> int:
        """Restituisce il numero di elementi nella coda"""
        return len(self.data.get("queue", []))
    
    def count_pending(self) -> int:
        """Restituisce il numero di elementi pending"""
        return len(self.get_pending())


# Istanza globale per facilità d'uso
queue = DownloadQueue()
