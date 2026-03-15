import pygame
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class KatanaSoundManager:
    """Gestisce i suoni per Katana Samurai v3.0"""
    
    def __init__(self):
        self.sounds_dir = Path(__file__).parent / "sounds"
        self.initialized = False
        self.startup_sound = None
        self.completion_sound = None
        
        # Inizializza pygame mixer
        self._initialize_pygame()
        
        # Carica i suoni se disponibili
        self._load_sounds()
    
    def _initialize_pygame(self):
        """Inizializza pygame mixer per i suoni"""
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.initialized = True
            logger.info("Pygame mixer inizializzato con successo")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di pygame mixer: {e}")
            self.initialized = False
    
    def _load_sounds(self):
        """Carica i file audio se esistono"""
        if not self.initialized:
            return
            
        try:
            # Crea la directory sounds se non esiste
            self.sounds_dir.mkdir(exist_ok=True)
            
            # Formati audio supportati (in ordine di preferenza)
            audio_formats = ['.wav', '.ogg', '.mp3']
            
            # Carica suono di avvio
            startup_sound = self._find_and_load_sound('katana_startup', audio_formats)
            if startup_sound:
                self.startup_sound = startup_sound
                logger.info("Suono di avvio caricato con successo")
            else:
                logger.info("File suono di avvio non trovato in nessun formato supportato")
            
            # Carica suono di completamento
            completion_sound = self._find_and_load_sound('katana_completion', audio_formats)
            if completion_sound:
                self.completion_sound = completion_sound
                logger.info("Suono di completamento caricato con successo")
            else:
                logger.info("File suono di completamento non trovato in nessun formato supportato")
                
        except Exception as e:
            logger.error(f"Errore nel caricamento dei suoni: {e}")
    
    def _find_and_load_sound(self, base_name, formats):
        """Cerca e carica un file audio in diversi formati"""
        for fmt in formats:
            sound_path = self.sounds_dir / f"{base_name}{fmt}"
            if sound_path.exists():
                try:
                    sound = pygame.mixer.Sound(str(sound_path))
                    logger.info(f"Suono caricato: {sound_path}")
                    return sound
                except Exception as e:
                    logger.warning(f"Impossibile caricare {sound_path}: {e}")
                    continue
        return None
    
    def play_startup_sound(self, volume=0.7):
        """Riproduce il suono di avvio"""
        if not self.initialized or not self.startup_sound:
            return
            
        try:
            self.startup_sound.set_volume(volume)
            self.startup_sound.play()
            logger.info("Suono di avvio riprodotto")
        except Exception as e:
            logger.error(f"Errore nella riproduzione del suono di avvio: {e}")
    
    def play_completion_sound(self, volume=0.7):
        """Riproduce il suono di completamento"""
        if not self.initialized or not self.completion_sound:
            return
            
        try:
            self.completion_sound.set_volume(volume)
            self.completion_sound.play()
            logger.info("Suono di completamento riprodotto")
        except Exception as e:
            logger.error(f"Errore nella riproduzione del suono di completamento: {e}")
    
    def stop_all_sounds(self):
        """Ferma tutti i suoni in riproduzione"""
        if not self.initialized:
            return
            
        try:
            pygame.mixer.stop()
            logger.info("Tutti i suoni fermati")
        except Exception as e:
            logger.error(f"Errore nel fermare i suoni: {e}")
    
    def get_sounds_info(self):
        """Restituisce informazioni sui suoni caricati"""
        info = {
            'initialized': self.initialized,
            'sounds_dir': str(self.sounds_dir),
            'startup_sound_loaded': self.startup_sound is not None,
            'completion_sound_loaded': self.completion_sound is not None
        }
        return info
    
    def __del__(self):
        """Cleanup quando l'oggetto viene distrutto"""
        if self.initialized:
            try:
                pygame.mixer.quit()
            except:
                pass