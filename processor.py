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
    
    # ======= LOGOWANIE =======
    # Ustawmy poziom logowania na INFO w środowisku produkcyjnym
    # logging.basicConfig(level=logging.INFO)
    
    # W czasie debugowania możemy użyć poziomu DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    # ETAP 1: Dokładne wykrycie bloków dokumentów z pełnymi granicami
    dokumenty = []  # Lista wszystkich dokumentów z metadanymi
    linijki_poczatkowe = []  # Lista indeksów początku każdego dokumentu
    
    # Wykryj początki bloków (Kontrahent{) i ich zawartość
    for i, line in enumerate(lines):
        if 'Kontrahent{' in line.strip():
            linijki_poczatkowe.append(i)
    
    # Dodaj sztuczny koniec dla ostatniego bloku
    linijki_poczatkowe.append(len(lines))
    
    # ETAP 2: Wyodrębnij każdy blok dokumentu i przeanalizuj jego zawartość
    for i in range(len(linijki_poczatkowe) - 1):
        start_idx = linijki_poczatkowe[i]
        end_idx = linijki_poczatkowe[i+1]
        
        # Wyodrębnij blok linii
        blok_linii = lines[start_idx:end_idx]
        
        # Przygotuj słownik do analizy tego bloku
        dokument = {
            'id': i + 1,  # Numeracja od 1
            'data': None,
            'datasp': None,
            'linijki': blok_linii,
            'linia_start': start_idx,
            'linia_end': end_idx - 1,
            'konto_731_linia': None,
            'konto_731_wartosc': None,
            'okres_linia': None,
            'kwota_vat': None,
            'kwota_vat_ma_minus': False,
            'zmien_konto': False,
            'zmien_okres': False
        }
        
        # Analizuj każdą linię w bloku
        for j, linia in enumerate(blok_linii):
            linia_stripped = linia.strip()
            
            # Znajdź datę i datę sprzedaży (tylko pierwszej)
            if 'data =' in linia_stripped and dokument['data'] is None:
                dokument['data'] = linia_stripped.split('=')[1].strip()
                logging.debug(f"Blok {i+1}: Znaleziono data = {dokument['data']}")
            
            if 'datasp =' in linia_stripped and dokument['datasp'] is None:
                dokument['datasp'] = linia_stripped.split('=')[1].strip()
                logging.debug(f"Blok {i+1}: Znaleziono datasp = {dokument['datasp']}")
            
            # Znajdź kwotę VAT (przy koncie 221-1)
            if j+1 < len(blok_linii) and 'kwota =' in linia_stripped and 'konto =221-1' in blok_linii[j+1].strip():
                kwota_str = linia_stripped.split('=')[1].strip()
                dokument['kwota_vat'] = kwota_str
                dokument['kwota_vat_ma_minus'] = kwota_str.startswith('-')
                logging.debug(f"Blok {i+1}: Znaleziono kwotę VAT = {kwota_str}, ma minus: {dokument['kwota_vat_ma_minus']}")
            
            # Znajdź konto 731-*
            if 'konto =' in linia_stripped:
                konto_value = linia_stripped.split('=')[1].strip()
                
                if any(k in konto_value for k in ['731-1', '731-3', '731-4']):
                    dokument['konto_731_linia'] = start_idx + j
                    dokument['konto_731_wartosc'] = konto_value
                    logging.debug(f"Blok {i+1}: Znaleziono konto 731: {konto_value} w linii {start_idx + j}")
            
            # Znajdź linię z okresem (bardzo dokładnie)
            if 'okres =' in linia_stripped:
                dokument['okres_linia'] = start_idx + j
                logging.debug(f"Blok {i+1}: Znaleziono okres w linii {start_idx + j}")
        
        # Sprawdź czy wszystkie warunki biznesowe są spełnione:
        # 1) dokument ma obie daty
        # 2) data != datasp (różne daty)
        # 3) kwota VAT istnieje i nie ma znaku minus
        
        has_valid_dates = dokument['data'] and dokument['datasp']
        dates_are_different = has_valid_dates and dokument['data'] != dokument['datasp']
        has_valid_vat = dokument['kwota_vat'] is not None
        vat_not_negative = has_valid_vat and not dokument['kwota_vat_ma_minus']
        
        # Logowanie szczegółów warunków
        logging.debug(f"Blok {i+1}: Warunki: daty: {has_valid_dates}, różne daty: {dates_are_different}, " +
                     f"wartość VAT: {has_valid_vat}, bez minusa: {vat_not_negative}")
        
        # Sprawdź czy wszystkie warunki są spełnione
        if dates_are_different and vat_not_negative:
            
            # Kwalifikuje się do zmian, ale tylko określonych warunków
            if dokument['konto_731_linia'] is not None:
                dokument['zmien_konto'] = True
                logging.debug(f"Blok {i+1}: Kwalifikuje się do zmiany konta 731-* -> {dokument['konto_731_wartosc']}")
            
            # Zmiana okresu tylko gdy wszystkie warunki są spełnione
            if dokument['okres_linia'] is not None:
                dokument['zmien_okres'] = True
                logging.debug(f"Blok {i+1}: Kwalifikuje się do zmiany okresu -> różne daty i brak minusa w kwocie")
            
            logging.debug(f"Blok {i+1}: Finalne flagi -> zmien_konto={dokument['zmien_konto']}, zmien_okres={dokument['zmien_okres']}")
        else:
            # Nie kwalifikuje się - zapisz przyczynę
            if dokument['data'] and dokument['datasp'] and dokument['data'] == dokument['datasp']:
                changes['niezakwalifikowane_przez_date'] += 1
                logging.debug(f"Blok {i+1}: Nie kwalifikuje się - daty są takie same {dokument['data']} = {dokument['datasp']}")
            
            if dokument['kwota_vat'] and dokument['kwota_vat_ma_minus']:
                changes['niezakwalifikowane_przez_kwote'] += 1
                logging.debug(f"Blok {i+1}: Nie kwalifikuje się - kwota VAT ma minus: {dokument['kwota_vat']}")
        
        # Dodaj dokument do pełnej listy
        dokumenty.append(dokument)
    
    # Uaktualnij liczbę dokumentów
    changes['liczba_wszystkich_dokumentow'] = len(dokumenty)
    logging.info(f"Znaleziono {len(dokumenty)} dokumentów w pliku VAT")
    
    # ETAP 3: Wprowadź zmiany w dokumentach, które się kwalifikują
    for i, dokument in enumerate(dokumenty):
        # ZMIANA 1: Konto 731-* na 702-*
        if dokument['zmien_konto'] and dokument['konto_731_linia'] is not None:
            konto_org = dokument['konto_731_wartosc']
            new_konto = None
            
            if konto_org == '731-1':
                new_konto = '702-2-3-1'
            elif konto_org == '731-3':
                new_konto = '702-2-3-3'
            elif konto_org == '731-4':
                new_konto = '702-2-3-4'
            
            if new_konto:
                # Zachowaj dokładne formatowanie oryginału
                org_line = lines[dokument['konto_731_linia']]
                spaces_before = len(org_line) - len(org_line.lstrip())
                indent = ' ' * spaces_before
                
                # Dokładnie odtwórz formatowanie
                eq_pos = org_line.find('=')
                spaces_after_eq = len(org_line[eq_pos+1:]) - len(org_line[eq_pos+1:].lstrip())
                eq_space = ' ' * spaces_after_eq
                
                # Przygotuj nową linię z identycznym formatowaniem
                lines[dokument['konto_731_linia']] = f"{indent}konto ={eq_space}{new_konto}\n"
                changes['zmiany_konto_731'] += 1
                logging.info(f"Blok {i+1}: Zmieniono konto {konto_org} na {new_konto}")
        
        # ZMIANA 2: Okres na ostatni dzień poprzedniego miesiąca
        if dokument['zmien_okres'] and dokument['okres_linia'] is not None:
            org_line = lines[dokument['okres_linia']]
            okres_split = org_line.split('=')
            if len(okres_split) > 1:
                okres_value = okres_split[1].strip()
                nowy_okres = ostatni_dzien_poprzedniego_miesiaca(okres_value)
                
                # Zachowaj dokładne formatowanie oryginału
                spaces_before = len(org_line) - len(org_line.lstrip())
                indent = ' ' * spaces_before
                
                # Dokładnie odtwórz formatowanie
                eq_pos = org_line.find('=')
                spaces_after_eq = len(org_line[eq_pos+1:]) - len(org_line[eq_pos+1:].lstrip())
                eq_space = ' ' * spaces_after_eq
                
                # Przygotuj nową linię z identycznym formatowaniem
                lines[dokument['okres_linia']] = f"{indent}okres ={eq_space}{nowy_okres}\n"
                changes['zmiany_okres'] += 1
                logging.info(f"Blok {i+1}: Zmieniono okres {okres_value} na {nowy_okres}")
            else:
                logging.error(f"Blok {i+1}: Błąd parsowania linii okresu: {org_line}")
                
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
