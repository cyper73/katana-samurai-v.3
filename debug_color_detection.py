#!/usr/bin/env python3
"""
Script di debug per il rilevamento colori di Katana
Analizza ogni fase dell'algoritmo per identificare i colli di bottiglia
"""

import cv2
import numpy as np
import time
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_color_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def debug_color_analysis(image_path: str):
    """
    Debug completo del metodo _detect_by_color_analysis
    """
    logger.info(f"=== INIZIO DEBUG RILEVAMENTO COLORI ===")
    logger.info(f"Immagine: {image_path}")
    
    # Carica immagine
    start_time = time.time()
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Impossibile caricare l'immagine: {image_path}")
        return
    
    h, w = img.shape[:2]
    logger.info(f"Dimensioni immagine: {w}x{h} pixels")
    logger.info(f"Caricamento immagine: {time.time() - start_time:.3f}s")
    
    # FASE 1: Conversione spazi colore
    logger.info("\n=== FASE 1: CONVERSIONE SPAZI COLORE ===")
    start_time = time.time()
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    logger.info(f"Conversione spazi colore: {time.time() - start_time:.3f}s")
    
    # FASE 2: Setup analisi a blocchi
    logger.info("\n=== FASE 2: SETUP ANALISI A BLOCCHI ===")
    start_time = time.time()
    
    block_size = 200
    
    # Campionamento intelligente
    if w > 6000 or h > 6000:
        step_size = block_size * 2
        logger.info(f"Immagine molto grande, uso campionamento con step {step_size}")
    else:
        step_size = block_size
        logger.info(f"Immagine normale, uso step standard {step_size}")
    
    content_score_map = np.zeros((h, w), dtype=np.float32)
    total_blocks = ((h // step_size) + 1) * ((w // step_size) + 1)
    
    logger.info(f"Blocchi totali da processare: {total_blocks}")
    logger.info(f"Setup analisi: {time.time() - start_time:.3f}s")
    
    # FASE 3: Analisi a blocchi (la parte critica)
    logger.info("\n=== FASE 3: ANALISI A BLOCCHI (CRITICA) ===")
    start_time = time.time()
    processed_blocks = 0
    
    # Pre-calcola riferimenti
    white_ref = np.array([255, 255, 255], dtype=np.float32)
    
    # Timeout di sicurezza
    max_processing_time = 30
    timeout_reached = False
    
    for y in range(0, h, step_size):
        if timeout_reached:
            break
            
        for x in range(0, w, step_size):
            # Controllo timeout
            if time.time() - start_time > max_processing_time:
                logger.warning(f"TIMEOUT raggiunto dopo {max_processing_time}s!")
                timeout_reached = True
                break
            
            # Definisce limiti blocco
            y_end = min(y + block_size, h)
            x_end = min(x + block_size, w)
            
            block_h = y_end - y
            block_w = x_end - x
            
            # Salta blocchi troppo piccoli
            if block_h < 50 or block_w < 50:
                continue
            
            # Estrae blocchi
            block_bgr = img[y:y_end, x:x_end]
            block_hsv = hsv[y:y_end, x:x_end]
            block_gray = gray[y:y_end, x:x_end]
            
            # Analisi del blocco
            block_start = time.time()
            
            # Metodo 1: Deviazione dal bianco
            block_float = block_bgr.astype(np.float32)
            color_distances = np.linalg.norm(block_float - white_ref, axis=2)
            avg_color_distance = np.mean(color_distances)
            
            # Metodo 2: Saturazione
            avg_saturation = np.mean(block_hsv[:, :, 1])
            
            # Metodo 3: Varianza
            block_variance = np.var(block_gray)
            
            # Score combinato
            color_score = np.clip(avg_color_distance / 100.0, 0.0, 1.0)
            saturation_score = avg_saturation / 255.0
            variance_score = np.clip(block_variance / 10000.0, 0.0, 1.0)
            
            combined_score = (color_score * 0.4 + saturation_score * 0.3 + variance_score * 0.3)
            
            # Applica score
            content_score_map[y:y_end, x:x_end] = combined_score
            
            processed_blocks += 1
            block_time = time.time() - block_start
            
            # Log dettagliato ogni 100 blocchi
            if processed_blocks % 100 == 0:
                logger.debug(f"Blocco {processed_blocks}/{total_blocks} - Tempo: {block_time:.4f}s - Score: {combined_score:.3f}")
            
            # Controllo se un singolo blocco impiega troppo tempo
            if block_time > 0.1:  # Più di 100ms per blocco è sospetto
                logger.warning(f"Blocco lento rilevato! Posizione ({x},{y}) - Tempo: {block_time:.4f}s")
    
    analysis_time = time.time() - start_time
    logger.info(f"Analisi a blocchi completata: {processed_blocks}/{total_blocks} blocchi in {analysis_time:.3f}s")
    logger.info(f"Tempo medio per blocco: {analysis_time/max(processed_blocks,1):.4f}s")
    
    if timeout_reached:
        logger.error("ANALISI INTERROTTA PER TIMEOUT!")
        return
    
    # FASE 4: Operazioni morfologiche
    logger.info("\n=== FASE 4: OPERAZIONI MORFOLOGICHE ===")
    start_time = time.time()
    
    score_threshold = np.percentile(content_score_map, 75)
    content_mask = (content_score_map > score_threshold).astype(np.uint8) * 255
    
    logger.info(f"Creazione maschera: {time.time() - start_time:.3f}s")
    
    # Operazioni morfologiche ottimizzate
    morph_start = time.time()
    
    if w > 4000 or h > 4000:
        logger.info("Uso riduzione risoluzione per operazioni morfologiche")
        scale_factor = 0.25
        small_w, small_h = int(w * scale_factor), int(h * scale_factor)
        
        small_mask = cv2.resize(content_mask, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
        kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        small_mask = cv2.morphologyEx(small_mask, cv2.MORPH_CLOSE, kernel_morph)
        small_mask = cv2.morphologyEx(small_mask, cv2.MORPH_OPEN, kernel_morph)
        content_mask = cv2.resize(small_mask, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        logger.info("Uso operazioni morfologiche standard")
        kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        content_mask = cv2.morphologyEx(content_mask, cv2.MORPH_CLOSE, kernel_morph)
        content_mask = cv2.morphologyEx(content_mask, cv2.MORPH_OPEN, kernel_morph)
    
    logger.info(f"Operazioni morfologiche: {time.time() - morph_start:.3f}s")
    
    # FASE 5: Ricerca contorni
    logger.info("\n=== FASE 5: RICERCA CONTORNI ===")
    start_time = time.time()
    
    if w > 6000 or h > 6000:
        contours, _ = cv2.findContours(content_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        logger.info(f"Contorni trovati (approssimazione aggressiva): {len(contours)}")
    else:
        contours, _ = cv2.findContours(content_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        logger.info(f"Contorni trovati (metodo standard): {len(contours)}")
    
    logger.info(f"Ricerca contorni: {time.time() - start_time:.3f}s")
    
    # FASE 6: Filtraggio e risultato finale
    logger.info("\n=== FASE 6: FILTRAGGIO E RISULTATO ===")
    start_time = time.time()
    
    if contours:
        min_area = (w * h) * 0.005
        significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        logger.info(f"Contorni significativi: {len(significant_contours)}/{len(contours)}")
        
        if significant_contours:
            all_points = np.vstack(significant_contours)
            x, y, w_crop, h_crop = cv2.boundingRect(all_points)
            
            content_ratio = (w_crop * h_crop) / (w * h)
            logger.info(f"Bounding box: x={x}, y={y}, w={w_crop}, h={h_crop}")
            logger.info(f"Content ratio: {content_ratio:.3f}")
        else:
            logger.warning("Nessun contorno significativo trovato")
    else:
        logger.warning("Nessun contorno trovato")
    
    logger.info(f"Filtraggio finale: {time.time() - start_time:.3f}s")
    logger.info("\n=== DEBUG COMPLETATO ===")

def main():
    if len(sys.argv) != 2:
        print("Uso: python debug_color_detection.py <path_to_image>")
        print("Esempio: python debug_color_detection.py output_images/documentoaous11-08-2025-080123_page_1_img_1.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        logger.error(f"File non trovato: {image_path}")
        sys.exit(1)
    
    debug_color_analysis(image_path)

if __name__ == "__main__":
    main()