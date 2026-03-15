#!/usr/bin/env python3
"""
Agente Katana - Elaboratore di PDF Scansionati
Esamina scansioni PDF, estrapola metadati DPI e risoluzioni,
individua l'immagine scannerizzata per pagina, la ritaglia e ridimensiona
per un JPG singolo e la trasforma.
"""

import os
import sys
import io
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime
import time

try:
    import fitz  # PyMuPDF
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
    
    # Configurazione PIL per gestire immagini di grandi dimensioni
    Image.MAX_IMAGE_PIXELS = None  # Rimuove il limite di sicurezza
    # Oppure imposta un limite più alto: Image.MAX_IMAGE_PIXELS = 200000000
    
except ImportError as e:
    print(f"Errore nell'importazione delle librerie: {e}")
    print("Installare le dipendenze con: pip install -r requirements.txt")
    sys.exit(1)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('katana.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KatanaProcessor:
    """Classe principale per l'elaborazione dei PDF scansionati"""
    
    def __init__(self, output_dir: str = "output_images", learning_mode: bool = False):
        self.base_output_dir = Path(output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        self.output_dir = self.base_output_dir  # Directory corrente, verrà aggiornata per ogni PDF
        self.processed_files = []
        self.learning_mode = learning_mode
        self.feedback_data = []
        self.learning_file = "katana_learning.json"
        self.adaptive_params = self._load_learning_data()
        
    def extract_pdf_metadata(self, pdf_path: str) -> Dict:
        """Estrae metadati DPI e risoluzioni dal PDF"""
        try:
            doc = fitz.open(pdf_path)
            metadata = {
                'file_path': pdf_path,
                'page_count': len(doc),
                'pages_info': []
            }
            
            # Limita il numero di pagine se specificato
            total_pages = len(doc)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            logger.info(f"Processando {pages_to_process} di {total_pages} pagine")
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                page_rect = page.rect
                
                # Estrae informazioni sulla pagina
                page_info = {
                    'page_number': page_num + 1,
                    'width': page_rect.width,
                    'height': page_rect.height,
                    'rotation': page.rotation,
                    'images': []
                }
                
                # Cerca immagini nella pagina
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY o RGB
                        img_info = {
                            'index': img_index,
                            'xref': xref,
                            'width': pix.width,
                            'height': pix.height,
                            'colorspace': pix.colorspace.name if pix.colorspace else 'Unknown',
                            'bpp': pix.n,
                            'size_bytes': len(pix.tobytes())
                        }
                        
                        # Calcola DPI approssimativo
                        if page_rect.width > 0 and page_rect.height > 0:
                            dpi_x = (pix.width * 72) / page_rect.width
                            dpi_y = (pix.height * 72) / page_rect.height
                            img_info['dpi_x'] = round(dpi_x, 2)
                            img_info['dpi_y'] = round(dpi_y, 2)
                        
                        page_info['images'].append(img_info)
                    
                    pix = None
                
                metadata['pages_info'].append(page_info)
            
            doc.close()
            logger.info(f"Metadati estratti da {pdf_path}: {len(metadata['pages_info'])} pagine")
            return metadata
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione metadati da {pdf_path}: {e}")
            return {}
    
    def _load_learning_data(self) -> Dict:
        """Carica i dati di apprendimento dal file JSON"""
        default_params = {
            'variance_threshold': 50,
            'entropy_threshold': 1.5,
            'non_white_threshold': 0.02,
            'edge_threshold': 0.003,
            'white_threshold': 230,
            'margin_adjustment': 0.5
        }
        
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('adaptive_params', default_params)
        except Exception as e:
            logger.warning(f"Errore nel caricamento dati apprendimento: {e}")
        
        return default_params
    
    def save_feedback(self, pdf_name: str, page_num: int, feedback: str, bounds: Tuple[int, int, int, int] = None):
        """Salva il feedback dell'utente per migliorare i parametri"""
        if not self.learning_mode:
            return
            
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'pdf_name': pdf_name,
            'page_num': page_num,
            'feedback': feedback,
            'bounds': bounds,
            'current_params': self.adaptive_params.copy()
        }
        
        self.feedback_data.append(feedback_entry)
        self._update_adaptive_params(feedback)
        self._save_learning_data()
        
        logger.info(f"Feedback salvato per {pdf_name} pagina {page_num}: {feedback}")
    
    def _update_adaptive_params(self, feedback: str):
        """Aggiorna i parametri in base al feedback"""
        if feedback == 'excessive_cropping':
            # Riduci l'aggressività del ritaglio
            self.adaptive_params['variance_threshold'] = max(30, self.adaptive_params['variance_threshold'] * 0.85)
            self.adaptive_params['entropy_threshold'] = max(1.0, self.adaptive_params['entropy_threshold'] * 0.85)
            self.adaptive_params['edge_threshold'] = max(0.001, self.adaptive_params['edge_threshold'] * 0.85)
            self.adaptive_params['margin_adjustment'] = min(1.0, self.adaptive_params['margin_adjustment'] * 1.3)
            self.adaptive_params['white_threshold'] = max(220, self.adaptive_params['white_threshold'] - 5)
            logger.info("Parametri adattati per ridurre il taglio eccessivo")
            
        elif feedback == 'no_change':
            # Aumenta l'aggressività del ritaglio
            self.adaptive_params['variance_threshold'] = min(80, self.adaptive_params['variance_threshold'] * 1.15)
            self.adaptive_params['entropy_threshold'] = min(2.5, self.adaptive_params['entropy_threshold'] * 1.15)
            self.adaptive_params['edge_threshold'] = min(0.01, self.adaptive_params['edge_threshold'] * 1.15)
            self.adaptive_params['margin_adjustment'] = max(0.2, self.adaptive_params['margin_adjustment'] * 0.7)
            self.adaptive_params['white_threshold'] = min(240, self.adaptive_params['white_threshold'] + 3)
            logger.info("Parametri adattati per aumentare il ritaglio")
            
        elif feedback == 'insufficient_cropping':
            # Aumenta significativamente l'aggressività
            self.adaptive_params['variance_threshold'] = min(100, self.adaptive_params['variance_threshold'] * 1.25)
            self.adaptive_params['entropy_threshold'] = min(3.0, self.adaptive_params['entropy_threshold'] * 1.25)
            self.adaptive_params['edge_threshold'] = min(0.015, self.adaptive_params['edge_threshold'] * 1.25)
            self.adaptive_params['margin_adjustment'] = max(0.1, self.adaptive_params['margin_adjustment'] * 0.6)
            logger.info("Parametri adattati per ritaglio più aggressivo")
            
        elif feedback == 'light_cropping':
            # Leggero aggiustamento verso meno aggressività
            self.adaptive_params['variance_threshold'] = max(35, self.adaptive_params['variance_threshold'] * 0.95)
            self.adaptive_params['entropy_threshold'] = max(1.2, self.adaptive_params['entropy_threshold'] * 0.95)
            self.adaptive_params['margin_adjustment'] = min(0.8, self.adaptive_params['margin_adjustment'] * 1.1)
            logger.info("Parametri leggermente adattati per ridurre il taglio")
            
        elif feedback == 'insufficient_zoom':
            # Aumenta il fattore di zoom per immagini più grandi
            self.adaptive_params['margin_adjustment'] = max(0.1, self.adaptive_params['margin_adjustment'] * 0.8)
            self.adaptive_params['variance_threshold'] = min(90, self.adaptive_params['variance_threshold'] * 1.1)
            logger.info("Parametri adattati per aumentare lo zoom (immagini più grandi)")
            
        elif feedback == 'excessive_zoom':
            # Riduce il fattore di zoom per immagini più piccole
            self.adaptive_params['margin_adjustment'] = min(1.2, self.adaptive_params['margin_adjustment'] * 1.2)
            self.adaptive_params['variance_threshold'] = max(40, self.adaptive_params['variance_threshold'] * 0.9)
            logger.info("Parametri adattati per ridurre lo zoom (immagini più piccole)")
            
        elif feedback == 'perfect':
            # Mantieni i parametri attuali, ma registra il successo
            logger.info("Parametri confermati come ottimali")
        
        # Salva i parametri aggiornati
        self._save_learning_data()
    
    @property
    def learning_data(self) -> Dict:
        """Restituisce i dati di apprendimento correnti"""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Errore nel caricamento dati apprendimento: {e}")
        
        # Restituisce dati di default se il file non esiste o c'è un errore
        return {
            'adaptive_params': self.adaptive_params,
            'feedback_history': self.feedback_data,
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_learning_data(self):
        """Salva i dati di apprendimento nel file JSON"""
        try:
            learning_data = {
                'adaptive_params': self.adaptive_params,
                'feedback_history': self.feedback_data[-50:],  # Mantieni solo gli ultimi 50 feedback
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(learning_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Errore nel salvataggio dati apprendimento: {e}")
    
    def process_with_feedback(self, pdf_path: str, feedback_data: List[Dict] = None):
        """Processa un PDF applicando feedback manuale se fornito"""
        if feedback_data and self.learning_mode:
            pdf_name = os.path.basename(pdf_path)
            for feedback in feedback_data:
                page_num = feedback.get('page', 0)
                result = feedback.get('result', '')
                self.save_feedback(pdf_name, page_num, result)
        
        # Processa normalmente il PDF
        return self.process_pdf_file(pdf_path)
    
    def _create_pdf_output_dir(self, pdf_path: str) -> Path:
        """Crea una sottocartella specifica per il PDF"""
        pdf_name = Path(pdf_path).stem  # Nome del file senza estensione
        pdf_output_dir = self.base_output_dir / pdf_name
        pdf_output_dir.mkdir(exist_ok=True)
        logger.info(f"Directory di output creata: {pdf_output_dir}")
        return pdf_output_dir
    
    def extract_and_process_images(self, pdf_path: str, target_dpi: int = 300, max_pages: int = None) -> List[str]:
        """Estrae e processa le immagini dal PDF"""
        try:
            # Crea directory specifica per questo PDF
            self.output_dir = self._create_pdf_output_dir(pdf_path)
            
            doc = fitz.open(pdf_path)
            output_files = []
            pdf_name = Path(pdf_path).stem
            
            # Limita il numero di pagine se specificato
            total_pages = len(doc)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            logger.info(f"Processando {pages_to_process} di {total_pages} pagine")
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                
                # Metodo 1: Estrazione diretta delle immagini
                image_list = page.get_images(full=True)
                
                if image_list:
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY o RGB
                            # Log delle dimensioni originali dell'immagine estratta
                            logger.info(f"Immagine estratta dal PDF: {pix.width}x{pix.height} pixel")
                            
                            # Controlla se l'immagine è troppo grande (oltre 6000 pixel in qualsiasi dimensione)
                            if pix.width > 6000 or pix.height > 6000:
                                logger.warning(f"Immagine molto grande ({pix.width}x{pix.height}), potrebbe essere sovracampionata")
                                # Calcola un fattore di riduzione per portarla a dimensioni ragionevoli
                                max_dimension = max(pix.width, pix.height)
                                if max_dimension > 6000:
                                    scale_factor = 6000 / max_dimension
                                    new_width = int(pix.width * scale_factor)
                                    new_height = int(pix.height * scale_factor)
                                    logger.info(f"Ridimensiono a {new_width}x{new_height} per evitare sovracampionamento")
                                    
                                    # Ridimensiona il pixmap
                                    mat_scale = fitz.Matrix(scale_factor, scale_factor)
                                    pix_scaled = fitz.Pixmap(pix, mat_scale, pix.alpha)
                                    pix = pix_scaled
                            
                            # Converte in formato PIL
                            img_data = pix.tobytes("ppm")
                            pil_image = Image.open(io.BytesIO(img_data))
                            
                            # Processa l'immagine
                            processed_image = self.process_scanned_image(pil_image, target_dpi)
                            
                            # Salva l'immagine
                            output_filename = f"{pdf_name}_page_{page_num+1}_img_{img_index+1}.jpg"
                            output_path = self.output_dir / output_filename
                            processed_image.save(output_path, "JPEG", quality=95, dpi=(target_dpi, target_dpi))
                            output_files.append((str(output_path), processed_image, output_filename))
                            
                            logger.info(f"Immagine salvata: {output_path}")
                        
                        pix = None
                
                else:
                    # Metodo 2: Rendering della pagina come immagine
                    mat = fitz.Matrix(target_dpi/72, target_dpi/72)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("ppm")
                    pil_image = Image.open(io.BytesIO(img_data))
                    
                    # Processa l'immagine renderizzata
                    processed_image = self.process_scanned_image(pil_image, target_dpi)
                    
                    # Salva l'immagine
                    output_filename = f"{pdf_name}_page_{page_num+1}_rendered.jpg"
                    output_path = self.output_dir / output_filename
                    processed_image.save(output_path, "JPEG", quality=95, dpi=(target_dpi, target_dpi))
                    output_files.append((str(output_path), processed_image, output_filename))
                    
                    logger.info(f"Pagina renderizzata salvata: {output_path}")
                    pix = None
            
            doc.close()
            return output_files
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione immagini da {pdf_path}: {e}")
            return []
    
    def process_scanned_image(self, image: Image.Image, target_dpi: int = 300) -> Image.Image:
        """Processa un'immagine scansionata mantenendo l'aspetto originale"""
        try:
            # Converte in RGB se necessario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Ridimensiona se necessario per mantenere il DPI target
            current_dpi = image.info.get('dpi', (72, 72))
            if isinstance(current_dpi, tuple):
                current_dpi = current_dpi[0]
            
            if current_dpi != target_dpi:
                scale_factor = target_dpi / current_dpi
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Nessuna modifica di colore, contrasto o nitidezza per preservare l'aspetto originale
            return image
            
        except Exception as e:
            logger.error(f"Errore nel processamento dell'immagine: {e}")
            return image
    
    def rotate_image(self, image_input, angle: float) -> Image.Image:
        """Ruota un'immagine dell'angolo specificato (in gradi)
        
        Args:
            image_input: Immagine PIL o path del file
            angle: Angolo di rotazione in gradi (positivo = orario, negativo = antiorario)
            
        Returns:
            Image.Image: Immagine ruotata
        """
        try:
            # Gestisce sia path che immagini PIL
            if isinstance(image_input, str):
                image = Image.open(image_input)
            else:
                image = image_input
            
            # Converte in RGB se necessario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Ruota l'immagine
            # expand=True mantiene l'intera immagine visibile dopo la rotazione
            rotated = image.rotate(-angle, expand=True, fillcolor='white')
            
            logger.info(f"Immagine ruotata di {angle} gradi")
            return rotated
            
        except Exception as e:
            logger.error(f"Errore nella rotazione dell'immagine: {e}")
            return image_input if isinstance(image_input, Image.Image) else Image.open(image_input)
    
    def detect_and_crop_content(self, image_input, target_format: str = "A4") -> Optional[str]:
        """Rileva e ritaglia il contenuto principale dell'immagine con riconoscimento automatico delle dimensioni"""
        try:
            # Gestisce sia path che immagini PIL
            if isinstance(image_input, str):
                # Carica l'immagine con OpenCV dal path
                img = cv2.imread(image_input)
                if img is None:
                    logger.error(f"Impossibile caricare l'immagine: {image_input}")
                    return None
                image_path = image_input
                original_filename = None
            elif isinstance(image_input, tuple):
                # Tupla (pil_image, filename)
                pil_image, original_filename = image_input
                img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                image_path = str(self.output_dir / f"temp_{int(time.time())}.jpg")
            else:
                # Solo immagine PIL
                img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
                image_path = str(self.output_dir / f"temp_{int(time.time())}.jpg")
                original_filename = None
            
            original_height, original_width = img.shape[:2]
            logger.info(f"Dimensioni originali: {original_width}x{original_height}")
            
            # Rileva i bordi del documento con algoritmo migliorato
            document_bounds = self._detect_document_bounds(img)
            
            if document_bounds is not None:
                x, y, w, h = document_bounds
                logger.info(f"Bordi rilevati: x={x}, y={y}, w={w}, h={h}")
                
                # Ritaglia l'immagine ai bordi rilevati
                cropped = img[y:y+h, x:x+w]
                
                # Ridimensiona mantenendo le proporzioni per il formato target
                resized_cropped = self._resize_to_target_format(cropped, target_format)
                
                # Salva l'immagine ritagliata e ridimensionata nella directory output
                if isinstance(image_input, str):
                    base_name = Path(image_path).stem
                elif original_filename:
                    # Usa il nome originale del file
                    base_name = Path(original_filename).stem
                else:
                    # Fallback per immagini PIL senza nome
                    base_name = f"processed_{int(time.time())}"
                cropped_path = str(self.output_dir / f"{base_name}_cropped.jpg")
                cv2.imwrite(cropped_path, resized_cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                logger.info(f"Immagine ritagliata e ridimensionata salvata: {cropped_path}")
                return cropped_path
            else:
                logger.warning(f"Impossibile rilevare i bordi del documento in {image_path}, uso l'immagine originale")
                # Anche se non riusciamo a rilevare i bordi, creiamo comunque un file _cropped
                # usando l'immagine originale ridimensionata al formato target
                resized_original = self._resize_to_target_format(img, target_format)
                
                # Salva l'immagine ridimensionata con suffisso _cropped
                if isinstance(image_input, str):
                    base_name = Path(image_path).stem
                elif original_filename:
                    # Usa il nome originale del file
                    base_name = Path(original_filename).stem
                else:
                    # Fallback per immagini PIL senza nome
                    base_name = f"processed_{int(time.time())}"
                cropped_path = str(self.output_dir / f"{base_name}_cropped.jpg")
                cv2.imwrite(cropped_path, resized_original, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                logger.info(f"Immagine ridimensionata (senza ritaglio) salvata: {cropped_path}")
                return cropped_path
            
        except Exception as e:
            logger.error(f"Errore nel ritaglio dell'immagine: {e}")
            if isinstance(image_input, str):
                return image_input
            else:
                return None
    
    def _detect_document_bounds(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Rileva i bordi del documento con algoritmi avanzati per riconoscimento automatico delle dimensioni"""
        try:
            original_height, original_width = img.shape[:2]
            
            # Metodo 1: Rilevamento basato su linee e bordi
            bounds_method1 = self._detect_by_edges_and_lines(img)
            
            # Metodo 2: Rilevamento basato su analisi del colore
            bounds_method2 = self._detect_by_color_analysis(img)
            
            # Metodo 3: Rilevamento basato su contorni rettangolari
            bounds_method3 = self._detect_by_rectangular_contours(img)
            
            # Combina i risultati dei tre metodi con validazione
            valid_bounds = []
            for i, bounds in enumerate([bounds_method1, bounds_method2, bounds_method3]):
                if bounds is not None and self._validate_content_bounds(img, bounds):
                    valid_bounds.append(bounds)
                    logger.debug(f"Metodo {i+1}: {bounds} - validato")
                elif bounds is not None:
                    logger.debug(f"Metodo {i+1}: {bounds} - non validato")
            
            # Se nessun metodo ha prodotto risultati validi, usa fallback
            if not valid_bounds:
                logger.warning("Nessun metodo ha prodotto bordi validi, uso rilevamento fallback")
                fallback_bounds = self._detect_fallback_bounds(img)
                if fallback_bounds and self._validate_content_bounds(img, fallback_bounds):
                    valid_bounds.append(fallback_bounds)
            
            if not valid_bounds:
                logger.warning("Nessun metodo di rilevamento ha trovato bordi validi")
                return None
            
            # Seleziona il risultato più affidabile (quello con area maggiore ma ragionevole)
            best_bounds = self._select_best_bounds(valid_bounds, original_width, original_height)
            
            if best_bounds:
                x, y, w, h = best_bounds
                logger.info(f"Bordi selezionati: x={x}, y={y}, w={w}, h={h} (area: {w*h})")
                return best_bounds
            
            return None
            
        except Exception as e:
            logger.error(f"Errore nel rilevamento dei bordi: {e}")
            return None
    
    def _detect_by_edges_and_lines(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Metodo 1: Rilevamento avanzato basato su analisi dei bordi e contenuto"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Analisi dei bordi per trovare il contenuto reale
            # Calcola la varianza per ogni riga e colonna
            row_variance = np.var(gray, axis=1)
            col_variance = np.var(gray, axis=0)
            
            # Soglia dinamica basata sulla media delle varianze
            row_threshold = np.mean(row_variance) * 0.3
            col_threshold = np.mean(col_variance) * 0.3
            
            # Trova le righe e colonne con contenuto significativo
            content_rows = np.where(row_variance > row_threshold)[0]
            content_cols = np.where(col_variance > col_threshold)[0]
            
            if len(content_rows) == 0 or len(content_cols) == 0:
                # Fallback: usa rilevamento contorni
                return self._detect_largest_contour(img)
            
            # Trova i bordi del contenuto
            top = content_rows[0]
            bottom = content_rows[-1]
            left = content_cols[0]
            right = content_cols[-1]
            
            # Verifica che i bordi siano ragionevoli (non troppo vicini ai margini)
            margin_threshold = min(w, h) * 0.05  # 5% della dimensione minima
            
            if (top < margin_threshold or bottom > h - margin_threshold or 
                left < margin_threshold or right > w - margin_threshold):
                # Se i bordi sono troppo vicini ai margini, prova un approccio diverso
                return self._detect_by_content_analysis(img)
            
            # Aggiunge un piccolo margine
            margin = int(min(w, h) * 0.02)  # 2% della dimensione minima
            x = max(0, left - margin)
            y = max(0, top - margin)
            w_crop = min(w - x, right - left + 2 * margin)
            h_crop = min(h - y, bottom - top + 2 * margin)
            
            # Verifica che le dimensioni siano ragionevoli
            if w_crop < w * 0.3 or h_crop < h * 0.3:
                logger.debug("Dimensioni rilevate troppo piccole, usando fallback")
                return None
            
            logger.info(f"Rilevamento per varianza: x={x}, y={y}, w={w_crop}, h={h_crop}")
            return (x, y, w_crop, h_crop)
            
        except Exception as e:
            logger.debug(f"Errore nel rilevamento per linee: {e}")
            return None
    
    def _detect_largest_contour(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Rileva il contorno più grande nell'immagine"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Applica threshold adattivo
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Trova contorni
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Trova il contorno più grande
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Ottieni il rettangolo che racchiude il contorno
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Verifica che sia ragionevolmente grande
            img_area = img.shape[0] * img.shape[1]
            contour_area = w * h
            
            if contour_area < img_area * 0.1:  # Almeno 10% dell'immagine
                return None
            
            return (x, y, w, h)
            
        except Exception as e:
            logger.debug(f"Errore nel rilevamento contorni: {e}")
            return None
    
    def _detect_by_content_analysis(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Analisi avanzata del contenuto per rilevare i bordi del documento"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Analizza i margini per trovare dove inizia il contenuto
            margin_size = min(w, h) // 20  # Analizza il 5% dei margini
            
            # Analizza i margini superiore e inferiore
            top_margin = gray[:margin_size, :]
            bottom_margin = gray[-margin_size:, :]
            
            # Analizza i margini sinistro e destro
            left_margin = gray[:, :margin_size]
            right_margin = gray[:, -margin_size:]
            
            # Calcola la media dei margini (dovrebbero essere più uniformi)
            top_std = np.std(top_margin)
            bottom_std = np.std(bottom_margin)
            left_std = np.std(left_margin)
            right_std = np.std(right_margin)
            
            # Calcola la media del centro (dovrebbe avere più variazione)
            center_region = gray[h//4:3*h//4, w//4:3*w//4]
            center_std = np.std(center_region)
            
            # Se i margini hanno meno variazione del centro, probabilmente sono margini vuoti
            threshold_ratio = 0.5
            
            top_crop = margin_size if top_std < center_std * threshold_ratio else 0
            bottom_crop = margin_size if bottom_std < center_std * threshold_ratio else 0
            left_crop = margin_size if left_std < center_std * threshold_ratio else 0
            right_crop = margin_size if right_std < center_std * threshold_ratio else 0
            
            x = left_crop
            y = top_crop
            w_crop = w - left_crop - right_crop
            h_crop = h - top_crop - bottom_crop
            
            # Verifica che le dimensioni siano ragionevoli
            if w_crop < w * 0.5 or h_crop < h * 0.5:
                return None
            
            logger.info(f"Rilevamento per analisi contenuto: x={x}, y={y}, w={w_crop}, h={h_crop}")
            return (x, y, w_crop, h_crop)
            
        except Exception as e:
            logger.debug(f"Errore nell'analisi del contenuto: {e}")
            return None
    
    def _calculate_threshold_fast(self, score_map: np.ndarray, percentile: float) -> float:
        """
        Calcola threshold usando campionamento intelligente (metodo ultra-veloce)
        """
        try:
            h, w = score_map.shape
            total_pixels = h * w
            
            # Usa campionamento aggressivo per immagini grandi
            if total_pixels > 10_000_000:  # > 10M pixel
                # Campiona solo 1 pixel ogni 100 (riduzione 99%)
                sample_step = 100
                logger.debug(f"Campionamento ultra-aggressivo: 1/{sample_step} pixel")
            elif total_pixels > 5_000_000:  # > 5M pixel
                # Campiona solo 1 pixel ogni 50 (riduzione 98%)
                sample_step = 50
                logger.debug(f"Campionamento aggressivo: 1/{sample_step} pixel")
            elif total_pixels > 1_000_000:  # > 1M pixel
                # Campiona solo 1 pixel ogni 20 (riduzione 95%)
                sample_step = 20
                logger.debug(f"Campionamento moderato: 1/{sample_step} pixel")
            else:
                # Usa metodo standard per immagini piccole
                return np.percentile(score_map, percentile * 100)
            
            # Campionamento sistematico
            sampled_data = score_map.flatten()[::sample_step]
            
            # Calcola percentile sui dati campionati
            threshold = np.percentile(sampled_data, percentile * 100)
            
            logger.debug(f"Threshold calcolato su {len(sampled_data):,} campioni invece di {total_pixels:,} pixel")
            return threshold
            
        except Exception as e:
            logger.warning(f"Errore nel calcolo threshold veloce: {e}")
            # Fallback al metodo standard
            return np.percentile(score_map, percentile * 100)
    
    def _detect_by_color_analysis(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Metodo 2: Rilevamento ultra-ottimizzato basato su analisi dei colori con blocchi 200x200 pixel
        
        Ottimizzazioni implementate:
        - Blocchi 200x200 pixel per ridurre drasticamente i calcoli
        - Controlli di dimensione minima per evitare blocchi inutili
        - Uso di np.linalg.norm invece di sqrt(sum) per performance
        - Pre-calcolo di riferimenti comuni
        - Logging di progresso per monitoraggio
        """
        try:
            h, w = img.shape[:2]
            
            # Converte in diversi spazi colore per analisi più robusta
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Ottimizzazione: Analisi a blocchi 200x200 pixel con campionamento intelligente
            block_size = 200
            
            # Per immagini molto grandi, usa campionamento per ridurre il carico
            if w > 6000 or h > 6000:
                # Campiona ogni 2 blocchi per immagini enormi
                step_size = block_size * 2
                logger.info(f"Immagine molto grande ({w}x{h}), uso campionamento con step {step_size}")
            else:
                step_size = block_size
            
            content_score_map = np.zeros((h, w), dtype=np.float32)
            
            # Analisi a blocchi ottimizzata con controlli di performance e timeout
            total_blocks = ((h // step_size) + 1) * ((w // step_size) + 1)
            processed_blocks = 0
            
            # Controllo di timeout per evitare blocchi
            import time
            start_time = time.time()
            max_processing_time = 30  # Massimo 30 secondi per l'analisi colori
            
            # Pre-calcola riferimenti per ottimizzazione
            white_ref = np.array([255, 255, 255], dtype=np.float32)
            
            logger.info(f"Inizio analisi a blocchi: {total_blocks} blocchi totali da processare")
            
            # Flag per gestire il timeout
            timeout_reached = False
            
            for y in range(0, h, step_size):
                if timeout_reached:  # Esce anche dal loop esterno
                    break
                    
                for x in range(0, w, step_size):
                    # Controllo timeout per evitare blocchi infiniti
                    if time.time() - start_time > max_processing_time:
                        logger.warning(f"Timeout raggiunto dopo {max_processing_time}s, interrompo analisi colori")
                        timeout_reached = True
                        break
                    # Definisce i limiti del blocco
                    y_end = min(y + block_size, h)
                    x_end = min(x + block_size, w)
                    
                    # Verifica dimensione minima del blocco per evitare calcoli inutili
                    block_h = y_end - y
                    block_w = x_end - x
                    if block_h < 50 or block_w < 50:  # Salta blocchi troppo piccoli
                        continue
                    
                    # Estrae il blocco
                    block_bgr = img[y:y_end, x:x_end]
                    block_hsv = hsv[y:y_end, x:x_end]
                    block_gray = gray[y:y_end, x:x_end]
                    
                    # Metodo 1: Analisi ottimizzata della deviazione dal bianco
                    block_float = block_bgr.astype(np.float32)
                    color_distances = np.linalg.norm(block_float - white_ref, axis=2)  # Più veloce di sqrt(sum)
                    avg_color_distance = np.mean(color_distances)
                    
                    # Metodo 2: Analisi della saturazione media nel blocco
                    avg_saturation = np.mean(block_hsv[:, :, 1])
                    
                    # Metodo 3: Analisi della varianza nel blocco (ottimizzata)
                    block_variance = np.var(block_gray)
                    
                    # Calcola score combinato per il blocco (ottimizzato)
                    # Normalizza i valori per combinazione con clipping più efficiente
                    color_score = np.clip(avg_color_distance / 100.0, 0.0, 1.0)
                    saturation_score = avg_saturation / 255.0
                    variance_score = np.clip(block_variance / 10000.0, 0.0, 1.0)
                    
                    # Score combinato con pesi
                    combined_score = (color_score * 0.4 + saturation_score * 0.3 + variance_score * 0.3)
                    
                    # Applica lo score a tutto il blocco
                    content_score_map[y:y_end, x:x_end] = combined_score
                    
                    # Controllo di progresso per debug
                    processed_blocks += 1
                    if processed_blocks % 50 == 0:  # Log ogni 50 blocchi
                        logger.debug(f"Processati {processed_blocks}/{total_blocks} blocchi")
            
            # Crea maschera basata su soglia dinamica (OTTIMIZZATO)
            # Sostituisce np.percentile lento con metodo histogram veloce
            score_threshold = self._calculate_threshold_fast(content_score_map, 0.75)  # Top 25% dei blocchi
            content_mask = (content_score_map > score_threshold).astype(np.uint8) * 255
            
            logger.info(f"Applicazione operazioni morfologiche su immagine {w}x{h}")
            
            # Ottimizzazione critica: riduce risoluzione per operazioni morfologiche pesanti
            if w > 4000 or h > 4000:  # Per immagini molto grandi
                # Riduce temporaneamente la risoluzione per operazioni morfologiche
                scale_factor = 0.25  # Riduce a 1/4 della dimensione
                small_w, small_h = int(w * scale_factor), int(h * scale_factor)
                
                # Ridimensiona la maschera
                small_mask = cv2.resize(content_mask, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
                
                # Applica operazioni morfologiche sulla versione ridotta
                kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Kernel più piccolo
                small_mask = cv2.morphologyEx(small_mask, cv2.MORPH_CLOSE, kernel_morph)
                small_mask = cv2.morphologyEx(small_mask, cv2.MORPH_OPEN, kernel_morph)
                
                # Ridimensiona di nuovo alla dimensione originale
                content_mask = cv2.resize(small_mask, (w, h), interpolation=cv2.INTER_NEAREST)
                
                logger.info(f"Operazioni morfologiche completate su versione ridotta {small_w}x{small_h}")
            else:
                # Per immagini più piccole, usa il metodo normale
                kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                content_mask = cv2.morphologyEx(content_mask, cv2.MORPH_CLOSE, kernel_morph)
                content_mask = cv2.morphologyEx(content_mask, cv2.MORPH_OPEN, kernel_morph)
                
                logger.info("Operazioni morfologiche completate su dimensione normale")
            
            # Trova contorni significativi con ottimizzazioni per immagini grandi
            logger.info("Ricerca contorni in corso...")
            
            # Per immagini molto grandi, usa approssimazione più aggressiva
            if w > 6000 or h > 6000:
                contours, _ = cv2.findContours(content_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
                logger.info(f"Trovati {len(contours)} contorni con approssimazione aggressiva")
            else:
                contours, _ = cv2.findContours(content_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                logger.info(f"Trovati {len(contours)} contorni con metodo standard")
            
            if not contours:
                logger.warning("Nessun contorno trovato")
                return None
            
            # Filtra contorni troppo piccoli (adattato per analisi a blocchi)
            min_area = (w * h) * 0.005  # Almeno 0.5% dell'immagine per compensare blocchi
            significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            logger.info(f"Contorni significativi: {len(significant_contours)} su {len(contours)} totali")
            
            if not significant_contours:
                return None
            
            # Trova il bounding box che racchiude tutti i contorni significativi
            all_points = np.vstack(significant_contours)
            x, y, w_crop, h_crop = cv2.boundingRect(all_points)
            
            # Espansione intelligente basata sulla dimensione del contenuto
            content_ratio = (w_crop * h_crop) / (w * h)
            if content_ratio < 0.2:  # Contenuto piccolo, espandi di più
                expansion_factor = 0.12
            else:
                expansion_factor = 0.06
            
            margin_x = int(w_crop * expansion_factor)
            margin_y = int(h_crop * expansion_factor)
            
            x = max(0, x - margin_x)
            y = max(0, y - margin_y)
            w_crop = min(w - x, w_crop + 2 * margin_x)
            h_crop = min(h - y, h_crop + 2 * margin_y)
            
            # Verifica che il risultato sia ragionevole
            if w_crop < w * 0.1 or h_crop < h * 0.1:
                return None
            
            logger.info(f"Rilevamento per analisi colori ottimizzata: x={x}, y={y}, w={w_crop}, h={h_crop}, content_ratio={content_ratio:.3f}")
            return (x, y, w_crop, h_crop)
            
        except Exception as e:
            logger.debug(f"Errore nell'analisi colori ottimizzata: {e}")
            return None
    
    def _detect_by_rectangular_contours(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Metodo 3: Rilevamento specializzato per contenuto artistico usando clustering ottimizzato"""
        try:
            import time
            start_time = time.time()
            h, w = img.shape[:2]
            
            # Timeout di sicurezza per evitare blocchi
            max_processing_time = 15  # Massimo 15 secondi
            
            # Per immagini molto grandi, ridimensiona per K-means
            if w > 8000 or h > 8000:
                logger.info(f"Immagine molto grande ({w}x{h}), ridimensiono per clustering")
                scale_factor = 0.25
                small_w, small_h = int(w * scale_factor), int(h * scale_factor)
                small_img = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_AREA)
                img_data = small_img.reshape((-1, 3)).astype(np.float32)
            else:
                img_data = img.reshape((-1, 3)).astype(np.float32)
            
            # Controllo timeout prima di K-means
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto prima di K-means, salto metodo")
                return None
            
            # Applica K-means con parametri ottimizzati
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)  # Ridotto da 20 a 10
            k = 3  # Ridotto da 4 a 3 cluster
            _, labels, centers = cv2.kmeans(img_data, k, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS)  # Ridotto da 10 a 5 tentativi
            
            # Controllo timeout dopo K-means
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto dopo K-means, salto resto del metodo")
                return None
            
            # Identifica il cluster del bianco (quello con valori RGB più alti)
            white_cluster_idx = np.argmax(np.sum(centers, axis=1))
            
            # Crea maschera per tutti i pixel non-bianchi
            content_mask = (labels.flatten() != white_cluster_idx).astype(np.uint8)
            
            # Se abbiamo ridimensionato, ridimensiona la maschera
            if w > 8000 or h > 8000:
                content_mask = content_mask.reshape((small_h, small_w)) * 255
                content_mask = cv2.resize(content_mask, (w, h), interpolation=cv2.INTER_NEAREST)
            else:
                content_mask = content_mask.reshape((h, w)) * 255
            
            # Controllo timeout prima dell'analisi densità
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto prima dell'analisi densità, uso solo K-means")
                # Salta l'analisi densità e vai direttamente ai contorni
            else:
                # Metodo aggiuntivo: Analisi della densità dei pixel (solo se c'è tempo)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Calcola la densità di pixel non-bianchi in finestre scorrevoli ottimizzate
                window_size = min(h, w) // 30  # Ridotto da 20 a 30 per finestre più grandi
                density_map = np.zeros((h, w), dtype=np.float32)
                
                # Campionamento più aggressivo per grandi immagini
                step = window_size // 4 if w > 4000 or h > 4000 else window_size // 2
                
                for y in range(0, h - window_size, step):
                    # Controllo timeout durante il loop
                    if time.time() - start_time > max_processing_time:
                        logger.warning("Timeout raggiunto durante analisi densità")
                        break
                        
                    for x in range(0, w - window_size, step):
                        window = gray[y:y+window_size, x:x+window_size]
                        # Conta pixel che non sono quasi-bianchi
                        non_white_pixels = np.sum(window < 240)
                        density = non_white_pixels / (window_size * window_size)
                        density_map[y:y+window_size, x:x+window_size] = np.maximum(
                            density_map[y:y+window_size, x:x+window_size], density
                        )
                
                # Combina maschera K-means con mappa densità solo se completata
                if time.time() - start_time <= max_processing_time:
                    density_threshold = np.percentile(density_map, 60)
                    density_mask = (density_map > density_threshold).astype(np.uint8) * 255
                    content_mask = cv2.bitwise_or(content_mask, density_mask)
            
            # Controllo timeout finale prima delle operazioni morfologiche
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto, uso maschera K-means senza operazioni morfologiche")
                final_mask = content_mask
            else:
                # Operazioni morfologiche per pulire la maschera (solo se c'è tempo)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Ridotto da (7,7) a (3,3)
                final_mask = cv2.morphologyEx(content_mask, cv2.MORPH_CLOSE, kernel)
                final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel)
            
            # Trova contorni con timeout
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto prima della ricerca contorni")
                return None
                
            contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                logger.warning("Nessun contorno trovato nel metodo rectangular")
                return None
            
            # Filtra contorni per area minima con timeout
            if time.time() - start_time > max_processing_time:
                logger.warning("Timeout raggiunto durante filtro contorni")
                return None
                
            min_area = (w * h) * 0.005  # 0.5% dell'area totale
            significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            logger.info(f"Contorni significativi: {len(significant_contours)} su {len(contours)} totali")
            
            if not significant_contours:
                logger.warning("Nessun contorno significativo trovato")
                return None
            
            # Se ci sono più contorni significativi, trova il bounding box che li racchiude tutti
            if len(significant_contours) > 1:
                all_points = np.vstack(significant_contours)
                x, y, w_crop, h_crop = cv2.boundingRect(all_points)
            else:
                x, y, w_crop, h_crop = cv2.boundingRect(significant_contours[0])
            
            # Espansione intelligente basata sul contenuto rilevato
            content_ratio = (w_crop * h_crop) / (w * h)
            if content_ratio < 0.3:  # Se il contenuto è piccolo, espandi di più
                expansion_factor = 0.15
            else:
                expansion_factor = 0.08
            
            margin_x = int(w_crop * expansion_factor)
            margin_y = int(h_crop * expansion_factor)
            
            x = max(0, x - margin_x)
            y = max(0, y - margin_y)
            w_crop = min(w - x, w_crop + 2 * margin_x)
            h_crop = min(h - y, h_crop + 2 * margin_y)
            
            # Verifica finale delle dimensioni
            if w_crop < w * 0.15 or h_crop < h * 0.15:
                return None
            
            elapsed_time = time.time() - start_time
            logger.info(f"Rilevamento per clustering completato in {elapsed_time:.2f}s: x={x}, y={y}, w={w_crop}, h={h_crop}, content_ratio={content_ratio:.3f}")
            return (x, y, w_crop, h_crop)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.debug(f"Errore nel rilevamento per clustering dopo {elapsed_time:.2f}s: {e}")
            return None
    
    def _select_best_bounds(self, bounds_list: List[Tuple[int, int, int, int]], img_width: int, img_height: int) -> Optional[Tuple[int, int, int, int]]:
        """Seleziona i migliori bordi con algoritmo avanzato per contenuto artistico"""
        try:
            if not bounds_list:
                return None
            
            total_area = img_width * img_height
            scored_bounds = []
            
            for i, bounds in enumerate(bounds_list):
                x, y, w, h = bounds
                area = w * h
                area_ratio = area / total_area
                
                # 1. Punteggio area - favorisce contenuto significativo ma non l'intera immagine
                if area_ratio > 0.9:  # Troppo grande, probabilmente non ha rilevato i bordi
                    area_score = 10
                elif area_ratio < 0.05:  # Troppo piccolo
                    area_score = 20
                elif 0.2 <= area_ratio <= 0.7:  # Range ottimale per contenuto artistico
                    area_score = 100
                else:
                    area_score = 60
                
                # 2. Punteggio proporzioni - più flessibile per arte
                aspect_ratio = w / h if h > 0 else 0
                if 0.5 <= aspect_ratio <= 2.0:  # Range ampio per diverse forme artistiche
                    aspect_score = 30
                elif 0.3 <= aspect_ratio <= 3.0:  # Range accettabile
                    aspect_score = 21
                else:
                    aspect_score = 9
                
                # 3. Punteggio posizione - penalizza bordi che toccano i margini dell'immagine
                margin_threshold = min(img_width, img_height) * 0.02  # 2% della dimensione minima
                position_score = 30
                
                if x <= margin_threshold:  # Tocca il bordo sinistro
                    position_score *= 0.3
                if y <= margin_threshold:  # Tocca il bordo superiore
                    position_score *= 0.3
                if x + w >= img_width - margin_threshold:  # Tocca il bordo destro
                    position_score *= 0.3
                if y + h >= img_height - margin_threshold:  # Tocca il bordo inferiore
                    position_score *= 0.3
                
                # 4. Bonus per metodi specifici (alcuni sono più affidabili per l'arte)
                method_bonus = 0
                if i == 1:  # Metodo analisi colori - ottimo per arte colorata
                    method_bonus = 6
                elif i == 2:  # Metodo clustering - ottimo per contenuto complesso
                    method_bonus = 4.5
                elif i == 0:  # Metodo varianza - buono ma meno specifico
                    method_bonus = 0
                
                # 5. Punteggio compattezza - favorisce forme più compatte
                perimeter = 2 * (w + h)
                compactness = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0
                compactness_score = min(10.0, compactness * 20)  # Normalizza
                
                # Calcolo punteggio finale
                final_score = area_score + aspect_score + position_score + method_bonus + compactness_score
                
                scored_bounds.append((bounds, final_score, area, i))
                
                logger.debug(f"Metodo {i}: x={x}, y={y}, w={w}, h={h}, area_ratio={area_ratio:.3f}, "
                            f"aspect_ratio={aspect_ratio:.3f}, position_score={position_score:.1f}, "
                            f"method_bonus={method_bonus:.1f}, final_score={final_score:.1f}")
            
            # Ordina per punteggio decrescente
            scored_bounds.sort(key=lambda x: x[1], reverse=True)
            
            # Restituisce i bordi con il punteggio più alto
            best_bounds, best_score, best_area, best_method = scored_bounds[0]
            x, y, w, h = best_bounds
            
            logger.info(f"Selezionati bordi dal metodo {best_method} con punteggio {best_score:.1f} e area {best_area} "
                       f"(ratio: {best_area / total_area:.3f})")
            
            return best_bounds
            
        except Exception as e:
            logger.error(f"Errore nella selezione dei bordi: {e}")
            return bounds_list[0] if bounds_list else None
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Ordina i punti in senso orario: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Somma e differenza per trovare gli angoli
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left
        rect[2] = pts[np.argmax(s)]  # bottom-right
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        
        return rect
    
    def _expand_bounds_with_margin(self, bounds: Tuple[int, int, int, int], img_width: int, img_height: int, margin_percent: float = 0.05) -> Tuple[int, int, int, int]:
        """Espande i bordi con margine dinamico ottimizzato per contenuto artistico"""
        x, y, w, h = bounds
        area = w * h
        img_area = img_width * img_height
        area_ratio = area / img_area
        
        # Margine dinamico basato sulla dimensione del contenuto rilevato
        if area_ratio < 0.1:  # Contenuto molto piccolo - margine generoso
            base_margin = 0.15
        elif area_ratio < 0.3:  # Contenuto piccolo - margine moderato
            base_margin = 0.10
        elif area_ratio < 0.6:  # Contenuto medio - margine standard
            base_margin = 0.06
        else:  # Contenuto grande - margine minimo
            base_margin = 0.03
        
        # Adatta il margine alle proporzioni dell'immagine
        aspect_ratio = w / h if h > 0 else 1
        if aspect_ratio > 1.5:  # Immagine orizzontale
            margin_x_factor = 1.0
            margin_y_factor = 1.2
        elif aspect_ratio < 0.7:  # Immagine verticale
            margin_x_factor = 1.2
            margin_y_factor = 1.0
        else:  # Immagine quadrata
            margin_x_factor = 1.0
            margin_y_factor = 1.0
        
        # Calcola margini in pixel
        margin_x = int(img_width * base_margin * margin_x_factor)
        margin_y = int(img_height * base_margin * margin_y_factor)
        
        # Margine minimo assoluto per garantire visibilità
        min_margin_x = max(20, int(img_width * 0.02))
        min_margin_y = max(20, int(img_height * 0.02))
        
        margin_x = max(margin_x, min_margin_x)
        margin_y = max(margin_y, min_margin_y)
        
        # Espande i bordi
        new_x = max(0, x - margin_x)
        new_y = max(0, y - margin_y)
        new_w = min(img_width - new_x, w + 2 * margin_x)
        new_h = min(img_height - new_y, h + 2 * margin_y)
        
        # Verifica che l'espansione sia significativa
        expansion_ratio = (new_w * new_h) / area
        
        logger.debug(f"Espansione bordi: originale=({x},{y},{w},{h}), "
                    f"nuovo=({new_x},{new_y},{new_w},{new_h}), "
                    f"margini=({margin_x},{margin_y}), espansione={expansion_ratio:.2f}x")
        
        return (new_x, new_y, new_w, new_h)
    
    def _validate_content_bounds(self, img: np.ndarray, bounds: Tuple[int, int, int, int]) -> bool:
        """Valida che i bordi rilevati contengano effettivamente contenuto significativo"""
        try:
            x, y, w, h = bounds
            img_height, img_width = img.shape[:2]
            
            # Verifica che i bordi siano all'interno dell'immagine
            if x < 0 or y < 0 or x + w > img_width or y + h > img_height:
                logger.debug("Bordi fuori dall'immagine")
                return False
            
            # Verifica dimensioni minime
            min_size = min(img_width, img_height) * 0.1
            if w < min_size or h < min_size:
                logger.debug(f"Dimensioni troppo piccole: {w}x{h} < {min_size}")
                return False
            
            # Estrae la regione
            region = img[y:y+h, x:x+w]
            
            # Converte in scala di grigi per analisi
            if len(region.shape) == 3:
                gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            else:
                gray_region = region
            
            # Test 1: Varianza del contenuto (usa parametri adattivi)
            variance = np.var(gray_region)
            variance_threshold = self.adaptive_params.get('variance_threshold', 50)
            if variance < variance_threshold:
                logger.debug(f"Varianza troppo bassa: {variance} < {variance_threshold}")
                return False
            
            # Test 2: Distribuzione dei valori di grigio
            hist = cv2.calcHist([gray_region], [0], None, [256], [0, 256])
            hist_normalized = hist.flatten() / hist.sum()
            
            # Calcola l'entropia (misura della diversità dei valori)
            entropy = -np.sum(hist_normalized * np.log2(hist_normalized + 1e-10))
            entropy_threshold = self.adaptive_params.get('entropy_threshold', 1.5)
            
            if entropy < entropy_threshold:
                logger.debug(f"Entropia troppo bassa: {entropy} < {entropy_threshold}")
                return False
            
            # Test 3: Percentuale di pixel non-bianchi
            non_white_pixels = np.sum(gray_region < 240)
            total_pixels = gray_region.size
            non_white_ratio = non_white_pixels / total_pixels
            non_white_threshold = self.adaptive_params.get('non_white_threshold', 0.02)
            
            if non_white_ratio < non_white_threshold:
                logger.debug(f"Troppo pochi pixel non-bianchi: {non_white_ratio:.3f} < {non_white_threshold}")
                return False
            
            # Test 4: Rilevamento di bordi significativi (usa parametri adattivi)
            canny_low = self.adaptive_params.get('canny_low', 30)
            canny_high = self.adaptive_params.get('canny_high', 100)
            edges = cv2.Canny(gray_region, canny_low, canny_high)
            edge_pixels = np.sum(edges > 0)
            edge_ratio = edge_pixels / total_pixels
            edge_threshold = self.adaptive_params.get('edge_threshold', 0.003)
            
            if edge_ratio < edge_threshold:
                logger.debug(f"Troppo pochi bordi: {edge_ratio:.3f} < {edge_threshold}")
                return False
            
            logger.debug(f"Validazione superata: var={variance:.1f}, entropy={entropy:.2f}, "
                        f"non_white={non_white_ratio:.3f}, edges={edge_ratio:.3f}")
            return True
            
        except Exception as e:
            logger.debug(f"Errore nella validazione: {e}")
            return False
    
    def _detect_fallback_bounds(self, img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
         """Metodo di fallback robusto con dimensioni minime A4"""
         try:
             h, w = img.shape[:2]
             
             # Strategia più aggressiva: rimuove margini bianchi significativi
             gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
             
             # Analizza i margini per trovare aree uniformemente bianche
             margin_size = min(w, h) // 20  # Margine più piccolo per essere più aggressivi
             
             # Analisi orizzontale (top-bottom) con campionamento
             row_step = max(1, h // 100)  # Campionamento più denso
             row_means = []
             for i in range(0, h, row_step):
                 row_means.append((i, np.mean(gray[i, :])))
             
             white_threshold = 230  # Soglia più bassa per catturare più contenuto
             
             # Trova la prima riga con contenuto significativo dall'alto
             top_bound = 0
             for i, mean_val in row_means:
                 if mean_val < white_threshold:
                     top_bound = max(0, i - margin_size // 2)  # Margine più piccolo
                     break
             
             # Trova la prima riga con contenuto significativo dal basso
             bottom_bound = h
             for i, mean_val in reversed(row_means):
                 if mean_val < white_threshold:
                     bottom_bound = min(h, i + margin_size // 2)  # Margine più piccolo
                     break
             
             # Analisi verticale (left-right) con campionamento
             col_step = max(1, w // 200)  # Campiona ogni 200esima colonna
             col_means = []
             for i in range(0, w, col_step):
                 col_means.append((i, np.mean(gray[:, i])))
             
             # Trova la prima colonna con contenuto significativo da sinistra
             left_bound = 0
             for i, mean_val in col_means:
                 if mean_val < white_threshold:
                     left_bound = max(0, i - margin_size // 2)  # Margine più piccolo
                     break
             
             # Trova la prima colonna con contenuto significativo da destra
             right_bound = w
             for i, mean_val in reversed(col_means):
                 if mean_val < white_threshold:
                     right_bound = min(w, i + margin_size // 2)  # Margine più piccolo
                     break
             
             # Calcola i bordi rilevati
             detected_x = left_bound
             detected_y = top_bound
             detected_w = right_bound - left_bound
             detected_h = bottom_bound - top_bound
             
             # Verifica che le dimensioni siano ragionevoli (almeno 20% dell'immagine originale)
             min_width = int(w * 0.2)
             min_height = int(h * 0.2)
             
             if detected_w < min_width or detected_h < min_height:
                 logger.info(f"Rilevamento troppo piccolo ({detected_w}x{detected_h}), uso il 80% dell'immagine centrata")
                 # Usa l'80% dell'immagine centrata come fallback
                 final_w = int(w * 0.8)
                 final_h = int(h * 0.8)
                 final_x = (w - final_w) // 2
                 final_y = (h - final_h) // 2
                 final_bounds = (final_x, final_y, final_w, final_h)
             else:
                 final_bounds = (detected_x, detected_y, detected_w, detected_h)
             
             logger.info(f"Fallback bounds: {final_bounds}")
             return final_bounds
             
         except Exception as e:
             logger.debug(f"Errore nel fallback: {e}")
             # Ultimo fallback: usa metà A4 centrato
             min_w = min(int(210 * 150 / 25.4), int(img.shape[1] * 0.8))
             min_h = min(int(297 * 150 / 25.4), int(img.shape[0] * 0.8))
             x = (img.shape[1] - min_w) // 2
             y = (img.shape[0] - min_h) // 2
             return (max(0, x), max(0, y), min_w, min_h)
    
    def _resize_to_target_format(self, img: np.ndarray, target_format: str = "A4", target_dpi: int = 300) -> np.ndarray:
        """Ridimensiona l'immagine per massimizzare l'utilizzo del campo disponibile mantenendo proporzioni e qualità"""
        try:
            # Definisce le dimensioni target in pixel per diversi formati a 300 DPI
            format_dimensions = {
                "A4": (2480, 3508),  # 210x297mm a 300 DPI
                "A3": (3508, 4961),  # 297x420mm a 300 DPI
                "A5": (1748, 2480),  # 148x210mm a 300 DPI
                "LETTER": (2550, 3300),  # 8.5x11 inch a 300 DPI
                "LEGAL": (2550, 4200)   # 8.5x14 inch a 300 DPI
            }
            
            if target_format not in format_dimensions:
                logger.warning(f"Formato {target_format} non riconosciuto, uso A4")
                target_format = "A4"
            
            target_width, target_height = format_dimensions[target_format]
            
            # Adatta il DPI se diverso da 300
            if target_dpi != 300:
                scale_factor = target_dpi / 300
                target_width = int(target_width * scale_factor)
                target_height = int(target_height * scale_factor)
            
            current_height, current_width = img.shape[:2]
            logger.info(f"Ridimensionamento da {current_width}x{current_height} a {target_width}x{target_height} per formato {target_format} a {target_dpi} DPI")
            
            # Calcola i fattori di scala per entrambe le dimensioni
            scale_x = target_width / current_width
            scale_y = target_height / current_height
            
            # Strategia intelligente per contenuto artistico:
            # - Priorità alla preservazione del contenuto completo
            # - Scaling più conservativo per evitare perdite di dettagli
            aspect_ratio_current = current_width / current_height
            aspect_ratio_target = target_width / target_height
            aspect_ratio_diff = abs(aspect_ratio_current - aspect_ratio_target) / aspect_ratio_target
            
            # Strategia più conservativa per contenuto artistico
            if aspect_ratio_diff > 0.15:  # Ridotto da 20% a 15%
                scale_factor = min(scale_x, scale_y)  # FIT - mantiene tutto il contenuto
                logger.info(f"Aspect ratio diverso ({aspect_ratio_diff:.2%}), uso strategia FIT per preservare arte")
            elif aspect_ratio_diff > 0.08:  # Zona intermedia per contenuto artistico
                # Usa scaling ibrido per bilanciare preservazione e utilizzo spazio
                fit_scale = min(scale_x, scale_y)
                fill_scale = max(scale_x, scale_y)
                scale_factor = (fit_scale * 0.7 + fill_scale * 0.3)  # Bias verso FIT
                logger.info(f"Aspect ratio moderato ({aspect_ratio_diff:.2%}), uso strategia IBRIDA per arte")
            else:
                scale_factor = max(scale_x, scale_y)  # FILL - massimizza l'utilizzo dello spazio
                logger.info(f"Aspect ratio simile ({aspect_ratio_diff:.2%}), uso strategia FILL")
            
            # Calcola le nuove dimensioni
            new_width = int(current_width * scale_factor)
            new_height = int(current_height * scale_factor)
            
            logger.info(f"Fattore di scala applicato: {scale_factor:.3f}")
            logger.info(f"Nuove dimensioni calcolate: {new_width}x{new_height}")
            
            # Ridimensiona con interpolazione di alta qualità
            if scale_factor > 1:
                # Ingrandimento - usa INTER_CUBIC per migliore qualità
                resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            else:
                # Riduzione - usa INTER_AREA per migliore qualità
                resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Se l'immagine ridimensionata eccede il target, gestisci con margini intelligenti
            if new_width > target_width or new_height > target_height:
                # Calcola l'eccesso in ogni dimensione
                excess_x = max(0, new_width - target_width)
                excess_y = max(0, new_height - target_height)
                
                # Gestione più conservativa per contenuto artistico
                # Se l'eccesso è minimo (<3%), mantieni l'immagine e crea margini
                if excess_x < target_width * 0.03 and excess_y < target_height * 0.03:
                    logger.info(f"Eccesso minimo ({excess_x}x{excess_y}), mantengo dimensioni per preservare arte")
                    # Non ritagliare, verrà gestito nel canvas successivo
                elif excess_x < target_width * 0.08 and excess_y < target_height * 0.08:
                    # Eccesso moderato: ritaglio molto conservativo
                    logger.info(f"Eccesso moderato ({excess_x}x{excess_y}), ritaglio conservativo per arte")
                    # Ritaglio più piccolo per preservare più contenuto
                    crop_x = min(excess_x // 3, excess_x)  # Ritaglio solo 1/3 dell'eccesso
                    crop_y = min(excess_y // 3, excess_y)
                    
                    start_x = max(0, crop_x // 2)
                    start_y = max(0, crop_y // 2)
                    end_x = min(new_width, new_width - crop_x // 2)
                    end_y = min(new_height, new_height - crop_y // 2)
                    
                    resized = resized[start_y:end_y, start_x:end_x]
                    logger.info(f"Ritaglio conservativo applicato: {resized.shape[1]}x{resized.shape[0]}")
                else:
                    # Ritaglio centrato solo se l'eccesso è molto significativo
                    start_x = max(0, (new_width - target_width) // 2)
                    start_y = max(0, (new_height - target_height) // 2)
                    end_x = min(new_width, start_x + target_width)
                    end_y = min(new_height, start_y + target_height)
                    
                    resized = resized[start_y:end_y, start_x:end_x]
                    logger.info(f"Ritaglio significativo applicato: {resized.shape[1]}x{resized.shape[0]}")
            
            # Se l'immagine è più piccola del target, crea un canvas e centrala
            final_height, final_width = resized.shape[:2]
            if final_width < target_width or final_height < target_height:
                # Crea canvas bianco
                canvas = np.ones((target_height, target_width, 3), dtype=np.uint8) * 255
                
                # Centra l'immagine nel canvas
                y_offset = (target_height - final_height) // 2
                x_offset = (target_width - final_width) // 2
                
                canvas[y_offset:y_offset+final_height, x_offset:x_offset+final_width] = resized
                resized = canvas
                logger.info(f"Immagine centrata in canvas {target_width}x{target_height}")
            
            # Nessun miglioramento applicato per preservare l'aspetto originale
            
            logger.info(f"Ridimensionamento completato: {resized.shape[1]}x{resized.shape[0]}")
            return resized
            
        except Exception as e:
            logger.error(f"Errore nel ridimensionamento: {e}")
            return img
    

    

    
    def process_pdf_file(self, pdf_path: str, target_dpi: int = 300, crop_content: bool = True, target_format: str = "A4", max_pages: int = None) -> Dict:
        """Processa un singolo file PDF"""
        logger.info(f"Inizio elaborazione: {pdf_path}")
        
        result = {
            'pdf_path': pdf_path,
            'success': False,
            'metadata': {},
            'output_images': [],
            'cropped_images': [],
            'errors': []
        }
        
        try:
            # Estrae metadati
            result['metadata'] = self.extract_pdf_metadata(pdf_path)
            
            # Estrae e processa le immagini
            output_images = self.extract_and_process_images(pdf_path, target_dpi, max_pages)
            # Estrae solo i path per il risultato
            result['output_images'] = [item[0] if isinstance(item, tuple) else item for item in output_images]
            
            # Ritaglia il contenuto se richiesto
            if crop_content:
                cropped_images = []
                for item in output_images:
                    if isinstance(item, tuple) and len(item) >= 3:
                        img_path, pil_image, original_filename = item
                        # Passa l'immagine PIL direttamente per evitare ricaricamento
                        cropped_path = self.detect_and_crop_content((pil_image, original_filename), target_format=target_format)
                    elif isinstance(item, tuple):
                        img_path, pil_image = item
                        cropped_path = self.detect_and_crop_content(pil_image, target_format=target_format)
                    else:
                        # Fallback per compatibilità
                        cropped_path = self.detect_and_crop_content(item, target_format=target_format)
                    
                    if cropped_path:
                        cropped_images.append(cropped_path)
                result['cropped_images'] = cropped_images
            
            result['success'] = True
            self.processed_files.append(result)
            logger.info(f"Elaborazione completata: {pdf_path}")
            
        except Exception as e:
            error_msg = f"Errore nell'elaborazione di {pdf_path}: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
    
    def process_directory(self, directory_path: str, target_dpi: int = 300, crop_content: bool = True, target_format: str = "A4") -> List[Dict]:
        """Processa tutti i file PDF in una directory"""
        directory = Path(directory_path)
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"Nessun file PDF trovato in {directory_path}")
            return []
        
        logger.info(f"Trovati {len(pdf_files)} file PDF da elaborare")
        
        results = []
        for pdf_file in pdf_files:
            result = self.process_pdf_file(pdf_file, target_dpi, crop_content, target_format)
            results.append(result)
        
        return results
    
    def generate_report(self) -> str:
        """Genera un report delle elaborazioni effettuate"""
        report_lines = [
            "=== REPORT ELABORAZIONE KATANA ===",
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"File elaborati: {len(self.processed_files)}",
            ""
        ]
        
        for i, result in enumerate(self.processed_files, 1):
            report_lines.extend([
                f"{i}. {Path(result['pdf_path']).name}",
                f"   Successo: {'Sì' if result['success'] else 'No'}",
                f"   Pagine: {result['metadata'].get('page_count', 'N/A')}",
                f"   Immagini estratte: {len(result['output_images'])}",
                f"   Immagini ritagliate: {len(result['cropped_images'])}",
            ])
            
            if result['errors']:
                report_lines.append(f"   Errori: {'; '.join(result['errors'])}")
            
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        # Salva il report
        report_path = self.output_dir / f"katana_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Report salvato: {report_path}")
        return report_content

def main():
    """Funzione principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agente Katana - Elaboratore di PDF Scansionati")
    parser.add_argument("input_path", help="Percorso del file PDF o directory da elaborare")
    parser.add_argument("--output-dir", default="output_images", help="Directory di output (default: output_images)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI target per le immagini (default: 300)")
    parser.add_argument("--no-crop", action="store_true", help="Disabilita il ritaglio automatico")
    parser.add_argument("--format", type=str, default="A4", choices=["A4", "A3", "A5", "LETTER", "LEGAL"], help="Formato target per il ridimensionamento (default: A4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output verboso")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Inizializza il processore
    processor = KatanaProcessor(args.output_dir)
    
    input_path = Path(args.input_path)
    
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # Elabora un singolo file
        result = processor.process_pdf_file(str(input_path), args.dpi, not args.no_crop, args.format)
        print(f"Elaborazione completata. Successo: {result['success']}")
    elif input_path.is_dir():
        # Elabora una directory
        results = processor.process_directory(str(input_path), args.dpi, not args.no_crop, args.format)
        successful = sum(1 for r in results if r['success'])
        print(f"Elaborazione completata. {successful}/{len(results)} file elaborati con successo.")
    else:
        print(f"Errore: {input_path} non è un file PDF valido o una directory.")
        return 1
    
    # Genera e mostra il report
    report = processor.generate_report()
    print("\n" + report)
    
    return 0

if __name__ == "__main__":
    import io
    sys.exit(main())