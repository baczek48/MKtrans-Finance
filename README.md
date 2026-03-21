# MKtrans Finance

Aplikacja desktopowa do zarządzania kosztami firmy transportowej MKtrans.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green) ![SQLite](https://img.shields.io/badge/DB-SQLite-lightgrey)

## Funkcje

### Koszty stale
- **Koszty standardowe** — 12 predefiniowanych parametrow (ZUS, podatek, leasing, itp.) z mozliwoscia edycji kwot domyslnych
- **Paliwo** — rejestr tankowan: data, litry, licznik, kwota netto/brutto
- **Naprawy** — rejestr napraw: nr rejestracyjny, data, opis (autorozszerzalny), kwota, licznik

### Urlop / Chorobowe
- Rejestracja urlopow i zwolnien chorobowych
- Imie i nazwisko pracownika
- Automatyczne liczenie dni

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
- **Formatowanie kwot** — polski format z kropkami tysiecy i przecinkiem dziesietnym (np. 1.234,56)
- **Kalendarz** — wlasny DatePicker w jezyku polskim

## Wymagania

- Python 3.8+
- Pillow (do logo)

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

Sciezka do bazy to ten sam folder, w ktorym znajduje sie `main.py`.
Aby przeniesc dane na inny komputer, wystarczy skopiowac plik `mktrans.db`.

## Struktura projektu

```
mktrans_finance/
├── main.py            # Glowna aplikacja (GUI)
├── database.py        # Warstwa bazy danych SQLite
├── generate_icon.py   # Generator logo i ikony
├── requirements.txt   # Zależności Python
├── icon.ico           # Ikona aplikacji
├── logo.png           # Logo 256x256
└── logo_small.png     # Logo 48x48 (pasek tytulu)
```

## Licencja

Prywatny projekt firmy MKtrans.
