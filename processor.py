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
    
    # Configure logging to file - używamy UTF-8 zamiast latin-1 aby obsługiwać polskie znaki
    log_filename = datetime.now().strftime('logs/logdata_%Y%m%d_%H%M%S.txt')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
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
        # Porada: wczytujemy plik z tym samym kodowaniem jakiego używamy do zapisu logów
        with open(filename, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()
            logging.info(f"Wczytano plik {filename} używając kodowania UTF-8 z automatyczną zamianą nierozpoznanych znaków")
        
        if file_type == 'bank':
            results['changes'] = process_bank_file(lines)
        elif file_type == 'vat':
            results['changes'] = process_vat_file(lines)
        elif file_type == 'kasa':
            results['changes'] = process_kasa_file(lines)
        
        with open(filename, 'w', encoding='utf-8') as file:
            file.writelines(lines)
            logging.info(f"Zapisano plik {filename} używając kodowania UTF-8")
        
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
    logging.info("===== ROZPOCZYNAM PRZETWARZANIE PLIKU VAT =====")
    
    changes = {
        'zmiany_konto_731': 0,
        'zmiany_okres': 0,
        'niezakwalifikowane_przez_kwote': 0,
        'niezakwalifikowane_przez_date': 0,
        'liczba_wszystkich_dokumentow': 0,
        'liczba_dokumentow_z_roznymi_datami': 0,
        'dokumenty_zkwalifikowane': 0
    }
    
    # ETAP 1: Pobieranie danych - identyfikacja bloków i ekstrakcja ich parametrów
    logging.info("ETAP 1: Pobieranie danych z pliku")
    baza_dokumentow = []  # Ta "baza" będzie zawierać wszystkie wyekstrahowane dokumenty z ich danymi
    
    # Znajdź wszystkie bloki Kontrahent{ i ich ID
    kontrahenci = []
    aktualny_kontrahent = None
    
    for i, line in enumerate(lines):
        linia = line.strip()
        
        # Znajdź początek bloku kontrahenta
        if linia == 'Kontrahent{':
            aktualny_kontrahent = {
                'linia_start': i,
                'linia_koniec': None,
                'id': None,
                'nazwa': None,
                'dokumenty': []
            }
            kontrahenci.append(aktualny_kontrahent)
        
        # Pobierz ID kontrahenta
        elif aktualny_kontrahent and 'id =' in linia and aktualny_kontrahent['id'] is None:
            try:
                aktualny_kontrahent['id'] = linia.split('=', 1)[1].strip()
            except:
                aktualny_kontrahent['id'] = 'unknown'
            logging.debug(f"Znaleziono kontrahenta ID: {aktualny_kontrahent['id']} w linii {i}")
        
        # Pobierz nazwę kontrahenta
        elif aktualny_kontrahent and 'nazwa =' in linia and aktualny_kontrahent['nazwa'] is None:
            try:
                aktualny_kontrahent['nazwa'] = linia.split('=', 1)[1].strip()
            except:
                aktualny_kontrahent['nazwa'] = 'brak nazwy'
        
        # Znajdź koniec bloku kontrahenta - albo nowy Kontrahent{, albo koniec pliku
        if linia == 'Kontrahent{' and len(kontrahenci) > 1:
            kontrahenci[-2]['linia_koniec'] = i - 1
    
    # Ustaw koniec ostatniego kontrahenta
    if kontrahenci:
        kontrahenci[-1]['linia_koniec'] = len(lines) - 1
    
    # Sprawdź czy mamy kontrahenta TOMASZ HAMERA (001455) - znany problematyczny przypadek
    for k in kontrahenci:
        if k['id'] == '001455':
            logging.warning(f"UWAGA: Znaleziono kontrahenta TOMASZ HAMERA (ID: 001455). Wszystkie dokumenty tego kontrahenta będą dokładnie analizowane.")
            
    logging.info(f"Znaleziono {len(kontrahenci)} kontrahentów w pliku")
    
    # ETAP 2: Znajdź wszystkie dokumenty w blokach kontrahentów
    indeks_dokumentu = 0
    
    for kontrahent in kontrahenci:
        # Znajdź wszystkie bloki Dokument{ w ramach tego kontrahenta
        i_start = kontrahent['linia_start'] 
        i_koniec = kontrahent['linia_koniec']
        
        # Analizuj wszystkie linie w bloku kontrahenta
        for i in range(i_start, i_koniec + 1):
            linia = lines[i].strip()
            
            # Znajdź początek dokumentu
            if linia == 'Dokument{':
                indeks_dokumentu += 1
                dokument = {
                    'id': indeks_dokumentu,
                    'kontrahent_id': kontrahent['id'],
                    'kontrahent_nazwa': kontrahent['nazwa'],
                    'linia_start': i,
                    'linia_koniec': None,
                    'data': None,
                    'datasp': None,
                    'kwota_vat': None,
                    'kwota_vat_ma_minus': False,
                    'konto_731_linia': None,
                    'konto_731_wartosc': None,
                    'okres_linia': None,
                    'do_zmiany': False,
                    'data_clean': None,
                    'datasp_clean': None
                }
                
                # Znajdź koniec tego dokumentu (do następnego Dokument{ lub końca kontrahenta)
                for j in range(i + 1, i_koniec + 1):
                    if lines[j].strip() == 'Dokument{':
                        dokument['linia_koniec'] = j - 1
                        break
                    elif j == i_koniec:
                        dokument['linia_koniec'] = j
                
                # Teraz znajdź wszystkie potrzebne wartości w dokumencie
                for j in range(dokument['linia_start'], dokument['linia_koniec'] + 1):
                    linia_j = lines[j].strip()
                    
                    # Znajdź datę
                    if linia_j.startswith('data ='):
                        try:
                            dokument['data'] = linia_j.split('=', 1)[1].strip()
                            logging.debug(f"Dokument {indeks_dokumentu}: data = {dokument['data']}")
                        except:
                            pass
                    
                    # Znajdź datę sprzedaży
                    elif linia_j.startswith('datasp ='):
                        try:
                            dokument['datasp'] = linia_j.split('=', 1)[1].strip()
                            logging.debug(f"Dokument {indeks_dokumentu}: datasp = {dokument['datasp']}")
                        except:
                            pass
                    
                    # Znajdź okres
                    elif linia_j.startswith('okres ='):
                        dokument['okres_linia'] = j
                        logging.debug(f"Dokument {indeks_dokumentu}: znaleziono okres w linii {j}")
                    
                    # Znajdź kwotę VAT przy koncie 221-1
                    elif 'konto =' in linia_j and '221-1' in linia_j:
                        # Znajdź linię z kwotą w tym samym zapisie (powyżej konta)
                        for prev_j in range(max(dokument['linia_start'], j-5), j):
                            prev_line = lines[prev_j].strip()
                            if 'kwota =' in prev_line:
                                try:
                                    wartość_kwoty = prev_line.split('=', 1)[1].strip()
                                    dokument['kwota_vat'] = wartość_kwoty
                                    dokument['kwota_vat_ma_minus'] = '-' in wartość_kwoty
                                    logging.debug(f"Dokument {indeks_dokumentu}: kwota VAT = {wartość_kwoty}, ma minus: {dokument['kwota_vat_ma_minus']}")
                                except:
                                    pass
                                break
                    
                    # Znajdź konto 731-*
                    elif 'konto =' in linia_j:
                        try:
                            konto_value = linia_j.split('=', 1)[1].strip()
                            if any(k in konto_value for k in ['731-1', '731-3', '731-4']):
                                dokument['konto_731_linia'] = j
                                dokument['konto_731_wartosc'] = konto_value
                                logging.debug(f"Dokument {indeks_dokumentu}: znaleziono konto {konto_value} w linii {j}")
                        except:
                            pass
                
                # Dodaj dokument do bazy dokumentów
                baza_dokumentow.append(dokument)
    
    # Aktualizuj licznik dokumentów
    changes['liczba_wszystkich_dokumentow'] = len(baza_dokumentow)
    logging.info(f"Łącznie znaleziono {len(baza_dokumentow)} dokumentów")
    
    # ETAP 3: Analiza danych i podejmowanie decyzji
    # Reset liczników dla ETAPU 3
    changes.update({
        'liczba_dokumentow_z_roznymi_datami': 0,
        'dokumenty_zkwalifikowane': 0,
        'niezakwalifikowane_przez_kwote': 0,
        'niezakwalifikowane_przez_date': 0
    })
    
    logging.info("ETAP 3: Analiza dokumentów i warunków biznesowych")
    
    for dokument in baza_dokumentow:
        # Inicjalizacja - domyślnie dokument NIE kwalifikuje się do zmian
        dokument['do_zmiany'] = False
        
        # Sprawdź, czy mamy obie daty
        if dokument['data'] is None or dokument['datasp'] is None:
            logging.warning(f"Dokument {dokument['id']}: Brak kompletu dat: data={dokument['data']}, datasp={dokument['datasp']}")
            continue
            
        # Oczyść daty (usuwając białe znaki) przed porównaniem
        dokument['data_clean'] = dokument['data'].strip()
        dokument['datasp_clean'] = dokument['datasp'].strip()
        
        # Porównanie oczyszczonych dat
        daty_sa_rozne = dokument['data_clean'] != dokument['datasp_clean']
        
        # Jeżeli daty są różne, zwiększ odpowiedni licznik
        if daty_sa_rozne:
            changes['liczba_dokumentow_z_roznymi_datami'] += 1
        
        # Sprawdź warunek kwoty VAT – musi być obecna oraz bez minusa
        kwota_bez_minusa = dokument['kwota_vat'] is not None and not dokument['kwota_vat_ma_minus']
        
        # Szczegółowy log dla dokumentu
        logging.info(f"Analiza dokumentu {dokument['id']} (kontrahent: {dokument['kontrahent_id']}):")
        logging.info(f"  - Data oczyszczona: [{dokument['data_clean']}], DataSp oczyszczona: [{dokument['datasp_clean']}]")
        logging.info(f"  - Daty są różne: {daty_sa_rozne}")
        logging.info(f"  - Kwota VAT: {dokument['kwota_vat']}, bez minusa: {kwota_bez_minusa}")
        logging.info(f"  - Konto 731: {dokument['konto_731_wartosc'] if dokument['konto_731_wartosc'] else 'brak'}")
        
        # Decyzja o kwalifikacji do zmian – tylko gdy WSZYSTKIE warunki są spełnione
        if daty_sa_rozne:
            if kwota_bez_minusa:
                # Dokument spełnia wszystkie wymagane warunki
                dokument['do_zmiany'] = True
                changes['dokumenty_zkwalifikowane'] += 1
                logging.info(f"  => Dokument {dokument['id']} KWALIFIKUJE SIĘ do zmian")
            else:
                changes['niezakwalifikowane_przez_kwote'] += 1
                logging.info(f"  => Dokument {dokument['id']} NIE KWALIFIKUJE SIĘ - kwota VAT ma minus lub brak")
        else:
            changes['niezakwalifikowane_przez_date'] += 1
            logging.info(f"  => Dokument {dokument['id']} NIE KWALIFIKUJE SIĘ - daty są identyczne: [{dokument['data_clean']}] = [{dokument['datasp_clean']}]")
    
    # Log końcowy - podsumowanie wyników ETAPU 3
    logging.info(f"Podsumowanie ETAPU 3: {changes}")
    
    # ETAP 4: Wprowadzenie zmian w pliku na podstawie analizy
    logging.info("ETAP 4: Wprowadzanie zmian w dokumentach")
    
    for dokument in baza_dokumentow:
        # Pomiń dokumenty, które nie kwalifikują się do zmian
        if not dokument['do_zmiany']:
            continue
        
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
                logging.info(f"Dokument {dokument['id']}: Zmieniono konto {konto_org} na {new_konto}")
        
        # ZMIANA 2: Okres na ostatni dzień poprzedniego miesiąca
        if dokument['okres_linia'] is not None:
            org_line = lines[dokument['okres_linia']]
            okres_split = org_line.split('=', 1)
            if len(okres_split) > 1:
                okres_value = okres_split[1].strip()
                nowy_okres = ostatni_dzien_poprzedniego_miesiaca(okres_value)
                
                # Szczegółowe informacje o zmianie
                logging.info(f"Dokument {dokument['id']}: Zmiana okresu:")
                logging.info(f"  - Aktualny okres: {okres_value}")
                logging.info(f"  - Nowy okres: {nowy_okres}")
                
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
                logging.info(f"Dokument {dokument['id']}: Zmieniono okres {okres_value} na {nowy_okres}")
            else:
                logging.error(f"Dokument {dokument['id']}: Błąd parsowania linii okresu: {org_line}")
    
    # Podsumowanie
    logging.info("===== PODSUMOWANIE ZMIAN =====")
    logging.info(f"Łączna liczba dokumentów: {changes['liczba_wszystkich_dokumentow']}")
    logging.info(f"Łączna liczba dokumentów z różnymi datami: {changes['liczba_dokumentow_z_roznymi_datami']}")
    logging.info(f"Łączna liczba dokumentów zakwalifikowanych do zmian: {changes['dokumenty_zkwalifikowane']}")
    logging.info(f"Łączna liczba zmian konta 731-*: {changes['zmiany_konto_731']}")
    logging.info(f"Łączna liczba zmian daty okresu: {changes['zmiany_okres']}")
    logging.info(f"Łączna liczba dokumentów niezakwalifikowanych przez datę: {changes['niezakwalifikowane_przez_date']}")
    logging.info(f"Łączna liczba dokumentów niezakwalifikowanych przez kwotę: {changes['niezakwalifikowane_przez_kwote']}")
    logging.info("===== KONIEC PRZETWARZANIA PLIKU VAT =====")
    
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
