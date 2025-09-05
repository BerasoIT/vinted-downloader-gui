#!/usr/bin/env python3
"""
Wrapper per il downloader Vinted con organizzazione automatica dei file.
Esegue il downloader originale e poi organizza i file secondo la struttura richiesta.

Questo script mantiene completamente inalterato il core del downloader originale.
"""

import sys
import subprocess
import tempfile
import shutil
import json
import logging
import os
from pathlib import Path
import argparse
from vinted_organizer import organize_vinted_download
from download_tracker import tracker
from log_manager import get_logger, is_debug_mode

# Usa il nuovo sistema di logging centralizzato
logger = get_logger(__name__)


def run_vinted_downloader_with_organization(args_list, custom_closet_dir=None, skip_duplicates=True):
    """
    Esegue il downloader originale e poi organizza i file
    
    Args:
        args_list: Lista degli argomenti per il downloader
        custom_closet_dir: Directory closet personalizzata (opzionale)
        skip_duplicates: Se True, salta gli articoli già scaricati (default: True)
        
    Returns:
        Tuple (return_code, organization_result)
    """
    
    # Estrai l'URL dagli argomenti (primo argomento che non inizia con --)
    if not args_list:
        print("❌ Errore: Nessun URL fornito")
        return 1, {"success": False, "error": "Nessun URL fornito"}
    
    # Trova il primo argomento che sembra un URL (non inizia con -- e contiene vinted.it)
    item_url = None
    for arg in args_list:
        if not arg.startswith('--') and not arg.startswith('-') and 'vinted.' in arg:
            item_url = arg
            break
    
    if not item_url:
        print("❌ Errore: URL Vinted non trovato negli argomenti")
        return 1, {"success": False, "error": "URL Vinted non trovato"}
    
    logger.debug(f"🔍 DEBUG: URL estratto: {item_url}")
    
    # 🔍 CONTROLLO DUPLICATI: Verifica se l'articolo è già stato scaricato (solo se abilitato)
    if skip_duplicates and tracker.is_already_downloaded(item_url):
        logger.debug(f"⏭️  Articolo già scaricato, salto: {item_url}")
        print(f"⏭️  Articolo già scaricato, salto: {item_url}")
        print("✅ Download completato (saltato per duplicato)")
        return 0, {"success": True, "skipped": True, "reason": "Articolo già scaricato"}
    
    if skip_duplicates:
        # Log rimosso - viene già fatto dal tracker
        print(f"🆕 Nuovo articolo da scaricare: {item_url}")
    else:
        logger.debug(f"🔄 Forza riscaricamento articolo: {item_url}")
        print(f"🔄 Forza riscaricamento articolo: {item_url}")
    
    # Trova l'argomento -o per la directory di output
    output_dir = "."  # default
    
    try:
        if "-o" in args_list:
            o_index = args_list.index("-o")
            if o_index + 1 < len(args_list):
                output_dir = args_list[o_index + 1]
    except (ValueError, IndexError):
        pass
    
    output_path = Path(output_dir)
    
    # Se è specificato --save-in-dir, il downloader creerà una sottodirectory
    # Dobbiamo intercettare questo comportamento
    save_in_dir = "--save-in-dir" in args_list
    
    if save_in_dir:
        # In questo caso, il downloader creerà una sottodirectory
        # Useremo una directory temporanea e poi sposteremo tutto
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Modifica gli argomenti per usare la directory temporanea
            modified_args = args_list.copy()
            if "-o" in modified_args:
                o_index = modified_args.index("-o")
                modified_args[o_index + 1] = str(temp_path)
            else:
                # Aggiungi -o con directory temporanea
                modified_args.extend(["-o", str(temp_path)])
            
            # Esegui il downloader originale
            cmd = [sys.executable, "vinted_downloader.py"] + modified_args
            print(f"Eseguendo: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=False)
            
            if result.returncode == 0:
                # Trova la sottodirectory creata dal downloader
                subdirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if subdirs:
                    actual_download_dir = subdirs[0]  # Dovrebbe essere solo una
                    
                    # Organizza i file dalla directory temporanea
                    org_result = organize_vinted_download(actual_download_dir)
                    
                    if org_result["success"]:
                        # Sposta tutto nella directory finale
                        final_closet = output_path / "closet"
                        temp_closet = actual_download_dir / "closet"
                        
                        if temp_closet.exists():
                            # Assicurati che la directory di destinazione esista
                            final_closet.mkdir(parents=True, exist_ok=True)
                            
                            # Sposta il contenuto della cartella closet
                            for item in temp_closet.iterdir():
                                dest = final_closet / item.name
                                if dest.exists() and dest.is_dir():
                                    # Merge directories
                                    shutil.copytree(item, dest, dirs_exist_ok=True)
                                    shutil.rmtree(item)
                                else:
                                    shutil.move(str(item), str(dest))
                        
                        # Sposta anche i file JSON nella directory finale
                        for json_file in actual_download_dir.glob("*.json"):
                            shutil.move(str(json_file), str(output_path / json_file.name))
                        for summary_file in actual_download_dir.glob("item_summary"):
                            shutil.move(str(summary_file), str(output_path / summary_file.name))
                        
                        # 📝 TRACKING: Aggiungi record di download al tracking
                        add_tracking_record_from_org_result(item_url, org_result, output_path)
                    
                    return result.returncode, org_result
                else:
                    return result.returncode, {"success": False, "errors": ["Nessuna sottodirectory trovata"]}
            else:
                return result.returncode, {"success": False, "errors": ["Download fallito"]}
    
    else:
        # Caso normale: download diretto nella directory specificata
        # Esegui il downloader originale
        cmd = [sys.executable, "vinted_downloader.py"] + args_list
        print(f"Eseguendo: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode == 0:
            print(f"Download completato. Verifica file in {output_path}:")
            # Debug: elenca i file scaricati
            for file in output_path.glob("*.webp"):
                print(f"  File immagine: {file}")
            for file in output_path.glob("*.json"):
                print(f"  File JSON: {file}")
            
                        # Se c'è una directory closet personalizzata, dobbiamo gestirla diversamente
            if custom_closet_dir:
                # Prima organizziamo normalmente
                print(f"Directory closet personalizzata: {custom_closet_dir}")
                print(f"Directory closet predefinita: {output_path / 'closet'}")
                
                # Controlla se la directory personalizzata è la stessa di quella predefinita
                custom_closet = Path(custom_closet_dir)
                default_closet = output_path / "closet"
                
                if custom_closet.resolve() == default_closet.resolve():
                    print("Directory closet personalizzata è uguale a quella predefinita, uso organizzazione normale")
                    org_result = organize_vinted_download(str(output_path))
                    
                    # 📝 TRACKING: Aggiungi record di download al tracking
                    if org_result["success"]:
                        add_tracking_record_from_org_result(item_url, org_result, output_path)
                else:
                    print("Directory closet personalizzata diversa, organizzo e sposto")
                    org_result = organize_vinted_download(str(output_path))
                    
                    # Poi spostiamo la cartella closet creata nella posizione personalizzata
                    if org_result["success"] and default_closet.exists():
                        # Assicurati che la directory parent esista
                        custom_closet.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Se la directory di destinazione esiste già, merge del contenuto
                        if custom_closet.exists():
                            for user_dir in default_closet.iterdir():
                                if user_dir.is_dir():
                                    dest_user_dir = custom_closet / user_dir.name
                                    if dest_user_dir.exists():
                                        # Merge files nella directory utente
                                        for file in user_dir.iterdir():
                                            if file.is_file():
                                                dest_file = dest_user_dir / file.name
                                                if not dest_file.exists():
                                                    shutil.move(str(file), str(dest_file))
                                                # Se il file esiste già, lo saltiamo silenziosamente
                                    else:
                                        # Sposta l'intera directory utente
                                        shutil.move(str(user_dir), str(dest_user_dir))
                            # Rimuovi la directory closet vuota
                            shutil.rmtree(default_closet)
                        else:
                            # Sposta direttamente
                            shutil.move(str(default_closet), str(custom_closet))
                        
                        # Aggiorna il risultato con la nuova posizione
                        org_result["final_location"] = str(custom_closet)
                        
                        # 📝 TRACKING: Aggiungi record di download al tracking
                        add_tracking_record_from_org_result(item_url, org_result, output_path)
            else:
                # Organizzazione normale
                print("Avvio organizzazione normale...")
                org_result = organize_vinted_download(str(output_path))
                print(f"Risultato organizzazione: {org_result['success']}")
                
                if org_result['success']:
                    print(f"File organizzati: {len(org_result.get('moved_files', []))}")
                    print(f"Posizione finale: {org_result.get('final_location', 'N/A')}")
                    
                    # 📝 TRACKING: Aggiungi record di download al tracking
                    add_tracking_record_from_org_result(item_url, org_result, output_path)
                    
                else:
                    print(f"Errori organizzazione: {org_result.get('errors', [])}")
                
            return result.returncode, org_result
        else:
            return result.returncode, {"success": False, "errors": ["Download fallito"]}


def add_tracking_record_from_org_result(item_url, org_result, output_path):
    """
    Aggiunge un record di tracking basandosi sui risultati dell'organizzazione
    
    Args:
        item_url: URL dell'articolo scaricato
        org_result: Risultato dell'organizzazione dal vinted_organizer
        output_path: Path della directory di output
    """
    try:
        logger.debug(f"🔍 DEBUG: Inizio tracking per {item_url}")
        
        # Estrai informazioni dal file item.json
        item_json_path = Path(output_path) / "item.json"
        logger.debug(f"🔍 DEBUG: Cercando item.json in: {item_json_path}")
        
        if not item_json_path.exists():
            logger.warning(f"⚠️  Warning: item.json non trovato in {item_json_path}")
            print("⚠️  Warning: item.json non trovato, impossibile tracciare il download")
            return
            
        logger.debug(f"📖 DEBUG: Caricando dati da item.json")
        with open(item_json_path, 'r', encoding='utf-8') as f:
            item_data = json.load(f)
        
        logger.debug(f"📊 DEBUG: Dati item.json caricati: {len(str(item_data))} caratteri")
        
        # Estrai username usando la stessa logica dell'organizer
        username = ""
        try:
            if "user" in item_data and "login" in item_data["user"]:
                username = str(item_data["user"]["login"])
            elif "login" in item_data:
                username = str(item_data["login"])
            elif "seller" in item_data and "login" in item_data["seller"]:
                username = str(item_data["seller"]["login"])
        except (KeyError, TypeError) as e:
            logger.debug(f"🔍 DEBUG: Errore estrazione username: {e}")
            
        logger.debug(f"👤 DEBUG: Username estratto: '{username}'")
            
        # Estrai titolo
        title = ""
        try:
            if "title" in item_data:
                title = str(item_data["title"])
        except (KeyError, TypeError) as e:
            logger.debug(f"🔍 DEBUG: Errore estrazione title: {e}")
        
        logger.debug(f"📝 DEBUG: Titolo estratto: '{title}'")
        
        if not username or not title:
            logger.warning(f"⚠️  Warning: Informazioni incomplete per tracking (username='{username}', title='{title}')")
            print(f"⚠️  Warning: Informazioni incomplete per tracking (username='{username}', title='{title}')")
            return
            
        # Conta le immagini spostate
        img_count = len(org_result.get('moved_files', []))
        logger.debug(f"📊 DEBUG: Conteggio immagini: {img_count}")
        
        # Aggiungi il record al tracker
        logger.debug(f"💾 DEBUG: Aggiunta record al tracker...")
        success = tracker.add_download_record(username, title, item_url, img_count)
        
        if success:
            logger.debug(f"📝 Tracking aggiornato: {username} -> {title} ({img_count} immagini)")
            print(f"📝 Tracking aggiornato: {username} -> {title} ({img_count} immagini)")
        else:
            logger.warning("⚠️  Warning: Errore nel salvataggio del tracking")
            print("⚠️  Warning: Errore nel salvataggio del tracking")
            
    except Exception as e:
        logger.error(f"⚠️  Warning: Errore durante il tracking: {e}")
        print(f"⚠️  Warning: Errore durante il tracking: {e}")


def main():
    """Funzione principale"""
    # Passa tutti gli argomenti al wrapper (escluso il nome dello script)
    if len(sys.argv) < 2:
        print("Uso: python3 vinted_downloader_organized.py <URL> [opzioni]")
        print("Questo script esegue il downloader originale e organizza automaticamente i file.")
        print("\nOpzioni supportate:")
        print("  -o DIR              Directory di output")
        print("  --save-in-dir       Salva in sottodirectory")
        print("  --all              Scarica tutti gli articoli del venditore")
        print("  --seller           Scarica foto profilo venditore (se abilitato)")
        print("  --closet-dir DIR   Directory personalizzata per closet")
        print("  --force-download   Forza il download anche se l'articolo è già stato scaricato")
        print("  --debug            Abilita logging di debug dettagliato")
        sys.exit(1)
    
    args_list = sys.argv[1:]
    
    # Estrai --closet-dir se presente
    custom_closet_dir = None
    if "--closet-dir" in args_list:
        try:
            closet_index = args_list.index("--closet-dir")
            if closet_index + 1 < len(args_list):
                custom_closet_dir = args_list[closet_index + 1]
                # Rimuovi questi argomenti dalla lista per il downloader originale
                args_list = args_list[:closet_index] + args_list[closet_index + 2:]
        except (ValueError, IndexError):
            pass
    
    # Estrai --force-download se presente
    skip_duplicates = True
    if "--force-download" in args_list:
        skip_duplicates = False
        # Rimuovi questo argomento dalla lista per il downloader originale
        args_list = [arg for arg in args_list if arg != "--force-download"]
    
    # Rimuovi --debug se presente (non è per il downloader originale)
    args_list = [arg for arg in args_list if arg != "--debug"]
    
    print("=== Vinted Downloader con Organizzazione Automatica ===")
    print("Fase 1: Download dei file...")
    if custom_closet_dir:
        print(f"Directory closet personalizzata: {custom_closet_dir}")
    if not skip_duplicates:
        print("🔄 Modalità forza download (ignora controllo duplicati)")
    
    return_code, org_result = run_vinted_downloader_with_organization(args_list, custom_closet_dir, skip_duplicates)
    
    print(f"\nFase 2: Organizzazione dei file...")
    
    if return_code == 0:
        print("Download completato con successo!")
        
        if org_result["success"]:
            print("Organizzazione completata con successo!")
            print(f"File organizzati in: {org_result.get('final_location', 'N/A')}")
            
            if org_result.get("moved_files"):
                print(f"Immagini spostate: {len(org_result['moved_files'])}")
                
        else:
            print("Problemi durante l'organizzazione:")
            for error in org_result.get("errors", []):
                print(f"   - {error}")
    else:
        print(f"Download fallito (codice: {return_code})")
        
    return return_code


if __name__ == "__main__":
    sys.exit(main())
