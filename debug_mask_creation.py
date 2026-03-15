#!/usr/bin/env python3
"""
Script di debug specifico per la creazione della maschera
Analizza il collo di bottiglia nella FASE 4
"""

import cv2
import numpy as np
import time
import logging
import sys
from pathlib import Path
import psutil
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_mask_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def monitor_memory():
    """Monitora l'uso della memoria"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # MB

def debug_mask_creation_bottleneck(image_path: str):
    """
    Debug specifico per il problema della creazione maschera
    """
    logger.info(f"=== DEBUG CREAZIONE MASCHERA ===")
    logger.info(f"Immagine: {image_path}")
    logger.info(f"Memoria iniziale: {monitor_memory():.1f} MB")
    
    # Carica immagine
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Impossibile caricare l'immagine: {image_path}")
        return
    
    h, w = img.shape[:2]
    logger.info(f"Dimensioni immagine: {w}x{h} pixels")
    logger.info(f"Memoria dopo caricamento: {monitor_memory():.1f} MB")
    
    # Simula la creazione della content_score_map
    logger.info("\n=== CREAZIONE CONTENT_SCORE_MAP ===")
    start_time = time.time()
    
    # Crea una mappa di score simulata (come farebbe l'algoritmo reale)
    content_score_map = np.random.random((h, w)).astype(np.float32) * 0.8
    
    creation_time = time.time() - start_time
    logger.info(f"Creazione content_score_map: {creation_time:.3f}s")
    logger.info(f"Memoria dopo content_score_map: {monitor_memory():.1f} MB")
    
    # PROBLEMA IDENTIFICATO: np.percentile su array grandi
    logger.info("\n=== ANALISI np.percentile (SOSPETTO COLLO DI BOTTIGLIA) ===")
    
    # Test diversi metodi per calcolare il threshold
    methods = [
        ("np.percentile standard", lambda x: np.percentile(x, 75)),
        ("np.percentile con interpolazione nearest", lambda x: np.percentile(x, 75, interpolation='nearest')),
        ("np.quantile", lambda x: np.quantile(x, 0.75)),
        ("Metodo campionamento", lambda x: np.percentile(x.flatten()[::100], 75)),
        ("Metodo histogram", lambda x: calculate_threshold_histogram(x, 0.75))
    ]
    
    for method_name, method_func in methods:
        logger.info(f"\nTestando: {method_name}")
        start_time = time.time()
        
        try:
            threshold = method_func(content_score_map)
            elapsed = time.time() - start_time
            logger.info(f"  Risultato: {threshold:.6f}")
            logger.info(f"  Tempo: {elapsed:.3f}s")
            logger.info(f"  Memoria: {monitor_memory():.1f} MB")
            
            if elapsed > 0.5:
                logger.warning(f"  ⚠️  METODO LENTO RILEVATO!")
            elif elapsed < 0.1:
                logger.info(f"  ✅ METODO VELOCE")
                
        except Exception as e:
            logger.error(f"  ❌ ERRORE: {e}")
    
    # Test creazione maschera con metodo ottimizzato
    logger.info("\n=== TEST CREAZIONE MASCHERA OTTIMIZZATA ===")
    start_time = time.time()
    
    # Usa il metodo più veloce trovato
    threshold_fast = calculate_threshold_histogram(content_score_map, 0.75)
    content_mask = (content_score_map > threshold_fast).astype(np.uint8) * 255
    
    mask_time = time.time() - start_time
    logger.info(f"Creazione maschera ottimizzata: {mask_time:.3f}s")
    logger.info(f"Memoria finale: {monitor_memory():.1f} MB")
    
    # Analisi della maschera risultante
    white_pixels = np.sum(content_mask == 255)
    total_pixels = h * w
    content_ratio = white_pixels / total_pixels
    
    logger.info(f"\n=== RISULTATI MASCHERA ===")
    logger.info(f"Pixel bianchi: {white_pixels:,}")
    logger.info(f"Pixel totali: {total_pixels:,}")
    logger.info(f"Ratio contenuto: {content_ratio:.3f}")
    
    # Salva maschera per ispezione visiva
    debug_mask_path = "debug_mask_output.jpg"
    cv2.imwrite(debug_mask_path, content_mask)
    logger.info(f"Maschera salvata in: {debug_mask_path}")

def calculate_threshold_histogram(score_map, percentile):
    """
    Calcola threshold usando histogram (metodo veloce)
    """
    # Usa histogram per calcolo veloce del percentile
    hist, bin_edges = np.histogram(score_map.flatten(), bins=1000, range=(0, 1))
    
    # Calcola CDF
    cdf = np.cumsum(hist) / np.sum(hist)
    
    # Trova il bin corrispondente al percentile
    target_idx = np.searchsorted(cdf, percentile)
    
    if target_idx < len(bin_edges) - 1:
        return bin_edges[target_idx]
    else:
        return bin_edges[-1]

def test_array_operations(h, w):
    """
    Test specifici per operazioni su array grandi
    """
    logger.info(f"\n=== TEST OPERAZIONI ARRAY {w}x{h} ===")
    
    # Test creazione array
    start_time = time.time()
    test_array = np.random.random((h, w)).astype(np.float32)
    logger.info(f"Creazione array: {time.time() - start_time:.3f}s")
    
    # Test percentile
    start_time = time.time()
    perc_result = np.percentile(test_array, 75)
    logger.info(f"np.percentile: {time.time() - start_time:.3f}s")
    
    # Test operazioni booleane
    start_time = time.time()
    bool_mask = test_array > perc_result
    logger.info(f"Operazione booleana: {time.time() - start_time:.3f}s")
    
    # Test conversione tipo
    start_time = time.time()
    uint_mask = bool_mask.astype(np.uint8) * 255
    logger.info(f"Conversione tipo: {time.time() - start_time:.3f}s")
    
    del test_array, bool_mask, uint_mask

def main():
    if len(sys.argv) != 2:
        print("Uso: python debug_mask_creation.py <path_to_image>")
        print("Esempio: python debug_mask_creation.py output_images/documentoaous11-08-2025-080123_page_1_img_1.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        logger.error(f"File non trovato: {image_path}")
        sys.exit(1)
    
    # Carica immagine per ottenere dimensioni
    img = cv2.imread(image_path)
    if img is not None:
        h, w = img.shape[:2]
        test_array_operations(h, w)
    
    debug_mask_creation_bottleneck(image_path)

if __name__ == "__main__":
    main()