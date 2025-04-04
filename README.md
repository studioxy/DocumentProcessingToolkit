# Aplikacja do przetwarzania dokumentów finansowych

Aplikacja webowa umożliwiająca przetwarzanie plików tekstowych zawierających dokumenty finansowe. Aplikacja obsługuje trzy rodzaje dokumentów: bankowe, VAT oraz kasowe/zakupy.

## Funkcje

- Interfejs webowy do przesyłania i przetwarzania plików dokumentów
- Automatyczne wykrywanie typu dokumentu na podstawie nazwy pliku
- Szczegółowe statystyki zmian dokonanych w plikach
- Możliwość pobrania przetworzonych plików
- Przeglądarka logów z historią przetwarzania

## Typy dokumentów i wprowadzane zmiany

### Dokumenty bankowe
- Zamiana konta 202-2-1-900102 na 131-5
- Zamiana dat na poprzedni dzień roboczy
- Zamiana konta 9 na 0 (dotyczy kont 201-2-1-9 i 202-2-1-9)

### Dokumenty VAT
- Zamiana kont 731-1, 731-3, 731-4 na odpowiednio 702-2-3-1, 702-2-3-3, 702-2-3-4
- Zmiana daty okresu na ostatni dzień poprzedniego miesiąca
- Zmiany są wprowadzane tylko dla dokumentów z kwotą > 0

### Dokumenty kasowe/zakupy
- Zmiana konta 9 na 0 (dotyczy kont 201-2-1-9 i 202-2-1-9)

## Uruchomienie aplikacji

```bash
python main.py
