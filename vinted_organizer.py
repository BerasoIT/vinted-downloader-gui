"""
Modulo per l'organizzazione avanzata dei file scaricati da Vinted.
Questo modulo estende le funzionalità del downloader originale senza modificarlo.

Funzionalità:
- Organizza le immagini in cartelle per utente
- Rinomina le immagini secondo il titolo dell'articolo
- Mantiene la struttura "closet/username/images"
"""

import json
import re
import shutil
import logging
import os
from pathlib import Path
from typing import Dict, Any, List
from log_manager import get_logger

# Usa il nuovo sistema di logging centralizzato
logger = get_logger(__name__)


class VintedFileOrganizer:
    """Organizzatore di file per il downloader Vinted"""
    
    def __init__(self, base_output_dir: Path):
        self.base_output_dir = Path(base_output_dir)
        self.closet_dir = self.base_output_dir / "closet"
        
    def organize_downloaded_files(self) -> Dict[str, Any]:
        """
        Organizza i file scaricati secondo la struttura richiesta.
        
        Returns:
            Dict con informazioni sull'organizzazione effettuata
        """
        result = {
            "success": False,
            "moved_files": [],
            "errors": [],
            "user_folder": None,
            "final_location": None
        }
        
        try:
            logger.debug("🚀 Avvio organizzazione file scaricati")
            
            # Legge il file item.json per ottenere le informazioni
            item_json_path = self.base_output_dir / "item.json"
            if not item_json_path.exists():
                result["errors"].append("File item.json non trovato")
                return result
                
            with open(item_json_path, 'r', encoding='utf-8') as f:
                item_data = json.load(f)
            
            # Estrae username e title
            username = self._extract_username(item_data)
            title = self._extract_title(item_data)
            
            if not username:
                result["errors"].append("Username non trovato nel file JSON")
                return result
                
            if not title:
                result["errors"].append("Titolo non trovato nel file JSON")
                return result
            
            # Normalizza username e title
            normalized_username = self._normalize_filename(username)
            normalized_title = self._normalize_filename(title)
            
            logger.debug(f"👤 Username: '{username}' → '{normalized_username}'")
            logger.debug(f"📝 Titolo: '{title}' → '{normalized_title}'")
            
            # Crea la struttura di cartelle
            user_folder = self._create_user_folder(normalized_username)
            result["user_folder"] = str(user_folder)
            
            logger.debug(f"📁 Cartella utente creata: {user_folder}")
            
            # Trova e organizza le immagini
            photo_files = self._find_photo_files()
            if not photo_files:
                result["errors"].append("Nessuna immagine trovata da organizzare")
                return result
            
            # Sposta e rinomina le immagini
            moved_files = self._move_and_rename_photos(
                photo_files, user_folder, normalized_title
            )
            result["moved_files"] = moved_files
            result["final_location"] = str(user_folder)
            result["success"] = True
            
        except Exception as e:
            logger.error(f"❌ Errore durante l'organizzazione: {str(e)}")
            result["errors"].append(f"Errore durante l'organizzazione: {str(e)}")
            
        return result
    
    def _extract_username(self, item_data: Dict[str, Any]) -> str:
        """Estrae lo username dal JSON dell'articolo"""
        try:
            # Prova con user.login
            if "user" in item_data and "login" in item_data["user"]:
                return str(item_data["user"]["login"])
            
            # Fallback per altre strutture possibili
            if "login" in item_data:
                return str(item_data["login"])
                
            # Altro fallback con seller info
            if "seller" in item_data and "login" in item_data["seller"]:
                return str(item_data["seller"]["login"])
                
        except (KeyError, TypeError):
            pass
            
        return ""
    
    def _extract_title(self, item_data: Dict[str, Any]) -> str:
        """Estrae il titolo dal JSON dell'articolo"""
        try:
            if "title" in item_data:
                return str(item_data["title"])
        except (KeyError, TypeError):
            pass
            
        return ""
    
    def _normalize_filename(self, filename: str) -> str:
        """
        Normalizza un nome file rimuovendo caratteri speciali e sostituendo spazi con _
        
        Args:
            filename: Nome da normalizzare
            
        Returns:
            Nome file normalizzato
        """
        # Rimuove caratteri speciali mantenendo solo alfanumerici, spazi, trattini e underscore
        normalized = re.sub(r'[^\w\s\-_]', '', filename)
        
        # Sostituisce spazi multipli con spazio singolo
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Sostituisce spazi con underscore
        normalized = normalized.replace(' ', '_')
        
        # Rimuove underscore multipli
        normalized = re.sub(r'_+', '_', normalized)
        
        # Rimuove underscore all'inizio e alla fine
        normalized = normalized.strip('_')
        
        # Limita la lunghezza per evitare problemi con i filesystem
        if len(normalized) > 100:
            normalized = normalized[:100].rstrip('_')
            
        return normalized or "unknown"
    
    def _create_user_folder(self, normalized_username: str) -> Path:
        """
        Crea la cartella dell'utente se non esiste
        
        Args:
            normalized_username: Username normalizzato
            
        Returns:
            Path della cartella utente
        """
        # Crea cartella closet se non esiste
        self.closet_dir.mkdir(exist_ok=True)
        
        # Crea cartella utente se non esiste
        user_folder = self.closet_dir / normalized_username
        user_folder.mkdir(exist_ok=True)
        
        return user_folder
    
    def _find_photo_files(self) -> List[Path]:
        """
        Trova tutti i file di immagini nella directory base
        
        Returns:
            Lista dei file immagine trovati
        """
        photo_files = []
        
        # Pattern per trovare le foto (photo_X.webp, photo_X_itemId.webp, etc.)
        patterns = [
            "photo_*.webp",
            "photo_*.jpg", 
            "photo_*.jpeg",
            "photo_*.png"
        ]
        
        for pattern in patterns:
            photo_files.extend(self.base_output_dir.glob(pattern))
            
        # Ordina per nome per mantenere l'ordine sequenziale
        return sorted(photo_files)
    
    def _move_and_rename_photos(
        self, 
        photo_files: List[Path], 
        user_folder: Path, 
        normalized_title: str
    ) -> List[Dict[str, str]]:
        """
        Sposta e rinomina le foto nella cartella dell'utente
        
        Args:
            photo_files: Lista dei file foto da spostare
            user_folder: Cartella di destinazione
            normalized_title: Titolo normalizzato per il naming
            
        Returns:
            Lista dei file spostati con informazioni old->new path
        """
        moved_files = []
        
        logger.debug(f"📂 Inizio organizzazione di {len(photo_files)} immagini in: {user_folder}")
        
        for i, photo_file in enumerate(photo_files):
            try:
                # Estrae l'estensione originale
                extension = photo_file.suffix
                
                # Crea il nuovo nome: title_001.ext, title_002.ext, etc.
                new_name = f"{normalized_title}_{i+1:03d}{extension}"
                new_path = user_folder / new_name
                
                # Se il file di destinazione esiste già, aggiungi un suffisso
                counter = 1
                original_new_path = new_path
                while new_path.exists():
                    name_without_ext = original_new_path.stem
                    new_name = f"{name_without_ext}_dup{counter}{extension}"
                    new_path = user_folder / new_name
                    counter += 1
                
                # Sposta il file
                shutil.move(str(photo_file), str(new_path))
                
                # Log dettagliato per ogni immagine spostata
                logger.debug(f"🖼️  Immagine {i+1:03d}: '{photo_file.name}' → '{new_name}' in '{user_folder.name}/'")
                
                moved_files.append({
                    "from": str(photo_file),
                    "to": str(new_path),
                    "new_name": new_name
                })
                
            except Exception as e:
                # Log degli errori
                logger.error(f"❌ Errore spostando '{photo_file.name}': {str(e)}")
                
                moved_files.append({
                    "from": str(photo_file),
                    "to": f"ERROR: {str(e)}",
                    "new_name": "ERROR"
                })
        
        logger.debug(f"✅ Organizzazione completata: {len([f for f in moved_files if 'ERROR' not in f['to']])}/{len(photo_files)} immagini spostate con successo")
                
        return moved_files
    
    def cleanup_empty_dirs(self):
        """Rimuove directory vuote se necessario"""
        try:
            # Non rimuoviamo directory in questo caso, ma la funzione è disponibile
            pass
        except Exception:
            pass


def organize_vinted_download(output_dir: str | Path) -> Dict[str, Any]:
    """
    Funzione principale per organizzare un download di Vinted
    
    Args:
        output_dir: Directory dove sono stati scaricati i file
        
    Returns:
        Dizionario con il risultato dell'organizzazione
    """
    organizer = VintedFileOrganizer(Path(output_dir))
    return organizer.organize_downloaded_files()


# Funzione di utilità per testare l'organizzazione
def test_organization(output_dir: str = "."):
    """
    Testa l'organizzazione dei file in una directory
    
    Args:
        output_dir: Directory da organizzare (default: directory corrente)
    """
    result = organize_vinted_download(output_dir)
    
    print("=== Risultato Organizzazione ===")
    print(f"Successo: {result['success']}")
    
    if result["user_folder"]:
        print(f"Cartella utente: {result['user_folder']}")
        
    if result["final_location"]:
        print(f"Posizione finale: {result['final_location']}")
        
    if result["moved_files"]:
        print(f"\nFile spostati ({len(result['moved_files'])}):")
        for file_info in result["moved_files"]:
            print(f"  {file_info['from']} -> {file_info['to']}")
            
    if result["errors"]:
        print(f"\nErrori ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  - {error}")


if __name__ == "__main__":
    # Test della funzionalità
    import sys
    
    if len(sys.argv) > 1:
        test_organization(sys.argv[1])
    else:
        test_organization()
