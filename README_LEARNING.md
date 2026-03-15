# Sistema di Apprendimento Katana

## Panoramica

Katana ora include un sistema di apprendimento automatico che migliora le prestazioni di ritaglio basandosi sui feedback dell'utente. Il sistema adatta dinamicamente i parametri di rilevamento dei bordi per ottimizzare i risultati futuri.

## Funzionalità Implementate

### 1. Modalità Apprendimento
- **Attivazione**: `KatanaProcessor(learning_mode=True)`
- **File di persistenza**: `katana_learning.json`
- **Parametri adattivi**: Soglie di validazione che si aggiornano automaticamente

### 2. Tipi di Feedback Supportati

| Feedback | Descrizione | Effetto sui Parametri |
|----------|-------------|----------------------|
| `perfect` | Risultato ottimale | Mantiene parametri attuali |
| `excessive_cropping` | Taglio eccessivo di contenuto importante | Riduce aggressività (-15% soglie, +30% margini) |
| `no_change` | Nessun miglioramento rispetto all'originale | Aumenta aggressività (+15% soglie, -30% margini) |
| `light_cropping` | Taglio leggero ma accettabile | Riduzione leggera aggressività (-5% soglie, +10% margini) |
| `insufficient_cropping` | Troppi margini bianchi rimasti | Aumenta significativamente aggressività (+25% soglie, -40% margini) |
| `insufficient_zoom` | Immagine troppo piccola, zoom insufficiente | Riduce margini (-20%), aumenta soglie (+10%) |
| `excessive_zoom` | Immagine troppo ingrandita, zoom eccessivo | Aumenta margini (+20%), riduce soglie (-10%) |

### 3. Parametri Adattivi

- **variance_threshold**: Soglia varianza contenuto (30-100)
- **entropy_threshold**: Soglia entropia distribuzione grigio (1.0-3.0)
- **edge_threshold**: Soglia rilevamento bordi (0.001-0.015)
- **non_white_threshold**: Soglia pixel non-bianchi (fisso: 0.02)
- **white_threshold**: Soglia definizione pixel bianco (220-240)
- **margin_adjustment**: Fattore aggiustamento margini (0.1-1.0)

## Strumenti Disponibili

### 1. Script di Test Automatico
```bash
python test_learning.py
```
Applica automaticamente i feedback forniti dall'utente e aggiorna i parametri.

### 2. Strumento di Feedback Interattivo
```bash
python feedback_tool.py
```
Interfaccia interattiva per raccogliere feedback su immagini elaborate:
- Seleziona PDF da valutare
- Mostra immagini ritagliate
- Raccoglie feedback per ogni pagina
- Aggiorna automaticamente i parametri

### 3. Analisi Statistiche
```bash
python learning_stats.py
```
Visualizza:
- Parametri attuali vs iniziali
- Timeline dei feedback
- Statistiche di distribuzione
- Raccomandazioni automatiche

## Utilizzo Pratico

### Scenario 1: Primo Utilizzo
```python
# Elabora PDF con modalità apprendimento
processor = KatanaProcessor(learning_mode=True)
processor.extract_and_process_images("documento.pdf")

# Fornisci feedback manualmente
python feedback_tool.py
```

### Scenario 2: Feedback Automatico
```python
# Definisci feedback per ogni pagina
feedback_data = [
    {"page": 1, "feedback": "excessive_cropping"},
    {"page": 2, "feedback": "perfect"},
    {"page": 3, "feedback": "no_change"}
]

# Applica feedback
for fb in feedback_data:
    processor.save_feedback("documento.pdf", fb["page"], fb["feedback"])
```

### Scenario 3: Monitoraggio Prestazioni
```bash
# Visualizza statistiche
python learning_stats.py

# Elabora con parametri aggiornati
python katana.py documento.pdf --verbose
```

## Esempio di Evoluzione Parametri

**Parametri Iniziali:**
```json
{
  "variance_threshold": 50,
  "entropy_threshold": 1.5,
  "edge_threshold": 0.003,
  "margin_adjustment": 0.5
}
```

**Dopo Feedback (6x excessive_cropping, 2x no_change, 2x perfect):**
```json
{
  "variance_threshold": 30,
  "entropy_threshold": 1.0,
  "edge_threshold": 0.0015,
  "margin_adjustment": 1.0
}
```

## Raccomandazioni d'Uso

### Per Documenti Scansionati
- Inizia con elaborazione standard
- Usa `feedback_tool.py` per valutare risultati
- Fornisci feedback per almeno 10-15 pagine
- Monitora miglioramenti con `learning_stats.py`

### Per Documenti con Arte/Grafica
- Feedback `excessive_cropping` per preservare dettagli
- Parametri si adatteranno per essere meno aggressivi
- Verifica risultati su documenti simili

### Per Documenti con Molti Margini
- Feedback `insufficient_cropping` per rimuovere spazi bianchi
- Sistema aumenterà aggressività automaticamente
- Monitora per evitare over-cropping

## File di Output

- **katana_learning.json**: Parametri e cronologia feedback
- **katana.log**: Log dettagliato delle operazioni
- **output_images/**: Immagini elaborate
- **katana_report_*.txt**: Report di elaborazione

## Limitazioni

- Parametri hanno range di sicurezza per evitare valori estremi
- Sistema richiede feedback umano per apprendimento iniziale
- Prestazioni ottimali dopo 20+ feedback su documenti simili
- Non distingue automaticamente tipi di documento diversi

## Troubleshooting

**Problema**: Parametri non si aggiornano
- Verifica `learning_mode=True`
- Controlla permessi scrittura file `katana_learning.json`

**Problema**: Risultati peggiorati dopo feedback
- Usa `learning_stats.py` per analizzare trend
- Considera reset parametri se necessario
- Fornisci feedback più bilanciato

**Problema**: Sistema troppo conservativo/aggressivo
- Bilancia feedback con più `perfect` per stabilizzare
- Usa feedback specifici (`light_cropping`, `insufficient_cropping`)

---

*In memory of Minoru Shigematsu*
