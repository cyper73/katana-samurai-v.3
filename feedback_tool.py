#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strumento interattivo per raccogliere feedback dell'utente
e migliorare il sistema di apprendimento di Katana
"""

import sys
import os
from katana import KatanaProcessor

def show_feedback_options():
    """Mostra le opzioni di feedback disponibili"""
    print("\nOpzioni di feedback disponibili:")
    print("1. perfect - Risultato perfetto")
    print("2. excessive_cropping - Taglio eccessivo (parti importanti tagliate)")
    print("3. no_change - Nessun cambiamento rispetto all'originale")
    print("4. light_cropping - Leggero taglio, ma accettabile")
    print("5. insufficient_cropping - Taglio insufficiente (troppi margini bianchi)")
    print("6. insufficient_zoom - Zoom insufficiente (immagine troppo piccola)")
    print("7. excessive_zoom - Zoom eccessivo (immagine troppo ingrandita)")
    print("8. skip - Salta questa immagine")
    print("9. quit - Termina la sessione di feedback")

def get_feedback_input():
    """Ottiene il feedback dall'utente"""
    while True:
        choice = input("\nInserisci il numero dell'opzione (1-9): ").strip()
        
        feedback_map = {
            '1': 'perfect',
            '2': 'excessive_cropping', 
            '3': 'no_change',
            '4': 'light_cropping',
            '5': 'insufficient_cropping',
            '6': 'insufficient_zoom',
            '7': 'excessive_zoom',
            '8': 'skip',
            '9': 'quit'
        }
        
        if choice in feedback_map:
            return feedback_map[choice]
        else:
            print("Opzione non valida. Riprova.")

def list_available_pdfs():
    """Elenca i PDF disponibili nella directory corrente"""
    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    if not pdf_files:
        print("Nessun file PDF trovato nella directory corrente.")
        return None
    
    print("\nPDF disponibili:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"{i}. {pdf}")
    
    while True:
        try:
            choice = int(input(f"\nSeleziona un PDF (1-{len(pdf_files)}): "))
            if 1 <= choice <= len(pdf_files):
                return pdf_files[choice - 1]
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Inserisci un numero valido.")

def list_output_images(pdf_name):
    """Elenca le immagini di output per un PDF specifico"""
    output_dir = "output_images"
    if not os.path.exists(output_dir):
        print(f"Directory {output_dir} non trovata.")
        return []
    
    # Cerca immagini ritagliate per questo PDF
    base_name = pdf_name.replace('.pdf', '')
    cropped_images = []
    
    for file in os.listdir(output_dir):
        if file.startswith(base_name) and file.endswith('_cropped.jpg'):
            cropped_images.append(file)
    
    cropped_images.sort()
    return cropped_images

def main():
    print("=== STRUMENTO DI FEEDBACK KATANA ===")
    print("Questo strumento ti permette di fornire feedback sui risultati")
    print("del ritaglio per migliorare le prestazioni future.")
    
    # Inizializza il processore con modalità apprendimento
    processor = KatanaProcessor(learning_mode=True)
    
    # Seleziona PDF
    pdf_name = list_available_pdfs()
    if not pdf_name:
        return
    
    print(f"\nPDF selezionato: {pdf_name}")
    
    # Trova le immagini di output
    images = list_output_images(pdf_name)
    if not images:
        print(f"Nessuna immagine ritagliata trovata per {pdf_name}")
        print("Assicurati di aver elaborato il PDF prima di fornire feedback.")
        return
    
    print(f"\nTrovate {len(images)} immagini ritagliate.")
    
    # Mostra parametri attuali
    print("\nParametri attuali:")
    for param, value in processor.adaptive_params.items():
        print(f"  {param}: {value}")
    
    # Raccoglie feedback per ogni immagine
    feedback_count = 0
    
    for i, image_file in enumerate(images, 1):
        print(f"\n{'='*50}")
        print(f"Immagine {i}/{len(images)}: {image_file}")
        print(f"Percorso completo: output_images\\{image_file}")
        
        # Estrai numero pagina dal nome file
        try:
            page_num = int(image_file.split('_page_')[1].split('_')[0])
        except:
            page_num = i
        
        print(f"Pagina {page_num}")
        
        show_feedback_options()
        feedback = get_feedback_input()
        
        if feedback == 'quit':
            break
        elif feedback == 'skip':
            continue
        else:
            # Salva il feedback
            processor.save_feedback(
                pdf_name=pdf_name,
                page_num=page_num,
                feedback=feedback
            )
            feedback_count += 1
            print(f"Feedback '{feedback}' salvato per pagina {page_num}")
    
    # Mostra parametri aggiornati
    if feedback_count > 0:
        print(f"\n{'='*50}")
        print(f"Feedback completato! Raccolti {feedback_count} feedback.")
        print("\nParametri aggiornati:")
        for param, value in processor.adaptive_params.items():
            print(f"  {param}: {value}")
        print("\nI nuovi parametri verranno utilizzati per le prossime elaborazioni.")
    else:
        print("\nNessun feedback raccolto.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrotto dall'utente.")
    except Exception as e:
        print(f"\nErrore: {e}")