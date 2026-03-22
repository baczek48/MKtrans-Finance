import sqlite3
import os
import sys
import shutil
from datetime import datetime

# When running as PyInstaller exe, use the folder where the exe lives (not temp dir)
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(_BASE_DIR, 'mktrans.db')
BACKUP_DIR = os.path.join(_BASE_DIR, 'backups')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS months (
            id TEXT PRIMARY KEY,
            accepted INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS standard_costs (
            month_id TEXT,
            param_key TEXT,
            value REAL DEFAULT 0,
            PRIMARY KEY (month_id, param_key),
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cost_defaults (
            param_key TEXT,
            value REAL DEFAULT 0,
            effective_from TEXT DEFAULT '0000-00',
            PRIMARY KEY (param_key, effective_from)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fuel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_id TEXT,
            plate TEXT DEFAULT '',
            date TEXT,
            liters REAL,
            odometer INTEGER,
            netto REAL,
            brutto REAL,
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fuel_plates (
            plate TEXT PRIMARY KEY
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            name TEXT PRIMARY KEY
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS other_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_id TEXT,
            description TEXT DEFAULT '',
            amount REAL DEFAULT 0,
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_id TEXT,
            plate TEXT,
            date TEXT,
            description TEXT,
            amount REAL,
            odometer INTEGER,
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_id TEXT,
            type TEXT,
            name TEXT DEFAULT '',
            date_from TEXT,
            date_to TEXT,
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_id TEXT,
            date TEXT,
            number TEXT,
            amount REAL,
            paid INTEGER DEFAULT 0,
            FOREIGN KEY (month_id) REFERENCES months(id)
        )
    """)

    # Migrate: add 'paid' column to invoices if missing
    inv_cols = [row[1] for row in c.execute("PRAGMA table_info(invoices)").fetchall()]
    if 'paid' not in inv_cols:
        c.execute("ALTER TABLE invoices ADD COLUMN paid INTEGER DEFAULT 0")

    c.execute("""
        CREATE TABLE IF NOT EXISTS annual_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            type TEXT,
            description TEXT DEFAULT '',
            amount REAL DEFAULT 0
        )
    """)

    # Migrate: add 'name' column to leaves if missing
    cols = [row[1] for row in c.execute("PRAGMA table_info(leaves)").fetchall()]
    if 'name' not in cols:
        c.execute("ALTER TABLE leaves ADD COLUMN name TEXT DEFAULT ''")

    # Migrate: add 'effective_from' column to cost_defaults if missing (old schema had single PK)
    cd_cols = [row[1] for row in c.execute("PRAGMA table_info(cost_defaults)").fetchall()]
    if 'effective_from' not in cd_cols:
        c.execute("ALTER TABLE cost_defaults ADD COLUMN effective_from TEXT DEFAULT '0000-00'")

    # Migrate: add 'plate' column to fuel if missing
    fuel_cols = [row[1] for row in c.execute("PRAGMA table_info(fuel)").fetchall()]
    if 'plate' not in fuel_cols:
        c.execute("ALTER TABLE fuel ADD COLUMN plate TEXT DEFAULT ''")

    # Seed default plates if fuel_plates table is empty
    plate_count = c.execute("SELECT COUNT(*) FROM fuel_plates").fetchone()[0]
    if plate_count == 0:
        for p in ['PNT7966A', 'PNTMR28']:
            c.execute("INSERT OR IGNORE INTO fuel_plates (plate) VALUES (?)", (p,))

    conn.commit()
    conn.close()


def ensure_month(month_id):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO months (id) VALUES (?)", (month_id,))
    conn.commit()
    conn.close()


def is_month_accepted(month_id):
    conn = get_connection()
    row = conn.execute("SELECT accepted FROM months WHERE id = ?", (month_id,)).fetchone()
    conn.close()
    return bool(row and row['accepted'])


def set_month_accepted(month_id, accepted):
    ensure_month(month_id)
    conn = get_connection()
    conn.execute("UPDATE months SET accepted = ? WHERE id = ?", (1 if accepted else 0, month_id))
    conn.commit()
    conn.close()


# --- Cost Defaults ---

def get_cost_defaults(month_id=None):
    """Get cost defaults effective for given month.
    For each param_key, returns the value from the latest effective_from <= month_id."""
    conn = get_connection()
    if month_id:
        rows = conn.execute("""
            SELECT param_key, value FROM cost_defaults
            WHERE (param_key, effective_from) IN (
                SELECT param_key, MAX(effective_from)
                FROM cost_defaults
                WHERE effective_from <= ?
                GROUP BY param_key
            )
        """, (month_id,)).fetchall()
    else:
        # Fallback: get the latest defaults overall
        rows = conn.execute("""
            SELECT param_key, value FROM cost_defaults
            WHERE (param_key, effective_from) IN (
                SELECT param_key, MAX(effective_from)
                FROM cost_defaults
                GROUP BY param_key
            )
        """).fetchall()
    conn.close()
    return {r['param_key']: r['value'] for r in rows}


def save_cost_default(param_key, value, effective_from='0000-00'):
    conn = get_connection()
    conn.execute("""
        INSERT INTO cost_defaults (param_key, value, effective_from)
        VALUES (?, ?, ?)
        ON CONFLICT(param_key, effective_from) DO UPDATE SET value = excluded.value
    """, (param_key, value, effective_from))
    conn.commit()
    conn.close()


# --- Standard Costs ---

def get_standard_costs(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT param_key, value FROM standard_costs WHERE month_id = ?", (month_id,)).fetchall()
    conn.close()
    return {r['param_key']: r['value'] for r in rows}


def save_standard_cost(month_id, param_key, value):
    ensure_month(month_id)
    conn = get_connection()
    conn.execute("""
        INSERT INTO standard_costs (month_id, param_key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(month_id, param_key) DO UPDATE SET value = excluded.value
    """, (month_id, param_key, value))
    conn.commit()
    conn.close()


# --- Fuel ---

def get_fuel(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM fuel WHERE month_id = ? ORDER BY date", (month_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_fuel(month_id, entries):
    conn = get_connection()
    conn.execute("DELETE FROM fuel WHERE month_id = ?", (month_id,))
    for e in entries:
        conn.execute(
            "INSERT INTO fuel (month_id, plate, date, liters, odometer, netto, brutto) VALUES (?,?,?,?,?,?,?)",
            (month_id, e.get('plate', ''), e['date'], e['liters'], e['odometer'], e['netto'], e['brutto'])
        )
    conn.commit()
    conn.close()


# --- Fuel Plates ---

def get_fuel_plates():
    conn = get_connection()
    rows = conn.execute("SELECT plate FROM fuel_plates ORDER BY plate").fetchall()
    conn.close()
    return [r['plate'] for r in rows]


def add_fuel_plate(plate):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO fuel_plates (plate) VALUES (?)", (plate,))
    conn.commit()
    conn.close()


def remove_fuel_plate(plate):
    conn = get_connection()
    conn.execute("DELETE FROM fuel_plates WHERE plate = ?", (plate,))
    conn.commit()
    conn.close()


def get_fuel_stats_for_year(year, plate=None):
    """Get monthly fuel statistics for a given year, optionally filtered by plate."""
    conn = get_connection()
    results = {}
    for m in range(1, 13):
        month_id = f"{year}-{m:02d}"
        if plate:
            rows = conn.execute(
                "SELECT * FROM fuel WHERE month_id = ? AND plate = ? ORDER BY date",
                (month_id, plate)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM fuel WHERE month_id = ? ORDER BY date",
                (month_id,)).fetchall()
        entries = [dict(r) for r in rows]

        total_liters = sum(e['liters'] or 0 for e in entries)
        total_netto = sum(e['netto'] or 0 for e in entries)
        total_brutto = sum(e['brutto'] or 0 for e in entries)

        # Calculate km driven: max odometer - min odometer in that month
        odometers = [e['odometer'] for e in entries if e['odometer'] and e['odometer'] > 0]
        if len(odometers) >= 2:
            km_driven = max(odometers) - min(odometers)
        else:
            km_driven = 0

        # Average consumption: liters / (km / 100)
        if km_driven > 0 and total_liters > 0:
            avg_consumption = (total_liters / km_driven) * 100
        else:
            avg_consumption = 0

        results[m] = {
            'entries': len(entries),
            'total_liters': total_liters,
            'km_driven': km_driven,
            'total_netto': total_netto,
            'total_brutto': total_brutto,
            'avg_consumption': avg_consumption,
        }
    conn.close()
    return results


def get_repair_stats_for_year(year, plate=None):
    """Get monthly repair statistics for a given year, optionally filtered by plate."""
    conn = get_connection()
    results = {}
    for m in range(1, 13):
        month_id = f"{year}-{m:02d}"
        if plate:
            rows = conn.execute(
                "SELECT * FROM repairs WHERE month_id = ? AND plate = ? ORDER BY date",
                (month_id, plate)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM repairs WHERE month_id = ? ORDER BY date",
                (month_id,)).fetchall()
        entries = [dict(r) for r in rows]

        total_amount = sum(e['amount'] or 0 for e in entries)
        descriptions = [e.get('description', '') for e in entries if e.get('description', '').strip()]

        results[m] = {
            'count': len(entries),
            'total_amount': total_amount,
            'descriptions': descriptions,
        }
    conn.close()
    return results


# --- Employees ---

def get_employees():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM employees ORDER BY name").fetchall()
    conn.close()
    return [r['name'] for r in rows]


def add_employee(name):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def remove_employee(name):
    conn = get_connection()
    conn.execute("DELETE FROM employees WHERE name = ?", (name,))
    conn.commit()
    conn.close()


# --- Other Costs ---

def get_other_costs(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM other_costs WHERE month_id = ? ORDER BY id", (month_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_other_costs(month_id, entries):
    conn = get_connection()
    conn.execute("DELETE FROM other_costs WHERE month_id = ?", (month_id,))
    for e in entries:
        conn.execute(
            "INSERT INTO other_costs (month_id, description, amount) VALUES (?,?,?)",
            (month_id, e.get('description', ''), e.get('amount', 0))
        )
    conn.commit()
    conn.close()


# --- Repairs ---

def get_repairs(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM repairs WHERE month_id = ? ORDER BY date", (month_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_repairs(month_id, entries):
    conn = get_connection()
    conn.execute("DELETE FROM repairs WHERE month_id = ?", (month_id,))
    for e in entries:
        conn.execute(
            "INSERT INTO repairs (month_id, plate, date, description, amount, odometer) VALUES (?,?,?,?,?,?)",
            (month_id, e['plate'], e['date'], e['description'], e['amount'], e['odometer'])
        )
    conn.commit()
    conn.close()


# --- Leaves ---

def get_leaves(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM leaves WHERE month_id = ? ORDER BY date_from", (month_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_leaves(month_id, entries):
    conn = get_connection()
    conn.execute("DELETE FROM leaves WHERE month_id = ?", (month_id,))
    for e in entries:
        conn.execute(
            "INSERT INTO leaves (month_id, type, name, date_from, date_to) VALUES (?,?,?,?,?)",
            (month_id, e['type'], e.get('name', ''), e['date_from'], e['date_to'])
        )
    conn.commit()
    conn.close()


# --- Invoices ---

def get_invoices(month_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM invoices WHERE month_id = ? ORDER BY date", (month_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_invoices(month_id, entries):
    conn = get_connection()
    conn.execute("DELETE FROM invoices WHERE month_id = ?", (month_id,))
    for e in entries:
        conn.execute(
            "INSERT INTO invoices (month_id, date, number, amount, paid) VALUES (?,?,?,?,?)",
            (month_id, e['date'], e['number'], e['amount'], 1 if e.get('paid') else 0)
        )
    conn.commit()
    conn.close()


# --- Annual Costs ---

def get_annual_costs(year):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM annual_costs WHERE year = ? ORDER BY type, id", (year,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_annual_costs(year, entries):
    conn = get_connection()
    conn.execute("DELETE FROM annual_costs WHERE year = ?", (year,))
    for e in entries:
        conn.execute(
            "INSERT INTO annual_costs (year, type, description, amount) VALUES (?,?,?,?)",
            (year, e['type'], e.get('description', ''), e.get('amount', 0))
        )
    conn.commit()
    conn.close()


def get_annual_costs_total(year):
    conn = get_connection()
    row = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM annual_costs WHERE year = ?",
                       (year,)).fetchone()
    conn.close()
    return row['total']


# --- Statistics ---

def get_all_months():
    conn = get_connection()
    rows = conn.execute("SELECT id FROM months ORDER BY id").fetchall()
    conn.close()
    return [r['id'] for r in rows]


def get_months_for_year(year):
    prefix = f"{year}-"
    conn = get_connection()
    rows = conn.execute("SELECT id FROM months WHERE id LIKE ? ORDER BY id", (prefix + '%',)).fetchall()
    conn.close()
    return [r['id'] for r in rows]


def get_all_years():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT SUBSTR(id, 1, 4) as year FROM months ORDER BY year").fetchall()
    conn.close()
    years = [int(r['year']) for r in rows]
    # Also check annual_costs years
    rows2 = conn = get_connection()
    rows2 = conn.execute("SELECT DISTINCT year FROM annual_costs ORDER BY year").fetchall()
    conn.close()
    for r in rows2:
        if r['year'] not in years:
            years.append(r['year'])
    years.sort()
    return years


def get_month_summary(month_id):
    costs = get_standard_costs(month_id)
    total_standard = sum(costs.values())

    fuel = get_fuel(month_id)
    total_fuel_netto = sum(f['netto'] or 0 for f in fuel)

    repairs = get_repairs(month_id)
    total_repairs = sum(r['amount'] or 0 for r in repairs)

    other = get_other_costs(month_id)
    total_other = sum(o['amount'] or 0 for o in other)

    invoices = get_invoices(month_id)
    total_invoices = sum(i['amount'] or 0 for i in invoices)

    leaves = get_leaves(month_id)
    urlop_days = 0
    chorobowe_days = 0
    urlop_by_person = {}
    chorobowe_by_person = {}
    for l in leaves:
        days = _calc_days(l['date_from'], l['date_to'])
        name = l.get('name', '') or 'Nieprzypisane'
        if l['type'] == 'urlop':
            urlop_days += days
            urlop_by_person[name] = urlop_by_person.get(name, 0) + days
        else:
            chorobowe_days += days
            chorobowe_by_person[name] = chorobowe_by_person.get(name, 0) + days

    total_costs = total_standard + total_fuel_netto + total_repairs + total_other
    result = total_invoices - total_costs

    return {
        'standard': total_standard,
        'fuel_netto': total_fuel_netto,
        'repairs': total_repairs,
        'other': total_other,
        'total_costs': total_costs,
        'invoices': total_invoices,
        'urlop_days': urlop_days,
        'chorobowe_days': chorobowe_days,
        'urlop_by_person': urlop_by_person,
        'chorobowe_by_person': chorobowe_by_person,
        'result': result,
    }


def _calc_days(date_from, date_to):
    if not date_from or not date_to:
        return 0
    try:
        d1 = datetime.strptime(date_from, '%Y-%m-%d')
        d2 = datetime.strptime(date_to, '%Y-%m-%d')
        diff = (d2 - d1).days + 1
        return max(0, diff)
    except (ValueError, TypeError):
        return 0


# --- Backup ---

def create_backup():
    if not os.path.exists(DB_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'mktrans_{timestamp}.db')
    shutil.copy2(DB_PATH, backup_path)
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
    while len(backups) > 10:
        os.remove(os.path.join(BACKUP_DIR, backups.pop(0)))
    return backup_path
