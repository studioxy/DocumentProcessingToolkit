import logging
import processor
import os

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)

# Przygotuj przykładowy plik VAT do testów
test_content = """Kontrahent{
        id =015213
        kod =WALDEMAR SZYSZKA
        nazwa =WALDEMAR SZYSZKA
        miejscowosc =MIERZYN
        ulica =EKOLOGICZNA 36
        dom =
        lokal =
        kodpocz =72-006
        nip =851-112-09-62 
        tel1=43-22-143,696-082-243         
        tel2=
        fax =                              
        }
Dokument{
        data =2025-04-01
        datasp =2025-03-31
        Dane nabywcy{
                khid =015213
                khnip =851-112-09-62 
        }
        symbol FK=FKS
        FK nazwa =F01457/S/25 
        JPK_V7 =
        opis FK =Sprzedaż towarów
        Zapis{
                strona=WN
                kwota =161.87
                konto =201-2-1-015213
        }
        Zapis{
                strona=MA
                kwota =131.60
                konto =702-2-3-1
        }
        Zapis{
                strona =MA
                kwota =30.27
                konto =221-1
        }
        Rejestr{
                JPK_V7 =GTU_06
                okres =2025-03-31
                stawka =23.00
                brutto =161.87
                netto =131.60
                vat =30.27
                stawka1 =23
                brutto2 =0.00
                netto2 =0.00
                vat2 =0.00
                stawka2 =22
                brutto3 =0.00
                netto3 =0.00
                vat3 =0.00
                stawka3 =8
                brutto4 =0.00
                netto4 =0.00
                vat4 =0.00
                stawka4 =7
                brutto5 =0.00
                netto5 =0.00
                vat5 =0.00
                stawka5 =5
                brutto6 =0.00
                netto6 =0.00
                vat6 =0.00
                stawka6 =3
                brutto7 =0.00
                netto7 =0.00
                vat7 =0.00
                stawka4 =0
                nettoWolne =0.00
                sumanetto =131.60
                sumavat =30.27
                brutto =161.87
        }
        Transakcja{
                termin =2025-04-15
                IdDlaRozliczen =-1
        }
}

Kontrahent{
        id =001455
        kod =TOMASZ HAMERA
        nazwa =TOMASZ HAMERA
        miejscowosc =Siadlo Dolne
        ulica =Wichrowe Wzgorza 9
        dom =
        lokal =
        kodpocz =72-001
        nip =851-240-40-87 
        tel1=512-309-973                   
        tel2=
        fax =Storrady 1c/6 budynek szklany 
        }
Dokument{
        data =2025-04-01
        datasp =2025-04-01
        Dane nabywcy{
                khid =001455
                khnip =851-240-40-87 
        }
        symbol FK=FKS
        FK nazwa =F01458/S/25 
        JPK_V7 =
        opis FK =Sprzedaż towarów
        Zapis{
                strona=WN
                kwota =92.25
                konto =201-2-1-001455
        }
        Zapis{
                strona=MA
                kwota =75.00
                konto =702-2-3-1
        }
        Zapis{
                strona =MA
                kwota =17.25
                konto =221-1
        }
        Rejestr{
                JPK_V7 =GTU_06
                okres =2025-03-31
                stawka =23.00
                brutto =92.25
                netto =75.00
                vat =17.25
                stawka1 =23
                brutto2 =0.00
                netto2 =0.00
                vat2 =0.00
                stawka2 =22
                brutto3 =0.00
                netto3 =0.00
                vat3 =0.00
                stawka3 =8
                brutto4 =0.00
                netto4 =0.00
                vat4 =0.00
                stawka4 =7
                brutto5 =0.00
                netto5 =0.00
                vat5 =0.00
                stawka5 =5
                brutto6 =0.00
                netto6 =0.00
                vat6 =0.00
                stawka6 =3
                brutto7 =0.00
                netto7 =0.00
                vat7 =0.00
                stawka4 =0
                nettoWolne =0.00
                sumanetto =75.00
                sumavat =17.25
                brutto =92.25
        }
        Transakcja{
                termin =2025-04-15
                IdDlaRozliczen =-1
        }
}

Kontrahent{
        id =000123
        kod =TEST KONTA 731
        nazwa =TEST KONTA 731
        miejscowosc =TESTOWE
        ulica =TESTOWA
        dom =
        lokal =
        kodpocz =72-001
        nip =111-222-33-44 
        tel1=111-222-333
        tel2=
        fax =
        }
Dokument{
        data =2025-04-01
        datasp =2025-03-31
        Dane nabywcy{
                khid =000123
                khnip =111-222-33-44
        }
        symbol FK=FKS
        FK nazwa =TEST 
        JPK_V7 =
        opis FK =Sprzedaż towarów
        Zapis{
                strona=WN
                kwota =161.87
                konto =201-2-1-000123
        }
        Zapis{
                strona=MA
                kwota =131.60
                konto =731-1
        }
        Zapis{
                strona =MA
                kwota =30.27
                konto =221-1
        }
        Rejestr{
                JPK_V7 =GTU_06
                okres =2025-03-31
                stawka =23.00
                brutto =161.87
                netto =131.60
                vat =30.27
        }
        Transakcja{
                termin =2025-04-15
                IdDlaRozliczen =-1
        }
}
"""

# Zrezygnujmy z zapisywania do pliku ze względu na problemy z kodowaniem
test_file = "test_vat.txt"
# Przetwarzamy bezpośrednio z pamięci

print("Test procesu przetwarzania pliku VAT:")
print("=" * 50)

# Przetwórz plik za pomocą naszej funkcji
lines = test_content.splitlines(keepends=True)
results = processor.process_vat_file(lines)

print("\nAnaliza wyników:")
print(f"- Liczba dokumentów: {results['liczba_wszystkich_dokumentow']}")
print(f"- Dokumenty z różnymi datami: {results.get('liczba_dokumentow_z_roznymi_datami', 'nie zliczono')}")
print(f"- Dokumenty niezakwalifikowane przez datę: {results['niezakwalifikowane_przez_date']}")
print(f"- Dokumenty niezakwalifikowane przez kwotę: {results['niezakwalifikowane_przez_kwote']}")
print(f"- Zmiany konta 731: {results['zmiany_konto_731']}")
print(f"- Zmiany okresu: {results['zmiany_okres']}")

# Usuń testowy plik
if os.path.exists(test_file):
    os.remove(test_file)

print("\nCzy wyniki są zgodne z oczekiwaniami?")
print("Oczekiwania:")
print("1. Dokument nr 1 (WALDEMAR SZYSZKA) ma różne daty: 2025-04-01 i 2025-03-31")
print("   - Powinien się kwalifikować do zmian okresu, ale NIE ma konta 731")
print("2. Dokument nr 2 (TOMASZ HAMERA) ma takie same daty: 2025-04-01 i 2025-04-01")
print("   - NIE powinien się kwalifikować do żadnych zmian")
print("3. Dokument nr 3 (TEST KONTA 731) ma różne daty i konto 731-1")
print("   - Powinien się kwalifikować do zmiany konta 731-1 na 702-2-3-1 i zmiany okresu")