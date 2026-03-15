# 🗡️ Logo Katana - Documentazione

## Panoramica
Il logo Katana è stato integrato nell'interfaccia grafica per dare un'identità visiva professionale al sistema di elaborazione PDF.

## File Creati

### 1. `katana_logo.py`
Script per generare il logo in formato SVG e PNG:
- **SVG**: Logo vettoriale scalabile con gradiente e dettagli
- **PNG**: Versione bitmap per l'integrazione in Tkinter

### 2. `katana_logo.svg` (1761 bytes)
Logo vettoriale con:
- Lama della katana con gradiente metallico
- Guardia (tsuba) in nero
- Manico (tsuka) in legno con texture
- Riflesso sulla lama
- Testo "KATANA" stilizzato

### 3. `katana_logo.png` (310 bytes)
Versione bitmap ottimizzata per Tkinter:
- Dimensioni: 120x40 pixel
- Formato: RGBA con trasparenza
- Compatibile con ImageTk

## Integrazione nella GUI

### Modifiche a `katana_gui.py`

1. **Import aggiuntivi**:
   ```python
   from PIL import Image, ImageTk, ImageDraw, ImageFont
   ```

2. **Nuovo metodo `load_logo()`**:
   - Carica il logo PNG
   - Ridimensiona se necessario
   - Gestisce errori con fallback
   - Mostra titolo con emoji se il logo non è disponibile

3. **Header frame**:
   - Frame dedicato per logo e titolo
   - Layout orizzontale con logo a sinistra
   - Titolo "KATANA - Sistema di Elaborazione PDF"

### Struttura Layout
```
┌─────────────────────────────────────────┐
│ [🗡️ LOGO] KATANA - Sistema di Elaborazione PDF │
├─────────────────────────────────────────┤
│ [Carica PDF] [Carica Immagini] [Elabora] │
│ [◀ Precedente] [Info] [Successiva ▶]    │
├─────────────────────────────────────────┤
│                                         │
│           Area Immagine                 │
│                                         │
└─────────────────────────────────────────┘
```

## Caratteristiche Tecniche

### Gestione Errori
- **Logo non trovato**: Mostra emoji 🗡️ come fallback
- **Errore di caricamento**: Log dell'errore e fallback
- **Problemi di ridimensionamento**: Usa dimensioni originali

### Ottimizzazioni
- Logo pre-ridimensionato per evitare calcoli runtime
- Formato PNG per compatibilità Tkinter
- Trasparenza per integrazione pulita
- Dimensioni ottimizzate (310 bytes)

### Compatibilità
- ✅ Windows (testato)
- ✅ Tkinter standard
- ✅ PIL/Pillow
- ✅ Tutti i temi di sistema

## Test e Verifica

### `test_logo_integration.py`
Script di test completo che verifica:
1. **Creazione file**: Presenza di SVG e PNG
2. **Caricamento**: Apertura e ridimensionamento
3. **Integrazione**: Funzionamento in Tkinter

### Risultati Test
```
✓ katana_logo.png creato correttamente (310 bytes)
✓ katana_logo.svg creato correttamente (1761 bytes)
✓ Logo caricato: (120, 40) pixels, modalità RGBA
✓ Logo ridimensionato a: (120, 40)
✓ Logo convertito per Tkinter
✓ Logo integrato correttamente nella GUI
```

## Utilizzo

### Rigenerazione Logo
```bash
python katana_logo.py
```

### Test Integrazione
```bash
python test_logo_integration.py
```

### Avvio GUI con Logo
```bash
python katana_gui.py
```

## Personalizzazione

### Modifica Dimensioni
Nel file `katana_gui.py`, metodo `load_logo()`:
```python
logo_img = logo_img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
```

### Modifica Posizione
Cambiare il `pack()` del logo_label:
```python
logo_label.pack(side=tk.RIGHT)  # Logo a destra
```

### Modifica Stile
Editare `katana_logo.py` per cambiare:
- Colori del gradiente
- Dimensioni della lama
- Stile del manico
- Font del testo

## Note Tecniche

- Il logo è generato programmaticamente per facilità di modifica
- SVG per scalabilità, PNG per performance
- Gestione robusta degli errori
- Fallback elegante con emoji
- Test automatizzati per verifica funzionamento

---

*Logo integrato con successo nel sistema Katana* 🗡️

---

*In memory of Minoru Shigematsu*
