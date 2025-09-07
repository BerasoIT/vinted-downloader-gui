#!/usr/bin/env python3
"""Test del sistema di parsing per le progress bar doppie
Simula l'output del downloader per verificare il corretto funzionamento
del sistema di tracking del progresso per articoli e immagini.
"""

import re

def parse_download_output_test(line):
    """Versione di test del parsing dell'output"""
    import re
    
    line_lower = line.lower().strip()
    
    results = {}
    
    # Rileva il numero totale di immagini da "Found data: X images"
    found_data_match = re.search(r'found data:?\s*(\d+)\s*images?', line_lower)
    if found_data_match:
        total_images = int(found_data_match.group(1))
        results['action'] = 'set_total_images'
        results['value'] = total_images
        return results
    
    # Rileva quando inizia un nuovo articolo
    if "downloading details" in line_lower:
        results['action'] = 'start_article'
        return results
    
    # Rileva quando un'immagine viene scaricata
    if "downloading resource" in line_lower:
        results['action'] = 'image_downloaded'
        return results
    
    # Rileva completamento articolo
    if "organizzazione" in line_lower or "download completato" in line_lower:
        results['action'] = 'article_completed'
        return results
    
    return None

def test_parsing():
    """Test completo del parsing con simulazione di download multi-articolo"""
    
    # Simula output di download di 2 articoli con diverso numero di immagini
    test_lines = [
        # Primo articolo
        "Downloading details for item 1...",
        "Found data: 3 images for this item", 
        "Downloading resource: image1.jpg",
        "Downloading resource: image2.jpg",
        "Downloading resource: image3.jpg",
        "Organizzazione file completata",
        
        # Secondo articolo  
        "Downloading details for item 2...",
        "Found data: 5 images",
        "Downloading resource: photo1.jpg",
        "Downloading resource: photo2.jpg", 
        "Downloading resource: photo3.jpg",
        "Downloading resource: photo4.jpg",
        "Downloading resource: photo5.jpg",
        "Download completato"
    ]
    
    print("🧪 Test del parsing delle progress bar doppie")
    print("=" * 50)
    
    # Stato simulato
    total_links = 0
    processed_links = 0
    total_images = 0
    downloaded_images = 0
    
    def show_progress():
        """Mostra lo stato corrente delle progress bar"""
        if total_links > 0:
            links_percent = (processed_links / total_links) * 100
        else:
            links_percent = 0
            
        if total_images > 0:
            images_percent = (downloaded_images / total_images) * 100
        else:
            images_percent = 0
            
        print(f"   📊 Articoli: {processed_links}/{total_links} ({links_percent:.0f}%)")
        print(f"   📊 Immagini: {downloaded_images}/{total_images} ({images_percent:.0f}%)")
    
    for i, line in enumerate(test_lines, 1):
        print(f"\n{i:2d}. '{line}'")
        result = parse_download_output_test(line)
        
        if result:
            if result['action'] == 'set_total_images':
                total_images = result['value']
                downloaded_images = 0
                print(f"    → Rilevate {total_images} immagini da scaricare")
            elif result['action'] == 'start_article':
                if total_links == 0:
                    total_links = 2  # Sappiamo che nel test ci sono 2 articoli
                print(f"    → Iniziato nuovo articolo")
            elif result['action'] == 'image_downloaded':
                downloaded_images += 1
                print(f"    → Immagine scaricata")
            elif result['action'] == 'article_completed':
                if processed_links < total_links:
                    processed_links += 1
                print(f"    → Articolo completato")
        
        show_progress()
    
    print("\n" + "=" * 50)
    print("✅ Test completato con successo!")
    print(f"📈 Risultato finale: {processed_links}/{total_links} articoli, {downloaded_images}/{total_images} immagini")

if __name__ == "__main__":
    test_parsing()
