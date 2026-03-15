# Agente Katana - Elaboratore di PDF Scansionati

## Descrizione

L'Agente Katana è un sistema avanzato per l'elaborazione di documenti PDF scansionati. Il sistema è in grado di:

- ✅ Esaminare scansioni PDF
- ✅ Estrarre metadati DPI e risoluzioni
- ✅ Individuare immagini scannerizzate per pagina
- ✅ Ritagliare e ridimensionare immagini
- ✅ Convertire in formato JPG singolo
- ✅ Preservare l'aspetto originale delle immagini
- ✅ Rilevamento automatico del contenuto

## Installazione

### 1. Installare le dipendenze Python

```bash
pip install -r requirements.txt
```

### 2. Installare Tesseract OCR (opzionale)

**Windows:**
- Scaricare da: https://github.com/UB-Mannheim/tesseract/wiki
- Aggiungere al PATH di sistema

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

## Utilizzo

### Elaborazione di un singolo PDF

```bash
python katana.py documento.pdf
```

### Elaborazione di tutti i PDF in una directory

```bash
python katana.py .
```

### Opzioni avanzate

```bash
# Specificare directory di output
python katana.py documento.pdf --output-dir ./immagini_elaborate

# Impostare DPI personalizzato
python katana.py documento.pdf --dpi 600

# Disabilitare il ritaglio automatico
python katana.py documento.pdf --no-crop

# Output verboso
python katana.py documento.pdf --verbose
```

## Funzionalità Principali

### 1. Estrazione Metadati
- Analisi DPI e risoluzioni
- Informazioni sulle pagine
- Dettagli delle immagini incorporate

### 2. Elaborazione Immagini
- Estrazione diretta delle immagini dal PDF
- Rendering delle pagine come immagini ad alta risoluzione
- Preservazione dell'aspetto originale senza modifiche di colore o contrasto

### 3. Ritaglio Intelligente
- Rilevamento automatico dei bordi del documento
- Rimozione di margini e spazi vuoti
- Conservazione del contenuto principale

### 4. Ottimizzazione Qualità
- Ridimensionamento intelligente
- Preservazione dei colori originali
- Mantenimento dell'aspetto naturale
- Conversione in formato JPG ottimizzato

## Struttura Output

Il sistema crea una directory `output_images` (o quella specificata) contenente:

```
output_images/
├── documento_page_1_img_1.jpg          # Immagine originale estratta
├── documento_page_1_img_1_cropped.jpg  # Immagine ritagliata
├── documento_page_2_rendered.jpg       # Pagina renderizzata
└── katana_report_YYYYMMDD_HHMMSS.txt   # Report dettagliato
```

## Logging

Il sistema genera automaticamente:
- `katana.log` - Log dettagliato delle operazioni
- Report finale con statistiche di elaborazione

## Librerie Utilizzate

- **PyMuPDF (fitz)** - Elaborazione PDF
- **OpenCV** - Elaborazione immagini e rilevamento bordi
- **Pillow (PIL)** - Manipolazione immagini
- **NumPy** - Operazioni numeriche
- **pytesseract** - OCR (opzionale)

## Esempi di Utilizzo

### Elaborazione Batch

```python
from katana import KatanaProcessor

# Inizializza il processore
processor = KatanaProcessor("./output")

# Elabora tutti i PDF nella directory corrente
results = processor.process_directory(".", target_dpi=300, crop_content=True)

# Genera report
report = processor.generate_report()
print(report)
```

### Elaborazione Singola

```python
from katana import KatanaProcessor

processor = KatanaProcessor()
result = processor.process_pdf_file("documento.pdf", target_dpi=600)

if result['success']:
    print(f"Elaborate {len(result['output_images'])} immagini")
else:
    print(f"Errori: {result['errors']}")
```

## Risoluzione Problemi

### Errore: "Impossibile importare fitz"
```bash
pip install PyMuPDF
```

### Errore: "Tesseract non trovato"
- Verificare l'installazione di Tesseract OCR
- Aggiungere Tesseract al PATH di sistema

### Immagini di bassa qualità
- Aumentare il DPI target: `--dpi 600`
- Verificare la qualità del PDF originale

## Contributi

Per contribuire al progetto:
1. Fork del repository
2. Creare un branch per le modifiche
3. Testare le modifiche
4. Creare una pull request

## Licenza

Questo progetto è rilasciato sotto **Licenza Personalizzata Katana Samurai**.

**IMPORTANTE:** L'uso commerciale è **VIETATO** senza autorizzazione scritta esplicita degli autori.

Per dettagli completi, consultare il file LICENSE nella directory principale.

### Riassunto Licenza:
- ✅ **Uso personale e non commerciale** - Libero
- ✅ **Modifica e studio** - Permesso
- ❌ **Uso commerciale** - Richiede permesso scritto
- 📧 **Contatti per licenza commerciale:** Cohen AI Assistant & Claudio Barracu (claudiob73@hotmail.com)