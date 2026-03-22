import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import calendar as cal_mod
from PIL import Image, ImageTk
import os

import database as db

import sys
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = sys._MEIPASS  # PyInstaller extracts bundled files here
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = APP_DIR

# ============================================================
# CUSTOM DATE PICKER (Polish, reliable navigation)
# ============================================================

PL_MONTHS = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
             'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień']
PL_DAYS = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd']


class DatePicker(tk.Frame):
    """Date entry with a popup calendar in Polish."""

    def __init__(self, master, width=12, initial='', on_select=None, **kw):
        super().__init__(master, bg=kw.get('bg', '#ffffff'))
        self._on_select = on_select
        self._date = date.today()
        self._popup = None

        self._var = tk.StringVar()
        self._entry = tk.Entry(self, textvariable=self._var, width=width,
                                font=('Segoe UI', 9), bd=1, relief='solid', justify='center')
        self._entry.pack(side='left')
        self._entry.bind('<FocusOut>', self._on_manual_edit)
        self._entry.bind('<Return>', self._on_manual_edit)

        self._btn = tk.Button(self, text='\u25bc', font=('Segoe UI', 7), bd=1, relief='solid',
                               bg='#e2e8f0', cursor='hand2', padx=4, pady=0,
                               command=self._toggle_popup)
        self._btn.pack(side='left', padx=(1, 0))

        if initial:
            try:
                self._date = datetime.strptime(initial, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        self._var.set(self._date.strftime('%Y-%m-%d'))

    def get(self):
        return self._var.get()

    def get_date(self):
        try:
            return datetime.strptime(self._var.get(), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return self._date

    def set_date(self, d):
        self._date = d
        self._var.set(d.strftime('%Y-%m-%d'))

    def config(self, **kw):
        state = kw.get('state')
        if state is not None:
            self._entry.config(state=state)
            self._btn.config(state=state)
        else:
            super().config(**kw)

    configure = config

    def _on_manual_edit(self, event=None):
        try:
            self._date = datetime.strptime(self._var.get(), '%Y-%m-%d').date()
            if self._on_select:
                self._on_select()
        except (ValueError, TypeError):
            pass

    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return
        self._show_popup()

    def _show_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()

        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes('-topmost', True)

        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        self._popup.geometry(f'+{x}+{y}')

        try:
            self._date = datetime.strptime(self._var.get(), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            self._date = date.today()

        self._cal_year = self._date.year
        self._cal_month = self._date.month

        # Main frame that holds everything
        self._cal_frame = tk.Frame(self._popup, bg='#1e3a8a', bd=2, relief='solid')
        self._cal_frame.pack()

        # Content frame (rebuilt on navigation)
        self._cal_content = tk.Frame(self._cal_frame, bg='white')
        self._cal_content.pack()

        self._render_month()

        # Close popup when clicking anywhere else in the app
        self._popup.bind('<Escape>', lambda e: self._close_popup())
        self.winfo_toplevel().bind('<Button-1>', self._on_root_click, add='+')

    def _on_root_click(self, event):
        """Close popup if click is outside the popup and the picker button."""
        if not self._popup or not self._popup.winfo_exists():
            self._unbind_root_click()
            return
        # Check if click is inside popup
        try:
            w = event.widget
            if str(w).startswith(str(self._popup)):
                return
            # Check if click is on the dropdown button itself
            if w == self._btn:
                return
        except (tk.TclError, ValueError):
            pass
        self._close_popup()

    def _unbind_root_click(self):
        try:
            self.winfo_toplevel().unbind('<Button-1>')
        except tk.TclError:
            pass

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._unbind_root_click()

    def _render_month(self):
        """Rebuild just the calendar content for current month/year."""
        for w in self._cal_content.winfo_children():
            w.destroy()

        # Navigation: <<  <  [Month Year]  >  >>
        nav = tk.Frame(self._cal_content, bg='#1e3a8a')
        nav.grid(row=0, column=0, sticky='ew')

        nav.columnconfigure(0, weight=0)  # <<
        nav.columnconfigure(1, weight=0)  # <
        nav.columnconfigure(2, weight=1)  # title (expands)
        nav.columnconfigure(3, weight=0)  # >
        nav.columnconfigure(4, weight=0)  # >>

        btn_cfg = dict(font=('Segoe UI', 9, 'bold'), bg='#1e3a8a', fg='white',
                       bd=0, cursor='hand2', padx=6, pady=4,
                       activebackground='#3b82f6', activeforeground='white')

        tk.Button(nav, text='<<', command=self._prev_year, **btn_cfg).grid(row=0, column=0, padx=1)
        tk.Button(nav, text='<', command=self._prev_month, **btn_cfg).grid(row=0, column=1, padx=1)

        title = f'{PL_MONTHS[self._cal_month - 1]} {self._cal_year}'
        tk.Label(nav, text=title, bg='#1e3a8a', fg='white',
                 font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, padx=8)

        tk.Button(nav, text='>', command=self._next_month, **btn_cfg).grid(row=0, column=3, padx=1)
        tk.Button(nav, text='>>', command=self._next_year, **btn_cfg).grid(row=0, column=4, padx=1)

        # Day name headers
        days_row = tk.Frame(self._cal_content, bg='#e2e8f0')
        days_row.grid(row=1, column=0, sticky='ew')
        for i, name in enumerate(PL_DAYS):
            fg_color = '#dc2626' if i >= 5 else '#475569'
            tk.Label(days_row, text=name, bg='#e2e8f0', fg=fg_color,
                     font=('Segoe UI', 8, 'bold'), width=4).grid(row=0, column=i, pady=2)

        # Days grid
        grid_frame = tk.Frame(self._cal_content, bg='white')
        grid_frame.grid(row=2, column=0, sticky='ew', padx=1)

        # calendar.monthrange: returns (weekday_of_first_day, number_of_days)
        # weekday: 0=Monday ... 6=Sunday (Python standard)
        first_weekday, num_days = cal_mod.monthrange(self._cal_year, self._cal_month)
        today_date = date.today()
        selected_date = self._date

        # Fill empty cells before first day
        grid_row = 0
        for col in range(first_weekday):
            tk.Label(grid_frame, text='', bg='white', width=3).grid(row=0, column=col, padx=1, pady=1)

        col = first_weekday
        for day in range(1, num_days + 1):
            current_date = date(self._cal_year, self._cal_month, day)
            is_today = (current_date == today_date)
            is_selected = (current_date == selected_date)
            is_weekend = (col >= 5)

            if is_selected:
                cell_bg, cell_fg = '#1a56db', 'white'
            elif is_today:
                cell_bg, cell_fg = '#dbeafe', '#1e3a8a'
            elif is_weekend:
                cell_bg, cell_fg = '#f8fafc', '#475569'
            else:
                cell_bg, cell_fg = 'white', '#1a1a2e'

            font_weight = 'bold' if (is_selected or is_today) else ''

            btn = tk.Button(grid_frame, text=str(day), width=3,
                             bg=cell_bg, fg=cell_fg,
                             font=('Segoe UI', 9, font_weight),
                             bd=0, cursor='hand2', activebackground='#93c5fd',
                             command=lambda dd=day: self._select_day(dd))
            btn.grid(row=grid_row, column=col, padx=1, pady=1)

            col += 1
            if col > 6:
                col = 0
                grid_row += 1

        # "Dzisiaj" button
        today_btn_frame = tk.Frame(self._cal_content, bg='#f1f5f9')
        today_btn_frame.grid(row=3, column=0, sticky='ew')
        tk.Button(today_btn_frame, text=f'Dzisiaj: {today_date.strftime("%Y-%m-%d")}',
                  font=('Segoe UI', 8, 'bold'), bg='#f1f5f9', fg='#1a56db',
                  bd=0, cursor='hand2', pady=4,
                  command=self._select_today).pack(fill='x')

    def _prev_month(self):
        if self._cal_month == 1:
            self._cal_month = 12
            self._cal_year -= 1
        else:
            self._cal_month -= 1
        self._render_month()

    def _next_month(self):
        if self._cal_month == 12:
            self._cal_month = 1
            self._cal_year += 1
        else:
            self._cal_month += 1
        self._render_month()

    def _prev_year(self):
        self._cal_year -= 1
        self._render_month()

    def _next_year(self):
        self._cal_year += 1
        self._render_month()

    def _select_day(self, day):
        self._date = date(self._cal_year, self._cal_month, day)
        self._var.set(self._date.strftime('%Y-%m-%d'))
        self._close_popup()
        if self._on_select:
            self._on_select()

    def _select_today(self):
        today_date = date.today()
        self._cal_year = today_date.year
        self._cal_month = today_date.month
        self._select_day(today_date.day)

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

# Column pixel widths for consistent alignment (header <-> rows)
FUEL_COLS = [('Nr rej.', 130), ('Data', 130), ('Litry', 100), ('Licznik (km)', 120),
             ('Kwota netto', 120), ('Kwota brutto', 120), ('', 40)]
REPAIR_COLS = [('Nr rejestracyjny', 140), ('Data', 130), ('Co zrobione', 200),
               ('Kwota (PLN)', 120), ('Licznik', 100), ('', 40)]
LEAVE_COLS = [('Typ', 110), ('Imię i nazwisko', 170), ('Data od', 130),
              ('Data do', 130), ('Liczba dni', 90), ('', 40)]
INVOICE_COLS = [('Data', 130), ('Nr faktury', 170), ('Kwota (PLN)', 120),
                ('Termin', 110), ('Status', 140), ('Zapłacona', 80), ('', 40)]


class MKtransApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MKtrans Finance")
        self.root.geometry("1440x960")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 750)

        # Set window icon
        ico_path = os.path.join(ASSETS_DIR, 'icon.ico')
        if os.path.exists(ico_path):
            self.root.iconbitmap(ico_path)

        # Load header logo
        logo_path = os.path.join(ASSETS_DIR, 'logo_small.png')
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
        self.other_cost_rows = []

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

    def _make_date_entry(self, parent, initial='', width=12, on_select=None):
        return DatePicker(parent, width=width, initial=initial, on_select=on_select)

    @staticmethod
    def _configure_table_cols(frame, col_widths):
        """Apply fixed column widths (in pixels) to a frame using grid columnconfigure."""
        for i, w in enumerate(col_widths):
            frame.columnconfigure(i, minsize=w)

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

        # Load saved defaults from DB (for current month)
        saved_defaults = db.get_cost_defaults(self.current_month)

        self.cost_entries = {}
        for key, label, hardcoded_default in STANDARD_COST_PARAMS:
            default = saved_defaults.get(key, hardcoded_default)
            row = tk.Frame(lf1, bg=CARD)
            row.pack(fill='x', pady=3)
            tk.Label(row, text=label, bg=CARD, fg=LABEL_FG,
                     font=('Segoe UI', 10), width=30, anchor='w').pack(side='left')
            var = tk.StringVar(value=self._fmt_input(default) if default else '')
            entry = tk.Entry(row, textvariable=var, width=15, font=('Segoe UI', 10),
                             justify='right', bd=1, relief='solid')
            entry.pack(side='left', padx=(8, 0))
            tk.Label(row, text='PLN', bg=CARD, fg='#9ca3af', font=('Segoe UI', 9)).pack(side='left', padx=4)
            self._format_money_input(var, entry, callback=self._recalc)
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

        # Top bar: add fuel + plate management
        fuel_top = tk.Frame(lf2, bg=CARD)
        fuel_top.pack(fill='x', pady=(0, 8))

        self.btn_add_fuel = tk.Button(fuel_top, text='+ Dodaj wpis', bg='#e0e7ff', fg=PRIMARY,
                                       font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                       cursor='hand2', command=self._add_fuel_row)
        self.btn_add_fuel.pack(side='left')

        # Plate management (right side)
        plate_mgmt = tk.Frame(fuel_top, bg=CARD)
        plate_mgmt.pack(side='right')

        tk.Label(plate_mgmt, text='Zarządzaj nr rej.:', bg=CARD, fg=LABEL_FG,
                 font=('Segoe UI', 8)).pack(side='left', padx=(0, 4))

        self._new_plate_var = tk.StringVar()
        self._new_plate_entry = tk.Entry(plate_mgmt, textvariable=self._new_plate_var, width=12,
                                          font=('Segoe UI', 9), bd=1, relief='solid')
        self._new_plate_entry.pack(side='left', padx=2)

        self.btn_add_plate = tk.Button(plate_mgmt, text='+ Dodaj', bg='#d1fae5', fg=GREEN,
                                        font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2,
                                        cursor='hand2', command=self._add_fuel_plate)
        self.btn_add_plate.pack(side='left', padx=2)

        self.btn_remove_plate = tk.Button(plate_mgmt, text='- Usuń', bg='#fee2e2', fg=RED,
                                           font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2,
                                           cursor='hand2', command=self._remove_fuel_plate)
        self.btn_remove_plate.pack(side='left', padx=2)

        fh = tk.Frame(lf2, bg='#f1f5f9')
        fh.pack(fill='x')
        col_widths = [w for _, w in FUEL_COLS]
        self._configure_table_cols(fh, col_widths)
        for i, (text, _) in enumerate(FUEL_COLS):
            tk.Label(fh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

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
        col_widths = [w for _, w in REPAIR_COLS]
        self._configure_table_cols(rh, col_widths)
        for i, (text, _) in enumerate(REPAIR_COLS):
            tk.Label(rh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.repair_container = tk.Frame(lf3, bg=CARD)
        self.repair_container.pack(fill='x')

        self.repair_sum_label = tk.Label(lf3, text='Suma napraw: 0,00 PLN', bg=CARD,
                                          fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self.repair_sum_label.pack(fill='x', pady=(8, 0))

        # --- Podsekcja: Koszty inne ---
        OTHER_COST_COLS = [('Koszt', 300), ('Kwota (PLN)', 150), ('', 40)]
        lf4 = tk.LabelFrame(main, text='  Koszty inne  ', bg=CARD,
                             font=('Segoe UI', 11, 'bold'), fg=PRIMARY_DARK, padx=20, pady=10)
        lf4.pack(fill='x', pady=(0, 16))

        self.btn_add_other_cost = tk.Button(lf4, text='+ Dodaj koszt', bg='#e0e7ff', fg=PRIMARY,
                                             font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                             cursor='hand2', command=self._add_other_cost_row)
        self.btn_add_other_cost.pack(anchor='w', pady=(0, 8))

        och = tk.Frame(lf4, bg='#f1f5f9')
        och.pack(fill='x')
        oc_widths = [w for _, w in OTHER_COST_COLS]
        self._configure_table_cols(och, oc_widths)
        for i, (text, _) in enumerate(OTHER_COST_COLS):
            tk.Label(och, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

        self.other_cost_container = tk.Frame(lf4, bg=CARD)
        self.other_cost_container.pack(fill='x')

        self.other_cost_sum_label = tk.Label(lf4, text='Suma kosztów innych: 0,00 PLN', bg=CARD,
                                              fg=LABEL_FG, font=('Segoe UI', 10), anchor='e')
        self.other_cost_sum_label.pack(fill='x', pady=(8, 0))

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
        self.total_repairs_label.pack(side='left', padx=(0, 28))
        self.total_other_label = tk.Label(breakdown, text='Inne: 0,00 PLN',
                                           bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10))
        self.total_other_label.pack(side='left')

        self.total_costs_label = tk.Label(totals, text='RAZEM: 0,00 PLN', bg=CARD,
                                           fg=RED, font=('Segoe UI', 13, 'bold'))
        self.total_costs_label.pack(anchor='w', pady=(4, 0))

    def _save_defaults(self):
        month_id = self.current_month
        for key, (var, entry) in self.cost_entries.items():
            val = self._safe_float(var.get())
            db.save_cost_default(key, val, effective_from=month_id)
        messagebox.showinfo('Kwoty domyślne',
                            f'Zapisano aktualne kwoty jako domyślne\n'
                            f'od miesiąca {month_id} w górę.')

    # ============================================================
    # TAB: URLOP
    # ============================================================

    def _build_leave_tab(self):
        inner = tk.Frame(self.tab_leave, bg=BG, padx=24, pady=20)
        inner.pack(fill='both', expand=True)

        card = tk.Frame(inner, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=20, pady=16)
        card.pack(fill='x')

        top_bar = tk.Frame(card, bg=CARD)
        top_bar.pack(fill='x', pady=(0, 8))

        self.btn_add_leave = tk.Button(top_bar, text='+ Dodaj wpis', bg='#e0e7ff', fg=PRIMARY,
                                        font=('Segoe UI', 9, 'bold'), bd=0, padx=12, pady=4,
                                        cursor='hand2', command=self._add_leave_row)
        self.btn_add_leave.pack(side='left')

        # Employee management
        emp_mgmt = tk.Frame(top_bar, bg=CARD)
        emp_mgmt.pack(side='right')

        tk.Label(emp_mgmt, text='Zarządzaj osobami:', bg=CARD, fg=LABEL_FG,
                 font=('Segoe UI', 8)).pack(side='left', padx=(0, 4))

        self._new_emp_var = tk.StringVar()
        self._new_emp_entry = tk.Entry(emp_mgmt, textvariable=self._new_emp_var, width=16,
                                        font=('Segoe UI', 9), bd=1, relief='solid')
        self._new_emp_entry.pack(side='left', padx=2)

        self.btn_add_emp = tk.Button(emp_mgmt, text='+ Dodaj', bg='#d1fae5', fg=GREEN,
                                      font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2,
                                      cursor='hand2', command=self._add_employee)
        self.btn_add_emp.pack(side='left', padx=2)

        self.btn_remove_emp = tk.Button(emp_mgmt, text='- Usuń', bg='#fee2e2', fg=RED,
                                         font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2,
                                         cursor='hand2', command=self._remove_employee)
        self.btn_remove_emp.pack(side='left', padx=2)

        lh = tk.Frame(card, bg='#f1f5f9')
        lh.pack(fill='x')
        col_widths = [w for _, w in LEAVE_COLS]
        self._configure_table_cols(lh, col_widths)
        for i, (text, _) in enumerate(LEAVE_COLS):
            tk.Label(lh, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

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
        col_widths = [w for _, w in INVOICE_COLS]
        self._configure_table_cols(ih, col_widths)
        for i, (text, _) in enumerate(INVOICE_COLS):
            tk.Label(ih, text=text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 8, 'bold'), anchor='w').grid(row=0, column=i, padx=3, pady=5, sticky='w')

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
        self._configure_table_cols(row, [w for _, w in FUEL_COLS])

        plates = db.get_fuel_plates()
        plate_var = tk.StringVar(value=d.get('plate', ''))
        plate_combo = ttk.Combobox(row, textvariable=plate_var, values=plates,
                                    width=14, font=('Segoe UI', 9))
        plate_combo.grid(row=0, column=0, padx=3, sticky='w')

        date_e = self._make_date_entry(row, d.get('date', ''), width=14)
        date_e.grid(row=0, column=1, padx=3, sticky='w')

        liters_e = tk.Entry(row, width=12, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        liters_e.insert(0, str(d.get('liters', '')) if d.get('liters') else '')
        liters_e.grid(row=0, column=2, padx=3, sticky='w')

        odo_e = tk.Entry(row, width=14, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        odo_e.insert(0, str(d.get('odometer', '')) if d.get('odometer') else '')
        odo_e.grid(row=0, column=3, padx=3, sticky='w')

        netto_var = tk.StringVar(value=self._fmt_input(d.get('netto', '')) if d.get('netto') else '')
        netto_e = tk.Entry(row, textvariable=netto_var, width=14, font=('Segoe UI', 9),
                            justify='right', bd=1, relief='solid')
        netto_e.grid(row=0, column=4, padx=3, sticky='w')
        self._format_money_input(netto_var, netto_e, callback=self._recalc)

        brutto_var = tk.StringVar(value=self._fmt_input(d.get('brutto', '')) if d.get('brutto') else '')
        brutto_e = tk.Entry(row, textvariable=brutto_var, width=14, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        brutto_e.grid(row=0, column=5, padx=3, sticky='w')
        self._format_money_input(brutto_var, brutto_e)

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.fuel_rows))
        del_btn.grid(row=0, column=6, padx=3, sticky='w')

        self.fuel_rows.append({
            'frame': row, 'plate': plate_combo, 'plate_var': plate_var,
            'date': date_e, 'liters': liters_e, 'odometer': odo_e,
            'netto': netto_e, 'netto_var': netto_var, 'brutto': brutto_e, 'del_btn': del_btn,
        })
        self._recalc()

    def _add_repair_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.repair_container, bg=CARD)
        row.pack(fill='x', pady=2)
        self._configure_table_cols(row, [w for _, w in REPAIR_COLS])

        plates = db.get_fuel_plates()
        plate_var = tk.StringVar(value=d.get('plate', ''))
        plate_e = ttk.Combobox(row, textvariable=plate_var, values=plates,
                                width=14, font=('Segoe UI', 9))
        plate_e.grid(row=0, column=0, padx=3, sticky='w')

        date_e = self._make_date_entry(row, d.get('date', ''), width=14)
        date_e.grid(row=0, column=1, padx=3, sticky='w')

        desc_e = tk.Text(row, width=24, height=1, font=('Segoe UI', 9), bd=1, relief='solid',
                         wrap='word')
        desc_e.insert('1.0', d.get('description', ''))
        desc_e.grid(row=0, column=2, padx=3, sticky='nsew')
        desc_e.bind('<KeyRelease>', lambda e, t=desc_e: self._auto_resize_text(t))
        self._auto_resize_text(desc_e)

        amount_var = tk.StringVar(value=self._fmt_input(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=14, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=3, padx=3, sticky='w')
        self._format_money_input(amount_var, amount_e, callback=self._recalc)

        odo_e = tk.Entry(row, width=12, font=('Segoe UI', 9), justify='right', bd=1, relief='solid')
        odo_e.insert(0, str(d.get('odometer', '')) if d.get('odometer') else '')
        odo_e.grid(row=0, column=4, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.repair_rows))
        del_btn.grid(row=0, column=5, padx=3, sticky='w')

        self.repair_rows.append({
            'frame': row, 'plate': plate_e, 'plate_var': plate_var, 'date': date_e, 'description': desc_e,
            'amount': amount_e, 'amount_var': amount_var, 'odometer': odo_e, 'del_btn': del_btn,
        })
        self._recalc()

    def _add_leave_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.leave_container, bg=CARD)
        row.pack(fill='x', pady=2)
        self._configure_table_cols(row, [w for _, w in LEAVE_COLS])

        type_var = tk.StringVar(value=d.get('type', 'urlop'))
        type_combo = ttk.Combobox(row, textvariable=type_var, values=['urlop', 'chorobowe'],
                                   state='readonly', width=10, font=('Segoe UI', 9))
        type_combo.grid(row=0, column=0, padx=3, sticky='w')

        employees = db.get_employees()
        name_var = tk.StringVar(value=d.get('name', ''))
        name_e = ttk.Combobox(row, textvariable=name_var, values=employees,
                               width=18, font=('Segoe UI', 9))
        name_e.grid(row=0, column=1, padx=3, sticky='w')

        from_e = self._make_date_entry(row, d.get('date_from', ''), width=12,
                                       on_select=self._recalc_leaves)
        from_e.grid(row=0, column=2, padx=3, sticky='w')

        to_e = self._make_date_entry(row, d.get('date_to', ''), width=12,
                                     on_select=self._recalc_leaves)
        to_e.grid(row=0, column=3, padx=3, sticky='w')

        days_label = tk.Label(row, text='0', bg=CARD, fg=LABEL_FG,
                               font=('Segoe UI', 10, 'bold'), width=10, anchor='center')
        days_label.grid(row=0, column=4, padx=3, sticky='w')

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.leave_rows, self._recalc_leaves))
        del_btn.grid(row=0, column=5, padx=3, sticky='w')

        self.leave_rows.append({
            'frame': row, 'type': type_var, 'type_combo': type_combo,
            'name': name_var, 'name_combo': name_e,
            'date_from': from_e, 'date_to': to_e, 'days_label': days_label, 'del_btn': del_btn,
        })
        self._recalc_leaves()

    def _add_invoice_row(self, data_dict=None):
        d = data_dict or {}
        row = tk.Frame(self.invoice_container, bg=CARD)
        row.pack(fill='x', pady=2)
        self._configure_table_cols(row, [w for _, w in INVOICE_COLS])

        date_e = self._make_date_entry(row, d.get('date', ''), width=12,
                                       on_select=self._update_invoice_statuses)
        date_e.grid(row=0, column=0, padx=3, sticky='w')

        number_e = tk.Entry(row, width=20, font=('Segoe UI', 9), bd=1, relief='solid')
        number_e.insert(0, d.get('number', ''))
        number_e.grid(row=0, column=1, padx=3, sticky='w')

        amount_var = tk.StringVar(value=self._fmt_input(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=14, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=2, padx=3, sticky='w')
        self._format_money_input(amount_var, amount_e, callback=self._recalc)

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

    def _add_other_cost_row(self, data_dict=None):
        d = data_dict or {}
        OTHER_COST_COLS = [('Koszt', 300), ('Kwota (PLN)', 150), ('', 40)]
        row = tk.Frame(self.other_cost_container, bg=CARD)
        row.pack(fill='x', pady=2)
        self._configure_table_cols(row, [w for _, w in OTHER_COST_COLS])

        desc_e = tk.Entry(row, width=40, font=('Segoe UI', 9), bd=1, relief='solid')
        desc_e.insert(0, d.get('description', ''))
        desc_e.grid(row=0, column=0, padx=3, sticky='w')

        amount_var = tk.StringVar(value=self._fmt_input(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=16, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=1, padx=3, sticky='w')
        self._format_money_input(amount_var, amount_e, callback=self._recalc)

        del_btn = tk.Button(row, text='X', fg=RED, bg=CARD, bd=0,
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', width=3,
                             command=lambda r=row: self._delete_row(r, self.other_cost_rows))
        del_btn.grid(row=0, column=2, padx=3, sticky='w')

        self.other_cost_rows.append({
            'frame': row, 'description': desc_e,
            'amount': amount_e, 'amount_var': amount_var, 'del_btn': del_btn,
        })
        self._recalc()

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
            total_standard += self._safe_float(var.get())

        total_fuel = 0
        for r in self.fuel_rows:
            total_fuel += self._safe_float(r['netto'].get())

        total_repairs = 0
        for r in self.repair_rows:
            total_repairs += self._safe_float(r['amount'].get())

        total_other = 0
        for r in self.other_cost_rows:
            total_other += self._safe_float(r['amount'].get())

        total_invoices = 0
        for r in self.invoice_rows:
            total_invoices += self._safe_float(r['amount'].get())

        total_costs = total_standard + total_fuel + total_repairs + total_other
        result = total_invoices - total_costs

        self.fuel_netto_label.config(text=f'Suma netto paliwa: {self._fmt(total_fuel)}')
        self.repair_sum_label.config(text=f'Suma napraw: {self._fmt(total_repairs)}')
        self.other_cost_sum_label.config(text=f'Suma kosztów innych: {self._fmt(total_other)}')
        self.total_standard_label.config(text=f'Koszty standardowe: {self._fmt(total_standard)}')
        self.total_fuel_label.config(text=f'Paliwo (netto): {self._fmt(total_fuel)}')
        self.total_repairs_label.config(text=f'Naprawy: {self._fmt(total_repairs)}')
        self.total_other_label.config(text=f'Inne: {self._fmt(total_other)}')
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

    def _auto_resize_text(self, widget):
        """Auto-resize Text widget height based on content."""
        content = widget.get('1.0', 'end-1c')
        lines = content.count('\n') + 1
        # Also account for line wrapping
        widget.update_idletasks()
        try:
            width_chars = widget.cget('width')
            if len(content) > 0:
                wrapped_lines = max(lines, (len(content) // max(width_chars, 1)) + 1)
            else:
                wrapped_lines = 1
        except Exception:
            wrapped_lines = lines
        new_height = max(1, min(wrapped_lines, 8))
        widget.config(height=new_height)

    def _fmt(self, val):
        formatted = f"{val:,.2f}".replace(',', '.').replace(' ', '').replace('\u00a0', '')
        # Now formatted looks like "1.234.567,89" — but we need dots as thousands
        # f"{val:,.2f}" gives "1,234,567.89"
        # Replace commas with dots (thousands), then dot with comma (decimal)
        parts = f"{val:,.2f}"
        parts = parts.replace(',', '.')  # 1.234.567.89
        # Last dot is decimal separator
        idx = parts.rfind('.')
        formatted = parts[:idx] + ',' + parts[idx+1:]
        return f"{formatted} PLN"

    @staticmethod
    def _format_money_input(var, entry, callback=None):
        """Format money input: free typing, format with dots on FocusOut."""
        def on_focus_out(event):
            val = var.get().strip()
            if not val:
                return
            # Parse current value (handles both Polish and plain format)
            clean = val.replace('.', '').replace(',', '.')
            try:
                num = float(clean)
            except ValueError:
                return
            # Re-format with Polish thousands dots
            if num == int(num) and ',' not in val:
                formatted = f"{int(num):,}".replace(',', '.')
            else:
                parts = f"{num:,.2f}"
                parts = parts.replace(',', '.')
                idx = parts.rfind('.')
                formatted = parts[:idx] + ',' + parts[idx+1:]
            if formatted != val:
                var.set(formatted)

        def on_focus_in(event):
            val = var.get().strip()
            if not val:
                return
            # Strip dots (thousands) so user can edit freely
            clean = val.replace('.', '')
            if clean != val:
                var.set(clean)
                entry.icursor(len(clean))

        entry.bind('<FocusOut>', on_focus_out, add='+')
        entry.bind('<FocusIn>', on_focus_in, add='+')

        if callback:
            var.trace_add('write', lambda *a: callback())

    @staticmethod
    def _fmt_input(val):
        """Format a number for display in input field (Polish: dots=thousands, comma=decimal)."""
        try:
            num = float(val)
        except (ValueError, TypeError):
            return str(val) if val else ''
        if num == 0:
            return ''
        if num == int(num):
            # Integer - format without decimals
            parts = f"{int(num):,}".replace(',', '.')
            return parts
        parts = f"{num:,.2f}"
        parts = parts.replace(',', '.')
        idx = parts.rfind('.')
        return parts[:idx] + ',' + parts[idx+1:]

    @staticmethod
    def _parse_money(val):
        """Parse money string with dots as thousands and comma as decimal to float."""
        if not val:
            return 0.0
        try:
            clean = val.replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, TypeError):
            return 0.0

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
        saved_defaults = db.get_cost_defaults(month_id)
        saved_costs = db.get_standard_costs(month_id)
        for key, (var, entry) in self.cost_entries.items():
            hardcoded = next((d for k, l, d in STANDARD_COST_PARAMS if k == key), 0)
            default = saved_defaults.get(key, hardcoded)
            val = saved_costs.get(key, default)
            var.set(self._fmt_input(val) if val else '0')

        for f in db.get_fuel(month_id):
            self._add_fuel_row(f)
        for r in db.get_repairs(month_id):
            self._add_repair_row(r)
        for l in db.get_leaves(month_id):
            self._add_leave_row(l)
        for oc in db.get_other_costs(month_id):
            self._add_other_cost_row(oc)
        for inv in db.get_invoices(month_id):
            self._add_invoice_row(inv)

        self.is_locked = db.is_month_accepted(month_id)
        self._update_lock_state()
        self._recalc()
        self._recalc_leaves()

    def _save_month(self):
        month_id = self.current_month

        for key, (var, entry) in self.cost_entries.items():
            val = self._safe_float(var.get())
            db.save_standard_cost(month_id, key, val)

        fuel_data = []
        for r in self.fuel_rows:
            fuel_data.append({
                'plate': r['plate_var'].get(),
                'date': r['date'].get(),
                'liters': self._safe_float_plain(r['liters'].get()),
                'odometer': self._safe_int(r['odometer'].get()),
                'netto': self._safe_float(r['netto'].get()),
                'brutto': self._safe_float(r['brutto'].get()),
            })
        db.save_fuel(month_id, fuel_data)

        repair_data = []
        for r in self.repair_rows:
            repair_data.append({
                'plate': r['plate_var'].get(),
                'date': r['date'].get(),
                'description': r['description'].get('1.0', 'end-1c').strip(),
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

        other_cost_data = []
        for r in self.other_cost_rows:
            other_cost_data.append({
                'description': r['description'].get(),
                'amount': self._safe_float(r['amount'].get()),
            })
        db.save_other_costs(month_id, other_cost_data)

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
        for lst in [self.fuel_rows, self.repair_rows, self.leave_rows, self.other_cost_rows, self.invoice_rows]:
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
            r['plate'].config(state='disabled' if state == 'disabled' else 'normal')
            r['date'].config(state=state)
            r['del_btn'].config(state=state)

        for r in self.repair_rows:
            for k in ['amount', 'odometer']:
                r[k].config(state=state)
            r['plate'].config(state='disabled' if state == 'disabled' else 'normal')
            r['description'].config(state=state)
            r['date'].config(state=state)
            r['del_btn'].config(state=state)

        for r in self.leave_rows:
            r['name_combo'].config(state='disabled' if state == 'disabled' else 'normal')
            r['date_from'].config(state=state)
            r['date_to'].config(state=state)
            r['type_combo'].config(state='disabled' if state == 'disabled' else 'readonly')
            r['del_btn'].config(state=state)

        for r in self.other_cost_rows:
            r['description'].config(state=state)
            r['amount'].config(state=state)
            r['del_btn'].config(state=state)

        for r in self.invoice_rows:
            for k in ['number', 'amount']:
                r[k].config(state=state)
            r['date'].config(state=state)
            r['paid_cb'].config(state=state)
            r['del_btn'].config(state=state)

        btn_state = 'disabled' if state == 'disabled' else 'normal'
        for btn in [self.btn_add_fuel, self.btn_add_repair, self.btn_add_leave,
                    self.btn_add_invoice, self.btn_set_defaults, self.btn_add_other_cost,
                    self.btn_add_plate, self.btn_remove_plate,
                    self.btn_add_emp, self.btn_remove_emp]:
            btn.config(state=btn_state)
        self._new_plate_entry.config(state=state)
        self._new_emp_entry.config(state=state)

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

        # Tab 3: Paliwa
        self._stats_tab_fuel = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_fuel, text='  Paliwa  ')

        # Tab 4: Naprawy
        self._stats_tab_repairs = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_repairs, text='  Naprawy  ')

        # Tab 5: Podsumowanie roku (last)
        self._stats_tab_yearly = tk.Frame(self._stats_notebook, bg=BG)
        self._stats_notebook.add(self._stats_tab_yearly, text='  Podsumowanie roku  ')

        self._refresh_stats()

    def _refresh_stats(self):
        year = int(self._stats_year_var.get())
        self._build_stats_monthly_table(year)
        self._build_stats_annual_costs(year)
        self._build_stats_fuel(year)
        self._build_stats_repairs(year)
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
            'Koszty standardowe', 'Paliwo (netto)', 'Naprawy', 'Koszty inne',
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
                    'Koszty inne': s['other'],
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

        amount_var = tk.StringVar(value=self._fmt_input(d.get('amount', '')) if d.get('amount') else '')
        amount_e = tk.Entry(row, textvariable=amount_var, width=16, font=('Segoe UI', 9),
                             justify='right', bd=1, relief='solid')
        amount_e.grid(row=0, column=1, padx=3, sticky='w')
        self._format_money_input(amount_var, amount_e, callback=self._recalc_annual)

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
            val = self._safe_float(r['amount'].get())
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
        yearly_other = 0
        yearly_urlop = 0
        yearly_chorobowe = 0
        yearly_urlop_by_person = {}
        yearly_chorobowe_by_person = {}

        for m in range(1, 13):
            month_id = f"{year}-{m:02d}"
            s = db.get_month_summary(month_id)
            yearly_invoices += s['invoices']
            yearly_standard += s['standard']
            yearly_fuel += s['fuel_netto']
            yearly_repairs += s['repairs']
            yearly_other += s['other']
            yearly_urlop += s['urlop_days']
            yearly_chorobowe += s['chorobowe_days']
            for name, days in s['urlop_by_person'].items():
                yearly_urlop_by_person[name] = yearly_urlop_by_person.get(name, 0) + days
            for name, days in s['chorobowe_by_person'].items():
                yearly_chorobowe_by_person[name] = yearly_chorobowe_by_person.get(name, 0) + days

        yearly_monthly_costs = yearly_standard + yearly_fuel + yearly_repairs + yearly_other
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
            ('Koszty inne (suma)', self._fmt(yearly_other), LABEL_FG, False),
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
                 bg=CARD, fg=LABEL_FG, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 6))

        # Per-person breakdown
        all_persons = sorted(set(list(yearly_urlop_by_person.keys()) + list(yearly_chorobowe_by_person.keys())))
        if all_persons:
            for person in all_persons:
                u_days = yearly_urlop_by_person.get(person, 0)
                c_days = yearly_chorobowe_by_person.get(person, 0)
                parts = []
                if u_days > 0:
                    parts.append(f'urlop: {u_days} dni')
                if c_days > 0:
                    parts.append(f'chorobowe: {c_days} dni')
                tk.Label(leave_frame, text=f'  {person}: {", ".join(parts)}',
                         bg=CARD, fg=LABEL_FG, font=('Segoe UI', 9)).pack(anchor='w')

    # ============================================================
    # STATS TAB 5: REPAIR STATISTICS
    # ============================================================

    def _build_stats_repairs(self, year):
        for w in self._stats_tab_repairs.winfo_children():
            w.destroy()

        main = tk.Frame(self._stats_tab_repairs, bg=BG, padx=24, pady=16)
        main.pack(fill='both', expand=True)

        # Header with plate selector
        top = tk.Frame(main, bg=BG)
        top.pack(fill='x', pady=(0, 12))

        tk.Label(top, text=f'Statystyki napraw - {year}', bg=BG, fg=PRIMARY_DARK,
                 font=('Segoe UI', 13, 'bold')).pack(side='left')

        plate_frame = tk.Frame(top, bg=BG)
        plate_frame.pack(side='right')

        tk.Label(plate_frame, text='Pojazd:', bg=BG, fg=LABEL_FG,
                 font=('Segoe UI', 10)).pack(side='left', padx=(0, 6))

        plates = db.get_fuel_plates()
        all_options = ['Wszystkie'] + plates
        prev_selection = getattr(self, '_stats_repair_plate_var', None)
        prev_value = prev_selection.get() if prev_selection else 'Wszystkie'
        if prev_value not in all_options:
            prev_value = 'Wszystkie'
        self._stats_repair_plate_var = tk.StringVar(value=prev_value)
        plate_combo = ttk.Combobox(plate_frame, textvariable=self._stats_repair_plate_var,
                                    values=all_options, state='readonly', width=16,
                                    font=('Segoe UI', 10))
        plate_combo.pack(side='left')
        plate_combo.bind('<<ComboboxSelected>>', lambda e: self._build_stats_repairs(
            int(self._stats_year_var.get())))

        # Get repair stats
        selected_plate = self._stats_repair_plate_var.get()
        plate_filter = None if selected_plate == 'Wszystkie' else selected_plate
        stats = db.get_repair_stats_for_year(year, plate_filter)

        # Build table
        frame = tk.Frame(main, bg=BG)
        frame.pack(fill='x', pady=(0, 12))

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

        categories = ['Naprawy (szt.)', 'Suma kosztów']

        # Header row
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

        for i, cat in enumerate(categories):
            bg_color = '#f8fafc' if i % 2 == 0 else CARD

            tk.Label(inner, text=cat, bg=bg_color, fg=LABEL_FG,
                     font=('Segoe UI', 9), width=22, anchor='w', padx=8, pady=5,
                     relief='ridge').grid(row=i + 1, column=0, sticky='nsew')

            year_sum = 0
            for m in range(1, 13):
                s = stats[m]
                val = s['count'] if cat == 'Naprawy (szt.)' else s['total_amount']
                year_sum += val

                if cat == 'Naprawy (szt.)':
                    text = str(int(val)) if val else '-'
                else:
                    text = self._fmt(val) if val else '-'

                fg = RED if cat == 'Suma kosztów' and val > 0 else LABEL_FG

                tk.Label(inner, text=text, bg=bg_color, fg=fg,
                         font=('Segoe UI', 9), width=13, anchor='e', padx=6, pady=5,
                         relief='ridge').grid(row=i + 1, column=m, sticky='nsew')

            if cat == 'Naprawy (szt.)':
                sum_text = str(int(year_sum))
            else:
                sum_text = self._fmt(year_sum)

            tk.Label(inner, text=sum_text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 9, 'bold'), width=14, anchor='e', padx=6, pady=5,
                     relief='ridge').grid(row=i + 1, column=13, sticky='nsew')

        # Detailed list of repairs per month
        detail_frame = tk.Frame(main, bg=CARD, bd=1, relief='solid', highlightbackground=BORDER, padx=20, pady=12)
        detail_frame.pack(fill='both', expand=True, pady=(0, 0))

        tk.Label(detail_frame, text='Szczegóły napraw', bg=CARD, fg=PRIMARY_DARK,
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 8))

        has_any = False
        for m in range(1, 13):
            s = stats[m]
            if s['count'] > 0:
                has_any = True
                month_label = f"{MONTHS_PL[m - 1]}: {s['count']} napraw(y) - {self._fmt(s['total_amount'])}"
                tk.Label(detail_frame, text=month_label, bg=CARD, fg=PRIMARY_DARK,
                         font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(4, 0))
                for desc in s['descriptions']:
                    tk.Label(detail_frame, text=f'  - {desc}', bg=CARD, fg=LABEL_FG,
                             font=('Segoe UI', 9)).pack(anchor='w')

        if not has_any:
            tk.Label(detail_frame, text='Brak napraw w wybranym roku', bg=CARD, fg=LABEL_FG,
                     font=('Segoe UI', 9)).pack(anchor='w')

    # ============================================================
    # FUEL PLATE MANAGEMENT
    # ============================================================

    def _add_fuel_plate(self):
        plate = self._new_plate_var.get().strip().upper()
        if not plate:
            return
        db.add_fuel_plate(plate)
        self._new_plate_var.set('')
        self._refresh_fuel_plate_combos()

    def _remove_fuel_plate(self):
        plate = self._new_plate_var.get().strip().upper()
        if not plate:
            return
        db.remove_fuel_plate(plate)
        self._new_plate_var.set('')
        self._refresh_fuel_plate_combos()

    def _refresh_fuel_plate_combos(self):
        plates = db.get_fuel_plates()
        for r in self.fuel_rows:
            r['plate']['values'] = plates
        for r in self.repair_rows:
            r['plate']['values'] = plates

    # ============================================================
    # EMPLOYEE MANAGEMENT
    # ============================================================

    def _add_employee(self):
        name = self._new_emp_var.get().strip()
        if not name:
            return
        db.add_employee(name)
        self._new_emp_var.set('')
        self._refresh_employee_combos()

    def _remove_employee(self):
        name = self._new_emp_var.get().strip()
        if not name:
            return
        db.remove_employee(name)
        self._new_emp_var.set('')
        self._refresh_employee_combos()

    def _refresh_employee_combos(self):
        employees = db.get_employees()
        for r in self.leave_rows:
            r['name_combo']['values'] = employees

    # ============================================================
    # STATS TAB 4: FUEL STATISTICS
    # ============================================================

    def _build_stats_fuel(self, year):
        for w in self._stats_tab_fuel.winfo_children():
            w.destroy()

        main = tk.Frame(self._stats_tab_fuel, bg=BG, padx=24, pady=16)
        main.pack(fill='both', expand=True)

        # Header with plate selector
        top = tk.Frame(main, bg=BG)
        top.pack(fill='x', pady=(0, 12))

        tk.Label(top, text=f'Statystyki paliwa - {year}', bg=BG, fg=PRIMARY_DARK,
                 font=('Segoe UI', 13, 'bold')).pack(side='left')

        plate_frame = tk.Frame(top, bg=BG)
        plate_frame.pack(side='right')

        tk.Label(plate_frame, text='Pojazd:', bg=BG, fg=LABEL_FG,
                 font=('Segoe UI', 10)).pack(side='left', padx=(0, 6))

        plates = db.get_fuel_plates()
        all_options = ['Wszystkie'] + plates
        # Preserve previous selection if it exists
        prev_selection = getattr(self, '_stats_fuel_plate_var', None)
        prev_value = prev_selection.get() if prev_selection else 'Wszystkie'
        if prev_value not in all_options:
            prev_value = 'Wszystkie'
        self._stats_fuel_plate_var = tk.StringVar(value=prev_value)
        plate_combo = ttk.Combobox(plate_frame, textvariable=self._stats_fuel_plate_var,
                                    values=all_options, state='readonly', width=16,
                                    font=('Segoe UI', 10))
        plate_combo.pack(side='left')
        plate_combo.bind('<<ComboboxSelected>>', lambda e: self._build_stats_fuel(
            int(self._stats_year_var.get())))

        # Get fuel stats
        selected_plate = self._stats_fuel_plate_var.get()
        plate_filter = None if selected_plate == 'Wszystkie' else selected_plate
        stats = db.get_fuel_stats_for_year(year, plate_filter)

        # Build table
        frame = tk.Frame(main, bg=BG)
        frame.pack(fill='both', expand=True)

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
            'Tankowania (szt.)',
            'Litry (suma)',
            'Kilometry',
            'Śr. spalanie (l/100km)',
            'Suma netto',
            'Suma brutto',
        ]

        # Header row
        tk.Label(inner, text='Kategoria', bg='#e2e8f0', fg=PRIMARY_DARK,
                 font=('Segoe UI', 9, 'bold'), width=22, anchor='w', padx=8, pady=8,
                 relief='ridge').grid(row=0, column=0, sticky='nsew')

        for m in range(1, 13):
            tk.Label(inner, text=MONTHS_PL[m - 1][:3], bg='#e2e8f0', fg=PRIMARY_DARK,
                     font=('Segoe UI', 9, 'bold'), width=13, anchor='center', padx=4, pady=8,
                     relief='ridge').grid(row=0, column=m, sticky='nsew')

        tk.Label(inner, text='SUMA/ŚR.', bg=PRIMARY_DARK, fg='white',
                 font=('Segoe UI', 9, 'bold'), width=14, anchor='center', padx=4, pady=8,
                 relief='ridge').grid(row=0, column=13, sticky='nsew')

        # Data rows
        for i, cat in enumerate(categories):
            bg_color = '#f8fafc' if i % 2 == 0 else CARD

            tk.Label(inner, text=cat, bg=bg_color, fg=LABEL_FG,
                     font=('Segoe UI', 9), width=22, anchor='w', padx=8, pady=5,
                     relief='ridge').grid(row=i + 1, column=0, sticky='nsew')

            year_sum = 0
            year_total_liters = 0
            year_total_km = 0

            for m in range(1, 13):
                s = stats[m]
                val_map = {
                    'Tankowania (szt.)': s['entries'],
                    'Litry (suma)': s['total_liters'],
                    'Kilometry': s['km_driven'],
                    'Śr. spalanie (l/100km)': s['avg_consumption'],
                    'Suma netto': s['total_netto'],
                    'Suma brutto': s['total_brutto'],
                }
                val = val_map[cat]

                if cat == 'Śr. spalanie (l/100km)':
                    year_total_liters += s['total_liters']
                    year_total_km += s['km_driven']
                    text = f"{val:.1f}" if val > 0 else '-'
                elif cat == 'Tankowania (szt.)' or cat == 'Kilometry':
                    text = str(int(val)) if val else '-'
                    year_sum += val
                elif cat == 'Litry (suma)':
                    text = f"{val:.1f}" if val else '-'
                    year_sum += val
                else:
                    text = self._fmt(val) if val else '-'
                    year_sum += val

                fg = LABEL_FG
                if cat in ('Suma netto', 'Suma brutto') and val > 0:
                    fg = RED

                tk.Label(inner, text=text, bg=bg_color, fg=fg,
                         font=('Segoe UI', 9), width=13, anchor='e', padx=6, pady=5,
                         relief='ridge').grid(row=i + 1, column=m, sticky='nsew')

            # SUMA column
            if cat == 'Śr. spalanie (l/100km)':
                avg = (year_total_liters / year_total_km) * 100 if year_total_km > 0 else 0
                sum_text = f"{avg:.1f}" if avg > 0 else '-'
            elif cat == 'Tankowania (szt.)' or cat == 'Kilometry':
                sum_text = str(int(year_sum))
            elif cat == 'Litry (suma)':
                sum_text = f"{year_sum:.1f}"
            else:
                sum_text = self._fmt(year_sum)

            tk.Label(inner, text=sum_text, bg='#f1f5f9', fg=LABEL_FG,
                     font=('Segoe UI', 9, 'bold'), width=14, anchor='e', padx=6, pady=5,
                     relief='ridge').grid(row=i + 1, column=13, sticky='nsew')

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _safe_float(val):
        try:
            # Handle Polish format: dots as thousands, comma as decimal
            clean = str(val).replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_float_plain(val):
        """Parse a plain number (not Polish money format). Accepts both '.' and ',' as decimal."""
        try:
            clean = str(val).replace(',', '.')
            return float(clean)
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
