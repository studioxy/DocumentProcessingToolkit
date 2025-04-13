import os
import logging
import time
import json
from datetime import datetime, timedelta

def detect_file_type(filename):
    """Detect file type based on filename."""
    filename = filename.lower()
    if 'bank' in filename:
        return 'bank'
    elif 'vat' in filename:
        return 'vat'
    elif 'zak' in filename or 'kasa' in filename:
        return 'kasa'
    return 'unknown'

def poprzedni_dzien_roboczy(data):
    """Calculate the previous working day."""
    data = datetime.strptime(data, '%Y-%m-%d')
    previous_day = data - timedelta(days=1)
    while previous_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        previous_day -= timedelta(days=1)
    return previous_day.strftime('%Y-%m-%d')

def ostatni_dzien_poprzedniego_miesiaca(data):
    """Calculate the last day of the previous month."""
    data = datetime.strptime(data, '%Y-%m-%d')
    first_day_current_month = data.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    return last_day_previous_month.strftime('%Y-%m-%d')

def log_separator():
    """Add a separator to the log."""
    logging.info('-' * 80)

def process_file(filename, file_type):
    """Process a file based on its type and return statistics."""
    start_time = time.time()
    
    # Configure logging to file
    log_filename = datetime.now().strftime('logs/logdata_%Y%m%d_%H%M%S.txt')
    file_handler = logging.FileHandler(log_filename, encoding='latin-1')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    log_separator()
    logging.info(f'Start przetwarzania pliku {file_type}: {filename}')
    
    results = {
        'changes': {},
        'errors': [],
        'processing_time': 0,
        'log_file': log_filename
    }
    
    try:
        with open(filename, 'r', encoding='latin-1') as file:
            lines = file.readlines()
        
        if file_type == 'bank':
            results['changes'] = process_bank_file(lines)
        elif file_type == 'vat':
            results['changes'] = process_vat_file(lines)
        elif file_type == 'kasa':
            results['changes'] = process_kasa_file(lines)
        
        with open(filename, 'w', encoding='latin-1') as file:
            file.writelines(lines)
        
        elapsed_time = (time.time() - start_time) * 1000  # time in milliseconds
        results['processing_time'] = round(elapsed_time, 5)
        
        logging.info(f'Zakończono przetwarzanie pliku {file_type}: {filename}')
        logging.info(f'Czas przetwarzania pliku: {results["processing_time"]:.5f} ms')
        log_separator()
        
    except Exception as e:
        error_message = f'Błąd podczas przetwarzania pliku {file_type} {filename}: {str(e)}'
        logging.error(error_message)
        results['errors'].append(error_message)
        log_separator()
    
    # Remove the file handler to avoid duplicate logging
    root_logger.removeHandler(file_handler)
    file_handler.close()
    
    return results

def process_bank_file(lines):
    """Process a bank file and return statistics."""
    changes = {
        'zmiany_konto_900102': 0,
        'zmiany_data': 0,
        'zmiany_konto_9': 0
    }
    
    # First pass - replace 'konto =202-2-1-900102' with 'konto =131-5'
    for i, line in enumerate(lines):
        if 'konto =202-2-1-900102' in line:
            lines[i] = line.replace('202-2-1-900102', '131-5')
            changes['zmiany_konto_900102'] += 1
    
    # Second pass - replace dates and account numbers
    for i, line in enumerate(lines):
        if any(key in line for key in ['data =', 'datasp =', 'dataKPKW =']):
            prefix, data_value = line.split('=', 1)
            data_value = data_value.strip()
            
            nowa_data = poprzedni_dzien_roboczy(data_value)
            lines[i] = f'{prefix}= {nowa_data}\n'
            changes['zmiany_data'] += 1
        
        elif 'konto =' in line:
            if '201-2-1-9' in line or '202-2-1-9' in line:
                new_value = line.replace('9', '0', 1)
                lines[i] = new_value
                changes['zmiany_konto_9'] += 1
    
    logging.info(f'Łączna liczba zmian konta 202-2-1-900102 na 131-5: {changes["zmiany_konto_900102"]}')
    logging.info(f'Łączna liczba zmian dat: {changes["zmiany_data"]}')
    logging.info(f'Łączna liczba zmian konta 9 na 0: {changes["zmiany_konto_9"]}')
    
    return changes

def process_vat_file(lines):
    """Process a VAT file and return statistics."""
    changes = {
        'zmiany_konto_731': 0,
        'zmiany_okres': 0,
        'niezakwalifikowane_przez_kwote': 0,
        'niezakwalifikowane_przez_date': 0
    }
    
    # Przetwarzanie dokumentów w dwóch etapach:
    # 1. Najpierw identyfikujemy wszystkie dokumenty i analizujemy ich zawartość
    # 2. Następnie wprowadzamy zmiany zgodnie z regułami biznesowymi
    
    # Zbieramy kompletne dokumenty
    dokumenty = []
    dokument_aktualny = None
    
    # Faza 1: Identyfikacja i analiza dokumentów
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Początek nowego kontrahenta - zawsze resetujemy dokument
        if 'Kontrahent{' in line:
            dokument_aktualny = {
                'kontrahent': True,
                'data': None,
                'datasp': None,
                'kwota_vat': None,
                'kwota_vat_str': None,
                'kwota_vat_ma_minus': False,
                'zapis_drugi_konto_linia': None,
                'zapis_drugi_konto_wartosc': None,
                'okres_linia': None,
                'okres_wartosc': None,
                'zmieniac_konto': False,
                'zmieniac_okres': False,
                'jest_konto_731': False  # Czy jest konto 731 w dokumencie
            }
        
        # Jeśli mamy aktywny dokument
        if dokument_aktualny is not None:
            # Zbieramy daty z dokumentu
            if 'data =' in line:
                dokument_aktualny['data'] = line.split('=')[1].strip()
            
            if 'datasp =' in line:
                dokument_aktualny['datasp'] = line.split('=')[1].strip()
            
            # Identyfikujemy kwotę VAT w trzecim zapisie
            if 'kwota =' in line and 'konto =221-1' in lines[i+1]:
                kwota_str = line.split('=')[1].strip()
                dokument_aktualny['kwota_vat_str'] = kwota_str
                dokument_aktualny['kwota_vat_ma_minus'] = kwota_str.startswith('-')
                try:
                    dokument_aktualny['kwota_vat'] = float(kwota_str)
                except ValueError:
                    dokument_aktualny['kwota_vat'] = 0
            
            # Śledzenie zapisów w dokumencie
            if 'Zapis{' in line:
                zapis_counter = 0  # Reset licznika zapisów
            
            # Identyfikujemy drugie konto (zarówno 731-* jak i 702-*)
            if 'konto =' in line:
                # Wykrywanie drugiego zapisu (numer 2)
                if 'Zapis{' in lines[i-5:i] and 'strona=MA' in lines[i-4:i]:
                    dokument_aktualny['zapis_drugi_konto_linia'] = i
                    dokument_aktualny['zapis_drugi_konto_wartosc'] = line.split('=')[1].strip()
                    
                    # Sprawdzenie czy to konto 731-*
                    if any(konto in line for konto in ['731-1', '731-3', '731-4']):
                        dokument_aktualny['jest_konto_731'] = True
            
            # Identyfikujemy linię z okresem
            if 'okres =' in line:
                dokument_aktualny['okres_linia'] = i
                dokument_aktualny['okres_wartosc'] = line.split('=')[1].strip()
            
            # Koniec dokumentu - dodajemy do kolekcji jeśli mamy wszystkie potrzebne dane
            if line == '}' and dokument_aktualny.get('data') is not None:
                # Sprawdzamy warunki modyfikacji (różnica dat i kwota bez minusa)
                # Ważne: zmieniamy konto tylko jeśli jest to 731-*, zmienamy okres zawsze gdy warunki spełnione
                if (dokument_aktualny['data'] != dokument_aktualny['datasp'] and 
                    not dokument_aktualny['kwota_vat_ma_minus']):
                    
                    # Konto zmieniamy tylko gdy jest to 731-*
                    dokument_aktualny['zmieniac_konto'] = dokument_aktualny['jest_konto_731']
                    dokument_aktualny['zmieniac_okres'] = True  # Okres zmieniamy zawsze gdy daty różne i brak minusa
                else:
                    # Logowanie przyczyn niezakwalifikowania
                    if dokument_aktualny['data'] == dokument_aktualny['datasp']:
                        changes['niezakwalifikowane_przez_date'] += 1
                        logging.debug(f'Dokument niezakwalifikowany: daty są takie same ({dokument_aktualny["data"]})')
                    if dokument_aktualny['kwota_vat_ma_minus']:
                        changes['niezakwalifikowane_przez_kwote'] += 1
                        logging.debug(f'Dokument niezakwalifikowany: kwota VAT ma minus ({dokument_aktualny["kwota_vat_str"]})')
                
                # Dodajemy dokument do kolekcji
                dokumenty.append(dokument_aktualny)
                dokument_aktualny = None  # Resetujemy aktualny dokument
    
    # Debug: Wypisanie informacji o dokumentach
    for i, dok in enumerate(dokumenty):
        logging.debug(f"Dokument {i+1}: data={dok['data']}, datasp={dok['datasp']}, " +
                     f"zmieniac_konto={dok['zmieniac_konto']}, zmieniac_okres={dok['zmieniac_okres']}, " +
                     f"jest_konto_731={dok['jest_konto_731']}, konto={dok.get('zapis_drugi_konto_wartosc')}")
    
    # Faza 2: Wprowadzanie zmian
    for dokument in dokumenty:
        # Zmiana konta 731-* na odpowiednie 702-* (tylko gdy jest to 731-*)
        if dokument['zmieniac_konto'] and dokument['zapis_drugi_konto_linia'] is not None and dokument['jest_konto_731']:
            konto_value = dokument['zapis_drugi_konto_wartosc']
            linia_idx = dokument['zapis_drugi_konto_linia']
            
            if konto_value == '731-1':
                new_konto = '702-2-3-1'
                original_line = lines[linia_idx]
                # Zachowujemy oryginalne wcięcie przed 'konto'
                spaces_before = len(original_line) - len(original_line.lstrip())
                indent = ' ' * spaces_before
                lines[linia_idx] = f'{indent}konto ={new_konto}\n'
                changes['zmiany_konto_731'] += 1
            elif konto_value == '731-3':
                new_konto = '702-2-3-3'
                original_line = lines[linia_idx]
                spaces_before = len(original_line) - len(original_line.lstrip())
                indent = ' ' * spaces_before
                lines[linia_idx] = f'{indent}konto ={new_konto}\n'
                changes['zmiany_konto_731'] += 1
            elif konto_value == '731-4':
                new_konto = '702-2-3-4'
                original_line = lines[linia_idx]
                spaces_before = len(original_line) - len(original_line.lstrip())
                indent = ' ' * spaces_before
                lines[linia_idx] = f'{indent}konto ={new_konto}\n'
                changes['zmiany_konto_731'] += 1
        
        # Zmiana okresu na ostatni dzień poprzedniego miesiąca
        if dokument['zmieniac_okres'] and dokument['okres_linia'] is not None:
            okres_value = dokument['okres_wartosc']
            linia_idx = dokument['okres_linia']
            
            nowy_okres = ostatni_dzien_poprzedniego_miesiaca(okres_value)
            original_line = lines[linia_idx]
            spaces_before = len(original_line) - len(original_line.lstrip())
            indent = ' ' * spaces_before
            lines[linia_idx] = f'{indent}okres ={nowy_okres}\n'
            changes['zmiany_okres'] += 1
    
    # Logowanie podsumowania
    logging.info(f'Łączna liczba zmian konta 731-1, 731-3, 731-4 na odpowiednie wartości: {changes["zmiany_konto_731"]}')
    logging.info(f'Łączna liczba zmian daty okresu na ostatni dzień poprzedniego miesiąca: {changes["zmiany_okres"]}')
    logging.info(f'Łączna liczba przypadków niezakwalifikowanych przez taką samą datę: {changes["niezakwalifikowane_przez_date"]}')
    logging.info(f'Łączna liczba przypadków niezakwalifikowanych przez ujemną kwotę (z minusem): {changes["niezakwalifikowane_przez_kwote"]}')
    
    return changes

def process_kasa_file(lines):
    """Process a cash register file and return statistics."""
    changes = {
        'zmiany_konto_9': 0
    }
    
    for i, line in enumerate(lines):
        if 'konto =' in line and ('201-2-1-9' in line or '202-2-1-9' in line):
            new_value = line.replace('9', '0', 1)
            lines[i] = new_value
            changes['zmiany_konto_9'] += 1
    
    logging.info(f'Łączna liczba zmian konta 9 na 0: {changes["zmiany_konto_9"]}')
    
    return changes
