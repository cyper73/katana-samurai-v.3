#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per visualizzare le statistiche del sistema di apprendimento di Katana
"""

import json
import os
from datetime import datetime
from collections import Counter, defaultdict

def load_learning_data():
    """Carica i dati di apprendimento dal file JSON"""
    learning_file = "katana_learning.json"
    if not os.path.exists(learning_file):
        print(f"File di apprendimento {learning_file} non trovato.")
        return None
    
    try:
        with open(learning_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento del file di apprendimento: {e}")
        return None

def analyze_feedback_patterns(feedback_history):
    """Analizza i pattern nei feedback"""
    if not feedback_history:
        return {}
    
    # Conteggio per tipo di feedback
    feedback_counts = Counter(item['feedback'] for item in feedback_history)
    
    # Feedback per PDF
    pdf_feedback = defaultdict(list)
    for item in feedback_history:
        pdf_feedback[item['pdf_name']].append(item['feedback'])
    
    # Feedback per pagina (se disponibile)
    page_feedback = defaultdict(list)
    for item in feedback_history:
        if 'page_num' in item:
            page_feedback[item['page_num']].append(item['feedback'])
    
    return {
        'total_feedback': len(feedback_history),
        'feedback_types': dict(feedback_counts),
        'pdf_feedback': dict(pdf_feedback),
        'page_feedback': dict(page_feedback)
    }

def show_parameter_evolution(feedback_history, current_params):
    """Mostra l'evoluzione dei parametri nel tempo"""
    print("\n=== EVOLUZIONE PARAMETRI ===")
    
    if not feedback_history:
        print("Nessuna cronologia di feedback disponibile.")
        return
    
    # Parametri iniziali (dal primo feedback)
    initial_params = feedback_history[0].get('current_params', {})
    
    print("\nParametri iniziali vs attuali:")
    print(f"{'Parametro':<25} {'Iniziale':<12} {'Attuale':<12} {'Variazione':<15}")
    print("-" * 70)
    
    for param in current_params:
        initial = initial_params.get(param, 'N/A')
        current = current_params[param]
        
        if isinstance(initial, (int, float)) and isinstance(current, (int, float)):
            variation = current - initial
            variation_str = f"{variation:+.3f}"
        else:
            variation_str = "N/A"
        
        print(f"{param:<25} {str(initial):<12} {str(current):<12} {variation_str:<15}")

def show_feedback_timeline(feedback_history):
    """Mostra la timeline dei feedback"""
    print("\n=== TIMELINE FEEDBACK ===")
    
    if not feedback_history:
        print("Nessun feedback disponibile.")
        return
    
    print(f"\n{'Data/Ora':<20} {'PDF':<30} {'Pagina':<8} {'Feedback':<20}")
    print("-" * 85)
    
    for item in feedback_history[-10:]:  # Mostra gli ultimi 10
        timestamp = item.get('timestamp', 'N/A')
        if timestamp != 'N/A':
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        pdf_name = item.get('pdf_name', 'N/A')[:28]
        page_num = str(item.get('page_num', 'N/A'))
        feedback = item.get('feedback', 'N/A')
        
        print(f"{timestamp:<20} {pdf_name:<30} {page_num:<8} {feedback:<20}")
    
    if len(feedback_history) > 10:
        print(f"\n... e altri {len(feedback_history) - 10} feedback precedenti")

def show_recommendations(analysis):
    """Mostra raccomandazioni basate sull'analisi"""
    print("\n=== RACCOMANDAZIONI ===")
    
    feedback_types = analysis.get('feedback_types', {})
    total = analysis.get('total_feedback', 0)
    
    if total == 0:
        print("Nessun feedback disponibile per generare raccomandazioni.")
        return
    
    excessive_cropping = feedback_types.get('excessive_cropping', 0)
    no_change = feedback_types.get('no_change', 0)
    perfect = feedback_types.get('perfect', 0)
    
    print(f"\nAnalisi di {total} feedback:")
    
    if excessive_cropping > total * 0.4:
        print("⚠️  ATTENZIONE: Alto numero di tagli eccessivi ({:.1f}%)".format(excessive_cropping/total*100))
        print("   Considera di ridurre l'aggressività del ritaglio")
        print("   Suggerimento: Aumenta margin_adjustment o riduci le soglie di validazione")
    
    if no_change > total * 0.3:
        print("⚠️  ATTENZIONE: Molte immagini senza cambiamenti ({:.1f}%)".format(no_change/total*100))
        print("   Il sistema potrebbe essere troppo conservativo")
        print("   Suggerimento: Riduci le soglie di validazione per rilevare più contenuto")
    
    if perfect > total * 0.6:
        print("✅ OTTIMO: Alta percentuale di risultati perfetti ({:.1f}%)".format(perfect/total*100))
        print("   Il sistema sta funzionando bene con i parametri attuali")
    
    # Raccomandazioni specifiche per PDF
    pdf_feedback = analysis.get('pdf_feedback', {})
    for pdf, feedbacks in pdf_feedback.items():
        pdf_excessive = feedbacks.count('excessive_cropping')
        if pdf_excessive > len(feedbacks) * 0.5:
            print(f"\n📄 PDF specifico: {pdf}")
            print(f"   Alto tasso di taglio eccessivo ({pdf_excessive}/{len(feedbacks)} pagine)")
            print("   Potrebbe richiedere parametri specifici per questo tipo di documento")

def main():
    print("=== STATISTICHE SISTEMA DI APPRENDIMENTO KATANA ===")
    
    # Carica i dati
    data = load_learning_data()
    if not data:
        return
    
    current_params = data.get('adaptive_params', {})
    feedback_history = data.get('feedback_history', [])
    
    # Mostra parametri attuali
    print("\n=== PARAMETRI ATTUALI ===")
    for param, value in current_params.items():
        print(f"{param}: {value}")
    
    # Analizza i feedback
    analysis = analyze_feedback_patterns(feedback_history)
    
    # Mostra statistiche generali
    print("\n=== STATISTICHE GENERALI ===")
    print(f"Totale feedback raccolti: {analysis.get('total_feedback', 0)}")
    print(f"PDF elaborati: {len(analysis.get('pdf_feedback', {}))}")
    
    feedback_types = analysis.get('feedback_types', {})
    if feedback_types:
        print("\nDistribuzione feedback:")
        for feedback_type, count in feedback_types.items():
            percentage = (count / analysis['total_feedback']) * 100
            print(f"  {feedback_type}: {count} ({percentage:.1f}%)")
    
    # Mostra evoluzione parametri
    show_parameter_evolution(feedback_history, current_params)
    
    # Mostra timeline
    show_feedback_timeline(feedback_history)
    
    # Mostra raccomandazioni
    show_recommendations(analysis)
    
    print("\n" + "="*60)
    print("Per raccogliere nuovo feedback, usa: python feedback_tool.py")
    print("Per elaborare un PDF: python katana.py <nome_file.pdf>")

if __name__ == "__main__":
    main()