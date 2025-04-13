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
    
    # Flagi stanu
    w_kontrahencie = False
    w_dokumencie = False
    w_zapisie = False
    
    # Zmienne dla bieżącego dokumentu
    data_value = None
    datasp_value = None
    kwota_value = None
    licznik_konto = 0
    zmiana_konta_731 = False
    zmiana_okresu = False
    vat_zapis_kwota_str = None
    
    # Funkcja do resetowania zmiennych dokumentu
    def reset_dokument_vars():
        nonlocal data_value, datasp_value, kwota_value, licznik_konto, zmiana_konta_731, zmiana_okresu, vat_zapis_kwota_str, w_dokumencie, w_zapisie
        data_value = None
        datasp_value = None
        kwota_value = None
        licznik_konto = 0
        zmiana_konta_731 = False
        zmiana_okresu = False
        vat_zapis_kwota_str = None
        w_dokumencie = False
        w_zapisie = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Wykryj początek nowego kontrahenta
        if 'Kontrahent{' in line:
            # Resetujemy wszystko dla nowego kontrahenta
            w_kontrahencie = True
            reset_dokument_vars()
        
        # Wykryj początek nowego dokumentu
        elif 'Dokument{' in line and w_kontrahencie:
            # Resetujemy zmienne dla nowego dokumentu
            reset_dokument_vars()
            w_dokumencie = True
        
        # Zbieramy daty z bieżącego dokumentu
        elif w_dokumencie:
            if 'data =' in line:
                data_value = line.split('=')[1].strip()
            
            elif 'datasp =' in line:
                datasp_value = line.split('=')[1].strip()
            
            # Początek zapisu
            elif 'Zapis{' in line:
                w_zapisie = True
                licznik_konto = 0  # Resetujemy licznik dla każdego zapisu
            
            # Przetwarzanie zapisów w dokumencie
            elif w_zapisie:
                # Szukamy kwoty VAT (3ci zapis, konto 221-1)
                if 'kwota =' in line:
                    kwota_str = line.split('=')[1].strip()
                    
                    # Jeśli następna linia ma konto 221-1, zapisujemy kwotę VAT
                    next_line_idx = i + 1
                    if next_line_idx < len(lines) and 'konto =221-1' in lines[next_line_idx]:
                        vat_zapis_kwota_str = kwota_str
                
                # Sprawdzamy konto w zapisie i liczymy wystąpienia
                elif 'konto =' in line:
                    licznik_konto += 1
                    
                    # Sprawdzamy czy to drugi zapis (konto 731-*)
                    if licznik_konto == 2 and zmiana_konta_731:
                        konto_pos = line.find('=') + 1
                        konto_value = line[konto_pos:].strip()
                        
                        if konto_value == '731-1':
                            lines[i] = line[:konto_pos] + '702-2-3-1\n'
                            changes['zmiany_konto_731'] += 1
                        elif konto_value == '731-3':
                            lines[i] = line[:konto_pos] + '702-2-3-3\n'
                            changes['zmiany_konto_731'] += 1
                        elif konto_value == '731-4':
                            lines[i] = line[:konto_pos] + '702-2-3-4\n'
                            changes['zmiany_konto_731'] += 1
                
                # Koniec zapisu
                elif '}' in line and 'Zapis{' not in line and 'Dokument{' not in line and 'Kontrahent{' not in line:
                    w_zapisie = False
            
            # Zmiana okresu rozliczenia
            elif zmiana_okresu and 'okres =' in line:
                okres_pos = line.find('=') + 1
                data_okresu = line[okres_pos:].strip()
                nowa_data_okresu = ostatni_dzien_poprzedniego_miesiaca(data_okresu)
                lines[i] = line[:okres_pos] + nowa_data_okresu + '\n'
                changes['zmiany_okres'] += 1
                zmiana_okresu = False
            
            # Po wszystkich zapisach, przed końcem dokumentu, sprawdzamy warunki
            elif 'Rejestr{' in line and data_value is not None and datasp_value is not None:
                # Analizujemy czy daty są różne i czy kwota VAT nie ma minusa
                if vat_zapis_kwota_str is not None:
                    # Główny warunek biznesowy - różnica dat w tym samym dokumencie i brak minusa
                    if data_value != datasp_value and not vat_zapis_kwota_str.startswith('-'):
                        zmiana_konta_731 = True
                        zmiana_okresu = True
                    else:
                        # Logowanie dlaczego nie zakwalifikowano
                        if data_value == datasp_value:
                            changes['niezakwalifikowane_przez_date'] += 1
                        if vat_zapis_kwota_str is not None and vat_zapis_kwota_str.startswith('-'):
                            changes['niezakwalifikowane_przez_kwote'] += 1
            
            # Koniec dokumentu - pusta linia lub koniec bloku
            elif line.strip() == '}' and w_dokumencie and not w_zapisie:
                w_dokumencie = False
        
        i += 1
    
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
