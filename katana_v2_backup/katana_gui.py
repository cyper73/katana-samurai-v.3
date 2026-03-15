#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Katana GUI - Interfaccia grafica per il ritaglio manuale e addestramento
Permette di visualizzare, ritagliare manualmente e fornire feedback per l'addestramento dell'agente
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
from pathlib import Path
import json
import os
import datetime
from typing import List, Dict, Tuple, Optional
from katana import KatanaProcessor
import logging

class ImageCropCanvas(tk.Canvas):
    """Canvas personalizzato per il ritaglio delle immagini"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.image = None
        self.original_image = None  # Mantiene l'immagine originale per le rotazioni
        self.photo_image = None
        self.scale_factor = 1.0
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.crop_coords = None
        self.rotation_angle = 0  # Angolo di rotazione corrente
        
        # Bind eventi mouse
        self.bind("<Button-1>", self.start_crop)
        self.bind("<B1-Motion>", self.update_crop)
        self.bind("<ButtonRelease-1>", self.end_crop)
        
    def load_image(self, image_path: str):
        """Carica un'immagine nel canvas"""
        try:
            self.original_image = Image.open(image_path)
            self.image = self.original_image.copy()
            self.rotation_angle = 0
            self.fit_image_to_canvas()
            return True
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare l'immagine: {e}")
            return False
    
    def fit_image_to_canvas(self):
        """Adatta l'immagine alle dimensioni del canvas"""
        if not self.image:
            return
            
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.after(100, self.fit_image_to_canvas)
            return
            
        img_width, img_height = self.image.size
        
        # Calcola il fattore di scala per adattare l'immagine
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        self.scale_factor = min(scale_x, scale_y, 1.0)  # Non ingrandire oltre le dimensioni originali
        
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        
        resized_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(resized_image)
        
        self.delete("all")
        self.create_image(canvas_width//2, canvas_height//2, image=self.photo_image, anchor="center")
        
    def start_crop(self, event):
        """Inizia la selezione del crop"""
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.delete(self.rect_id)
            
    def update_crop(self, event):
        """Aggiorna la selezione del crop"""
        if self.start_x is not None and self.start_y is not None:
            if self.rect_id:
                self.delete(self.rect_id)
            self.rect_id = self.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="red", width=2
            )
            
    def end_crop(self, event):
        """Termina la selezione del crop"""
        if self.start_x is not None and self.start_y is not None:
            # Converti le coordinate del canvas alle coordinate dell'immagine originale
            canvas_width = self.winfo_width()
            canvas_height = self.winfo_height()
            
            if self.image and self.scale_factor > 0:
                img_width, img_height = self.image.size
                scaled_width = int(img_width * self.scale_factor)
                scaled_height = int(img_height * self.scale_factor)
                
                # Offset per centrare l'immagine
                offset_x = (canvas_width - scaled_width) // 2
                offset_y = (canvas_height - scaled_height) // 2
                
                # Coordinate relative all'immagine scalata
                rel_x1 = max(0, min(self.start_x, event.x) - offset_x)
                rel_y1 = max(0, min(self.start_y, event.y) - offset_y)
                rel_x2 = min(scaled_width, max(self.start_x, event.x) - offset_x)
                rel_y2 = min(scaled_height, max(self.start_y, event.y) - offset_y)
                
                # Converti alle coordinate dell'immagine originale
                orig_x1 = int(rel_x1 / self.scale_factor)
                orig_y1 = int(rel_y1 / self.scale_factor)
                orig_x2 = int(rel_x2 / self.scale_factor)
                orig_y2 = int(rel_y2 / self.scale_factor)
                
                self.crop_coords = (orig_x1, orig_y1, orig_x2, orig_y2)
                
    def get_crop_coordinates(self) -> Optional[Tuple[int, int, int, int]]:
        """Restituisce le coordinate del crop nell'immagine originale"""
        return self.crop_coords
        
    def clear_selection(self):
        """Cancella la selezione corrente"""
        if self.rect_id:
            self.delete(self.rect_id)
            self.rect_id = None
        self.crop_coords = None
    
    def rotate_image(self, angle: float):
        """Ruota l'immagine dell'angolo specificato"""
        if self.original_image is None:
            return
        
        try:
            self.rotation_angle = (self.rotation_angle + angle) % 360
            # Ruota l'immagine originale
            self.image = self.original_image.rotate(-self.rotation_angle, expand=True, fillcolor='white')
            self.fit_image_to_canvas()
            self.clear_selection()  # Cancella la selezione dopo la rotazione
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella rotazione: {e}")
        self.start_x = None
        self.start_y = None

class KatanaGUI:
    """Interfaccia grafica principale per Katana"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Katana GUI - Ritaglio Manuale e Addestramento")
        self.root.geometry("1400x900")
        
        self.processor = KatanaProcessor(learning_mode=True)
        self.current_images = []
        self.current_image_index = 0
        self.current_pdf_path = None
        
        # Variabili per il controllo dei processi
        self.processing_active = False
        self.stop_processing = False
        
        self.setup_ui()
        self.setup_logging()
        
    def stop_processes(self):
        """Interrompe tutti i processi attivi"""
        if self.processing_active:
            self.stop_processing = True
            self.log("Richiesta di interruzione processi...")
        else:
            messagebox.showinfo("Info", "Nessun processo attivo da interrompere")
    
    def check_stop_processing(self):
        """Callback per controllare se interrompere l'elaborazione"""
        self.root.update()  # Aggiorna la GUI per processare eventi
        return self.stop_processing
    
    def update_progress(self, value: float, status: str = None):
        """Aggiorna la barra di progresso e lo stato"""
        self.progress_var.set(value)
        if status:
            self.status_var.set(status)
        self.root.update_idletasks()
    
    def reset_progress(self):
        """Resetta la barra di progresso"""
        self.progress_var.set(0)
        self.status_var.set("Pronto")
        self.root.update_idletasks()
        
    def load_logo(self, parent_frame):
        """Carica e mostra l'icona Itto nell'header"""
        try:
            # Prova a caricare l'icona Itto ridimensionata
            icon_path = "itto_icon_64.png"
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                self.icon_photo = ImageTk.PhotoImage(icon_img)
                
                # Frame per centrare l'icona
                header_container = ttk.Frame(parent_frame)
                header_container.pack(fill=tk.X)
                
                # Label con l'icona
                icon_label = ttk.Label(header_container, image=self.icon_photo)
                icon_label.pack(side=tk.LEFT, padx=(0, 15))
                
                # Titolo accanto all'icona
                title_label = ttk.Label(header_container, text="KATANA - Sistema di Elaborazione PDF", 
                                      font=('Arial', 12, 'bold'))
                title_label.pack(side=tk.LEFT, pady=5)
                
                # Sottotitolo con icona Itto
                subtitle_label = ttk.Label(header_container, text="⚡ Powered by Itto", 
                                         font=('Arial', 9, 'italic'), foreground='#666666')
                subtitle_label.pack(side=tk.LEFT, padx=(10, 0), pady=5)
                
            else:
                # Se l'icona non esiste, mostra solo il titolo
                title_label = ttk.Label(parent_frame, text="🗡️ KATANA - Sistema di Elaborazione PDF", 
                                      font=('Arial', 14, 'bold'))
                title_label.pack(pady=5)
                
        except Exception as e:
            # In caso di errore, mostra solo il titolo con emoji
            title_label = ttk.Label(parent_frame, text="🗡️ KATANA - Sistema di Elaborazione PDF", 
                                  font=('Arial', 14, 'bold'))
            title_label.pack(pady=5)
            self.log(f"Errore nel caricamento icona: {e}")
    
    def setup_logging(self):
        """Configura il logging per la GUI"""
        self.logger = logging.getLogger("KatanaGUI")
        self.logger.setLevel(logging.INFO)
        
    def setup_ui(self):
        """Configura l'interfaccia utente"""
        # Frame principale
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame header con logo
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Carica e mostra il logo
        self.load_logo(header_frame)
        
        # Frame superiore per i controlli
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pulsanti di controllo
        ttk.Button(control_frame, text="Carica PDF", command=self.load_pdf).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Carica Immagini", command=self.load_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Elabora PDF", command=self.process_pdf).pack(side=tk.LEFT, padx=(0, 5))
        
        # Pulsante stop processi
        self.stop_button = ttk.Button(control_frame, text="⏹ Stop Processi", command=self.stop_processes, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(5, 10))
        
        # Separatore
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Controlli navigazione
        ttk.Button(control_frame, text="◀ Precedente", command=self.prev_image).pack(side=tk.LEFT, padx=(5, 2))
        self.image_label = ttk.Label(control_frame, text="Nessuna immagine")
        self.image_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Successiva ▶", command=self.next_image).pack(side=tk.LEFT, padx=(2, 5))
        
        # Frame centrale con pannelli
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pannello sinistro - Canvas per l'immagine
        left_frame = ttk.LabelFrame(content_frame, text="Immagine e Ritaglio")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Canvas per l'immagine
        self.canvas = ImageCropCanvas(left_frame, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame per i controlli del crop
        crop_control_frame = ttk.Frame(left_frame)
        crop_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Prima riga di controlli - Ritaglio
        crop_row1 = ttk.Frame(crop_control_frame)
        crop_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(crop_row1, text="Applica Ritaglio", command=self.apply_crop).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row1, text="Cancella Selezione", command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row1, text="Salva Ritaglio", command=self.save_crop).pack(side=tk.LEFT)
        
        # Seconda riga di controlli - Rotazione
        crop_row2 = ttk.Frame(crop_control_frame)
        crop_row2.pack(fill=tk.X)
        
        ttk.Label(crop_row2, text="Rotazione:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row2, text="↺ 90°", command=lambda: self.rotate_image(-90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(crop_row2, text="↻ 90°", command=lambda: self.rotate_image(90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(crop_row2, text="↺ 180°", command=lambda: self.rotate_image(180)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row2, text="Reset", command=self.reset_rotation).pack(side=tk.LEFT)
        
        # Pannello destro - Feedback e controlli
        right_frame = ttk.LabelFrame(content_frame, text="Feedback e Addestramento")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.configure(width=350)
        right_frame.pack_propagate(False)
        
        # Informazioni immagine corrente
        info_frame = ttk.LabelFrame(right_frame, text="Informazioni Immagine")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=4, width=40)
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Coordinate del crop
        coord_frame = ttk.LabelFrame(right_frame, text="Coordinate Ritaglio")
        coord_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(coord_frame, text="X1:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.x1_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.x1_var, width=8).grid(row=0, column=1, padx=2)
        
        ttk.Label(coord_frame, text="Y1:").grid(row=0, column=2, sticky=tk.W, padx=2)
        self.y1_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.y1_var, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(coord_frame, text="X2:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.x2_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.x2_var, width=8).grid(row=1, column=1, padx=2)
        
        ttk.Label(coord_frame, text="Y2:").grid(row=1, column=2, sticky=tk.W, padx=2)
        self.y2_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.y2_var, width=8).grid(row=1, column=3, padx=2)
        
        ttk.Button(coord_frame, text="Applica Coordinate", command=self.apply_manual_coords).grid(row=2, column=0, columnspan=4, pady=5)
        
        # Feedback per l'addestramento
        feedback_frame = ttk.LabelFrame(right_frame, text="Feedback per Addestramento")
        feedback_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.feedback_var = tk.StringVar(value="perfect")
        feedback_options = [
            ("Perfetto", "perfect"),
            ("Ritaglio Eccessivo", "excessive_cropping"),
            ("Ritaglio Insufficiente", "insufficient_cropping"),
            ("Ritaglio Leggero", "light_cropping"),
            ("Nessun Cambiamento", "no_change"),
            ("Zoom Insufficiente", "insufficient_zoom"),
            ("Zoom Eccessivo", "excessive_zoom")
        ]
        
        for text, value in feedback_options:
            ttk.Radiobutton(feedback_frame, text=text, variable=self.feedback_var, value=value).pack(anchor=tk.W, padx=5)
        
        # Note aggiuntive
        ttk.Label(feedback_frame, text="Note:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.notes_text = scrolledtext.ScrolledText(feedback_frame, height=3, width=40)
        self.notes_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Pulsanti azione
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(action_frame, text="Salva Feedback", command=self.save_feedback).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Addestra Agente", command=self.train_agent).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Visualizza Statistiche", command=self.show_stats).pack(fill=tk.X, pady=2)
        
        # Log area
        log_frame = ttk.LabelFrame(right_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Barra di progresso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            log_frame, 
            variable=self.progress_var, 
            maximum=100, 
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Label per stato corrente
        self.status_var = tk.StringVar(value="Pronto")
        self.status_label = ttk.Label(log_frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, width=40)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def load_pdf(self):
        """Carica un file PDF"""
        file_path = filedialog.askopenfilename(
            title="Seleziona PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.current_pdf_path = file_path
            self.log(f"PDF caricato: {Path(file_path).name}")
            
    def load_images(self):
        """Carica immagini da directory o file singoli"""
        # Chiedi all'utente cosa vuole fare
        choice = messagebox.askyesnocancel(
            "Carica Immagini",
            "Vuoi caricare:\n\n• SÌ = Una directory con più immagini\n• NO = File singoli\n• ANNULLA = Annulla operazione"
        )
        
        if choice is True:  # Directory
            directory = filedialog.askdirectory(title="Seleziona directory con immagini")
            if directory:
                self.load_images_from_directory(directory)
        elif choice is False:  # File singoli
            files = filedialog.askopenfilenames(
                title="Seleziona file immagine",
                filetypes=[
                    ("Immagini", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("PNG", "*.png"),
                    ("TIFF", "*.tiff *.tif"),
                    ("BMP", "*.bmp"),
                    ("Tutti i file", "*.*")
                ]
            )
            if files:
                self.load_image_files(files)
        # Se choice è None (ANNULLA), non fare nulla
            
    def load_images_from_directory(self, directory: str):
        """Carica tutte le immagini da una directory"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        self.current_images = []
        
        for file_path in Path(directory).rglob('*'):
            if file_path.suffix.lower() in image_extensions:
                self.current_images.append(str(file_path))
                
        self.current_images.sort()
        self.current_image_index = 0
        
        if self.current_images:
            self.load_current_image()
            self.log(f"Caricate {len(self.current_images)} immagini da {directory}")
        else:
            self.log("Nessuna immagine trovata nella directory")
            
    def load_image_files(self, file_paths: tuple):
        """Carica file immagine specifici selezionati dall'utente"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        self.current_images = []
        
        for file_path in file_paths:
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() in image_extensions:
                self.current_images.append(str(file_path))
            else:
                self.log(f"File ignorato (formato non supportato): {file_path_obj.name}")
                
        self.current_images.sort()
        self.current_image_index = 0
        
        if self.current_images:
            self.load_current_image()
            self.log(f"Caricati {len(self.current_images)} file immagine")
        else:
            self.log("Nessun file immagine valido selezionato")
            
    def process_pdf(self):
        """Elabora il PDF corrente"""
        if not self.current_pdf_path:
            messagebox.showwarning("Attenzione", "Seleziona prima un PDF")
            return
        
        if self.processing_active:
            messagebox.showwarning("Attenzione", "Elaborazione già in corso")
            return
            
        try:
            self.processing_active = True
            self.stop_processing = False
            self.stop_button.config(state="normal")
            
            self.update_progress(0, "Inizializzazione...")
            self.log("Elaborazione PDF in corso...", "PROGRESS")
            
            # Simula progresso durante l'elaborazione
            self.update_progress(10, "Lettura PDF...")
            self.log("Lettura e analisi del file PDF...", "PROGRESS")
            self.root.update()
            
            # Elabora il PDF con controllo di interruzione
            self.update_progress(30, "Estrazione immagini...")
            self.log("Estrazione immagini dalle pagine PDF...", "PROGRESS")
            
            # Usa process_pdf_file per includere auto-cropping
            result = self.processor.process_pdf_file(
                self.current_pdf_path, 
                crop_content=True,  # Abilita auto-cropping
                target_format="A4"
            )
            
            if self.stop_processing:
                self.log("Elaborazione interrotta dall'utente", "WARNING")
                self.update_progress(0, "Interrotto")
                messagebox.showinfo("Interrotto", "Elaborazione interrotta")
            elif result['success']:
                self.update_progress(60, "Auto-cropping in corso...")
                self.log("Esecuzione auto-cropping e zoom automatico...", "PROGRESS")
                self.root.update()
                
                self.update_progress(80, "Caricamento immagini...")
                self.log("Caricamento immagini elaborate nella GUI...", "PROGRESS")
                
                # Carica le immagini elaborate
                pdf_name = Path(self.current_pdf_path).stem
                output_dir = self.processor.base_output_dir / pdf_name
                self.load_images_from_directory(str(output_dir))
                
                # Conta immagini originali e ritagliate
                original_count = len(result['output_images'])
                cropped_count = len(result['cropped_images'])
                total_count = original_count + cropped_count
                
                self.update_progress(100, "Completato")
                self.log(f"PDF elaborato con successo. {original_count} immagini estratte + {cropped_count} ritagliate = {total_count} totali.", "SUCCESS")
                messagebox.showinfo("Successo", f"PDF elaborato con successo!\nImmagini originali: {original_count}\nImmagini ritagliate: {cropped_count}\nTotale: {total_count}")
            else:
                self.update_progress(100, "Errore nell'elaborazione")
                error_msg = "; ".join(result.get('errors', ['Errore sconosciuto']))
                self.log(f"Errore nell'elaborazione: {error_msg}", "ERROR")
                messagebox.showerror("Errore", f"Errore nell'elaborazione:\n{error_msg}")
                
        except Exception as e:
            self.update_progress(0, "Errore")
            self.log(f"Errore nell'elaborazione: {e}", "ERROR")
            messagebox.showerror("Errore", f"Errore nell'elaborazione: {e}")
        finally:
            self.processing_active = False
            self.stop_processing = False
            self.stop_button.config(state="disabled")
            # Reset progress dopo 3 secondi se completato con successo
            if not self.stop_processing and 'result' in locals() and result.get('success', False):
                self.root.after(3000, self.reset_progress)
            
    def load_current_image(self):
        """Carica l'immagine corrente nel canvas"""
        if not self.current_images:
            return
            
        image_path = self.current_images[self.current_image_index]
        if self.canvas.load_image(image_path):
            self.update_image_info()
            self.update_image_label()
            self.canvas.clear_selection()
            self.clear_coordinates()
            
    def update_image_info(self):
        """Aggiorna le informazioni dell'immagine corrente"""
        if not self.current_images:
            return
            
        image_path = self.current_images[self.current_image_index]
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = Path(image_path).stat().st_size
                
            info = f"File: {Path(image_path).name}\n"
            info += f"Dimensioni: {width}x{height}\n"
            info += f"Dimensione: {file_size // 1024} KB\n"
            info += f"Percorso: {image_path}"
            
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
            
        except Exception as e:
            self.log(f"Errore nel caricamento info immagine: {e}")
            
    def update_image_label(self):
        """Aggiorna l'etichetta con il numero dell'immagine"""
        if self.current_images:
            self.image_label.config(text=f"Immagine {self.current_image_index + 1} di {len(self.current_images)}")
        else:
            self.image_label.config(text="Nessuna immagine")
            
    def prev_image(self):
        """Vai all'immagine precedente"""
        if self.current_images and self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
            
    def next_image(self):
        """Vai all'immagine successiva"""
        if self.current_images and self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.load_current_image()
            
    def apply_crop(self):
        """Applica il ritaglio selezionato"""
        coords = self.canvas.get_crop_coordinates()
        if coords:
            self.x1_var.set(str(coords[0]))
            self.y1_var.set(str(coords[1]))
            self.x2_var.set(str(coords[2]))
            self.y2_var.set(str(coords[3]))
            self.log(f"Coordinate ritaglio: {coords}")
        else:
            messagebox.showwarning("Attenzione", "Seleziona prima un'area da ritagliare")
            
    def apply_manual_coords(self):
        """Applica le coordinate inserite manualmente"""
        try:
            x1 = int(self.x1_var.get())
            y1 = int(self.y1_var.get())
            x2 = int(self.x2_var.get())
            y2 = int(self.y2_var.get())
            
            if x1 >= x2 or y1 >= y2:
                messagebox.showerror("Errore", "Coordinate non valide")
                return
                
            self.canvas.crop_coords = (x1, y1, x2, y2)
            self.log(f"Coordinate manuali applicate: ({x1}, {y1}, {x2}, {y2})")
            
        except ValueError:
            messagebox.showerror("Errore", "Inserisci coordinate numeriche valide")
            
    def clear_selection(self):
        """Cancella la selezione corrente"""
        self.canvas.clear_selection()
        self.clear_coordinates()
        
    def clear_coordinates(self):
        """Cancella i campi delle coordinate"""
        self.x1_var.set("")
        self.y1_var.set("")
        self.x2_var.set("")
        self.y2_var.set("")
    
    def rotate_image(self, angle: float):
        """Ruota l'immagine corrente"""
        if not self.current_images:
            messagebox.showwarning("Attenzione", "Nessuna immagine caricata")
            return
        
        self.canvas.rotate_image(angle)
        self.log(f"Immagine ruotata di {angle} gradi")
    
    def reset_rotation(self):
        """Resetta la rotazione dell'immagine"""
        if not self.current_images:
            messagebox.showwarning("Attenzione", "Nessuna immagine caricata")
            return
        
        if self.canvas.original_image:
            self.canvas.rotation_angle = 0
            self.canvas.image = self.canvas.original_image.copy()
            self.canvas.fit_image_to_canvas()
            self.canvas.clear_selection()
            self.log("Rotazione resettata")
        
    def save_crop(self):
        """Salva l'immagine ritagliata e registra feedback per addestramento"""
        if not self.current_images:
            messagebox.showwarning("Attenzione", "Nessuna immagine caricata")
            return
            
        coords = self.canvas.get_crop_coordinates()
        if not coords:
            messagebox.showwarning("Attenzione", "Seleziona prima un'area da ritagliare")
            return
            
        try:
            image_path = self.current_images[self.current_image_index]
            base_path = Path(image_path)
            
            # Determina se è un file elaborato dall'IA (contiene "_cropped")
            is_ai_processed = "_cropped" in base_path.stem
            
            with Image.open(image_path) as img:
                # Applica la rotazione se presente nel canvas
                if hasattr(self.canvas, 'rotation_angle') and self.canvas.rotation_angle != 0:
                    img = img.rotate(-self.canvas.rotation_angle, expand=True, fillcolor='white')
                    self.log(f"Rotazione applicata: {self.canvas.rotation_angle}°", "INFO")
                
                cropped = img.crop(coords)
                
                # Applica ridimensionamento automatico come fa l'IA
                if hasattr(self, 'processor') and self.processor:
                    import cv2
                    import numpy as np
                    
                    # Converti PIL a OpenCV per il ridimensionamento
                    cv_image = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
                    
                    # Applica il ridimensionamento al formato target
                    resized_cv = self.processor._resize_to_target_format(cv_image, "A4")
                    
                    # Riconverti a PIL
                    cropped = Image.fromarray(cv2.cvtColor(resized_cv, cv2.COLOR_BGR2RGB))
                    self.log("Ridimensionamento automatico applicato al formato A4", "INFO")
                
                if is_ai_processed:
                    # Sostituisci SEMPRE il file _cropped con il ritaglio manuale
                    original_path = image_path
                    backup_path = base_path.parent / f"{base_path.stem}_ai_backup{base_path.suffix}"
                    
                    # Crea backup del file IA solo se non esiste già
                    import shutil
                    if not backup_path.exists():
                        shutil.copy2(original_path, backup_path)
                        self.log(f"Backup IA creato: {backup_path.name}", "INFO")
                    
                    # Sostituisci con il ritaglio manuale
                    cropped.save(original_path)
                    
                    self.log(f"File IA sovrascritto con ritaglio manuale: {base_path.name}", "SUCCESS")
                    
                    # Registra feedback di addestramento automaticamente
                    self._save_training_feedback(image_path, coords, "manual_correction")
                    
                    messagebox.showinfo("Successo", 
                        f"Ritaglio manuale salvato!\n"
                        f"File IA sovrascritto: {base_path.name}\n"
                        f"Feedback registrato per addestramento")
                else:
                    # Salva come nuovo file per immagini non elaborate dall'IA
                    crop_path = base_path.parent / f"{base_path.stem}_manual_crop{base_path.suffix}"
                    cropped.save(crop_path)
                    
                    self.log(f"Ritaglio manuale salvato: {crop_path.name}", "SUCCESS")
                    
                    # Registra feedback per nuovi ritagli
                    self._save_training_feedback(image_path, coords, "new_manual_crop")
                    
                    messagebox.showinfo("Successo", 
                        f"Ritaglio salvato come: {crop_path.name}\n"
                        f"Feedback registrato per addestramento")
                
        except Exception as e:
            self.log(f"Errore nel salvataggio: {e}", "ERROR")
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")
    
    def _save_training_feedback(self, image_path: str, coords: tuple, feedback_type: str):
        """Salva automaticamente il feedback per l'addestramento"""
        try:
            # Estrai informazioni dal nome del file
            file_name = Path(image_path).stem
            if "_page_" in file_name:
                parts = file_name.split("_page_")
                pdf_name = parts[0]
                page_info = parts[1].split("_")
                page_num = int(page_info[0])
            else:
                pdf_name = file_name
                page_num = 1
            
            # Ottieni feedback e note dalla GUI
            feedback = self.feedback_var.get()
            notes = self.notes_text.get(1.0, tk.END).strip()
            
            # Aggiungi informazioni sul tipo di feedback
            if feedback_type == "manual_correction":
                notes = f"[CORREZIONE MANUALE] {notes}" if notes else "[CORREZIONE MANUALE] Ritaglio corretto manualmente"
                feedback = "manual_correction"  # Forza il feedback per correzioni manuali
            elif feedback_type == "new_manual_crop":
                notes = f"[NUOVO RITAGLIO] {notes}" if notes else "[NUOVO RITAGLIO] Ritaglio manuale su immagine originale"
            
            # Salva il feedback usando il processor
            if hasattr(self, 'processor'):
                # Il metodo save_feedback di KatanaProcessor accetta solo 4 parametri
                self.processor.save_feedback(pdf_name, page_num, feedback, coords)
                self.log(f"Feedback addestramento salvato: {feedback_type} per {pdf_name} pagina {page_num}", "SUCCESS")
            else:
                # Fallback: salva direttamente nel file JSON
                self._save_feedback_direct(pdf_name, page_num, feedback, coords, notes)
                self.log(f"Feedback addestramento salvato (diretto): {feedback_type}", "SUCCESS")
                
        except Exception as e:
            self.log(f"Errore nel salvataggio feedback: {e}", "ERROR")
    
    def _save_feedback_direct(self, pdf_name: str, page_num: int, feedback: str, coords: tuple, notes: str):
        """Salva il feedback direttamente nel file JSON"""
        feedback_file = Path("katana_learning.json")
        
        # Carica feedback esistenti
        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"feedback_data": []}
        
        # Aggiungi nuovo feedback
        feedback_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "pdf_name": pdf_name,
            "page_number": page_num,
            "feedback": feedback,
            "coordinates": coords,
            "notes": notes,
            "manual_training": True
        }
        
        data["feedback_data"].append(feedback_entry)
        
        # Salva il file aggiornato
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def save_feedback(self):
        """Salva il feedback per l'addestramento"""
        if not self.current_images:
            messagebox.showwarning("Attenzione", "Nessuna immagine caricata")
            return
            
        image_path = self.current_images[self.current_image_index]
        feedback = self.feedback_var.get()
        notes = self.notes_text.get(1.0, tk.END).strip()
        coords = self.canvas.get_crop_coordinates()
        
        try:
            self.log("Inizio salvataggio feedback manuale...", "PROGRESS")
            
            # Estrai informazioni dal nome del file
            file_name = Path(image_path).stem
            if "_page_" in file_name:
                parts = file_name.split("_page_")
                pdf_name = parts[0]
                page_info = parts[1].split("_")
                page_num = int(page_info[0])
            else:
                pdf_name = file_name
                page_num = 1
            
            self.log(f"Analisi file: {pdf_name}, pagina {page_num}", "INFO")
            self.log(f"Feedback selezionato: {feedback}", "INFO")
            if coords:
                self.log(f"Coordinate ritaglio: {coords}", "INFO")
            else:
                self.log("Nessuna coordinata di ritaglio specificata", "WARNING")
                
            # Salva il feedback
            if hasattr(self, 'processor'):
                # Il metodo save_feedback di KatanaProcessor accetta solo 4 parametri
                self.processor.save_feedback(pdf_name, page_num, feedback, coords)
            else:
                self._save_feedback_direct(pdf_name, page_num, feedback, coords, notes)
            
            # Log con note se presenti
            log_msg = f"Feedback salvato: {feedback} per {pdf_name} pagina {page_num}"
            if notes:
                log_msg += f" - Note: {notes}"
            if coords:
                log_msg += f" - Coordinate: {coords}"
            
            self.log(log_msg, "SUCCESS")
            messagebox.showinfo("Successo", "Feedback salvato per l'addestramento")
            
        except Exception as e:
            self.log(f"Errore nel salvataggio feedback: {e}", "ERROR")
            messagebox.showerror("Errore", f"Errore nel salvataggio feedback: {e}")
            
    def train_agent(self):
        """Avvia l'addestramento dell'agente"""
        try:
            self.log("Inizio processo di addestramento agente...", "PROGRESS")
            
            # Aggiorna i parametri adattivi basati sul feedback
            feedback_data = self.processor.learning_data.get('feedback_history', [])
            
            if not feedback_data:
                self.log("Nessun feedback disponibile per l'addestramento", "WARNING")
                messagebox.showwarning("Attenzione", "Nessun feedback disponibile per l'addestramento")
                return
                
            self.log(f"Trovati {len(feedback_data)} feedback per l'addestramento", "INFO")
                
            # Conta i tipi di feedback
            feedback_counts = {}
            for entry in feedback_data:
                feedback_type = entry.get('feedback', 'unknown')
                feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
                
            self.log("Analisi feedback completata", "INFO")
            self.log(f"Distribuzione feedback: {feedback_counts}", "INFO")
            
            # Simula l'addestramento aggiornando i parametri
            recent_feedback = feedback_data[-10:]  # Usa gli ultimi 10 feedback
            self.log(f"Elaborazione degli ultimi {len(recent_feedback)} feedback...", "PROGRESS")
            
            for i, entry in enumerate(recent_feedback):
                feedback_type = entry.get('feedback', 'perfect')
                self.processor._update_adaptive_params(feedback_type)
                self.log(f"Processato feedback {i+1}/{len(recent_feedback)}: {feedback_type}", "INFO")
                
            self.log("Addestramento completato con successo", "SUCCESS")
            self.log(f"Parametri aggiornati: {self.processor.adaptive_params}", "INFO")
            messagebox.showinfo("Successo", "Addestramento completato")
            
        except Exception as e:
            self.log(f"Errore nell'addestramento: {e}", "ERROR")
            messagebox.showerror("Errore", f"Errore nell'addestramento: {e}")
            
    def show_stats(self):
        """Mostra le statistiche di apprendimento"""
        try:
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Statistiche Apprendimento")
            stats_window.geometry("600x400")
            
            stats_text = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
            stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Carica i dati di apprendimento
            learning_data = self.processor.learning_data
            feedback_history = learning_data.get('feedback_history', [])
            adaptive_params = learning_data.get('adaptive_params', {})
            
            # Genera statistiche
            stats = "=== STATISTICHE APPRENDIMENTO KATANA ===\n\n"
            
            # Parametri attuali
            stats += "PARAMETRI ADATTIVI ATTUALI:\n"
            for param, value in adaptive_params.items():
                stats += f"  {param}: {value}\n"
            stats += "\n"
            
            # Statistiche feedback
            if feedback_history:
                feedback_counts = {}
                pdf_counts = {}
                
                for entry in feedback_history:
                    feedback_type = entry.get('feedback', 'unknown')
                    pdf_name = entry.get('pdf_name', 'unknown')
                    
                    feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
                    pdf_counts[pdf_name] = pdf_counts.get(pdf_name, 0) + 1
                    
                stats += "DISTRIBUZIONE FEEDBACK:\n"
                total_feedback = len(feedback_history)
                for feedback_type, count in sorted(feedback_counts.items()):
                    percentage = (count / total_feedback) * 100
                    stats += f"  {feedback_type}: {count} ({percentage:.1f}%)\n"
                    
                stats += "\nPDF ELABORATI:\n"
                for pdf_name, count in sorted(pdf_counts.items()):
                    stats += f"  {pdf_name}: {count} feedback\n"
                    
                stats += f"\nTOTALE FEEDBACK: {total_feedback}\n"
            else:
                stats += "Nessun feedback disponibile\n"
                
            stats_text.insert(1.0, stats)
            stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log(f"Errore nella visualizzazione statistiche: {e}")
            messagebox.showerror("Errore", f"Errore nella visualizzazione statistiche: {e}")
            
    def log(self, message: str, level: str = "INFO"):
        """Aggiunge un messaggio al log con timestamp e livello"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        
        # Configura i tag per i colori
        if not hasattr(self, '_log_tags_configured'):
            self.log_text.tag_configure("INFO", foreground="black")
            self.log_text.tag_configure("SUCCESS", foreground="green")
            self.log_text.tag_configure("WARNING", foreground="orange")
            self.log_text.tag_configure("ERROR", foreground="red")
            self.log_text.tag_configure("PROGRESS", foreground="blue")
            self._log_tags_configured = True
        
        # Inserisci il messaggio con il tag appropriato
        start_pos = self.log_text.index(tk.END + "-1c")
        self.log_text.insert(tk.END, log_message)
        end_pos = self.log_text.index(tk.END + "-1c")
        self.log_text.tag_add(level, start_pos, end_pos)
        
        self.log_text.see(tk.END)
        
        # Mantieni solo le ultime 100 righe
        lines = self.log_text.get("1.0", tk.END).split("\n")
        if len(lines) > 100:
            self.log_text.delete("1.0", f"{len(lines) - 100}.0")
        
        self.root.update_idletasks()
            
    def run(self):
        """Avvia l'interfaccia grafica"""
        self.root.mainloop()

def main():
    """Funzione principale"""
    app = KatanaGUI()
    app.run()

if __name__ == "__main__":
    main()