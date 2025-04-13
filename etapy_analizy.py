import logging

# Funkcja inicjalizująca licznik zmian
def reset_changes():
    """
    Resetuje licznik zmian do stanu wyjściowego
    """
    return {
        'liczba_dokumentow_z_roznymi_datami': 0,
        'dokumenty_zkwalifikowane': 0,
        'niezakwalifikowane_przez_kwote': 0,
        'niezakwalifikowane_przez_date': 0,
        'zmiany_konto_731': 0,
        'zmiany_okres': 0
    }

# Funkcja czyszcząca i porównująca daty
def clean_and_compare_dates(dokument):
    """
    Czyści daty i dokonuje porównania.
    Zwraca: (data_clean, datasp_clean, czy_daty_sa_rozne)
    Jeżeli brak którejkolwiek daty, zwraca (None, None, False)
    """
    if dokument.get('data') is None or dokument.get('datasp') is None:
        logging.warning(
            f"Dokument {dokument.get('id')}: Brak kompletu dat: data={dokument.get('data')}, datasp={dokument.get('datasp')}"
        )
        return None, None, False

    data_clean = dokument['data'].strip()
    datasp_clean = dokument['datasp'].strip()
    # Bezpośrednie porównanie ciągów, gdy format jest jednolity
    daty_sa_rozne = data_clean != datasp_clean
    return data_clean, datasp_clean, daty_sa_rozne

# Funkcja przetwarzająca pojedynczy dokument
def process_document(dokument, changes):
    """
    Przetwarza pojedynczy dokument, aktualizując liczniki oraz flagę kwalifikacji.
    """
    # Inicjalizacja – domyślnie dokument NIE kwalifikuje się do zmian
    dokument['do_zmiany'] = False

    # Przetwórz i porównaj daty
    data_clean, datasp_clean, daty_sa_rozne = clean_and_compare_dates(dokument)
    if data_clean is None:
        return  # Pomijamy dokument bez kompletnych dat

    dokument['data_clean'] = data_clean
    dokument['datasp_clean'] = datasp_clean

    if daty_sa_rozne:
        changes['liczba_dokumentow_z_roznymi_datami'] += 1

    # Sprawdź warunek dotyczący kwoty VAT: wartość musi być dostępna i bez minusa
    kwota_bez_minusa = dokument.get('kwota_vat') is not None and not dokument.get('kwota_vat_ma_minus', False)

    # Szczegółowe logowanie dla danego dokumentu
    logging.info(f"Analiza dokumentu {dokument.get('id')} (kontrahent: {dokument.get('kontrahent_id', 'nieznany')}):")
    logging.info(f"  - Data oczyszczona: [{data_clean}], DataSp oczyszczona: [{datasp_clean}]")
    logging.info(f"  - Daty są różne: {daty_sa_rozne}")
    logging.info(f"  - Kwota VAT: {dokument.get('kwota_vat')} (bez minusa: {kwota_bez_minusa})")
    konto731 = dokument.get('konto_731_wartosc')
    logging.info(f"  - Konto 731: {konto731 if konto731 else 'brak'}")

    # Decyzja o kwalifikacji do zmian – dokument kwalifikuje się wyłącznie, gdy
    # daty są różne i kwota VAT spełnia warunek
    if daty_sa_rozne:
        if kwota_bez_minusa:
            dokument['do_zmiany'] = True
            changes['dokumenty_zkwalifikowane'] += 1
            logging.info(f"  => Dokument {dokument.get('id')} KWALIFIKUJE SIĘ do zmian")
        else:
            changes['niezakwalifikowane_przez_kwote'] += 1
            logging.info(f"  => Dokument {dokument.get('id')} NIE KWALIFIKUJE SIĘ - kwota VAT ma minus lub brak")
    else:
        changes['niezakwalifikowane_przez_date'] += 1
        logging.info(
            f"  => Dokument {dokument.get('id')} NIE KWALIFIKUJE SIĘ - daty są identyczne: [{data_clean}] = [{datasp_clean}]"
        )

# Główna funkcja analizy dokumentów
def analyze_documents(baza_dokumentow):
    """
    Przeprowadza analizę dokumentów według założonej logiki ETAPU 3.
    """
    changes = reset_changes()
    logging.info("ETAP 3: Analiza dokumentów i warunków biznesowych")

    for dokument in baza_dokumentow:
        process_document(dokument, changes)

    logging.info(f"Podsumowanie ETAPU 3: {changes}")
    return changes

# Funkcja przetwarzająca zmiany w dokumencie
def process_document_changes(dokument, lines, changes):
    """
    Wprowadza zmiany w dokumencie, który został zakwalifikowany do modyfikacji.
    """
    # Pomiń dokumenty, które nie kwalifikują się do zmian
    if not dokument.get('do_zmiany', False):
        return
    
    # ZMIANA 1: Konto 731-* na 702-*
    if dokument.get('konto_731_linia') is not None:
        konto_org = dokument.get('konto_731_wartosc')
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
            logging.info(f"Dokument {dokument.get('id')}: Zmieniono konto {konto_org} na {new_konto}")
    
    # ZMIANA 2: Okres na ostatni dzień poprzedniego miesiąca
    if dokument.get('okres_linia') is not None:
        from processor import ostatni_dzien_poprzedniego_miesiaca
        
        org_line = lines[dokument['okres_linia']]
        okres_split = org_line.split('=', 1)
        if len(okres_split) > 1:
            okres_value = okres_split[1].strip()
            nowy_okres = ostatni_dzien_poprzedniego_miesiaca(okres_value)
            
            # Szczegółowe informacje o zmianie
            logging.info(f"Dokument {dokument.get('id')}: Zmiana okresu:")
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
            logging.info(f"Dokument {dokument.get('id')}: Zmieniono okres {okres_value} na {nowy_okres}")
        else:
            logging.error(f"Dokument {dokument.get('id')}: Błąd parsowania linii okresu: {org_line}")

# Funkcja wprowadzająca zmiany we wszystkich dokumentach
def apply_document_changes(baza_dokumentow, lines, changes):
    """
    Przeprowadza ETAP 4 - wprowadzanie zmian w dokumentach na podstawie wcześniejszej analizy.
    """
    logging.info("ETAP 4: Wprowadzanie zmian w dokumentach")
    
    for dokument in baza_dokumentow:
        process_document_changes(dokument, lines, changes)
    
    # Podsumowanie zmian
    logging.info("===== PODSUMOWANIE ZMIAN =====")
    logging.info(f"Łączna liczba dokumentów: {changes.get('liczba_wszystkich_dokumentow', 0)}")
    logging.info(f"Łączna liczba dokumentów z różnymi datami: {changes.get('liczba_dokumentow_z_roznymi_datami', 0)}")
    logging.info(f"Łączna liczba dokumentów zakwalifikowanych do zmian: {changes.get('dokumenty_zkwalifikowane', 0)}")
    logging.info(f"Łączna liczba zmian konta 731-*: {changes.get('zmiany_konto_731', 0)}")
    logging.info(f"Łączna liczba zmian daty okresu: {changes.get('zmiany_okres', 0)}")
    logging.info(f"Łączna liczba dokumentów niezakwalifikowanych przez datę: {changes.get('niezakwalifikowane_przez_date', 0)}")
    logging.info(f"Łączna liczba dokumentów niezakwalifikowanych przez kwotę: {changes.get('niezakwalifikowane_przez_kwote', 0)}")
    logging.info("===== KONIEC PRZETWARZANIA PLIKU VAT =====")