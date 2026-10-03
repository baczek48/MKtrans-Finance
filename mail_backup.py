"""Send an encrypted database backup by e-mail (SMTP + AES-256 ZIP).

Settings live in mail_settings.json next to the app (outside the database, so they
never travel inside a backup). Passwords are protected with Windows DPAPI: they can
only be decrypted by the same Windows user on the same computer.
"""
import base64
import ctypes
import ctypes.wintypes
import json
import os
import smtplib
import sqlite3
import ssl
import tempfile
from datetime import datetime
from email.message import EmailMessage

import pyzipper

import database as db

SETTINGS_PATH = os.path.join(db._BASE_DIR, 'mail_settings.json')

DEFAULT_SETTINGS = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 465,
    'security': 'SSL',          # 'SSL' (port 465) or 'STARTTLS' (port 587)
    'login': '',
    'smtp_password': '',
    'sender': '',
    'recipients': '',           # comma / semicolon separated
    'zip_password': '',
}
_SECRET_FIELDS = ('smtp_password', 'zip_password')


# --- DPAPI (Windows) ---

class _Blob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _blob(data):
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _dpapi(data, protect):
    crypt32 = ctypes.windll.crypt32
    src, _keep = _blob(data)
    out = _Blob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError('DPAPI error')
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _protect(text):
    if not text:
        return ''
    return base64.b64encode(_dpapi(text.encode('utf-8'), True)).decode('ascii')


def _unprotect(token):
    if not token:
        return ''
    try:
        return _dpapi(base64.b64decode(token), False).decode('utf-8')
    except (OSError, ValueError):
        return ''  # file copied from another user / computer


# --- Settings ---

def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding='utf-8') as f:
                stored = json.load(f)
        except (OSError, ValueError):
            stored = {}
        for k in DEFAULT_SETTINGS:
            if k in stored:
                settings[k] = stored[k]
        for k in _SECRET_FIELDS:
            settings[k] = _unprotect(stored.get(k, ''))
    return settings


def save_settings(settings):
    data = {k: settings.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS}
    for k in _SECRET_FIELDS:
        data[k] = _protect(data[k])
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def missing_settings(settings):
    """Labels of required settings that are still empty."""
    required = [('smtp_host', 'Serwer SMTP'), ('login', 'Login'), ('smtp_password', 'Hasło SMTP'),
                ('recipients', 'Odbiorca'), ('zip_password', 'Hasło do backupu')]
    return [label for key, label in required if not str(settings.get(key, '')).strip()]


def parse_recipients(text):
    return [r.strip() for r in text.replace(';', ',').split(',') if r.strip()]


# --- Backup + send ---

def build_encrypted_backup(zip_password, out_dir):
    """Consistent snapshot of the live database packed into an AES-256 ZIP.
    Returns the path of the ZIP file."""
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    snap_path = os.path.join(out_dir, 'mktrans.db')
    src = sqlite3.connect(db.DB_PATH)
    dst = sqlite3.connect(snap_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    zip_path = os.path.join(out_dir, f'MKtrans_backup_{stamp}.zip')
    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(zip_password.encode('utf-8'))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        zf.write(snap_path, 'mktrans.db')
    os.remove(snap_path)
    return zip_path


def send_backup(settings, timeout=60):
    """Build the encrypted backup and send it. Returns (zip_name, size_bytes, recipients).
    Raises on any failure (SMTP / auth / network)."""
    recipients = parse_recipients(settings['recipients'])
    if not recipients:
        raise ValueError('Brak adresu odbiorcy.')
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = build_encrypted_backup(settings['zip_password'], tmp)
        zip_name = os.path.basename(zip_path)
        with open(zip_path, 'rb') as f:
            payload = f.read()

    now = datetime.now()
    msg = EmailMessage()
    msg['Subject'] = f'MKtrans Finance - backup danych {now:%Y-%m-%d %H:%M}'
    msg['From'] = settings.get('sender') or settings['login']
    msg['To'] = ', '.join(recipients)
    msg.set_content(
        f'Kopia zapasowa danych MKtrans Finance z {now:%Y-%m-%d %H:%M}.\n\n'
        f'Załącznik: {zip_name} (archiwum ZIP zaszyfrowane AES-256).\n'
        'Aby odtworzyć dane: rozpakuj archiwum 7-Zipem lub WinRAR-em (hasło do backupu),\n'
        'zamknij aplikację i podmień plik mktrans.db w folderze programu.\n')
    msg.add_attachment(payload, maintype='application', subtype='zip', filename=zip_name)

    host = settings['smtp_host'].strip()
    port = int(settings.get('smtp_port') or (465 if settings.get('security') == 'SSL' else 587))
    context = ssl.create_default_context()
    if settings.get('security') == 'SSL':
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
    try:
        if settings.get('security') != 'SSL':
            server.starttls(context=context)
        server.login(settings['login'].strip(), settings['smtp_password'])
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return zip_name, len(payload), recipients


def describe_error(exc):
    """Human readable (Polish) explanation of a send failure."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return ('Serwer odrzucił login lub hasło.\n'
                'Dla Gmaila potrzebne jest „hasło aplikacji” (Konto Google → Bezpieczeństwo → '
                'Weryfikacja dwuetapowa → Hasła aplikacji), a nie zwykłe hasło do konta.')
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return 'Serwer odrzucił adres odbiorcy. Sprawdź pole „Odbiorca”.'
    if isinstance(exc, (smtplib.SMTPConnectError, ConnectionError, TimeoutError, OSError)) \
            and not isinstance(exc, smtplib.SMTPException):
        return (f'Brak połączenia z serwerem poczty ({exc}).\n'
                'Sprawdź internet, adres serwera, port i rodzaj szyfrowania.')
    return f'{type(exc).__name__}: {exc}'
