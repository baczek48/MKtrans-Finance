# MKtrans Finance

Aplikacja desktopowa do zarządzania kosztami firmy transportowej MKtrans.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green) ![SQLite](https://img.shields.io/badge/DB-SQLite-lightgrey)

## Funkcje

### Koszty stale
- **Koszty standardowe** — 12 predefiniowanych parametrow (ZUS, podatek, leasing, itp.) z mozliwoscia edycji kwot domyslnych
- **Paliwo** — rejestr tankowan: data, litry, licznik, kwota netto/brutto
- **Naprawy** — rejestr napraw: nr rejestracyjny, data, opis (autorozszerzalny), kwota, licznik

### Personel
- **Lista personelu** — imie i nazwisko, stanowisko, telefon oraz daty waznosci: Uprawnienia ADR, Karta kierowcy, Prawo jazdy
- **Urlop / Chorobowe** — rejestracja urlopow i zwolnien, osoba wybierana z listy personelu, automatyczne liczenie dni

### Pojazdy
- Nr rejestracyjny, marka, model, uwagi oraz daty waznosci: Ubezpieczenie, Przeglad, Tachograf, UDT windy
- Paliwo i naprawy wybieraja pojazd z tej listy

### Ostrzezenia o terminach
- Panel na gorze glownego okna + komunikat przy starcie: 30 dni przed, 7 dni przed i po uplywie terminu
- Kazdy etap trzeba zaakceptowac; nowa data waznosci = nowe ostrzezenia
- Usuniecie osoby/pojazdu nie zmienia wczesniejszych wpisow (historia wyswietla sie jak dotad)

### Faktury
- Rejestr faktur z numerem, data i kwota
- Automatyczny termin platnosci 45 dni od daty wystawienia
- Kolorowy status: zielony (OK), zolty (zbliza sie), pomaranczowy (pilne), czerwony (po terminie)
- Checkbox "zaplacona"

### Podsumowanie
- Zestawienie przychodow (faktury) vs kosztow
- Wynik miesiaca

### Statystyki (osobne okno)
- Tabela porownawcza miesiecy w wybranym roku
- Koszty roczne: ubezpieczenia i podatek drogowy
- Podsumowanie roczne

### Inne
- **Akceptacja miesiaca** — blokada edycji po zatwierdzeniu (z mozliwoscia odblokowania)
- **Autozapis** co 60 sekund + przy zmianie miesiaca + przy zamknieciu
- **Backup** automatyczny przy starcie (maks. 10 kopii rotacyjnie)
- **Backup na e-mail** — guzik z koperta w gornym pasku wysyla baze jako ZIP zaszyfrowany AES-256 (SMTP, np. Gmail z haslem aplikacji); ustawienia pod guzikiem z zebatka. Odtworzenie: rozpakuj 7-Zipem/WinRAR-em i podmien `mktrans.db`
- **Formatowanie kwot** — polski format z kropkami tysiecy i przecinkiem dziesietnym (np. 1.234,56)
- **Kalendarz** — wlasny DatePicker w jezyku polskim

## Wymagania

- Python 3.8+
- Pillow (do logo)
- pyzipper (szyfrowany backup)

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python main.py
```

## Dane aplikacji

Wszystkie dane sa przechowywane lokalnie w katalogu aplikacji:

| Plik / Katalog | Opis |
|---|---|
| `mktrans.db` | Baza danych SQLite — wszystkie wpisy (koszty, faktury, urlopy, itp.) |
| `backups/` | Automatyczne kopie zapasowe bazy (maks. 10, tworzone przy kazdym uruchomieniu) |
| `mail_settings.json` | Ustawienia wysylki backupu; hasla zaszyfrowane Windows DPAPI (dzialaja tylko na tym koncie Windows) |

Baza `mktrans.db` nie jest szyfrowana ani hashowana — zaszyfrowany jest tylko backup wysylany mailem.

Sciezka do bazy to ten sam folder, w ktorym znajduje sie `main.py`.
Aby przeniesc dane na inny komputer, wystarczy skopiowac plik `mktrans.db`.

## Struktura projektu

```
mktrans_finance/
├── main.py            # Glowna aplikacja (GUI)
├── database.py        # Warstwa bazy danych SQLite
├── mail_backup.py     # Backup na e-mail (ZIP AES-256 + SMTP)
├── generate_icon.py   # Generator logo i ikony
├── requirements.txt   # Zależności Python
├── icon.ico           # Ikona aplikacji
├── logo.png           # Logo 256x256
└── logo_small.png     # Logo 48x48 (pasek tytulu)
```

## Licencja

Prywatny projekt firmy MKtrans.
