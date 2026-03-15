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
from katana_sounds import KatanaSoundManager
import logging
from katana_i18n import i18n, _

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
            messagebox.showerror(_("error_title"), _("image_load_error", error=e))
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
            messagebox.showerror(_("error_title"), _("error_generic", error=e))
        self.start_x = None
        self.start_y = None

class KatanaGUI:
    """Interfaccia grafica principale per Katana"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(_("app_title"))
        self.root.geometry("1400x900")
        
        # Inizializza con profilo generale
        self.current_samurai_profile = "generale"
        self.processor = KatanaProcessor(learning_mode=True, samurai_profile=self.current_samurai_profile)
        self.current_images = []
        self.current_image_index = 0
        self.current_pdf_path = None
        
        # Variabili per il controllo dei processi
        self.processing_active = False
        self.stop_processing = False
        
        # Inizializza il sistema audio
        self.sound_manager = KatanaSoundManager()
        
        self.setup_ui()
        self.setup_logging()
        
        # Riproduce il suono di avvio
        self.sound_manager.play_startup_sound()
        
    def stop_processes(self):
        """Interrompe tutti i processi attivi"""
        if self.processing_active:
            self.stop_processing = True
            self.log(_("stop_request"))
        else:
            messagebox.showinfo(_("info"), _("no_process_active"))
    
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
                title_label = ttk.Label(header_container, text=_("header_title_simple"), 
                                      font=('Arial', 12, 'bold'))
                title_label.pack(side=tk.LEFT, pady=5)
                
                # Sottotitolo con icona Itto
                subtitle_label = ttk.Label(header_container, text=_("powered_by"), 
                                         font=('Arial', 9, 'italic'), foreground='#666666')
                subtitle_label.pack(side=tk.LEFT, padx=(10, 0), pady=5)
                
            else:
                # Se l'icona non esiste, mostra solo il titolo
                title_label = ttk.Label(parent_frame, text=_("header_title_simple"), 
                                      font=('Arial', 14, 'bold'))
                title_label.pack(pady=5)
                
        except Exception as e:
            # In caso di errore, mostra solo il titolo con emoji
            title_label = ttk.Label(parent_frame, text=_("header_title_simple"), 
                                  font=('Arial', 14, 'bold'))
            title_label.pack(pady=5)
            self.log(_("icon_error", error=e))
    
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
        ttk.Button(control_frame, text=_("load_pdf"), command=self.load_pdf).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text=_("load_images"), command=self.load_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text=_("process_pdf"), command=self.process_pdf).pack(side=tk.LEFT, padx=(0, 5))
        
        # Pulsante stop processi
        self.stop_button = ttk.Button(control_frame, text=_("stop_processes"), command=self.stop_processes, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(5, 10))
        
        # Separatore
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Selezione profilo Samurai
        ttk.Label(control_frame, text=_("samurai_profile")).pack(side=tk.LEFT, padx=(5, 2))
        self.profile_var = tk.StringVar(value=self.current_samurai_profile)
        self.profile_combo = ttk.Combobox(control_frame, textvariable=self.profile_var, 
                                         values=list(self.processor.get_available_profiles().keys()),
                                         state="readonly", width=15)
        self.profile_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)
        
        # Separatore
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Controllo rilevamento automatico ratio
        self.auto_ratio_var = tk.BooleanVar(value=self.processor.is_auto_ratio_detection_enabled())
        self.auto_ratio_check = ttk.Checkbutton(control_frame, text=_("auto_ratio"), 
                                               variable=self.auto_ratio_var,
                                               command=self.toggle_auto_ratio)
        self.auto_ratio_check.pack(side=tk.LEFT, padx=(5, 10))
        
        # Controllo rilevamento automatico orientamento
        self.auto_orientation_var = tk.BooleanVar(value=True)
        self.auto_orientation_check = ttk.Checkbutton(control_frame, text=_("auto_orient"), 
                                                     variable=self.auto_orientation_var,
                                                     command=self.toggle_auto_orientation)
        self.auto_orientation_check.pack(side=tk.LEFT, padx=(5, 10))
        
        # Separatore
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Controlli navigazione
        ttk.Button(control_frame, text=_("prev_image"), command=self.prev_image).pack(side=tk.LEFT, padx=(5, 2))
        self.image_label = ttk.Label(control_frame, text=_("no_image"))
        self.image_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text=_("next_image"), command=self.next_image).pack(side=tk.LEFT, padx=(2, 5))
        
        # Selettore lingua (aggiunto a destra)
        lang_frame = ttk.Frame(control_frame)
        lang_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Label(lang_frame, text="🌐").pack(side=tk.LEFT, padx=2)
        
        self.lang_var = tk.StringVar(value=i18n.current_lang)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, 
                                 values=["it", "en"], state="readonly", width=3)
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", self.change_language)
        
        # Frame centrale con pannelli
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pannello sinistro - Canvas per l'immagine
        left_frame = ttk.LabelFrame(content_frame, text=_("image_crop_panel"))
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
        
        ttk.Button(crop_row1, text=_("apply_crop"), command=self.apply_crop).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row1, text=_("clear_selection"), command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row1, text=_("save_crop"), command=self.save_crop).pack(side=tk.LEFT)
        
        # Seconda riga di controlli - Rotazione e Orientamento
        crop_row2 = ttk.Frame(crop_control_frame)
        crop_row2.pack(fill=tk.X)
        
        ttk.Label(crop_row2, text=_("rotation")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row2, text="↺ 90°", command=lambda: self.rotate_image(-90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(crop_row2, text="↻ 90°", command=lambda: self.rotate_image(90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(crop_row2, text="↺ 180°", command=lambda: self.rotate_image(180)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row2, text=_("auto_orient"), command=self.auto_correct_current_orientation).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(crop_row2, text=_("reset"), command=self.reset_rotation).pack(side=tk.LEFT)
        
        # Pannello destro - Feedback e controlli
        right_frame = ttk.LabelFrame(content_frame, text=_("feedback_panel"))
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.configure(width=350)
        right_frame.pack_propagate(False)
        
        # Informazioni immagine corrente
        info_frame = ttk.LabelFrame(right_frame, text=_("image_info"))
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=4, width=40)
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Coordinate del crop
        coord_frame = ttk.LabelFrame(right_frame, text=_("crop_coords"))
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
        
        ttk.Button(coord_frame, text=_("apply_coords"), command=self.apply_manual_coords).grid(row=2, column=0, columnspan=4, pady=5)
        
        # Feedback per l'addestramento
        feedback_frame = ttk.LabelFrame(right_frame, text=_("feedback_training"))
        feedback_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.feedback_var = tk.StringVar(value="perfect")
        feedback_options = [
            (_("perfect"), "perfect"),
            (_("excessive_cropping"), "excessive_cropping"),
            (_("insufficient_cropping"), "insufficient_cropping"),
            (_("light_cropping"), "light_cropping"),
            (_("no_change"), "no_change"),
            (_("insufficient_zoom"), "insufficient_zoom"),
            (_("excessive_zoom"), "excessive_zoom")
        ]
        
        for text, value in feedback_options:
            ttk.Radiobutton(feedback_frame, text=text, variable=self.feedback_var, value=value).pack(anchor=tk.W, padx=5)
        
        # Note aggiuntive
        ttk.Label(feedback_frame, text=_("notes")).pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.notes_text = scrolledtext.ScrolledText(feedback_frame, height=3, width=40)
        self.notes_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Pulsanti azione
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(action_frame, text=_("save_feedback"), command=self.save_feedback).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text=_("train_agent"), command=self.train_agent).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text=_("view_stats"), command=self.show_stats).pack(fill=tk.X, pady=2)
        
        # Log area
        log_frame = ttk.LabelFrame(right_frame, text=_("log"))
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
        self.status_var = tk.StringVar(value=_("ready"))
        self.status_label = ttk.Label(log_frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, width=40)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def change_language(self, event=None):
        """Cambia la lingua dell'interfaccia"""
        new_lang = self.lang_var.get()
        if new_lang != i18n.current_lang:
            i18n.set_language(new_lang)
            messagebox.showinfo(_("restart_required"), _("restart_msg"))
        
    def load_pdf(self):
        """Carica un file PDF"""
        file_path = filedialog.askopenfilename(
            title=_("select_pdf"),
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.current_pdf_path = file_path
            self.log(f"PDF caricato: {Path(file_path).name}")
            
    def load_images(self):
        """Carica immagini da directory o file singoli"""
        # Chiedi all'utente cosa vuole fare
        choice = messagebox.askyesnocancel(
            _("load_images_title"),
            _("load_images_prompt")
        )
        
        if choice is True:  # Directory
            directory = filedialog.askdirectory(title=_("select_dir"))
            if directory:
                self.load_images_from_directory(directory)
        elif choice is False:  # File singoli
            files = filedialog.askopenfilenames(
                title=_("select_files"),
                filetypes=[
                    ("Immagini", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("PNG", "*.png"),
                    ("TIFF", "*.tiff *.tif"),
                    ("BMP", "*.bmp"),
                    (_("all_files"), "*.*")
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
            self.log(_("loaded_images_dir", count=len(self.current_images), path=directory))
        else:
            self.log(_("no_images_dir"))
            
    def load_image_files(self, file_paths: tuple):
        """Carica file immagine specifici selezionati dall'utente"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        self.current_images = []
        
        for file_path in file_paths:
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() in image_extensions:
                self.current_images.append(str(file_path))
            else:
                self.log(_("file_ignored", name=file_path_obj.name))
                
        self.current_images.sort()
        self.current_image_index = 0
        
        if self.current_images:
            self.load_current_image()
            self.log(_("loaded_images_files", count=len(self.current_images)))
        else:
            self.log(_("no_valid_images"))
            
    def process_pdf(self):
        """Elabora il PDF corrente"""
        if not self.current_pdf_path:
            messagebox.showwarning(_("warning"), _("select_pdf_first"))
            return
        
        if self.processing_active:
            messagebox.showwarning(_("warning"), _("processing_active"))
            return
            
        try:
            self.processing_active = True
            self.stop_processing = False
            self.stop_button.config(state="normal")
            
            self.update_progress(0, _("initializing"))
            self.log(_("processing_pdf"), "PROGRESS")
            
            # Simula progresso durante l'elaborazione
            self.update_progress(10, _("reading_pdf"))
            self.log(_("analyzing_pdf"), "PROGRESS")
            self.root.update()
            
            # Elabora il PDF con controllo di interruzione
            self.update_progress(30, _("extracting_images"))
            self.log(_("extracting_images_pages"), "PROGRESS")
            
            # Usa process_pdf_file per includere auto-cropping
            result = self.processor.process_pdf_file(
                self.current_pdf_path, 
                crop_content=True,  # Abilita auto-cropping
                target_format="A4",
                stop_callback=self.check_stop_processing,  # Passa il callback di interruzione
                progress_callback=self.update_progress  # Passa il callback di progresso
            )
            
            if self.stop_processing:
                self.log(_("processing_interrupted"), "WARNING")
                self.update_progress(0, _("interrupted"))
                messagebox.showinfo(_("interrupted"), _("processing_interrupted_title"))
            elif result['success']:
                self.update_progress(90, _("loading_images"))
                self.log(_("loading_images_gui"), "PROGRESS")
                
                # Carica le immagini elaborate
                pdf_name = Path(self.current_pdf_path).stem
                output_dir = self.processor.base_output_dir / pdf_name
                self.load_images_from_directory(str(output_dir))
                
                # Conta immagini originali e ritagliate
                original_count = len(result['output_images'])
                cropped_count = len(result['cropped_images'])
                total_count = original_count + cropped_count
                
                self.update_progress(100, _("completed"))
                self.log(_("success_log", original=original_count, cropped=cropped_count, total=total_count), "SUCCESS")
                
                # Riproduce il suono di completamento
                self.sound_manager.play_completion_sound()
                
                messagebox.showinfo(_("success_title"), _("success_msg", original=original_count, cropped=cropped_count, total=total_count))
            else:
                self.update_progress(100, _("processing_error"))
                error_msg = "; ".join(result.get('errors', [_("unknown_error")]))
                self.log(_("error_log", error=error_msg), "ERROR")
                messagebox.showerror(_("error_title"), _("error_msg", error=error_msg))
                
        except Exception as e:
            self.update_progress(0, "Errore")
            self.log(_("error_generic", error=e), "ERROR")
            messagebox.showerror(_("error_title"), _("error_generic", error=e))
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
            self.log(_("image_info_error", error=e))
            
    def update_image_label(self):
        """Aggiorna l'etichetta con il numero dell'immagine"""
        if self.current_images:
            self.image_label.config(text=_("image_counter", current=self.current_image_index + 1, total=len(self.current_images)))
        else:
            self.image_label.config(text=_("no_image"))
            
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
            self.log(_("crop_coords_log", coords=coords))
        else:
            messagebox.showwarning(_("warning"), _("select_crop_area"))
            
    def apply_manual_coords(self):
        """Applica le coordinate inserite manualmente"""
        try:
            x1 = int(self.x1_var.get())
            y1 = int(self.y1_var.get())
            x2 = int(self.x2_var.get())
            y2 = int(self.y2_var.get())
            
            if x1 >= x2 or y1 >= y2:
                messagebox.showerror(_("error_title"), _("invalid_coords"))
                return
                
            self.canvas.crop_coords = (x1, y1, x2, y2)
            self.log(_("manual_coords_applied", x1=x1, y1=y1, x2=x2, y2=y2))
            
        except ValueError:
            messagebox.showerror(_("error_title"), _("enter_valid_coords"))
            
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
        
    def on_profile_change(self, event=None):
        """Gestisce il cambio di profilo Samurai"""
        new_profile = self.profile_var.get()
        if new_profile != self.current_samurai_profile:
            self.current_samurai_profile = new_profile
            self.processor.set_active_profile(new_profile)
            
            # Aggiorna il titolo della finestra
            profile_info = self.processor.get_available_profiles().get(new_profile, {})
            profile_name = profile_info.get('name', new_profile)
            self.root.title(_("app_title_profile", profile=profile_name))
            
            self.log(_("profile_changed", name=profile_name), "SUCCESS")
            
            # Mostra statistiche del profilo
            if hasattr(self.processor, 'samurai_profiles') and self.processor.samurai_profiles:
                profile_data = self.processor.samurai_profiles['samurai_profiles'].get(new_profile, {})
                stats = profile_data.get('performance_stats', {})
                accuracy = stats.get('accuracy_rate', 0) * 100
                total = stats.get('total_processed', 0)
                self.log(_("profile_stats", total=total, accuracy=accuracy), "INFO")
    
    def toggle_auto_ratio(self):
        """Gestisce l'abilitazione/disabilitazione del rilevamento automatico del ratio"""
        if self.auto_ratio_var.get():
            self.processor.enable_auto_ratio_detection()
            self.log(_("auto_ratio_enabled"), "SUCCESS")
        else:
            self.processor.disable_auto_ratio_detection()
            self.log(_("auto_ratio_disabled"), "WARNING")
    
    def toggle_auto_orientation(self):
        """Gestisce l'abilitazione/disabilitazione del rilevamento automatico dell'orientamento"""
        if self.auto_orientation_var.get():
            if hasattr(self.processor, 'enable_auto_orientation_detection'):
                self.processor.enable_auto_orientation_detection()
            self.log(_("auto_orient_enabled"), "SUCCESS")
        else:
            if hasattr(self.processor, 'disable_auto_orientation_detection'):
                self.processor.disable_auto_orientation_detection()
            self.log(_("auto_orient_disabled"), "WARNING")
    
    def auto_correct_current_orientation(self):
        """Applica la correzione automatica dell'orientamento all'immagine corrente"""
        if not self.current_images:
            messagebox.showwarning(_("warning"), _("no_image_loaded"))
            return
        
        try:
            image_path = self.current_images[self.current_image_index]
            self.log(_("analyzing_orientation", name=Path(image_path).name), "PROGRESS")
            
            # Carica l'immagine per l'analisi
            import cv2
            image = cv2.imread(image_path)
            
            if image is None:
                self.log(_("error_orientation_load"), "ERROR")
                return
            
            # Usa il metodo del processor se disponibile
            if hasattr(self.processor, 'detect_orientation'):
                rotation_angle = self.processor.detect_orientation(image)
                self.log(_("orientation_detected", angle=rotation_angle), "INFO")
                
                if rotation_angle != 0:
                    self.rotate_image(rotation_angle)
                    self.log(_("orientation_corrected", angle=rotation_angle), "SUCCESS")
                else:
                    self.log(_("orientation_ok"), "INFO")
            else:
                # Fallback: analisi semplificata basata su dimensioni
                height, width = image.shape[:2]
                if height > width * 1.2:  # Probabilmente verticale
                    self.log(_("vertical_detected"), "INFO")
                elif width > height * 1.2:  # Probabilmente orizzontale
                    self.rotate_image(90)
                    self.log(_("horizontal_detected"), "SUCCESS")
                else:
                    self.log(_("orientation_ambiguous"), "WARNING")
                    
        except Exception as e:
            self.log(_("error_auto_orientation", error=e), "ERROR")
            messagebox.showerror(_("error_title"), _("error_auto_orientation", error=e))
    
    def rotate_image(self, angle: float):
        """Ruota l'immagine corrente"""
        if not self.current_images:
            messagebox.showwarning(_("warning"), _("no_image_loaded"))
            return
        
        self.canvas.rotate_image(angle)
        self.log(_("image_rotated", angle=angle))
    
    def reset_rotation(self):
        """Resetta la rotazione dell'immagine"""
        if not self.current_images:
            messagebox.showwarning(_("warning"), _("no_image_loaded"))
            return
        
        if self.canvas.original_image:
            self.canvas.rotation_angle = 0
            self.canvas.image = self.canvas.original_image.copy()
            self.canvas.fit_image_to_canvas()
            self.canvas.clear_selection()
            self.log(_("rotation_reset"))
        
    def save_crop(self):
        """Salva l'immagine ritagliata e registra feedback per addestramento"""
        if not self.current_images:
            messagebox.showwarning(_("warning"), _("no_image_loaded"))
            return
            
        coords = self.canvas.get_crop_coordinates()
        if not coords:
            messagebox.showwarning(_("warning"), _("select_crop_area"))
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
                    self.log(_("rotation_applied", angle=self.canvas.rotation_angle), "INFO")
                
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
                    self.log(_("auto_resize_a4"), "INFO")
                
                if is_ai_processed:
                    # Sostituisci SEMPRE il file _cropped con il ritaglio manuale
                    original_path = image_path
                    backup_path = base_path.parent / f"{base_path.stem}_ai_backup{base_path.suffix}"
                    
                    # Crea backup del file IA solo se non esiste già
                    import shutil
                    if not backup_path.exists():
                        shutil.copy2(original_path, backup_path)
                        self.log(_("backup_created", name=backup_path.name), "INFO")
                    
                    # Sostituisci con il ritaglio manuale
                    cropped.save(original_path)
                    
                    self.log(_("ai_file_overwritten", name=base_path.name), "SUCCESS")
                    
                    # Registra feedback di addestramento automaticamente
                    self._save_training_feedback(image_path, coords, "manual_correction")
                    
                    messagebox.showinfo(_("success_title"), _("manual_crop_saved_ai", name=base_path.name))
                else:
                    # Salva come nuovo file per immagini non elaborate dall'IA
                    crop_path = base_path.parent / f"{base_path.stem}_manual_crop{base_path.suffix}"
                    cropped.save(crop_path)
                    
                    self.log(_("manual_crop_saved", name=crop_path.name), "SUCCESS")
                    
                    # Registra feedback per nuovi ritagli
                    self._save_training_feedback(image_path, coords, "new_manual_crop")
                    
                    messagebox.showinfo(_("success_title"), _("manual_crop_saved_new", name=crop_path.name))
                
        except Exception as e:
            self.log(_("save_error", error=e), "ERROR")
            messagebox.showerror(_("error_title"), _("save_error", error=e))
    
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
                notes = f"{_('manual_correction_prefix')}{notes}" if notes else _("manual_correction_note")
                feedback = "manual_correction"  # Forza il feedback per correzioni manuali
            elif feedback_type == "new_manual_crop":
                notes = f"{_('new_crop_prefix')}{notes}" if notes else _("new_crop_note")
            
            # Salva il feedback usando il processor
            if hasattr(self, 'processor'):
                # Il metodo save_feedback di KatanaProcessor accetta solo 4 parametri
                self.processor.save_feedback(pdf_name, page_num, feedback, coords)
                self.log(_("feedback_saved_log", type=feedback_type, pdf=pdf_name, page=page_num), "SUCCESS")
            else:
                # Fallback: salva direttamente nel file JSON
                self._save_feedback_direct(pdf_name, page_num, feedback, coords, notes)
                self.log(_("feedback_saved_direct", type=feedback_type), "SUCCESS")
                
        except Exception as e:
            self.log(_("feedback_save_error", error=e), "ERROR")
    
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
            messagebox.showwarning(_("warning"), _("no_image_loaded"))
            return
            
        image_path = self.current_images[self.current_image_index]
        feedback = self.feedback_var.get()
        notes = self.notes_text.get(1.0, tk.END).strip()
        coords = self.canvas.get_crop_coordinates()
        
        try:
            self.log(_("saving_feedback_start"), "PROGRESS")
            
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
            
            self.log(_("analyzing_file", pdf=pdf_name, page=page_num), "INFO")
            self.log(_("feedback_selected", feedback=feedback), "INFO")
            if coords:
                self.log(_("crop_coords_log", coords=coords), "INFO")
            else:
                self.log(_("no_crop_coords"), "WARNING")
                
            # Salva il feedback
            if hasattr(self, 'processor'):
                # Il metodo save_feedback di KatanaProcessor accetta solo 4 parametri
                self.processor.save_feedback(pdf_name, page_num, feedback, coords)
            else:
                self._save_feedback_direct(pdf_name, page_num, feedback, coords, notes)
            
            # Log con note se presenti
            log_msg = _("feedback_saved_msg", feedback=feedback, pdf=pdf_name, page=page_num)
            if notes:
                log_msg += f" - {_('notes')} {notes}"
            if coords:
                log_msg += f" - {_('crop_coords')} {coords}"
            
            self.log(log_msg, "SUCCESS")
            messagebox.showinfo(_("success_title"), _("feedback_saved_success"))
            
        except Exception as e:
            self.log(_("feedback_save_error", error=e), "ERROR")
            messagebox.showerror(_("error_title"), _("feedback_save_error", error=e))
            
    def train_agent(self):
        """Avvia l'addestramento dell'agente"""
        try:
            self.log(_("training_start"), "PROGRESS")
            
            # Aggiorna i parametri adattivi basati sul feedback
            feedback_data = self.processor.learning_data.get('feedback_history', [])
            
            if not feedback_data:
                self.log(_("no_feedback_training"), "WARNING")
                messagebox.showwarning(_("warning"), _("no_feedback_training"))
                return
                
            self.log(_("feedback_found", count=len(feedback_data)), "INFO")
                
            # Conta i tipi di feedback
            feedback_counts = {}
            for entry in feedback_data:
                feedback_type = entry.get('feedback', 'unknown')
                feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
                
            self.log(_("feedback_analysis_complete"), "INFO")
            self.log(_("feedback_distribution", dist=feedback_counts), "INFO")
            
            # Simula l'addestramento aggiornando i parametri
            recent_feedback = feedback_data[-10:]  # Usa gli ultimi 10 feedback
            self.log(_("processing_last_feedback", count=len(recent_feedback)), "PROGRESS")
            
            for i, entry in enumerate(recent_feedback):
                feedback_type = entry.get('feedback', 'perfect')
                self.processor._update_adaptive_params(feedback_type)
                self.log(_("processed_feedback", current=i+1, total=len(recent_feedback), type=feedback_type), "INFO")
                
            self.log(_("training_success"), "SUCCESS")
            self.log(_("params_updated", params=self.processor.adaptive_params), "INFO")
            messagebox.showinfo(_("training_complete_title"), _("training_complete_msg"))
            
        except Exception as e:
            self.log(_("training_error", error=e), "ERROR")
            messagebox.showerror(_("error_title"), _("training_error", error=e))
            
    def show_stats(self):
        """Mostra le statistiche di apprendimento"""
        try:
            stats_window = tk.Toplevel(self.root)
            stats_window.title(_("stats_title"))
            stats_window.geometry("600x400")
            
            stats_text = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
            stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Carica i dati di apprendimento
            learning_data = self.processor.learning_data
            feedback_history = learning_data.get('feedback_history', [])
            adaptive_params = learning_data.get('adaptive_params', {})
            
            # Genera statistiche
            stats = _("stats_header")
            
            # Parametri attuali
            stats += _("current_params")
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
                    
                stats += _("feedback_dist_title")
                total_feedback = len(feedback_history)
                for feedback_type, count in sorted(feedback_counts.items()):
                    percentage = (count / total_feedback) * 100
                    stats += f"  {feedback_type}: {count} ({percentage:.1f}%)\n"
                    
                stats += _("processed_pdfs")
                for pdf_name, count in sorted(pdf_counts.items()):
                    stats += f"  {pdf_name}: {count} feedback\n"
                    
                stats += _("total_feedback", count=total_feedback)
            else:
                stats += _("no_feedback_avail")
                
            stats_text.insert(1.0, stats)
            stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log(_("stats_error", error=e))
            messagebox.showerror(_("error_title"), _("stats_error", error=e))
            
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