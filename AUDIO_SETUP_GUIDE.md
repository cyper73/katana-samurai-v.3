# 🔊 Guida Setup Audio - Katana Samurai v3.0

## File Audio Richiesti

Per abilitare i suoni in Katana Samurai v3.0, devi aggiungere questi file nella cartella `sounds/`:

### Formati Supportati (in ordine di preferenza):
1. **WAV** - Formato nativo pygame (raccomandato)
2. **OGG** - Formato compresso supportato
3. **MP3** - Richiede librerie aggiuntive

### File Necessari:
- **katana_startup.[wav/ogg/mp3]** - Suono di avvio dell'applicazione
- **katana_completion.[wav/ogg/mp3]** - Suono di completamento elaborazione

> ⚠️ **Nota**: I file MP3 potrebbero non funzionare su tutti i sistemi. Per la massima compatibilità, usa file WAV o OGG.

Per abilitare i suoni in Katana, devi aggiungere due file MP3 nella directory `sounds/`:

### 1. Suono di Avvio
**Nome file:** `katana_startup.mp3`  
**Percorso:** `sounds/katana_startup.mp3`  
**Quando viene riprodotto:** All'avvio della GUI  
**Durata consigliata:** 1-3 secondi  
**Tipo:** Suono energico, motivazionale (es. suono di spada che viene estratta)

### 2. Suono di Completamento
**Nome file:** `katana_completion.mp3`  
**Percorso:** `sounds/katana_completion.mp3`  
**Quando viene riprodotto:** Al completamento dell'elaborazione PDF  
**Durata consigliata:** 1-2 secondi  
**Tipo:** Suono di successo, vittoria (es. suono di spada che colpisce il bersaglio)

## Struttura Directory

```
catalogo-marga/
├── katana_gui.py
├── katana_sounds.py
├── sounds/
│   ├── katana_startup.mp3      ← AGGIUNGI QUESTO FILE
│   └── katana_completion.mp3   ← AGGIUNGI QUESTO FILE
└── ...
```

## Come Aggiungere i File Audio

1. **Trova o crea i file MP3:**
   - Puoi scaricare suoni gratuiti da siti come Freesound.org
   - Oppure registrare i tuoi suoni personalizzati
   - Assicurati che siano in formato MP3

2. **Rinomina i file:**
   - Il file di avvio deve chiamarsi esattamente `katana_startup.mp3`
   - Il file di completamento deve chiamarsi esattamente `katana_completion.mp3`

3. **Copia i file nella directory sounds:**
   ```bash
   # Esempio su Windows
   copy "il_tuo_suono_avvio.mp3" "sounds\katana_startup.mp3"
   copy "il_tuo_suono_completamento.mp3" "sounds\katana_completion.mp3"
   ```

## Funzionalità Audio Implementate

### ✅ Sistema Audio Completo
- **Pygame mixer** per la riproduzione audio
- **Gestione errori** robusta (l'app funziona anche senza audio)
- **Controllo volume** (default 70%)
- **Logging** dettagliato per debug

### ✅ Integrazione GUI
- **Suono di avvio** automatico all'apertura
- **Suono di completamento** al termine dell'elaborazione
- **Nessun impatto** sulle performance

### ✅ Gestione Errori
- Se i file audio non esistono, l'app funziona normalmente
- Se pygame non è installato, viene installato automaticamente
- Log informativi per troubleshooting

## Test Audio

Per testare i suoni:

1. **Avvia la GUI:**
   ```bash
   python katana_gui.py
   ```
   → Dovresti sentire il suono di avvio

2. **Elabora un PDF:**
   - Carica un PDF
   - Clicca "Elabora PDF"
   - Attendi il completamento
   → Dovresti sentire il suono di completamento

## 🔧 Risoluzione Problemi

### Suoni non funzionano:
1. **Formato Audio**: Prova a convertire i file MP3 in formato WAV o OGG
2. **Nomi File**: Verifica che i nomi siano esatti (katana_startup, katana_completion)
3. **Percorso**: Controlla che i file siano nella cartella `sounds/`
4. **Pygame**: Assicurati che pygame sia installato: `pip install pygame`
5. **Log**: Verifica i log nella console per errori specifici

### Conversione Audio:
- **Online**: Usa servizi come CloudConvert o Online-Convert
- **Software**: Audacity, VLC, FFmpeg
- **Comando FFmpeg**: `ffmpeg -i input.mp3 output.wav`

### Problema: Errore pygame
**Soluzioni:**
1. Reinstalla pygame: `pip install --upgrade pygame`
2. Verifica la compatibilità audio del sistema
3. Prova con file WAV invece di MP3

### Problema: File non trovati
**Soluzioni:**
1. Verifica il percorso: `sounds/katana_startup.[wav/ogg/mp3]`
2. Controlla i permessi della directory
3. Usa percorsi assoluti se necessario

## Personalizzazione

Puoi modificare il volume dei suoni editando `katana_sounds.py`:

```python
# Cambia il volume (0.0 = silenzioso, 1.0 = massimo)
self.sound_manager.play_startup_sound(volume=0.5)     # 50%
self.sound_manager.play_completion_sound(volume=0.8)  # 80%
```

## Note Tecniche

- **Formato supportato:** MP3 (raccomandato), WAV, OGG
- **Qualità audio:** 22050 Hz, 16-bit, stereo
- **Dimensione consigliata:** < 1MB per file
- **Compatibilità:** Windows, Linux, macOS

---

**🎵 Buon divertimento con i suoni di Katana! 🗡️**

---

*In memory of Minoru Shigematsu*
