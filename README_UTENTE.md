# 📖 Katana Samurai v3.0 - Guida Utente

## 🎯 Cosa fa questo programma?

Katana Samurai v3.0 è un programma che **estrae automaticamente le immagini dai documenti PDF** e le trasforma in file JPG di alta qualità.

### In parole semplici:
- Prendi un PDF con pagine scansionate
- Il programma trova le immagini in ogni pagina
- Le ritaglia automaticamente
- Le salva come file JPG separati

---

## 🚀 Come usare il programma

### 1. Avviare il programma
1. Fai doppio clic su `katana_gui.py` oppure
2. Apri il terminale e scrivi: `python katana_gui.py`
3. Si aprirà una finestra con l'interfaccia grafica

### 2. Caricare un PDF
1. Clicca sul pulsante **"Carica PDF"**
2. Seleziona il file PDF che vuoi elaborare
3. Il programma mostrerà il nome del file caricato

### 3. Avviare l'elaborazione
1. Clicca sul pulsante **"Avvia Elaborazione"**
2. Vedrai una barra di progresso che si riempie
3. Il programma elaborerà automaticamente tutte le pagine

### 4. Controllare i risultati
- I file JPG vengono salvati nella cartella `output_images/`
- Ogni PDF avrà la sua sottocartella
- Troverai un file JPG per ogni immagine trovata

---

## 📁 Struttura dei file di output

```
output_images/
└── nome_del_tuo_pdf/
    ├── nome_del_tuo_pdf_page_1_img_1.jpg
    ├── nome_del_tuo_pdf_page_1_img_1_cropped.jpg
    ├── nome_del_tuo_pdf_page_2_img_1.jpg
    └── nome_del_tuo_pdf_page_2_img_1_cropped.jpg
```

### Tipi di file generati:
- **`_img_1.jpg`** = Immagine originale estratta
- **`_cropped.jpg`** = Immagine ritagliata automaticamente
- **`_manual_crop.jpg`** = Immagine con ritaglio manuale (se applicato)

---

## 🛠️ Funzioni avanzate

### Ritaglio manuale
1. Durante l'elaborazione, puoi vedere l'anteprima delle immagini
2. Se il ritaglio automatico non è perfetto:
   - Clicca e trascina per selezionare l'area da ritagliare
   - Il programma salverà anche la versione con ritaglio manuale

### Pulsante Stop
- Se vuoi fermare l'elaborazione, clicca **"Stop"**
- Il programma si fermerà in modo sicuro
- I file già elaborati rimarranno salvati

### Sistema di Autoapprendimento Samurai 🥷

Il sistema Samurai è la funzione più avanzata di Katana v3.0 che impara dalle tue correzioni per migliorare automaticamente.

#### Come addestrare il sistema:

**1. Seleziona il campo Samurai da addestrare**
   - Durante l'elaborazione, vedrai i campi disponibili per l'addestramento
   - Scegli quale tipo di documento/immagine vuoi migliorare

**2. Applica la tua selezione**
   - Se vuoi correggere un ritaglio o una rotazione:
   - Fai la tua selezione manuale sull'immagine
   - Clicca su **"Applica Selezione"**
   - Compariranno i campi degli assi X e Y

**3. Controlla il Crop IA**
   - Verifica che il ritaglio automatico sia corretto
   - Se non è perfetto, procedi con il feedback

**4. Dai feedback di addestramento**
   - **Ritaglio**: Correggi i bordi se necessario
   - **Rotazione**: Correggi l'orientamento
   - Clicca su **"Salva Feedback"** per registrare il feedback
   - **⚠️ IMPORTANTE**: Prima di chiudere il programma, clicca su **"Addestra Agente"** per applicare tutti i feedback raccolti

#### Addestramento Multiplo

Puoi addestrare il sistema su più aspetti contemporaneamente:
- **Ritaglio + Rotazione**: Per documenti storti e mal inquadrati
- **Parametri Avanzati**: Per documenti con margini irregolari
- **Tutti i parametri**: Per un addestramento completo

#### Profili Samurai Disponibili:

- **Documenti Legali**: Per contratti, atti notarili, sentenze
- **Documenti Tecnici**: Per manuali, schemi, diagrammi
- **Documenti Medici**: Per referti, cartelle cliniche, analisi
- **Documenti Artistici**: Per opere d'arte, cataloghi, portfolio
- **Documenti Generali**: Per documenti non categorizzati

#### Come funziona l'apprendimento:
1. Il sistema analizza le tue correzioni
2. Crea un "profilo" per quel tipo di documento
3. Applica automaticamente le stesse correzioni a documenti simili
4. Migliora continuamente con ogni feedback che dai

#### ⚠️ PROCEDURA CORRETTA DI ADDESTRAMENTO:

**Quando salvi un ritaglio manuale:**
1. Ricevi il messaggio "Ritaglio manuale salvato! Feedback registrato per addestramento"
2. Il feedback viene **temporaneamente** salvato nel sistema
3. **PRIMA DI CHIUDERE IL PROGRAMMA** devi cliccare su **"Addestra Agente"**
4. Solo dopo aver cliccato "Addestra Agente" riceverai il messaggio "Addestramento completato"
5. **Se chiudi il programma senza fare "Addestra Agente", l'agente NON viene addestrato**

**Flusso completo:**
- Salva ritaglio manuale → Feedback registrato
- Clicca "Salva Feedback" (opzionale, per feedback aggiuntivi)
- **Clicca "Addestra Agente"** → Agente addestrato
- Ora puoi chiudere il programma in sicurezza

> 💡 **Suggerimento**: Più feedback dai, più preciso diventa il sistema. Dopo 5-10 correzioni dello stesso tipo, vedrai miglioramenti significativi!

---

## ⚠️ Cosa fare se qualcosa non funziona

### Il programma non si avvia
1. Assicurati di avere Python installato
2. Installa le dipendenze: `pip install -r requirements.txt`
3. Riprova ad avviare il programma

### Errore durante l'elaborazione
1. Controlla che il PDF non sia protetto da password
2. Verifica che il PDF contenga immagini scansionate
3. Prova con un PDF più piccolo per test

### I risultati non sono buoni
1. Usa il ritaglio manuale per correggere
2. Il programma imparerà dalle tue correzioni
3. I prossimi PDF simili saranno elaborati meglio

### File di output non trovati
1. Controlla la cartella `output_images/`
2. Cerca una sottocartella con il nome del tuo PDF
3. Se non c'è, il PDF potrebbe non contenere immagini

---

## 📋 Requisiti del sistema

### Software necessario:
- Python 3.8 o superiore
- Librerie Python (installate automaticamente):
  - PyMuPDF (per leggere PDF)
  - OpenCV (per elaborare immagini)
  - Pillow (per salvare JPG)
  - Tkinter (per l'interfaccia grafica)

### Formati supportati:
- **Input**: File PDF con immagini scansionate
- **Output**: File JPG ad alta risoluzione

---

## 💡 Consigli per ottenere i migliori risultati

1. **PDF di qualità**: Usa PDF con scansioni chiare e ben contrastate
2. **Dimensioni ragionevoli**: PDF troppo grandi potrebbero richiedere più tempo
3. **Pazienza**: La prima elaborazione può essere più lenta, poi il programma diventa più veloce
4. **Correzioni manuali**: Se fai ritagli manuali, il programma imparerà e migliorerà
5. **Backup**: Tieni sempre una copia del PDF originale

---

## 🆘 Supporto

Se hai problemi:
1. Controlla i file di log per errori dettagliati
2. Verifica che tutti i requisiti siano installati
3. Prova con un PDF di test più semplice
4. Riavvia il programma se necessario

---

**Buona elaborazione con Katana Samurai v3.0! 🥷**

---

*In memory of Minoru Shigematsu*
