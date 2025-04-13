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
    
    current_document = {
        'data': None,
        'datasp': None,
        'kwota': None,
        'kwota_vat': None,
        'licznik_konto': 0,
        'zmien_konto': False,
        'zmien_okres': False,
        'w_dokumencie': False,
        'w_zapisie': False,
        'zapisy': []
    }
    
    for i, line in enumerate(lines):
        # Początek nowego dokumentu dla kontrahenta
        if 'Dokument{' in line:
            # Jeśli kończymy poprzedni dokument, sprawdźmy czy nie były spełnione warunki
            if current_document['w_dokumencie'] and current_document['data'] is not None and current_document['datasp'] is not None:
                if current_document['data'] == current_document['datasp']:
                    changes['niezakwalifikowane_przez_date'] += 1
            
            # Reset dla nowego dokumentu
            current_document = {
                'data': None,
                'datasp': None,
                'kwota': None,
                'kwota_vat': None,
                'licznik_konto': 0,
                'zmien_konto': False,
                'zmien_okres': False,
                'w_dokumencie': True,
                'w_zapisie': False,
                'zapisy': []
            }
        
        # Zbieramy informacje o dokumencie
        if current_document['w_dokumencie']:
            # Daty dokumentu
            if 'datasp =' in line:
                current_document['datasp'] = line.split('=')[1].strip()
            
            if 'data =' in line:
                current_document['data'] = line.split('=')[1].strip()
            
            # Początek zapisu
            if 'Zapis{' in line:
                current_document['w_zapisie'] = True
                current_document['zapisy'].append({
                    'strona': None,
                    'kwota': None,
                    'konto': None
                })
            
            # Dane w zapisie
            if current_document['w_zapisie']:
                if 'strona =' in line or 'strona=' in line:
                    if '=' in line:
                        current_document['zapisy'][-1]['strona'] = line.split('=')[1].strip()
                
                if 'kwota =' in line:
                    try:
                        current_document['zapisy'][-1]['kwota'] = float(line.split('=')[1].strip())
                    except ValueError:
                        current_document['zapisy'][-1]['kwota'] = 0
                
                if 'konto =' in line:
                    current_document['zapisy'][-1]['konto'] = line.split('=')[1].strip()
                    
                    # Zliczamy konta dla późniejszej zmiany
                    current_document['licznik_konto'] += 1
                    
                    # Sprawdzamy drugi zapis z kontem 731-*
                    if current_document['zmien_konto'] and current_document['licznik_konto'] == 2:
                        konto_pos = line.find('=') + 1
                        konto_value = line[konto_pos:].strip()
                        if konto_value in ['731-1', '731-3', '731-4']:
                            # Zapisujemy nowe konto
                            new_konto = konto_value.replace('731-1', '702-2-3-1').replace('731-3', '702-2-3-3').replace('731-4', '702-2-3-4')
                            line = line[:konto_pos] + new_konto + '\n'
                            lines[i] = line
                            changes['zmiany_konto_731'] += 1
            
            # Koniec zapisu
            if current_document['w_zapisie'] and '}' in line and 'Zapis{' not in line and 'Dokument{' not in line:
                current_document['w_zapisie'] = False
                
                # Sprawdzamy, czy to zapis VAT (konto 221-1)
                ostatni_zapis = current_document['zapisy'][-1]
                if ostatni_zapis['konto'] == '221-1' and ostatni_zapis['strona'] == 'MA' and ostatni_zapis['kwota'] is not None:
                    current_document['kwota_vat'] = ostatni_zapis['kwota']
                    
                    # Pobierz oryginalny tekst linii z kwotą, aby sprawdzić czy jest minus
                    for prev_idx in range(i-5, i):
                        if prev_idx >= 0 and 'kwota =' in lines[prev_idx]:
                            kwota_line = lines[prev_idx]
                            kwota_str = kwota_line.split('=')[1].strip()
                            # Sprawdzamy warunki do zmian: data różna od datasp i brak minusa przed kwotą
                            if (current_document['data'] != current_document['datasp'] and 
                                not kwota_str.startswith('-')):
                                current_document['zmien_konto'] = True
                                current_document['zmien_okres'] = True
                            else:
                                if kwota_str.startswith('-'):
                                    changes['niezakwalifikowane_przez_kwote'] += 1
                            break
            
            # Zmiana okresu w Rejestrze
            if current_document['zmien_okres'] and 'okres =' in line:
                okres_pos = line.find('=') + 1
                data_okresu = line[okres_pos:].strip()
                nowa_data_okresu = ostatni_dzien_poprzedniego_miesiaca(data_okresu)
                line = line[:okres_pos] + nowa_data_okresu + '\n'
                lines[i] = line
                changes['zmiany_okres'] += 1
                current_document['zmien_okres'] = False
            
            # Koniec dokumentu
            if line.strip() == '}' and 'Zapis{' not in line and current_document['w_zapisie'] == False:
                current_document['w_dokumencie'] = False
    
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
