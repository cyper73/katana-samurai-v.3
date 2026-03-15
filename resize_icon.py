#!/usr/bin/env python3
"""
Script per ridimensionare itto.jpg e creare un'icona per l'header
"""

from PIL import Image
import os

def resize_image_for_header(input_path, output_path, size=(64, 64)):
    """
    Ridimensiona un'immagine per creare un'icona per l'header
    
    Args:
        input_path (str): Percorso dell'immagine originale
        output_path (str): Percorso dell'immagine ridimensionata
        size (tuple): Dimensioni target (larghezza, altezza)
    """
    try:
        # Apri l'immagine originale
        with Image.open(input_path) as img:
            print(f"Dimensioni originali: {img.size}")
            print(f"Formato: {img.format}")
            print(f"Modalità: {img.mode}")
            
            # Mantieni le proporzioni
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Crea una nuova immagine con sfondo trasparente se necessario
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Salva l'icona ridimensionata
            img.save(output_path, 'PNG', optimize=True)
            print(f"Icona salvata: {output_path}")
            print(f"Nuove dimensioni: {img.size}")
            
    except Exception as e:
        print(f"Errore durante il ridimensionamento: {e}")

def main():
    input_file = "itto.jpg"
    output_file = "itto_icon.png"
    
    if not os.path.exists(input_file):
        print(f"File {input_file} non trovato!")
        return
    
    # Crea diverse dimensioni per l'icona
    sizes = [
        (32, 32, "itto_icon_32.png"),
        (48, 48, "itto_icon_48.png"),
        (64, 64, "itto_icon_64.png"),
        (128, 128, "itto_icon_128.png")
    ]
    
    for width, height, filename in sizes:
        print(f"\nCreando icona {width}x{height}...")
        resize_image_for_header(input_file, filename, (width, height))

if __name__ == "__main__":
    main()