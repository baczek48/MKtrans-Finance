import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import os

import database as db

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# CONSTANTS
# ============================================================

STANDARD_COST_PARAMS = [
    ('zarzadzajacy', 'ZARZĄDZAJĄCY TRANSPORTEM', 300),
    ('zus', 'ZUS', 0),
    ('ppe', 'PPE', 0),
    ('pit4', 'PIT4', 0),
    ('vat7', 'VAT7', 0),
    ('ksiegowa', 'KSIĘGOWA', 200),
    ('adr', 'ADR', 100),
    ('tacho', 'TACHO', 200),
    ('leasing', 'LEASING', 0),
    ('amortyzacja', 'AMORTYZACJA', 3600),
    ('wyplata', 'WYPŁATA', 0),
    ('parking', 'PARKING', 520),
]

MONTHS_PL = [
    'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'
]

BG = '#f0f2f5'
CARD = '#ffffff'
PRIMARY = '#1a56db'
PRIMARY_DARK = '#1e3a8a'
GREEN = '#059669'
RED = '#dc2626'
BORDER = '#e2e8f0'
LABEL_FG = '#475569'


class MKtransApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MKtrans Finance")
        self.root.geometry("1440x960")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 750)

        # Set window icon
        ico_path = os.path.join(APP_DIR, 'icon.ico')
        if os.path.exists(ico_path):
            self.root.iconbitmap(ico_path)

        # Load header logo
        logo_path = os.path.join(APP_DIR, 'logo_small.png')
        if os.path.exists(logo_path):
            self._logo_img = ImageTk.PhotoImage(Image.open(logo_path).resize((44, 44), Image.LANCZOS))
        else:
            self._logo_img = None

        db.init_db()
        db.create_backup()

        self.current_month = self._current_month_key()
        self.is_locked = False

        self.cost_entries = {}
        self.fuel_rows = []
        self.repair_rows = []
        self.leave_rows = []
        self.invoice_rows = []

        self._build_styles()
        self._build_ui()
        self._load_month()

        # Auto-save every 60 seconds
        self._auto_save_loop()

    def _auto_save_loop(self):
        self._save_month()
        self.root.after(60000, self._auto_save_loop)

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', font=('Segoe UI', 11, 'bold'), padding=[24, 10],
                        background='#e2e8f0', foreground=LABEL_FG)
        style.map('TNotebook.Tab',
                  background=[('selected', PRIMARY)],
                  foreground=[('selected', 'white')])

    # ============================================================
    # DATE ENTRY HELPER
    # ============================================================

    def _make_date_entry(self, parent, initial='', width=12):
        de = DateEntry(parent, width=width, font=('Segoe UI', 9),
                       date_pattern='yyyy-mm-dd', locale='pl_PL',
                       background=PRIMARY_DARK, foreground='white',
                       headersbackground=PRIMARY, headersforeground='white',
                       selectbackground=PRIMARY, selectforeground='white',
                       borderwidth=1, relief='solid')
        if initial:
            try:
                de.set_date(datetime.strptime(initial, '%Y-%m-%d').date())
            except (ValueError, TypeError):
                pass
        return de

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        # --- Header ---
        header = tk.Frame(self.root, bg=PRIMARY_DARK, height=70)
        header.pack(fill='x')
        header.pack_propagate(False)

        hinner = tk.Frame(header, bg=PRIMARY_DARK)
        hinner.pack(fill='x', padx=20, pady=10)

        left = tk.Frame(hinner, bg=PRIMARY_DARK)
        left.pack(side='left')

        if self._logo_img:
            logo_label = tk.Label(left, image=self._logo_img, bg=PRIMARY_DARK)
            logo_label.pack(side='left', padx=(0, 12))
        else:
            logo = tk.Canvas(left, width=44, height=44, bg=PRIMARY_DARK, highlightthickness=0)
            logo.pack(side='left', padx=(0, 12))
            logo.create_rectangle(2, 2, 42, 42, fill=PRIMARY, outline='')
            logo.create_text(22, 16, text='MK', fill='white', font=('Segoe UI', 12, 'bold'))
            logo.create_text(22, 32, text='trans', fill='#fbbf24', font=('Segoe UI', 8, 'bold'))

        tf = tk.Frame(left, bg=PRIMARY_DARK)
        tf.pack(side='left')
        tk.Label(tf, text='MKtrans Finance', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(tf, text='Ewidencja kosztów firmy transportowej', bg=PRIMARY_DARK,
                 fg='#a5b4fc', font=('Segoe UI', 9)).pack(anchor='w')

        right = tk.Frame(hinner, bg=PRIMARY_DARK)
        right.pack(side='right')

        tk.Label(right, text='Miesiąc:', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))

        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(right, textvariable=self.month_var, state='readonly',
                                         width=20, font=('Segoe UI', 10))
        self._populate_months()
        self.month_combo.pack(side='left', padx=(0, 10))
        self.month_combo.bind('<<ComboboxSelected>>', self._on_month_change)

        self.btn_accept = tk.Button(right, text='Zaakceptuj', bg=GREEN, fg='white',
                                     font=('Segoe UI', 9, 'bold'), bd=0, padx=14, pady=5,
                                     cursor='hand2', command=self._accept_month)
        self.btn_accept.pack(side='left', padx=3)

        self.btn_edit = tk.Button(right, text='Tryb edycji', bg='#d97706', fg='white',
                                   font=('Segoe UI', 9, 'bold'), bd=0, padx=14, pady=5,
                                   cursor='hand2', command=self._enable_edit)

        self.btn_stats = tk.Button(right, text='Statystyki', bg='#7c3aed', fg='white',
                                    font=('Segoe UI', 9, 'bold'), bd=0, padx=14, pady=5,
                                    cursor='hand2', command=self._show_stats)
        self.btn_stats.pack(side='left', padx=3)

        # --- Locked bar ---
        self.locked_bar = tk.Frame(self.root, bg='#fef3c7', height=32)
        self.locked_label = tk.Label(self.locked_bar, text='Miesiąc zaakceptowany - tryb tylko do odczytu',
                                     bg='#fef3c7', fg='#92400e', font=('Segoe UI', 9, 'bold'))
        self.locked_label.pack(pady=6)

        # --- Notebook (tabs) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=16, pady=(8, 16))

        self.tab_costs = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_costs, text='  Koszty stałe  ')
        self._build_costs_tab()

        self.tab_leave = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_leave, text='  Urlop / Chorobowe  ')
        self._build_leave_tab()

        self.tab_invoices = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_invoices, text='  Faktury  ')
        self._build_invoices_tab()

        self.tab_summary = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_summary, text='  Podsumowanie  ')
        self._build_summary_tab()

    def _populate_months(self):
        now = datetime.now()
        months = []
        self._month_keys = []
        for i in range(-12, 3):
            y = now.year + (now.month - 1 + i) // 12
            m = (now.month - 1 + i) % 12 + 1
            key = f"{y}-{m:02d}"
            label = f"{MONTHS_PL[m - 1]} {y}"
            months.append(label)
            self._month_keys.append(key)
        self.month_combo['values'] = months
        current_key = self._current_month_key()
        if current_key in self._month_keys:
            self.month_combo.current(self._month_keys.index(current_key))
        else:
            self.month_combo.current(12)

    def _current_month_key(self):
        now = datetime.now()
        return f"{now.year}-{now.month:02d}"

    # ============================================================
    # TAB: KOSZTY STALE
    # ============================================================

    def _build_costs_tab(self):
        canvas = tk.Canvas(self.tab_costs, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_costs, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        main = tk.Frame(scroll_frame, bg=BG)
        main.pack(fill='x', padx=24, pady=20)

        # --- Podsekcja: Koszty standardowe ---
        lf1 = tk.LabelFrame(main, text='  Koszty standardowe  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf1.pack(fill='x', pady=(0, 16))

        # Load saved defaults from DB
        saved_defaults = db.get_cost_defaults()

        self.cost_entries = {}
        for key, label, hardcoded_default in STANDARD_COST_PARAMS:
            default = saved_defaults.get(key, hardcoded_default)
            row = tk.Frame(lf1, bg=CARD)
            row.pack(fill='x', pady=3)
            tk.Label(row, text=label, bg=CARD, fg=LABEL_FG,
                     font=('Segoe UI', 10), width=30, anchor='w').pack(side='left')
            var = tk.StringVar(value=str(default) if default else '')
            entry = tk.Entry(row, textvariable=var, width=15, font=('Segoe UI', 10),
                             justify='right', bd=1, relief='solid')
            entry.pack(side='left', padx=(8, 0))
            tk.Label(row, text='PLN', bg=CARD, fg='#9ca3af', font=('Segoe UI', 9)).pack(side='left', padx=4)
            var.trace_add('write', lambda *a: self._recalc())
            self.cost_entries[key] = (var, entry)

        # Button to set current values as new defaults
        defaults_frame = tk.Frame(lf1, bg=CARD)
        defaults_frame.pack(fill='x', pady=(10, 0))
        self.btn_set_defaults = tk.Button(
            defaults_frame, text='Zapisz aktualne kwoty jako domyślne',
            bg='#f0fdf4', fg=GREEN, font=('Segoe UI', 9, 'bold'), bd=1, relief='solid',
            padx=12, pady=4, cursor='hand2', command=self._save_defaults)
        self.btn_set_defaults.pack(side='right')
        tk.Label(defaults_frame, text='Kwoty domyślne będą używane dla nowych miesięcy',
                 bg=CARD, fg='#9ca3af', font=('Segoe UI', 8)).pack(side='right', padx=8)

        # --- Podsekcja: Paliwo ---
        lf2 = tk.LabelFrame(main, text='  Paliwo  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf2.pack(fill='x', pady=(0, 16))

        self.btn_add_fuel = tk.Button(lf2, text='+ Dodaj wpis', bg='#e0e7ff', fg=PRIMARY,
                                       font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                       cursor='hand2', command=self._add_fuel_row)
        self.btn_add_fuel.pack(anchor='w', pady=(0, 8))

        fh = tk.Frame(lf2, bg='#f1f5f9')
        fh.pack(fill='x')
        fuel_cols = [('Data', 16), ('Litry', 12), ('Licznik (km)', 14),
                     ('Kwota netto', 14), ('Kwota brutto', 14), ('', 5)]
        for i, (text, w) in enumerate(fuel_cols):
            tk.Label(fh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.fuel_container = tk.Frame(lf2, bg=CARD)
        self.fuel_container.pack(fill='x')

        self.fuel_netto_label = tk.Label(lf2, text='Suma netto paliwa: 0,00 PLN', bg=CARD,
                                          fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self.fuel_netto_label.pack(fill='x', pady=(8, 0))

        # --- Podsekcja: Naprawa auta ---
        lf3 = tk.LabelFrame(main, text='  Naprawa auta  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf3.pack(fill='x', pady=(0, 16))

        self.btn_add_repair = tk.Button(lf3, text='+ Dodaj wpis', bg='#e0e7ff', fg=PRIMARY,
                                         font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                         cursor='hand2', command=self._add_repair_row)
        self.btn_add_repair.pack(anchor='w', pady=(0, 8))

        rh = tk.Frame(lf3, bg='#f1f5f9')
        rh.pack(fill='x')
        repair_cols = [('Nr rejestracyjny', 16), ('Data', 16), ('Co zrobione', 24),
                       ('Kwota (PLN)', 14), ('Licznik', 12), ('', 5)]
        for i, (text, w) in enumerate(repair_cols):
            tk.Label(rh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.repair_container = tk.Frame(lf3, bg=CARD)
        self.repair_container.pack(fill='x')

        self.repair_sum_label = tk.Label(lf3, text='Suma napraw: 0,00 PLN', bg=CARD,
                                          fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self.repair_sum_label.pack(fill='x', pady=(8, 0))

        # --- Podsumowanie kosztow ---
        sep = tk.Frame(main, bg=PRIMARY, height=3)
        sep.pack(fill='x', pady=(8, 0))

        totals = tk.Frame(main, bg=CARD, padx=20, pady=16, bd=1, relief='solid',
                           highlightbackground=BORDER)
        totals.pack(fill='x', pady=(0, 8))

        tk.Label(totals, text='PODSUMOWANIE KOSZTÓW STAŁYCH', bg=CARD, fg=PRIMARY_DARK,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        breakdown = tk.Frame(totals, bg=CARD)
        breakdown.pack(fill='x', pady=8)

        self.total_standard_label = tk.Label(breakdown, text='Koszty standardowe: 0,00 PLN',
                                              bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_standard_label.pack(side='left', padx=(0, 28))
        self.total_fuel_label = tk.Label(breakdown, text='Paliwo (netto): 0,00 PLN',
                                          bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_fuel_label.pack(side='left', padx=(0, 28))
        self.total_repairs_label = tk.Label(breakdown, text='Naprawy: 0,00 PLN',
                                             bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_repairs_label.pack(side='left')

        self.total_costs_label = tk.Label(totals, text='RAZEM: 0,00 PLN', bg=CARD,
                                           fg=RED, font=('Segoe UI', 13, 'bold'))
        self.total_costs_label.pack(anchor='w', pady=(4, 0))

    def _save_defaults(self):
        for key, (var, entry) in self.cost_entries.items():
            try:
                val = float(var.get())
            except (ValueError, tk.TclError):
                val = 0
            db.save_cost_default(key, val)
        messagebox.showinfo('Kwoty domyślne', 'Zapisano aktualne kwoty jako domyślne.\n'
                            'Będą używane dla nowych miesięcy.')

    # ============================================================
    # TAB: URLOP
    # ============================================================

    def _build_leave_tab(self):
        inner = tk.Frame(self.tab_leave, bg=BG, padx=24, pady=20)
        inner.pack(fill='both', expand=True)

        card = tk.Frame(inner, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=20, pady=16)
        card.pack(fill='x')

        self.btn_add_leave = tk.Button(card, text='+ Dodaj wpis', bg='#e0e7ff', fg=PRIMARY,
                                        font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                        cursor='hand2', command=self._add_leave_row)
        self.btn_add_leave.pack(anchor='w', pady=(0, 8))

        lh = tk.Frame(card, bg='#f1f5f9')
        lh.pack(fill='x')
        leave_cols = [('Typ', 12), ('Imię i nazwisko', 20), ('Data od', 14), ('Data do', 14), ('Liczba dni', 10), ('', 5)]
        for i, (text, w) in enumerate(leave_cols):
            tk.Label(lh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.leave_container = tk.Frame(card, bg=CARD)
        self.leave_container.pack(fill='x')

        summary = tk.Frame(card, bg=CARD)
        summary.pack(fill='x', pady=(10, 0))

        self.total_vacation_label = tk.Label(summary, text='Urlop razem: 0 dni', bg=CARD,
                                              fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_vacation_label.pack(side='left', padx=(0, 36))
        self.total_sick_label = tk.Label(summary, text='Chorobowe razem: 0 dni', bg=CARD,
                                          fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_sick_label.pack(side='left')

    # ============================================================
    # TAB: FAKTURY
    # ============================================================

    def _build_invoices_tab(self):
        inner = tk.Frame(self.tab_invoices, bg=BG, padx=24, pady=20)
        inner.pack(fill='both', expand=True)

        card = tk.Frame(inner, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=20, pady=16)
        card.pack(fill='x')

        top_bar = tk.Frame(card, bg=CARD)
        top_bar.pack(fill='x', pady=(0, 8))

        self.btn_add_invoice = tk.Button(top_bar, text='+ Dodaj fakturę', bg='#e0e7ff', fg=PRIMARY,
                                          font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                          cursor='hand2', command=self._add_invoice_row)
        self.btn_add_invoice.pack(side='left')

        tk.Label(top_bar, text='Termin płatności: 45 dni od daty faktury', bg=CARD,
                 fg='#9ca3af', font=('Segoe UI', 8)).pack(side='right')

        ih = tk.Frame(card, bg='#f1f5f9')
        ih.pack(fill='x')
        inv_cols = [('Data', 14), ('Nr faktury', 20), ('Kwota (PLN)', 14),
                    ('Termin', 12), ('Status', 14), ('Zapłacona', 9), ('', 4)]
        for i, (text, w) in enumerate(inv_cols):
            tk.Label(ih, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.invoice_container = tk.Frame(card, bg=CARD)
        self.invoice_container.pack(fill='x')

        self.total_invoices_label = tk.Label(card, text='Suma faktur: 0,00 PLN', bg=CARD,
                                              fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self.total_invoices_label.pack(fill='x', pady=(8, 0))

    # ============================================================
    # TAB: PODSUMOWANIE
    # ============================================================

    def _build_summary_tab(self):
        inner = tk.Frame(self.tab_summary, bg=BG, padx=24, pady=20)
        inner.pack(fill='both', expand=True)

        card = tk.Frame(inner, bg='#e0f2fe', bd=2, relief='solid', highlightbackground=PRIMARY,
                         padx=32, pady=24)
        card.pack(fill='x')

        tk.Label(card, text='Podsumowanie miesiąca', bg='#e0f2fe', fg=PRIMARY_DARK,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w', pady=(0, 20))

        r1 = tk.Frame(card, bg='#e0f2fe')
        r1.pack(fill='x', pady=8)
        tk.Label(r1, text='Przychody (faktury):', bg='#e0f2fe', fg=LABEL_FG,
                 font=('Segoe UI', 12)).pack(side='left')
        self.summary_invoices_label = tk.Label(r1, text='0,00 PLN', bg='#e0f2fe', fg=GREEN,
                                                font=('Segoe UI', 12, 'bold'))
        self.summary_invoices_label.pack(side='right')

        r2 = tk.Frame(card, bg='#e0f2fe')
        r2.pack(fill='x', pady=8)
        tk.Label(r2, text='Koszty stałe:', bg='#e0f2fe', fg=LABEL_FG,
                 font=('Segoe UI', 12)).pack(side='left')
        self.summary_costs_label = tk.Label(r2, text='0,00 PLN', bg='#e0f2fe', fg=RED,
                                             font=('Segoe UI', 12, 'bold'))
        self.summary_costs_label.pack(side='right')

        tk.Frame(card, bg=PRIMARY, height=2).pack(fill='x', pady=10)

        r3 = tk.Frame(card, bg='#e0f2fe')
        r3.pack(fill='x', pady=8)
        tk.Label(r3, text='WYNIK:', bg='#e0f2fe', fg=PRIMARY_DARK,
                 font=('Segoe UI', 16, 'bold')).pack(side='left')
        self.summary_result_label = tk.Label(r3, text='0,00 PLN', bg='#e0f2fe', fg=PRIMARY_DARK,
                                              font=('Segoe UI', 16, 'bold'))
        self.summary_result_label.pack(side='right')

    # ============================================================
    # ROW BUILDERS - using grid for proper column alignment
    # ============================================================

    def _add_fuel_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.fuel_container, bg=CARD)
        row.pack(fill='x', pady=2)

        date_e = self._make_date_entry(row, d.get('date', ''), width=14)
        date_e.grid(row=0, column=0, padx=3, sticky='w')

        liters_e = tk.Entry(row, width=12, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        liters_e.insert(0, str(d.get('liters', '')) if d.get('liters') else '')
        liters_e.grid(row=0, column=1, padx=3, sticky='w')

        odo_e = tk.Entry(row, width=14, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        odo_e.insert(0, str(d.get('odometer', '')) if d.get('odometer') else '')
        odo_e.grid(row=0, column=2, padx=3, sticky='w')

        netto_var = tk.StringVar(value=str(d.get('netto', '')) if d.get('netto') else '')
        netto_e = tk.Entry(row, textvariable=netto_var, width=14, font=('Segoe UI', 9),
                            justify='right', bd=1, relief='solid')
        netto_e.grid(row=0, column=3, padx=3, sticky='w')
        netto_var.trace_add('write', lambda *a: self._recalc())

        brutto_e = tk.Entry(row, width=14, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        brutto_e.insert(0, str(d.get('brutto', '')) if d.get('brutto') else '')
        brutto_e.grid(row=0, column=4, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.fuel_rows))
        del_btn.grid(row=0, column=5, padx=3, sticky='w')

        self.fuel_rows.append({
            'frame': row, 'date': date_e, 'liters': liters_e, 'odometer': odo_e,
            'netto': netto_e, 'netto_var': netto_var, 'brutto': brutto_e, 'del_btn': del_btn,
        })
        self._recalc()

    def _add_repair_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.repair_container, bg=CARD)
        row.pack(fill='x', pady=2)

        plate_e = tk.Entry(row, width=16, font=('Segoe UI', 9), bd=1, relief='solid')
        plate_e.insert(0, d.get('plate', ''))
        plate_e.grid(row=0, column=0, padx=3, sticky='w')

        date_e = self._make_date_entry(row, d.get('date', ''), width=14)
        date_e.grid(row=0, column=1, padx=3, sticky='w')

        desc_e = tk.Entry(row, width=24, font=('Segoe UI', 9), bd=1, relief='solid')
        desc_e.insert(0, d.get('description', ''))
        desc_e.grid(row=0, column=2, padx=3, sticky='w')

        amount_var = tk.StringVar(value=str(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=14, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=3, padx=3, sticky='w')
        amount_var.trace_add('write', lambda *a: self._recalc())

        odo_e = tk.Entry(row, width=12, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        odo_e.insert(0, str(d.get('odometer', '')) if d.get('odometer') else '')
        odo_e.grid(row=0, column=4, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.repair_rows))
        del_btn.grid(row=0, column=5, padx=3, sticky='w')

        self.repair_rows.append({
            'frame': row, 'plate': plate_e, 'date': date_e, 'description': desc_e,
            'amount': amount_e, 'amount_var': amount_var, 'odometer': odo_e, 'del_btn': del_btn,
        })
        self._recalc()

    def _add_leave_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.leave_container, bg=CARD)
        row.pack(fill='x', pady=2)

        type_var = tk.StringVar(value=d.get('type', 'urlop'))
        type_combo = ttk.Combobox(row, textvariable=type_var, values=['urlop', 'chorobowe'],
                                   state='readonly', width=10, font=('Segoe UI', 9))
        type_combo.grid(row=0, column=0, padx=3, sticky='w')

        name_e = tk.Entry(row, width=20, font=('Segoe UI', 9), bd=1, relief='solid')
        name_e.insert(0, d.get('name', ''))
        name_e.grid(row=0, column=1, padx=3, sticky='w')

        from_e = self._make_date_entry(row, d.get('date_from', ''), width=12)
        from_e.grid(row=0, column=2, padx=3, sticky='w')
        from_e.bind('<<DateEntrySelected>>', lambda e: self._recalc_leaves())

        to_e = self._make_date_entry(row, d.get('date_to', ''), width=12)
        to_e.grid(row=0, column=3, padx=3, sticky='w')
        to_e.bind('<<DateEntrySelected>>', lambda e: self._recalc_leaves())

        days_label = tk.Label(row, text='0', bg=CARD, fg=LABEL_FG,
                               font=('Segoe UI', 10, 'bold'), width=10, anchor='center')
        days_label.grid(row=0, column=4, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.leave_rows, self._recalc_leaves))
        del_btn.grid(row=0, column=5, padx=3, sticky='w')

        self.leave_rows.append({
            'frame': row, 'type': type_var, 'type_combo': type_combo,
            'name': name_e,
            'date_from': from_e, 'date_to': to_e, 'days_label': days_label, 'del_btn': del_btn,
        })
        self._recalc_leaves()

    def _add_invoice_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.invoice_container, bg=CARD)
        row.pack(fill='x', pady=2)

        date_e = self._make_date_entry(row, d.get('date', ''), width=12)
        date_e.grid(row=0, column=0, padx=3, sticky='w')
        date_e.bind('<<DateEntrySelected>>', lambda e: self._update_invoice_statuses())

        number_e = tk.Entry(row, width=20, font=('Segoe UI', 9), bd=1, relief='solid')
        number_e.insert(0, d.get('number', ''))
        number_e.grid(row=0, column=1, padx=3, sticky='w')

        amount_var = tk.StringVar(value=str(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=14, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=2, padx=3, sticky='w')
        amount_var.trace_add('write', lambda *a: self._recalc())

        # Deadline label
        deadline_label = tk.Label(row, text='-', bg=CARD, fg=LABEL_FG,
                                   font=('Segoe UI', 8), width=12, anchor='w')
        deadline_label.grid(row=0, column=3, padx=3, sticky='w')

        # Status label (colored)
        status_label = tk.Label(row, text='', bg=CARD, fg=LABEL_FG,
                                 font=('Segoe UI', 8, 'bold'), width=14, anchor='w')
        status_label.grid(row=0, column=4, padx=3, sticky='w')

        # Paid checkbox
        paid_var = tk.IntVar(value=1 if d.get('paid') else 0)
        paid_cb = tk.Checkbutton(row, variable=paid_var, bg=CARD, activebackground=CARD,
                                  command=self._update_invoice_statuses)
        paid_cb.grid(row=0, column=5, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.invoice_rows))
        del_btn.grid(row=0, column=6, padx=3, sticky='w')

        self.invoice_rows.append({
            'frame': row, 'date': date_e, 'number': number_e,
            'amount': amount_e, 'amount_var': amount_var,
            'deadline_label': deadline_label, 'status_label': status_label,
            'paid_var': paid_var, 'paid_cb': paid_cb, 'del_btn': del_btn,
        })
        self._recalc()
        self._update_invoice_statuses()

    def _delete_row(self, frame, row_list, callback=None):
        for i, r in enumerate(row_list):
            if r['frame'] == frame:
                row_list.pop(i)
                break
        frame.destroy()
        self._recalc()
        if callback:
            callback()

    # ============================================================
    # CALCULATIONS
    # ============================================================

    def _recalc(self):
        total_standard = 0
        for key, (var, entry) in self.cost_entries.items():
            try:
                total_standard += float(var.get())
            except (ValueError, tk.TclError):
                pass

        total_fuel = 0
        for r in self.fuel_rows:
            try:
                total_fuel += float(r['netto'].get())
            except (ValueError, tk.TclError):
                pass

        total_repairs = 0
        for r in self.repair_rows:
            try:
                total_repairs += float(r['amount'].get())
            except (ValueError, tk.TclError):
                pass

        total_invoices = 0
        for r in self.invoice_rows:
            try:
                total_invoices += float(r['amount'].get())
            except (ValueError, tk.TclError):
                pass

        total_costs = total_standard + total_fuel + total_repairs
        result = total_invoices - total_costs

        self.fuel_netto_label.config(text=f'Suma netto paliwa: {self._fmt(total_fuel)}')
        self.repair_sum_label.config(text=f'Suma napraw: {self._fmt(total_repairs)}')
        self.total_standard_label.config(text=f'Koszty standardowe: {self._fmt(total_standard)}')
        self.total_fuel_label.config(text=f'Paliwo (netto): {self._fmt(total_fuel)}')
        self.total_repairs_label.config(text=f'Naprawy: {self._fmt(total_repairs)}')
        self.total_costs_label.config(text=f'RAZEM: {self._fmt(total_costs)}')
        self.total_invoices_label.config(text=f'Suma faktur: {self._fmt(total_invoices)}')
        self.summary_invoices_label.config(text=self._fmt(total_invoices))
        self.summary_costs_label.config(text=self._fmt(total_costs))
        self.summary_result_label.config(text=self._fmt(result))
        self.summary_result_label.config(fg=GREEN if result >= 0 else RED)

    def _recalc_leaves(self):
        total_vac = 0
        total_sick = 0
        for r in self.leave_rows:
            try:
                d1 = r['date_from'].get_date()
                d2 = r['date_to'].get_date()
                days = max(0, (d2 - d1).days + 1)
            except Exception:
                days = 0
            r['days_label'].config(text=str(days))
            if days > 0:
                if r['type'].get() == 'urlop':
                    total_vac += days
                else:
                    total_sick += days
        self.total_vacation_label.config(text=f'Urlop razem: {total_vac} dni')
        self.total_sick_label.config(text=f'Chorobowe razem: {total_sick} dni')

    def _update_invoice_statuses(self):
        from datetime import timedelta, date
        today = date.today()
        PAYMENT_DAYS = 45

        for r in self.invoice_rows:
            try:
                inv_date = r['date'].get_date()
                deadline = inv_date + timedelta(days=PAYMENT_DAYS)
                deadline_str = deadline.strftime('%Y-%m-%d')
                r['deadline_label'].config(text=deadline_str)

                if r['paid_var'].get():
                    r['status_label'].config(text='Zapłacona', fg=GREEN, bg='#f0fdf4')
                    r['deadline_label'].config(fg='#9ca3af')
                else:
                    days_left = (deadline - today).days
                    if days_left < 0:
                        r['status_label'].config(
                            text=f'Po terminie ({-days_left}d)', fg='white', bg=RED)
                        r['deadline_label'].config(fg=RED)
                    elif days_left <= 7:
                        r['status_label'].config(
                            text=f'Pilne! ({days_left}d)', fg='white', bg='#d97706')
                        r['deadline_label'].config(fg='#d97706')
                    elif days_left <= 14:
                        r['status_label'].config(
                            text=f'Zbliża się ({days_left}d)', fg='#92400e', bg='#fef3c7')
                        r['deadline_label'].config(fg='#92400e')
                    else:
                        r['status_label'].config(
                            text=f'OK ({days_left}d)', fg=GREEN, bg=CARD)
                        r['deadline_label'].config(fg=LABEL_FG)
            except Exception:
                r['deadline_label'].config(text='-', fg=LABEL_FG)
                r['status_label'].config(text='', bg=CARD)

    def _fmt(self, val):
        formatted = f"{val:,.2f}".replace(',', ' ').replace('.', ',')
        return f"{formatted} PLN"

    # ============================================================
    # LOAD / SAVE
    # ============================================================

    def _on_month_change(self, event=None):
        self._save_month()
        idx = self.month_combo.current()
        self.current_month = self._month_keys[idx]
        self._load_month()

    def _load_month(self):
        month_id = self.current_month
        db.ensure_month(month_id)
        self._clear_dynamic_rows()

        # Get defaults: DB defaults first, then hardcoded fallback
        saved_defaults = db.get_cost_defaults()
        saved_costs = db.get_standard_costs(month_id)
        for key, (var, entry) in self.cost_entries.items():
            hardcoded = next((d for k, l, d in STANDARD_COST_PARAMS if k == key), 0)
            default = saved_defaults.get(key, hardcoded)
            val = saved_costs.get(key, default)
            var.set(str(val) if val else '0')

        for f in db.get_fuel(month_id):
            self._add_fuel_row(f)
        for r in db.get_repairs(month_id):
            self._add_repair_row(r)
        for l in db.get_leaves(month_id):
            self._add_leave_row(l)
        for inv in db.get_invoices(month_id):
            self._add_invoice_row(inv)

        self.is_locked = db.is_month_accepted(month_id)
        self._update_lock_state()
        self._recalc()
        self._recalc_leaves()

    def _save_month(self):
        month_id = self.current_month

        for key, (var, entry) in self.cost_entries.items():
            try:
                val = float(var.get())
            except (ValueError, tk.TclError):
                val = 0
            db.save_standard_cost(month_id, key, val)

        fuel_data = []
        for r in self.fuel_rows:
            fuel_data.append({
                'date': r['date'].get(),
                'liters': self._safe_float(r['liters'].get()),
                'odometer': self._safe_int(r['odometer'].get()),
                'netto': self._safe_float(r['netto'].get()),
                'brutto': self._safe_float(r['brutto'].get()),
            })
        db.save_fuel(month_id, fuel_data)

        repair_data = []
        for r in self.repair_rows:
            repair_data.append({
                'plate': r['plate'].get(),
                'date': r['date'].get(),
                'description': r['description'].get(),
                'amount': self._safe_float(r['amount'].get()),
                'odometer': self._safe_int(r['odometer'].get()),
            })
        db.save_repairs(month_id, repair_data)

        leave_data = []
        for r in self.leave_rows:
            leave_data.append({
                'type': r['type'].get(),
                'name': r['name'].get(),
                'date_from': r['date_from'].get(),
                'date_to': r['date_to'].get(),
            })
        db.save_leaves(month_id, leave_data)

        invoice_data = []
        for r in self.invoice_rows:
            invoice_data.append({
                'date': r['date'].get(),
                'number': r['number'].get(),
                'amount': self._safe_float(r['amount'].get()),
                'paid': r['paid_var'].get(),
            })
        db.save_invoices(month_id, invoice_data)

    def _clear_dynamic_rows(self):
        for lst in [self.fuel_rows, self.repair_rows, self.leave_rows, self.invoice_rows]:
            for r in lst:
                r['frame'].destroy()
            lst.clear()

    # ============================================================
    # ACCEPT / EDIT
    # ============================================================

    def _accept_month(self):
        if not messagebox.askyesno('Akceptacja miesiąca',
                                    'Czy na pewno chcesz zaakceptować ten miesiąc?\nDane zostaną zablokowane do edycji.'):
            return
        self._save_month()
        db.set_month_accepted(self.current_month, True)
        self.is_locked = True
        self._update_lock_state()

    def _enable_edit(self):
        db.set_month_accepted(self.current_month, False)
        self.is_locked = False
        self._update_lock_state()

    def _update_lock_state(self):
        if self.is_locked:
            self.locked_bar.pack(fill='x', after=self.root.winfo_children()[0])
            self.btn_accept.pack_forget()
            self.btn_edit.pack(side='left', padx=3, before=self.btn_stats)
            self._set_inputs_state('disabled')
        else:
            self.locked_bar.pack_forget()
            self.btn_edit.pack_forget()
            self.btn_accept.pack(side='left', padx=3, before=self.btn_stats)
            self._set_inputs_state('normal')

    def _set_inputs_state(self, state):
        for key, (var, entry) in self.cost_entries.items():
            entry.config(state=state)

        for r in self.fuel_rows:
            for k in ['liters', 'odometer', 'netto', 'brutto']:
                r[k].config(state=state)
            r['date'].config(state=state)
            r['del_btn'].config(state=state)

        for r in self.repair_rows:
            for k in ['plate', 'description', 'amount', 'odometer']:
                r[k].config(state=state)
            r['date'].config(state=state)
            r['del_btn'].config(state=state)

        for r in self.leave_rows:
            r['name'].config(state=state)
            r['date_from'].config(state=state)
            r['date_to'].config(state=state)
            r['type_combo'].config(state='disabled' if state == 'disabled' else 'readonly')
            r['del_btn'].config(state=state)

        for r in self.invoice_rows:
            for k in ['number', 'amount']:
                r[k].config(state=state)
            r['date'].config(state=state)
            r['paid_cb'].config(state=state)
            r['del_btn'].config(state=state)

        btn_state = 'disabled' if state == 'disabled' else 'normal'
        for btn in [self.btn_add_fuel, self.btn_add_repair, self.btn_add_leave,
                    self.btn_add_invoice, self.btn_set_defaults]:
            btn.config(state=btn_state)

    # ============================================================
    # STATISTICS
    # ============================================================

    def _show_stats(self):
        self._save_month()

        win = tk.Toplevel(self.root)
        win.title('MKtrans Finance - Statystyki roczne')
        win.geometry('1300x750')
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        self._stats_win = win

        # --- Header with year selector ---
        header = tk.Frame(win, bg=PRIMARY_DARK, height=56)
        header.pack(fill='x')
        header.pack_propagate(False)

        hinner = tk.Frame(header, bg=PRIMARY_DARK)
        hinner.pack(fill='x', padx=20, pady=10)

        tk.Label(hinner, text='Statystyki roczne', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 14, 'bold')).pack(side='left')

        right_h = tk.Frame(hinner, bg=PRIMARY_DARK)
        right_h.pack(side='right')

        tk.Label(right_h, text='Rok:', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 10)).pack(side='left', padx=(0, 6))

        now = datetime.now()
        years = list(range(now.year - 3, now.year + 2))
        all_db_years = db.get_all_years()
        for y in all_db_years:
            if y not in years:
                years.append(y)
        years.sort()

        self._stats_year_var = tk.StringVar(value=str(now.year))
        year_combo = ttk.Combobox(right_h, textvariable=self._stats_year_var,
                                   values=[str(y) for y in years],
                                   state='readonly', width=8, font=('Segoe UI', 10))
        year_combo.pack(side='left', padx=(0, 10))
        year_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_stats())

        # --- Content area with notebook ---
        self._stats_notebook = ttk.Notebook(win)
        self._stats_notebook.pack(fill='both', expand=True, padx=16, pady=(8, 16))

        # Tab 1: Tabela miesięczna
        self._stats_tab_table = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_table, text='  Podsumowanie miesięcy  ')

        # Tab 2: Koszty roczne
        self._stats_tab_annual = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_annual, text='  Koszty roczne  ')

        # Tab 3: Podsumowanie roku
        self._stats_tab_yearly = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_yearly, text='  Podsumowanie roku  ')

        self._refresh_stats()

    def _refresh_stats(self):
        year = int(self._stats_year_var.get())
        self._build_stats_monthly_table(year)
        self._build_stats_annual_costs(year)
        self._build_stats_yearly_summary(year)

    # --- Stats Tab 1: Monthly table ---

    def _build_stats_monthly_table(self, year):
        for w in self._stats_tab_table.winfo_children():
            w.destroy()

        frame = tk.Frame(self._stats_tab_table, bg=BG)
        frame.pack(fill='both', expand=True, padx=16, pady=12)

        canvas = tk.Canvas(frame, bg=CARD, highlightthickness=0)
        h_scroll = ttk.Scrollbar(frame, orient='horizontal', command=canvas.xview)
        v_scroll = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)

        inner = tk.Frame(canvas, bg=CARD)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        v_scroll.pack(side='right', fill='y')
        h_scroll.pack(side='bottom', fill='x')
        canvas.pack(side='left', fill='both', expand=True)

        categories = [
            'Koszty standardowe', 'Paliwo (netto)', 'Naprawy',
            'KOSZTY MIESIĘCZNE', 'Faktury', 'Urlop (dni)', 'Chorobowe (dni)', 'WYNIK MIESIĄCA'
        ]

        # Header: Kategoria + 12 months + SUMA
        tk.Label(inner, text='Kategoria', bg='#e2e8f0', fg=PRIMARY_DARK,
                 font=('Segoe UI', 9, 'bold'), width=22, anchor='w', padx=8, pady=8,
                 relief='ridge').grid(row=0, column=0, sticky='nsew')

        for m in range(1, 13):
            tk.Label(inner, text=MONTHS_PL[m - 1][:3], bg='#e2e8f0', fg=PRIMARY_DARK,
                     font=('Segoe UI', 9, 'bold'), width=13, anchor='center', padx=4, pady=8,
                     relief='ridge').grid(row=0, column=m, sticky='nsew')

        tk.Label(inner, text='SUMA', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 9, 'bold'), width=14, anchor='center', padx=4, pady=8,
                 relief='ridge').grid(row=0, column=13, sticky='nsew')

        # Precompute summaries for all 12 months
        summaries = {}
        for m in range(1, 13):
            month_id = f"{year}-{m:02d}"
            summaries[m] = db.get_month_summary(month_id)

        for i, cat in enumerate(categories):
            is_total = cat in ('KOSZTY MIESIĘCZNE', 'WYNIK MIESIĄCA')
            bg_color = '#dbeafe' if is_total else ('#f8fafc' if i % 2 == 0 else CARD)
            font_weight = 'bold' if is_total else ''

            tk.Label(inner, text=cat, bg=bg_color, fg=PRIMARY_DARK if is_total else LABEL_FG,
                     font=('Segoe UI', 9, font_weight), width=22, anchor='w', padx=8, pady=5,
                     relief='ridge').grid(row=i + 1, column=0, sticky='nsew')

            row_sum = 0
            is_days = cat in ('Urlop (dni)', 'Chorobowe (dni)')

            for m in range(1, 13):
                s = summaries[m]
                val_map = {
                    'Koszty standardowe': s['standard'],
                    'Paliwo (netto)': s['fuel_netto'],
                    'Naprawy': s['repairs'],
                    'KOSZTY MIESIĘCZNE': s['total_costs'],
                    'Faktury': s['invoices'],
                    'Urlop (dni)': s['urlop_days'],
                    'Chorobowe (dni)': s['chorobowe_days'],
                    'WYNIK MIESIĄCA': s['result'],
                }
                val = val_map[cat]
                row_sum += val

                if is_days:
                    text = str(int(val)) if val else '-'
                    fg = LABEL_FG
                else:
                    text = self._fmt(val) if val else '-'
                    if cat == 'WYNIK MIESIĄCA':
                        fg = GREEN if val >= 0 else RED
                    elif cat == 'Faktury':
                        fg = GREEN if val > 0 else LABEL_FG
                    elif cat == 'KOSZTY MIESIĘCZNE':
                        fg = RED if val > 0 else LABEL_FG
                    else:
                        fg = LABEL_FG

                tk.Label(inner, text=text, bg=bg_color, fg=fg,
                         font=('Segoe UI', 9, font_weight), width=13, anchor='e', padx=6, pady=5,
                         relief='ridge').grid(row=i + 1, column=m, sticky='nsew')

            # SUMA column
            sum_bg = '#1e3a8a' if is_total else '#f1f5f9'
            sum_fg_color = 'white' if is_total else LABEL_FG
            if is_days:
                sum_text = str(int(row_sum))
            else:
                sum_text = self._fmt(row_sum)
                if cat == 'WYNIK MIESIĄCA':
                    sum_fg_color = '#86efac' if row_sum >= 0 else '#fca5a5'
                elif cat == 'Faktury' and not is_total:
                    sum_fg_color = GREEN
                elif cat == 'KOSZTY MIESIĘCZNE':
                    sum_fg_color = '#fca5a5'

            tk.Label(inner, text=sum_text, bg=sum_bg, fg=sum_fg_color,
                     font=('Segoe UI', 9, 'bold'), width=14, anchor='e', padx=6, pady=5,
                     relief='ridge').grid(row=i + 1, column=13, sticky='nsew')

    # --- Stats Tab 2: Annual costs (Ubezpieczenia + Podatek drogowy) ---

    def _build_stats_annual_costs(self, year):
        for w in self._stats_tab_annual.winfo_children():
            w.destroy()

        main = tk.Frame(self._stats_tab_annual, bg=BG, padx=24, pady=16)
        main.pack(fill='both', expand=True)

        # Info
        tk.Label(main, text=f'Koszty roczne - {year}', bg=BG, fg=PRIMARY_DARK,
                 font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 4))
        tk.Label(main, text='Koszty ponoszone raz w roku (ubezpieczenia, podatek drogowy). '
                 'Zostaną uwzględnione w podsumowaniu roku.',
                 bg=BG, fg=LABEL_FG, font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 12))

        # --- Ubezpieczenia ---
        lf1 = tk.LabelFrame(main, text='  Ubezpieczenia  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf1.pack(fill='x', pady=(0, 16))

        self._stats_ins_btn = tk.Button(lf1, text='+ Dodaj ubezpieczenie', bg='#e0e7ff', fg=PRIMARY,
                                         font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                         cursor='hand2', command=lambda: self._add_annual_row('ubezpieczenie'))
        self._stats_ins_btn.pack(anchor='w', pady=(0, 8))

        ih = tk.Frame(lf1, bg='#f1f5f9')
        ih.pack(fill='x')
        for i, (text, w) in enumerate([('Rodzaj ubezpieczenia', 30), ('Kwota (PLN)', 16), ('', 5)]):
            tk.Label(ih, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self._stats_ins_container = tk.Frame(lf1, bg=CARD)
        self._stats_ins_container.pack(fill='x')

        self._stats_ins_sum = tk.Label(lf1, text='Suma ubezpieczeń: 0,00 PLN', bg=CARD,
                                        fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self._stats_ins_sum.pack(fill='x', pady=(8, 0))

        # --- Podatek drogowy ---
        lf2 = tk.LabelFrame(main, text='  Podatek drogowy  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf2.pack(fill='x', pady=(0, 16))

        self._stats_tax_btn = tk.Button(lf2, text='+ Dodaj podatek', bg='#e0e7ff', fg=PRIMARY,
                                         font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                         cursor='hand2', command=lambda: self._add_annual_row('podatek_drogowy'))
        self._stats_tax_btn.pack(anchor='w', pady=(0, 8))

        th = tk.Frame(lf2, bg='#f1f5f9')
        th.pack(fill='x')
        for i, (text, w) in enumerate([('Opis', 30), ('Kwota (PLN)', 16), ('', 5)]):
            tk.Label(th, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), width=w, anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self._stats_tax_container = tk.Frame(lf2, bg=CARD)
        self._stats_tax_container.pack(fill='x')

        self._stats_tax_sum = tk.Label(lf2, text='Suma podatków: 0,00 PLN', bg=CARD,
                                        fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self._stats_tax_sum.pack(fill='x', pady=(8, 0))

        # Total
        total_frame = tk.Frame(main, bg='#fef3c7', bd=1, relief='solid', padx=20, pady=12)
        total_frame.pack(fill='x')
        self._stats_annual_total = tk.Label(total_frame, text='Koszty roczne razem: 0,00 PLN',
                                             bg='#fef3c7', fg='#92400e', font=('Segoe UI', 12, 'bold'))
        self._stats_annual_total.pack(anchor='e')

        # Save button
        tk.Button(main, text='Zapisz koszty roczne', bg=GREEN, fg='white',
                  font=('Segoe UI', 10, 'bold'), bd=0, padx=20, pady=6,
                  cursor='hand2', command=self._save_annual_costs).pack(anchor='e', pady=(12, 0))

        # Load existing data
        self._stats_annual_rows = []
        existing = db.get_annual_costs(year)
        for entry in existing:
            self._add_annual_row(entry['type'], entry)

        self._recalc_annual()

    def _add_annual_row(self, cost_type, data_dict=None):
        d = data_dict or {}
        container = self._stats_ins_container if cost_type == 'ubezpieczenie' else self._stats_tax_container

        row = tk.Frame(container, bg=CARD)
        row.pack(fill='x', pady=2)

        desc_e = tk.Entry(row, width=30, font=('Segoe UI', 9), bd=1, relief='solid')
        desc_e.insert(0, d.get('description', ''))
        desc_e.grid(row=0, column=0, padx=3, sticky='w')

        amount_var = tk.StringVar(value=str(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=16, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=1, padx=3, sticky='w')
        amount_var.trace_add('write', lambda *a: self._recalc_annual())

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda: self._delete_annual_row(row))
        del_btn.grid(row=0, column=2, padx=3, sticky='w')

        self._stats_annual_rows.append({
            'frame': row, 'type': cost_type,
            'description': desc_e, 'amount': amount_e, 'amount_var': amount_var, 'del_btn': del_btn,
        })
        self._recalc_annual()

    def _delete_annual_row(self, frame):
        for i, r in enumerate(self._stats_annual_rows):
            if r['frame'] == frame:
                self._stats_annual_rows.pop(i)
                break
        frame.destroy()
        self._recalc_annual()

    def _recalc_annual(self):
        total_ins = 0
        total_tax = 0
        for r in self._stats_annual_rows:
            try:
                val = float(r['amount'].get())
            except (ValueError, tk.TclError):
                val = 0
            if r['type'] == 'ubezpieczenie':
                total_ins += val
            else:
                total_tax += val
        total = total_ins + total_tax
        self._stats_ins_sum.config(text=f'Suma ubezpieczeń: {self._fmt(total_ins)}')
        self._stats_tax_sum.config(text=f'Suma podatków: {self._fmt(total_tax)}')
        self._stats_annual_total.config(text=f'Koszty roczne razem: {self._fmt(total)}')

    def _save_annual_costs(self):
        year = int(self._stats_year_var.get())
        entries = []
        for r in self._stats_annual_rows:
            entries.append({
                'type': r['type'],
                'description': r['description'].get(),
                'amount': self._safe_float(r['amount'].get()),
            })
        db.save_annual_costs(year, entries)
        messagebox.showinfo('Koszty roczne', f'Zapisano koszty roczne za {year}.')
        self._build_stats_yearly_summary(year)

    # --- Stats Tab 3: Yearly summary ---

    def _build_stats_yearly_summary(self, year):
        for w in self._stats_tab_yearly.winfo_children():
            w.destroy()

        main = tk.Frame(self._stats_tab_yearly, bg=BG, padx=24, pady=16)
        main.pack(fill='both', expand=True)

        tk.Label(main, text=f'Podsumowanie roku {year}', bg=BG, fg=PRIMARY_DARK,
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 16))

        # Calculate yearly totals from months
        yearly_invoices = 0
        yearly_standard = 0
        yearly_fuel = 0
        yearly_repairs = 0
        yearly_urlop = 0
        yearly_chorobowe = 0

        for m in range(1, 13):
            month_id = f"{year}-{m:02d}"
            s = db.get_month_summary(month_id)
            yearly_invoices += s['invoices']
            yearly_standard += s['standard']
            yearly_fuel += s['fuel_netto']
            yearly_repairs += s['repairs']
            yearly_urlop += s['urlop_days']
            yearly_chorobowe += s['chorobowe_days']

        yearly_monthly_costs = yearly_standard + yearly_fuel + yearly_repairs
        annual_total = db.get_annual_costs_total(year)
        yearly_total_costs = yearly_monthly_costs + annual_total
        yearly_result = yearly_invoices - yearly_total_costs

        # Summary card
        card = tk.Frame(main, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=24, pady=16)
        card.pack(fill='x', pady=(0, 16))

        rows_data = [
            ('PRZYCHODY', '', '', True),
            ('Faktury (suma roczna)', self._fmt(yearly_invoices), GREEN, False),
            ('', '', '', False),
            ('KOSZTY MIESIĘCZNE', '', '', True),
            ('Koszty standardowe (suma)', self._fmt(yearly_standard), LABEL_FG, False),
            ('Paliwo netto (suma)', self._fmt(yearly_fuel), LABEL_FG, False),
            ('Naprawy (suma)', self._fmt(yearly_repairs), LABEL_FG, False),
            ('Razem koszty miesięczne', self._fmt(yearly_monthly_costs), RED, False),
            ('', '', '', False),
            ('KOSZTY ROCZNE', '', '', True),
            ('Ubezpieczenia + Podatek drogowy', self._fmt(annual_total), LABEL_FG, False),
            ('', '', '', False),
            ('PODSUMOWANIE', '', '', True),
            ('Przychody', self._fmt(yearly_invoices), GREEN, False),
            ('Koszty miesięczne', self._fmt(yearly_monthly_costs), RED, False),
            ('Koszty roczne', self._fmt(annual_total), RED, False),
            ('Koszty łącznie', self._fmt(yearly_total_costs), RED, False),
        ]

        for label, value, color, is_header in rows_data:
            if not label and not value:
                tk.Frame(card, bg=BORDER, height=1).pack(fill='x', pady=4)
                continue
            r = tk.Frame(card, bg=CARD)
            r.pack(fill='x', pady=2)
            if is_header:
                tk.Label(r, text=label, bg=CARD, fg=PRIMARY_DARK,
                         font=('Segoe UI', 10, 'bold')).pack(side='left')
            else:
                tk.Label(r, text=label, bg=CARD, fg=LABEL_FG,
                         font=('Segoe UI', 10)).pack(side='left')
                tk.Label(r, text=value, bg=CARD, fg=color,
                         font=('Segoe UI', 10, 'bold')).pack(side='right')

        # Result line
        tk.Frame(card, bg=PRIMARY, height=3).pack(fill='x', pady=(8, 4))
        result_row = tk.Frame(card, bg=CARD)
        result_row.pack(fill='x', pady=4)
        tk.Label(result_row, text='WYNIK ROCZNY:', bg=CARD, fg=PRIMARY_DARK,
                 font=('Segoe UI', 14, 'bold')).pack(side='left')
        tk.Label(result_row, text=self._fmt(yearly_result), bg=CARD,
                 fg=GREEN if yearly_result >= 0 else RED,
                 font=('Segoe UI', 14, 'bold')).pack(side='right')

        # Leave summary
        leave_frame = tk.Frame(main, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=24, pady=12)
        leave_frame.pack(fill='x')
        tk.Label(leave_frame, text=f'Urlop w {year}: {yearly_urlop} dni    |    '
                 f'Chorobowe w {year}: {yearly_chorobowe} dni',
                 bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10)).pack(anchor='w')

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(val):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def on_close(self):
        self._save_month()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MKtransApp(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
