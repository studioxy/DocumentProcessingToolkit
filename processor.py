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
    """
    Przetwarza plik VAT zgodnie z określonymi regułami biznesowymi.
    Struktura pliku: plik składa się z bloków, z których każdy zaczyna się od "Kontrahent{", a następnie zawiera "Dokument{".
    
    Reguły przetwarzania:
    1. Jeśli w ramach JEDNEGO dokumentu (w obrębie tego samego bloku) data i datasp są różne,
       i kwota VAT (221-1) nie ma minusa, to:
       a) Jeśli w dokumencie jest konto 731-1, 731-3 lub 731-4, zmień je odpowiednio na 702-2-3-1, 702-2-3-3 lub 702-2-3-4
       b) Zmień datę okresu na ostatni dzień poprzedniego miesiąca
    2. W przeciwnym razie nie dokonuj zmian w dokumencie
    """
    changes = {
        'zmiany_konto_731': 0,
        'zmiany_okres': 0,
        'niezakwalifikowane_przez_kwote': 0,
        'niezakwalifikowane_przez_date': 0,
        'liczba_wszystkich_dokumentow': 0
    }
    
    # Pierwsza faza: wyodrębnienie wszystkich bloków dokumentów
    bloki = []
    current_block = []
    in_block = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Wykryj początek nowego bloku (Kontrahent{)
        if "Kontrahent{" in line_stripped:
            # Jeśli mamy już jakiś blok, zapisz go
            if in_block and current_block:
                bloki.append(current_block)
            
            # Rozpocznij nowy blok
            current_block = [line]
            in_block = True
        elif in_block:
            # Kontynuuj zbieranie linii dla bieżącego bloku
            current_block.append(line)
    
    # Nie zapomnij o ostatnim bloku
    if in_block and current_block:
        bloki.append(current_block)
    
    # Loguj liczbę znalezionych bloków
    changes['liczba_wszystkich_dokumentow'] = len(bloki)
    logging.info(f"Znaleziono {len(bloki)} dokumentów w pliku VAT")
    
    # Druga faza: analizowanie każdego bloku i wprowadzanie zmian
    for idx, blok in enumerate(bloki):
        # Słownik na dane dokumentu
        dokument = {
            'id': idx + 1,
            'data': None,
            'datasp': None,
            'konta': [],              # Lista wszystkich kont w bloku
            'konto_731_linia': None,  # Indeks linii z kontem 731-*
            'konto_731_wartosc': None,# Wartość konta 731-*
            'okres_linia': None,      # Indeks linii z okresem
            'kwota_vat': None,        # Kwota VAT
            'kwota_vat_ma_minus': False  # Czy kwota VAT ma minus
        }
        
        # Analiza linii w bloku
        lines_in_file_indices = []  # Indeksy linii w oryginalnym pliku
        data_found = False
        datasp_found = False
        
        for i, line in enumerate(blok):
            line_stripped = line.strip()
            # Mapuj indeks w bloku do indeksu w oryginalnym pliku
            idx_in_file = lines.index(line) if line in lines else -1
            lines_in_file_indices.append(idx_in_file)
            
            # Zbierz daty z dokumentu
            if 'data =' in line_stripped and not data_found:
                dokument['data'] = line_stripped.split('=')[1].strip()
                data_found = True
            elif 'datasp =' in line_stripped and not datasp_found:
                dokument['datasp'] = line_stripped.split('=')[1].strip()
                datasp_found = True
            
            # Identyfikuj zapisy księgowe
            if 'konto =' in line_stripped:
                konto_value = line_stripped.split('=')[1].strip()
                dokument['konta'].append((idx_in_file, konto_value))
                
                # Sprawdź czy to konto 731-*
                if any(k in konto_value for k in ['731-1', '731-3', '731-4']):
                    dokument['konto_731_linia'] = idx_in_file
                    dokument['konto_731_wartosc'] = konto_value
            
            # Zbierz kwotę VAT (konto 221-1)
            if ('kwota =' in line_stripped and i+1 < len(blok) and 
                'konto =221-1' in blok[i+1].strip()):
                kwota_str = line_stripped.split('=')[1].strip()
                dokument['kwota_vat'] = kwota_str
                dokument['kwota_vat_ma_minus'] = kwota_str.startswith('-')
            
            # Znajdź linię z okresem
            if 'okres =' in line_stripped:
                dokument['okres_linia'] = idx_in_file
        
        # Teraz decyzja o modyfikacji dokumentu
        # Warunki: 1) data != datasp, 2) kwota VAT nie ma minusa
        if (dokument['data'] and dokument['datasp'] and dokument['data'] != dokument['datasp'] and 
            dokument['kwota_vat'] and not dokument['kwota_vat_ma_minus']):
            
            # ZMIANA 1: Konto 731-* na 702-*
            if dokument['konto_731_linia'] is not None:
                konto_org = dokument['konto_731_wartosc']
                new_konto = None
                
                if konto_org == '731-1':
                    new_konto = '702-2-3-1'
                elif konto_org == '731-3':
                    new_konto = '702-2-3-3'
                elif konto_org == '731-4':
                    new_konto = '702-2-3-4'
                
                if new_konto:
                    # Zachowaj formatowanie oryginału
                    org_line = lines[dokument['konto_731_linia']]
                    spaces = len(org_line) - len(org_line.lstrip())
                    indent = ' ' * spaces
                    lines[dokument['konto_731_linia']] = f"{indent}konto ={new_konto}\n"
                    changes['zmiany_konto_731'] += 1
                    logging.info(f"Blok {idx+1}: Zmieniono konto {konto_org} na {new_konto}")
            
            # ZMIANA 2: Okres na ostatni dzień poprzedniego miesiąca
            if dokument['okres_linia'] is not None:
                org_line = lines[dokument['okres_linia']]
                okres_value = org_line.split('=')[1].strip()
                nowy_okres = ostatni_dzien_poprzedniego_miesiaca(okres_value)
                
                # Zachowaj formatowanie oryginału
                spaces = len(org_line) - len(org_line.lstrip())
                indent = ' ' * spaces
                lines[dokument['okres_linia']] = f"{indent}okres ={nowy_okres}\n"
                changes['zmiany_okres'] += 1
                logging.info(f"Blok {idx+1}: Zmieniono okres {okres_value} na {nowy_okres}")
        else:
            # Dokument nie kwalifikuje się do zmian - logowanie przyczyny
            if dokument['data'] and dokument['datasp'] and dokument['data'] == dokument['datasp']:
                changes['niezakwalifikowane_przez_date'] += 1
                logging.info(f"Blok {idx+1}: Niezakwalifikowany - daty są identyczne: {dokument['data']}")
            if dokument['kwota_vat'] and dokument['kwota_vat_ma_minus']:
                changes['niezakwalifikowane_przez_kwote'] += 1
                logging.info(f"Blok {idx+1}: Niezakwalifikowany - kwota VAT ma minus: {dokument['kwota_vat']}")
    
    # Podsumowanie
    logging.info(f'Łączna liczba bloków w pliku: {changes["liczba_wszystkich_dokumentow"]}')
    logging.info(f'Łączna liczba zmian konta 731-* na odpowiednie wartości: {changes["zmiany_konto_731"]}')
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
