#!/usr/bin/env python3
"""
Script per fare il merge intelligente dei file downloaded_items
"""

import json
from pathlib import Path

def load_json_file(filepath):
    """Carica un file JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore caricamento {filepath}: {e}")
        return {}

def merge_downloaded_items(main_file, temp_file, output_file):
    """
    Merge intelligente dei downloaded_items
    
    Args:
        main_file: File principale (più grande)
        temp_file: File da mergere (più piccolo)
        output_file: File di output
    """
    print("🔄 Inizio merge intelligente...")
    
    # Carica entrambi i file
    main_data = load_json_file(main_file)
    temp_data = load_json_file(temp_file)
    
    print(f"📊 File principale: {len(main_data)} utenti")
    print(f"📊 File da mergere: {len(temp_data)} utenti")
    
    # Statistiche
    users_added = 0
    items_added = 0
    items_skipped = 0
    
    # Merge per ogni utente nel file temp
    for username, user_items in temp_data.items():
        if username not in main_data:
            # Utente completamente nuovo
            main_data[username] = user_items
            users_added += 1
            items_added += len(user_items)
            print(f"👤 Nuovo utente aggiunto: {username} ({len(user_items)} articoli)")
        else:
            # Utente esiste, controlla singoli articoli
            for item_key, item_data in user_items.items():
                if item_key not in main_data[username]:
                    # Articolo non presente per questo utente
                    main_data[username][item_key] = item_data
                    items_added += 1
                    print(f"📝 Nuovo articolo per {username}: {item_key} - {item_data.get('title', 'N/A')}")
                else:
                    # Articolo già presente, salta
                    items_skipped += 1
    
    # Salva il risultato
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Merge salvato in: {output_file}")
    except Exception as e:
        print(f"❌ Errore salvataggio: {e}")
        return False
    
    # Riepilogo finale
    print("\n" + "="*50)
    print("📊 RIEPILOGO MERGE:")
    print(f"👤 Nuovi utenti aggiunti: {users_added}")
    print(f"📝 Nuovi articoli aggiunti: {items_added}")
    print(f"⏭️ Articoli già presenti (saltati): {items_skipped}")
    print(f"👥 Totale utenti finali: {len(main_data)}")
    
    total_items = sum(len(user_items) for user_items in main_data.values())
    print(f"📚 Totale articoli finali: {total_items}")
    print("="*50)
    
    return True

if __name__ == "__main__":
    data_dir = Path("data")
    
    main_file = data_dir / "downloaded_items.json"
    temp_file = data_dir / "downloaded_items_temp.json"
    output_file = data_dir / "downloaded_items_merged.json"
    
    # Backup del file principale
    backup_file = data_dir / f"downloaded_items_pre_merge_{int(__import__('time').time())}.json"
    import shutil
    shutil.copy2(main_file, backup_file)
    print(f"🛡️ Backup creato: {backup_file.name}")
    
    # Esegui merge
    if merge_downloaded_items(main_file, temp_file, output_file):
        print("✅ Merge completato con successo!")
        print(f"📁 Risultato in: {output_file}")
        print(f"🛡️ Backup in: {backup_file}")
    else:
        print("❌ Merge fallito!")
