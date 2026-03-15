# Katana GUI - Interfaccia Grafica per Ritaglio Manuale e Addestramento

## Panoramica

Katana GUI è un'interfaccia grafica completa che permette di:
- Visualizzare e navigare tra le immagini estratte dai PDF
- Ritagliare manualmente le immagini con selezione tramite coordinate x-y
- Fornire feedback per l'addestramento del sistema di apprendimento automatico
- Monitorare le statistiche e i progressi dell'addestramento

## Caratteristiche Principali

### 🖼️ Visualizzazione e Navigazione
- **Canvas interattivo** per la visualizzazione delle immagini
- **Navigazione** tra le immagini con pulsanti Precedente/Successiva
- **Adattamento automatico** delle dimensioni dell'immagine al canvas
- **Informazioni dettagliate** su ogni immagine (dimensioni, peso, percorso)

### ✂️ Ritaglio Manuale
- **Selezione visuale** tramite trascinamento del mouse
- **Coordinate precise** con campi di input manuali (X1, Y1, X2, Y2)
- **Anteprima in tempo reale** della selezione
- **Salvataggio** del ritaglio come file separato

### 🎯 Sistema di Feedback
- **Tipi di feedback** predefiniti:
  - Perfetto
  - Ritaglio Eccessivo
  - Ritaglio Insufficiente
  - Ritaglio Leggero
  - Nessun Cambiamento
- **Note aggiuntive** per feedback dettagliato
- **Salvataggio automatico** nel sistema di apprendimento

### 🤖 Addestramento Agente
- **Addestramento in tempo reale** basato sul feedback
- **Aggiornamento parametri adattivi** automatico
- **Visualizzazione statistiche** di apprendimento
- **Monitoraggio progressi** con log dettagliato

## Installazione e Avvio

### Prerequisiti
```bash
pip install tkinter pillow opencv-python numpy
```

### Avvio della GUI
```bash
python katana_gui.py
```

### Test delle Dipendenze
```bash
python test_gui.py
```

## Utilizzo dell'Interfaccia

### 1. Caricamento dei Dati

#### Opzione A: Elaborazione PDF
1. Clicca **"Carica PDF"** e seleziona un file PDF
2. Clicca **"Elabora PDF"** per estrarre e processare le immagini
3. Le immagini elaborate verranno caricate automaticamente

#### Opzione B: Caricamento Immagini Esistenti
1. Clicca **"Carica Immagini"** e seleziona una directory
2. Tutte le immagini supportate verranno caricate

### 2. Navigazione e Visualizzazione
- Usa i pulsanti **"◀ Precedente"** e **"Successiva ▶"** per navigare
- Le informazioni dell'immagine corrente appaiono nel pannello destro
- Il contatore mostra la posizione corrente (es. "Immagine 3 di 15")

### 3. Ritaglio Manuale

#### Metodo 1: Selezione Visuale
1. **Trascina** il mouse sull'immagine per selezionare l'area
2. Clicca **"Applica Ritaglio"** per confermare la selezione
3. Le coordinate appariranno nei campi X1, Y1, X2, Y2

#### Metodo 2: Coordinate Manuali
1. Inserisci le coordinate nei campi **X1, Y1, X2, Y2**
2. Clicca **"Applica Coordinate"** per confermare

#### Salvataggio
- Clicca **"Salva Ritaglio"** per salvare l'immagine ritagliata
- Il file verrà salvato con suffisso `_manual_crop`

### 4. Feedback e Addestramento

#### Fornire Feedback
1. Seleziona il **tipo di feedback** appropriato:
   - **Perfetto**: Il ritaglio automatico è ottimale
   - **Ritaglio Eccessivo**: L'agente ha ritagliato troppo
   - **Ritaglio Insufficiente**: L'agente ha ritagliato poco
   - **Ritaglio Leggero**: Ritaglio leggermente insufficiente
   - **Nessun Cambiamento**: Il ritaglio non ha migliorato l'immagine

2. Aggiungi **note opzionali** per dettagli specifici
3. Clicca **"Salva Feedback"** per registrare il feedback

#### ⚠️ Addestrare l'Agente - PROCEDURA OBBLIGATORIA
1. Accumula feedback su diverse immagini
2. **PRIMA DI CHIUDERE IL PROGRAMMA** clicca **"Addestra Agente"**
3. Il sistema aggiorna i parametri adattivi e conferma l'addestramento
4. **IMPORTANTE**: Se non clicchi "Addestra Agente" prima di chiudere, l'agente NON viene addestrato

#### Visualizzare Statistiche
- Clicca **"Visualizza Statistiche"** per vedere:
  - Parametri adattivi attuali
  - Distribuzione dei tipi di feedback
  - PDF elaborati e numero di feedback
  - Totale feedback raccolti

## Struttura dell'Interfaccia

### Pannello Superiore - Controlli
- **Carica PDF**: Seleziona un file PDF da elaborare
- **Carica Immagini**: Carica immagini da una directory
- **Elabora PDF**: Processa il PDF caricato
- **Navigazione**: Pulsanti per spostarsi tra le immagini

### Pannello Sinistro - Canvas Immagine
- **Area di visualizzazione** principale dell'immagine
- **Selezione interattiva** per il ritaglio
- **Controlli ritaglio**: Applica, Cancella, Salva

### Pannello Destro - Feedback e Controlli
- **Informazioni Immagine**: Dettagli del file corrente
- **Coordinate Ritaglio**: Campi per coordinate precise
- **Feedback**: Selezione tipo e note
- **Azioni**: Salva feedback, addestra, statistiche
- **Log**: Cronologia delle operazioni

## Flusso di Lavoro Consigliato

### Per Nuovi PDF
1. **Carica e elabora** un PDF con Katana
2. **Naviga** tra le immagini estratte
3. **Valuta** la qualità del ritaglio automatico
4. **Fornisci feedback** per ogni immagine
5. **Ritaglia manualmente** se necessario
6. **Addestra** l'agente periodicamente

### Per Miglioramento Continuo
1. **Accumula feedback** su diversi tipi di documenti
2. **Monitora** le statistiche di apprendimento
3. **Addestra** regolarmente l'agente
4. **Verifica** i miglioramenti sui nuovi PDF

## Formati Supportati

### Immagini
- JPG/JPEG
- PNG
- BMP
- TIFF

### PDF
- Tutti i formati supportati da PyMuPDF
- PDF con immagini incorporate
- PDF scansionati

## File di Output

### Immagini Ritagliate
- Salvate nella stessa directory dell'originale
- Suffisso `_manual_crop` aggiunto al nome
- Mantengono il formato originale

### Dati di Apprendimento
- `katana_learning.json`: Database del feedback e parametri
- Aggiornato automaticamente ad ogni feedback
- Utilizzato per l'addestramento dell'agente

## Risoluzione Problemi

### GUI Non Si Avvia
1. Verifica le dipendenze con `python test_gui.py`
2. Controlla che tkinter sia installato correttamente
3. Verifica la compatibilità del sistema grafico

### Errori di Caricamento Immagini
1. Verifica che il formato sia supportato
2. Controlla i permessi di lettura del file
3. Assicurati che il file non sia corrotto

### Problemi di Performance
1. Riduci la dimensione delle immagini se troppo grandi
2. Chiudi altre applicazioni che usano molta memoria
3. Limita il numero di immagini caricate contemporaneamente

## Scorciatoie da Tastiera

- **Freccia Sinistra**: Immagine precedente
- **Freccia Destra**: Immagine successiva
- **Escape**: Cancella selezione corrente
- **Enter**: Applica ritaglio selezionato

## Integrazione con Katana

La GUI è completamente integrata con il sistema Katana:
- Utilizza la stessa classe `KatanaProcessor`
- Condivide i parametri di apprendimento
- Salva feedback nello stesso formato
- Compatibile con tutti gli strumenti esistenti

## Sviluppi Futuri

### Funzionalità Pianificate
- **Zoom e pan** per immagini ad alta risoluzione
- **Batch processing** per feedback multipli
- **Esportazione** dei dati di addestramento
- **Importazione** di feedback esterni
- **Visualizzazione** grafici di performance
- **Confronto** prima/dopo del ritaglio

### Miglioramenti UI/UX
- **Temi** scuri e chiari
- **Personalizzazione** layout
- **Scorciatoie** configurabili
- **Anteprima** in tempo reale del ritaglio

## Supporto e Contributi

Per segnalazioni di bug, richieste di funzionalità o contributi:
1. Controlla i log nella sezione "Log" della GUI
2. Verifica il file `katana.log` per errori dettagliati
3. Testa con `test_gui.py` per problemi di dipendenze

---

**Nota**: Questa GUI è progettata per funzionare in sinergia con il sistema di apprendimento automatico di Katana, permettendo un miglioramento continuo delle performance di ritaglio attraverso il feedback umano.

---

*In memory of Minoru Shigematsu*
