import os
import logging
from datetime import datetime, timedelta
import time

# Sprawdź, czy katalog 'logs' istnieje, jeśli nie, utwórz go
os.makedirs('logs', exist_ok=True)

# Konfiguracja logowania do pliku z datą, godziną i słowem "logdata" w katalogu 'logs'
log_filename = datetime.now().strftime('logs/logdata_%Y%m%d_%H%M%S.txt')
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def poprzedni_dzien_roboczy(data):
    data = datetime.strptime(data, '%Y-%m-%d')
    previous_day = data - timedelta(days=1)
    while previous_day.weekday() >= 5:  # 5 = Sobota, 6 = Niedziela
        previous_day -= timedelta(days=1)
    return previous_day.strftime('%Y-%m-%d')


def ostatni_dzien_poprzedniego_miesiaca(data):
    data = datetime.strptime(data, '%Y-%m-%d')
    first_day_current_month = data.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    return last_day_previous_month.strftime('%Y-%m-%d')


def log_separator():
    logging.info('-' * 80)


def aktualizuj_plik(nazwa_pliku, typ):
    start_time = time.time()
    log_separator()
    logging.info(f'Start przetwarzania pliku {typ}: {nazwa_pliku}')

    try:
        with open(nazwa_pliku, 'r', encoding='latin-1') as plik:
            linie = plik.readlines()

        if typ == 'bank':
            zmiany_konto_900102 = 0
            zmiany_data = 0
            zmiany_konto_9 = 0

            # Pierwsza pętla - zamiana 'konto =202-2-1-900102' na 'konto =131-5'
            for i, linia in enumerate(linie):
                if 'konto =202-2-1-900102' in linia:
                    linie[i] = linia.replace('202-2-1-900102', '131-5')
                    zmiany_konto_900102 += 1

            # Druga pętla - zamiana dat i zmiana konta
            for i, linia in enumerate(linie):
                if any(key in linia for key in ['data =', 'datasp =', 'dataKPKW =']):
                    prefix, data_value = linia.split('=', 1)
                    data_value = data_value.strip()

                    nowa_data = poprzedni_dzien_roboczy(data_value)
                    linie[i] = f'{prefix}= {nowa_data}\n'
                    zmiany_data += 1

                elif 'konto =' in linia:
                    if '201-2-1-9' in linia or '202-2-1-9' in linia:
                        nowa_wartosc = linia.replace('9', '0', 1)
                        linie[i] = nowa_wartosc
                        zmiany_konto_9 += 1

            logging.info(
                f'Łączna liczba zmian konta 202-2-1-900102 na 131-5: {zmiany_konto_900102}')
            logging.info(f'Łączna liczba zmian dat: {zmiany_data}')
            logging.info(f'Łączna liczba zmian konta 9 na 0: {zmiany_konto_9}')

        elif typ == 'vat':
            zmiany_drugi_konto = 0
            niezakwalifikowane_przez_kwote = 0
            zmiany_konto_731 = 0
            zmiany_okres = 0

            data_value = None
            datasp_value = None
            kwota_value = None
            zmien_drugi_konto = False
            zmien_okres = False
            licznik_konto = 0

            for i, linia in enumerate(linie):
                if 'Dokument{' in linia:
                    # Początek nowego dokumentu, resetuj zmienne
                    data_value = None
                    datasp_value = None
                    kwota_value = None
                    zmien_drugi_konto = False
                    zmien_okres = False
                    licznik_konto = 0

                if 'datasp =' in linia:
                    datasp_value = linia.split('=')[1].strip()
                    licznik_konto = 0  # resetowanie licznika przy nowym dokumentie

                if 'data =' in linia:
                    data_value = linia.split('=')[1].strip()

                if 'kwota =' in linia:
                    try:
                        kwota_value = float(linia.split('=')[1].strip())
                    except ValueError:
                        kwota_value = None

                if kwota_value is not None and kwota_value > 0:
                    zmien_drugi_konto = True
                    zmien_okres = True
                else:
                    if kwota_value is not None and kwota_value <= 0:
                        niezakwalifikowane_przez_kwote += 1

                if 'konto =' in linia:
                    licznik_konto += 1
                    if zmien_drugi_konto and licznik_konto == 2:
                        konto_pos = linia.find('=') + 1
                        konto_value = linia[konto_pos:].strip()
                        if konto_value == '731-1':
                            linia = linia[:konto_pos] + '702-2-3-1\n'
                        elif konto_value == '731-3':
                            linia = linia[:konto_pos] + '702-2-3-3\n'
                        elif konto_value == '731-4':
                            linia = linia[:konto_pos] + '702-2-3-4\n'
                        linie[i] = linia
                        zmiany_konto_731 += 1
                        zmien_drugi_konto = False

                if zmien_okres and 'okres =' in linia:
                    okres_pos = linia.find('=') + 1
                    data_okresu = linia[okres_pos:].strip()
                    nowa_data_okresu = ostatni_dzien_poprzedniego_miesiaca(
                        data_okresu)
                    linia = linia[:okres_pos] + nowa_data_okresu + '\n'
                    linie[i] = linia
                    zmiany_okres += 1
                    zmien_okres = False

            logging.info(
                f'Łączna liczba zmian konta 731-1, 731-3, 731-4 na odpowiednie wartości: {zmiany_konto_731}')
            logging.info(
                f'Łączna liczba zmian daty okresu na ostatni dzień poprzedniego miesiąca: {zmiany_okres}')
            logging.info(
                f'Łączna liczba przypadków niezakwalifikowanych przez kwotę <= 0: {niezakwalifikowane_przez_kwote}')

        elif typ == 'kasa':
            zmiany_konto_9 = 0

            for i, linia in enumerate(linie):
                if 'konto =' in linia and ('201-2-1-9' in linia or '202-2-1-9' in linia):
                    nowa_wartosc = linia.replace('9', '0', 1)
                    linie[i] = nowa_wartosc
                    zmiany_konto_9 += 1

            logging.info(f'Łączna liczba zmian konta 9 na 0: {zmiany_konto_9}')

        with open(nazwa_pliku, 'w', encoding='latin-1') as plik:
            plik.writelines(linie)

        elapsed_time = (time.time() - start_time) * 1000  # czas w milisekundach
        logging.info(f'Zakończono przetwarzanie pliku {typ}: {nazwa_pliku}')
        logging.info(f'Czas przetwarzania pliku: {elapsed_time:.5f} ms')
        log_separator()

    except Exception as e:
        logging.error(
            f'Błąd podczas przetwarzania pliku {typ} {nazwa_pliku}: {str(e)}')
        log_separator()


def znajdz_i_aktualizuj_plik():
    for plik in os.listdir('.'):
        if plik.endswith('.txt'):
            if 'bank' in plik.lower():
                aktualizuj_plik(plik, 'bank')
            elif 'vat' in plik.lower():
                aktualizuj_plik(plik, 'vat')
            elif 'zak' in plik.lower() or 'kasa' in plik.lower():
                aktualizuj_plik(plik, 'kasa')


znajdz_i_aktualizuj_plik()
