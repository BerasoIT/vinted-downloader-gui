#!/usr/bin/env python3
"""
Download Tracker per Vinted Downloader
Gestisce il tracciamento degli articoli già scaricati per evitare duplicati.

Struttura JSON:
{
  "username_venditore1": {
    "articolo_1": {
      "url": "https://www.vinted.it/items/123456",
      "title": "Maglietta vintage", 
      "img_count": 3
    }
  }
}
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import re
from log_manager import get_logger

# Usa il nuovo sistema di logging centralizzato
logger = get_logger(__name__)

# File di tracciamento
TRACKING_FILE = "downloaded_items.json"

class DownloadTracker:
    """Gestisce il tracciamento degli articoli già scaricati"""
    
    def __init__(self, tracking_file: str = TRACKING_FILE):
        self.tracking_file = Path(tracking_file)
        self._data: Dict = {}
        self.load_tracking_data()
    
    def load_tracking_data(self) -> Dict:
        """Carica i dati di tracciamento dal file JSON"""
        try:
            if self.tracking_file.exists():
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.debug(f"📖 Caricati dati tracking da {self.tracking_file}")
            else:
                self._data = {}
                logger.debug(f"📝 File tracking non esistente, creata struttura vuota")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"⚠️ Errore caricamento tracking file: {e}, uso struttura vuota")
            self._data = {}
        
        return self._data
    
    def save_tracking_data(self) -> bool:
        """Salva i dati di tracciamento nel file JSON"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Salvati dati tracking in {self.tracking_file}")
            return True
        except IOError as e:
            logger.error(f"❌ Errore salvataggio tracking file: {e}")
            return False
    
    def extract_username_from_url(self, url: str) -> Optional[str]:
        """Estrae lo username del venditore dall'URL Vinted
        
        Esempi URL:
        - https://www.vinted.it/items/123456-titolo-articolo
        - https://www.vinted.it/member/12345-username
        """
        # Per ora restituiamo None, verrà estratto dal contenuto scaricato
        # Questo richiederà di essere chiamato dopo che abbiamo le info dell'articolo
        return None
    
    def extract_item_id_from_url(self, url: str) -> Optional[str]:
        """Estrae l'ID dell'articolo dall'URL"""
        match = re.search(r'/items/(\d+)', url)
        return match.group(1) if match else None
    
    def is_already_downloaded(self, url: str) -> bool:
        """Controlla se un articolo è già stato scaricato basandosi sull'URL"""
        for username, articles in self._data.items():
            for article_key, article_data in articles.items():
                if article_data.get('url') == url:
                    logger.debug(f"🔍 Articolo già scaricato: {url} (utente: {username})")
                    return True
        
        logger.debug(f"🆕 Articolo nuovo: {url}")
        return False
    
    def add_download_record(self, username: str, title: str, url: str, img_count: int) -> bool:
        """Aggiunge un record di download al tracking
        
        Args:
            username: Nome utente del venditore
            title: Titolo dell'articolo
            url: URL dell'articolo
            img_count: Numero di immagini scaricate
        """
        try:
            # Crea la struttura per l'utente se non esiste
            if username not in self._data:
                self._data[username] = {}
                logger.debug(f"👤 Creato nuovo utente nel tracking: {username}")
            
            # Genera una chiave unica per l'articolo (usa ID dall'URL se disponibile)
            item_id = self.extract_item_id_from_url(url)
            if item_id:
                article_key = f"item_{item_id}"
            else:
                # Fallback: usa un contatore
                article_key = f"article_{len(self._data[username]) + 1}"
            
            # Aggiunge il record
            self._data[username][article_key] = {
                "url": url,
                "title": title,
                "img_count": img_count
            }
            
            logger.debug(f"📝 Aggiunto record: {username} -> {article_key} ({title}) - {img_count} immagini")
            
            # Salva immediatamente
            return self.save_tracking_data()
            
        except Exception as e:
            logger.error(f"❌ Errore aggiunta record tracking: {e}")
            return False
    
    def get_user_stats(self, username: str) -> Dict:
        """Restituisce statistiche per un utente"""
        if username not in self._data:
            return {"articles_count": 0, "total_images": 0}
        
        user_data = self._data[username]
        total_images = sum(article.get('img_count', 0) for article in user_data.values())
        
        return {
            "articles_count": len(user_data),
            "total_images": total_images
        }
    
    def get_global_stats(self) -> Dict:
        """Restituisce statistiche globali"""
        total_users = len(self._data)
        total_articles = sum(len(user_data) for user_data in self._data.values())
        total_images = sum(
            sum(article.get('img_count', 0) for article in user_data.values())
            for user_data in self._data.values()
        )
        
        return {
            "total_users": total_users,
            "total_articles": total_articles,
            "total_images": total_images
        }
    
    def list_downloaded_items(self, username: Optional[str] = None) -> Dict:
        """Lista gli articoli scaricati, opzionalmente filtrati per utente"""
        if username:
            return self._data.get(username, {})
        return self._data


# Istanza globale del tracker
tracker = DownloadTracker()

# Funzioni di convenienza per compatibilità
def is_already_downloaded(url: str) -> bool:
    """Wrapper di convenienza per il controllo duplicati"""
    return tracker.is_already_downloaded(url)

def add_download_record(username: str, title: str, url: str, img_count: int) -> bool:
    """Wrapper di convenienza per aggiungere record"""
    return tracker.add_download_record(username, title, url, img_count)

def get_stats() -> Dict:
    """Wrapper di convenienza per statistiche globali"""
    return tracker.get_global_stats()
