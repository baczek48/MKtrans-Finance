"""PDF reports of costs: one month (detailed) or a whole year (simplified table)."""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import database as db

PRIMARY_DARK = colors.HexColor('#1e3a8a')
PRIMARY = colors.HexColor('#1a56db')
LABEL = colors.HexColor('#475569')
MUTED = colors.HexColor('#94a3b8')
GRID = colors.HexColor('#e2e8f0')
ZEBRA = colors.HexColor('#f8fafc')
HEAD_BG = colors.HexColor('#e2e8f0')
TOTAL_BG = colors.HexColor('#dbeafe')
GREEN = colors.HexColor('#059669')
RED = colors.HexColor('#dc2626')
AMBER_BG = colors.HexColor('#fef3c7')
AMBER_FG = colors.HexColor('#92400e')

MONTHS_PL = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
             'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień']

_FONT, _FONT_BOLD = 'Helvetica', 'Helvetica-Bold'


def _register_fonts():
    """Arial from Windows (Polish characters); Helvetica only as a last resort."""
    global _FONT, _FONT_BOLD
    if _FONT == 'PL':
        return
    fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    for regular, bold in (('arial.ttf', 'arialbd.ttf'), ('segoeui.ttf', 'segoeuib.ttf'),
                          ('calibri.ttf', 'calibrib.ttf')):
        r, b = os.path.join(fonts_dir, regular), os.path.join(fonts_dir, bold)
        if os.path.exists(r) and os.path.exists(b):
            pdfmetrics.registerFont(TTFont('PL', r))
            pdfmetrics.registerFont(TTFont('PL-Bold', b))
            _FONT, _FONT_BOLD = 'PL', 'PL-Bold'
            return


def fmt(val, unit=' PLN'):
    parts = f"{val or 0:,.2f}".replace(',', '.')
    idx = parts.rfind('.')
    return parts[:idx] + ',' + parts[idx + 1:] + unit


def fmt_liters(val):
    return fmt(val, '')[:-1]  # one decimal: 1.260,0


def _label(text):
    """'KSIĘGOWA' -> 'Księgowa', but short acronyms (ZUS, PIT4, ADR, TACHO) stay as they are."""
    if text.isupper() and len(text) > 5:
        return text.capitalize()
    return text


def _styles():
    return {
        'title': ParagraphStyle('t', fontName=_FONT_BOLD, fontSize=18, leading=22, textColor=PRIMARY_DARK),
        'sub': ParagraphStyle('s', fontName=_FONT, fontSize=9, leading=12, textColor=LABEL),
        'h2': ParagraphStyle('h2', fontName=_FONT_BOLD, fontSize=11.5, leading=15, textColor=PRIMARY_DARK,
                             spaceBefore=10, spaceAfter=4),
        'cell': ParagraphStyle('c', fontName=_FONT, fontSize=8.5, leading=10.5, textColor=colors.black),
        'note': ParagraphStyle('n', fontName=_FONT, fontSize=8, leading=10, textColor=MUTED),
        'right': ParagraphStyle('r', fontName=_FONT, fontSize=8.5, leading=10.5, alignment=TA_RIGHT),
    }


def _header(story, st, logo_path, title, subtitle):
    title_block = [Paragraph(title, st['title']), Spacer(1, 2), Paragraph(subtitle, st['sub'])]
    if logo_path and os.path.exists(logo_path):
        t = Table([[Image(logo_path, 14 * mm, 14 * mm), title_block]], colWidths=[18 * mm, None])
    else:
        t = Table([[title_block]])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('LINEBELOW', (0, 0), (-1, -1), 1.5, PRIMARY)]))
    story.append(t)
    story.append(Spacer(1, 8))


def _table(rows, col_widths, num_cols=(), total_row=False, header=True):
    """Generic zebra table. num_cols: right-aligned column indexes."""
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('FONTNAME', (0, 0), (-1, -1), _FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, GRID),
    ]
    if header:
        style += [('BACKGROUND', (0, 0), (-1, 0), HEAD_BG),
                  ('FONTNAME', (0, 0), (-1, 0), _FONT_BOLD),
                  ('TEXTCOLOR', (0, 0), (-1, 0), PRIMARY_DARK),
                  ('FONTSIZE', (0, 0), (-1, 0), 8)]
    first = 1 if header else 0
    last_body = len(rows) - (2 if total_row else 1)
    for r in range(first, last_body + 1):
        if (r - first) % 2 == 1:
            style.append(('BACKGROUND', (0, r), (-1, r), ZEBRA))
    for c in num_cols:
        style.append(('ALIGN', (c, 0), (c, -1), 'RIGHT'))
    if total_row:
        style += [('BACKGROUND', (0, -1), (-1, -1), TOTAL_BG),
                  ('FONTNAME', (0, -1), (-1, -1), _FONT_BOLD),
                  ('TEXTCOLOR', (0, -1), (-1, -1), PRIMARY_DARK),
                  ('LINEABOVE', (0, -1), (-1, -1), 0.8, PRIMARY)]
    t.setStyle(TableStyle(style))
    return t


def _kpis(invoices, costs, result, width, extra=None):
    """Three headline boxes: revenue / costs / result."""
    items = [('Przychody (faktury)', fmt(invoices), GREEN),
             ('Koszty razem', fmt(costs), RED),
             ('Wynik', fmt(result), GREEN if result >= 0 else RED)]
    if extra:
        items.insert(2, extra)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    t = Table([labels, values], colWidths=[width / len(items)] * len(items))
    style = [('FONTNAME', (0, 0), (-1, 0), _FONT), ('FONTSIZE', (0, 0), (-1, 0), 8.5),
             ('TEXTCOLOR', (0, 0), (-1, 0), LABEL),
             ('FONTNAME', (0, 1), (-1, 1), _FONT_BOLD), ('FONTSIZE', (0, 1), (-1, 1), 14),
             ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
             ('BOX', (0, 0), (-1, -1), 0.6, GRID), ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.white),
             ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 1), (-1, 1), 9),
             ('LEFTPADDING', (0, 0), (-1, -1), 10)]
    for i, item in enumerate(items):
        style.append(('TEXTCOLOR', (i, 1), (i, 1), item[2]))
    t.setStyle(TableStyle(style))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 7.5)
    canvas.setFillColor(MUTED)
    w, _ = doc.pagesize
    canvas.drawString(doc.leftMargin, 10 * mm,
                      f'MKtrans Finance · wygenerowano {datetime.now():%Y-%m-%d %H:%M}')
    canvas.drawRightString(w - doc.rightMargin, 10 * mm, f'Strona {doc.page}')
    canvas.restoreState()


def _doc(path, pagesize, title):
    return SimpleDocTemplate(path, pagesize=pagesize, title=title, author='MKtrans Finance',
                             leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=16 * mm)


# ============================================================
# MONTH (detailed)
# ============================================================

def build_month_report(path, month_id, std_params, logo_path=None):
    """std_params: [(key, label), ...] in display order."""
    _register_fonts()
    st = _styles()
    year, month = int(month_id[:4]), int(month_id[5:7])
    label = f'{MONTHS_PL[month - 1]} {year}'
    accepted = db.is_month_accepted(month_id)

    doc = _doc(path, A4, f'Raport kosztów - {label}')
    width = doc.width
    story = []
    _header(story, st, logo_path, f'Raport kosztów — {label}',
            'Miesiąc zaakceptowany' if accepted else
            '<font color="#92400e"><b>Miesiąc niezaakceptowany — dane robocze, mogą się jeszcze zmienić</b></font>')

    s = db.get_month_summary(month_id)
    story.append(_kpis(s['invoices'], s['total_costs'], s['result'], width))

    # Cost structure
    story.append(Paragraph('Struktura kosztów', st['h2']))
    rows = [['Kategoria', 'Kwota', 'Udział']]
    total = s['total_costs'] or 0
    for name, val in (('Koszty standardowe', s['standard']), ('Paliwo (netto)', s['fuel_netto']),
                      ('Naprawy', s['repairs']), ('Koszty inne', s['other'])):
        share = f'{val / total * 100:.1f}%'.replace('.', ',') if total else '-'
        rows.append([name, fmt(val), share])
    rows.append(['RAZEM KOSZTY', fmt(total), '100%' if total else '-'])
    story.append(_table(rows, [width * 0.5, width * 0.3, width * 0.2], num_cols=(1, 2), total_row=True))

    # Standard costs
    costs = db.get_standard_costs(month_id)
    rows = [['Koszt standardowy', 'Kwota']]
    for key, lbl in std_params:
        if costs.get(key):
            rows.append([_label(lbl), fmt(costs[key])])
    if len(rows) > 1:
        rows.append(['Razem', fmt(s['standard'])])
        story.append(KeepTogether([Paragraph('Koszty standardowe', st['h2']),
                                   _table(rows, [width * 0.7, width * 0.3], num_cols=(1,), total_row=True)]))

    # Fuel
    fuel = db.get_fuel(month_id)
    if fuel:
        rows = [['Nr rej.', 'Data', 'Litry', 'Licznik (km)', 'Netto', 'Brutto']]
        for f in fuel:
            rows.append([f['plate'] or '-', f['date'] or '', fmt_liters(f['liters']),
                         str(f['odometer'] or '') or '-', fmt(f['netto']), fmt(f['brutto'])])
        rows.append(['Razem', '', fmt_liters(sum(f['liters'] or 0 for f in fuel)), '',
                     fmt(s['fuel_netto']), fmt(sum(f['brutto'] or 0 for f in fuel))])
        w = [0.16, 0.16, 0.12, 0.16, 0.2, 0.2]
        story.append(KeepTogether([Paragraph('Paliwo', st['h2']),
                                   _table(rows, [width * x for x in w], num_cols=(2, 3, 4, 5), total_row=True)]))

    # Repairs
    repairs = db.get_repairs(month_id)
    if repairs:
        rows = [['Nr rej.', 'Data', 'Co zrobione', 'Licznik', 'Kwota']]
        for r in repairs:
            rows.append([r['plate'] or '-', r['date'] or '', Paragraph(r['description'] or '-', st['cell']),
                         str(r['odometer'] or '') or '-', fmt(r['amount'])])
        rows.append(['Razem', '', '', '', fmt(s['repairs'])])
        w = [0.14, 0.14, 0.42, 0.12, 0.18]
        story.append(KeepTogether([Paragraph('Naprawy', st['h2']),
                                   _table(rows, [width * x for x in w], num_cols=(3, 4), total_row=True)]))

    # Other costs
    other = db.get_other_costs(month_id)
    if other:
        rows = [['Koszt', 'Kwota']] + [[Paragraph(o['description'] or '-', st['cell']), fmt(o['amount'])]
                                       for o in other]
        rows.append(['Razem', fmt(s['other'])])
        story.append(KeepTogether([Paragraph('Koszty inne', st['h2']),
                                   _table(rows, [width * 0.7, width * 0.3], num_cols=(1,), total_row=True)]))

    # Invoices
    invoices = db.get_invoices(month_id)
    if invoices:
        rows = [['Data', 'Nr faktury', 'Status', 'Kwota']]
        for i in invoices:
            rows.append([i['date'] or '', i['number'] or '-', 'zapłacona' if i['paid'] else 'niezapłacona',
                         fmt(i['amount'])])
        rows.append(['Razem', '', '', fmt(s['invoices'])])
        story.append(KeepTogether([Paragraph('Faktury (przychody)', st['h2']),
                                   _table(rows, [width * x for x in (0.18, 0.37, 0.2, 0.25)], num_cols=(3,),
                                          total_row=True)]))

    # Leaves (days only)
    if s['urlop_days'] or s['chorobowe_days']:
        rows = [['Osoba', 'Urlop (dni)', 'Chorobowe (dni)']]
        people = sorted(set(s['urlop_by_person']) | set(s['chorobowe_by_person']))
        for p in people:
            rows.append([p, str(s['urlop_by_person'].get(p, 0) or '-'),
                         str(s['chorobowe_by_person'].get(p, 0) or '-')])
        rows.append(['Razem', str(s['urlop_days']), str(s['chorobowe_days'])])
        story.append(KeepTogether([Paragraph('Urlopy i chorobowe', st['h2']),
                                   _table(rows, [width * 0.5, width * 0.25, width * 0.25],
                                          num_cols=(1, 2), total_row=True)]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path


# ============================================================
# YEAR (simplified table)
# ============================================================

def build_year_report(path, year, logo_path=None):
    """Months as rows, cost groups as columns. Only accepted months are counted
    (same rule as the statistics window)."""
    _register_fonts()
    st = _styles()
    doc = _doc(path, landscape(A4), f'Raport kosztów - {year}')
    width = doc.width
    story = []
    _header(story, st, logo_path, f'Raport kosztów — rok {year}',
            'Zestawienie miesięczne · uwzględnione są tylko zaakceptowane miesiące')

    with_data = set(db.get_months_with_data())
    head = ['Miesiąc', 'Koszty stand.', 'Paliwo (netto)', 'Naprawy', 'Koszty inne',
            'Koszty razem', 'Faktury', 'Wynik']
    keys = ['standard', 'fuel_netto', 'repairs', 'other', 'total_costs', 'invoices', 'result']
    rows = [head]
    totals = dict.fromkeys(keys, 0)
    skipped = []
    pending_rows = []
    for m in range(1, 13):
        month_id = f'{year}-{m:02d}'
        if not db.is_month_accepted(month_id):
            if month_id in with_data and db.get_month_summary(month_id)['total_costs'] + \
                    db.get_month_summary(month_id)['invoices'] > 0:
                skipped.append(MONTHS_PL[m - 1])
                pending_rows.append(len(rows))
                rows.append([MONTHS_PL[m - 1], 'niezaakceptowany', '', '', '', '', '', ''])
            else:
                rows.append([MONTHS_PL[m - 1]] + ['-'] * len(keys))
            continue
        s = db.get_month_summary(month_id)
        for k in keys:
            totals[k] += s[k]
        rows.append([MONTHS_PL[m - 1]] + [fmt(s[k], '') if s[k] else '-' for k in keys])
    rows.append(['SUMA'] + [fmt(totals[k], '') for k in keys])

    cw = [width * 0.13] + [width * 0.87 / len(keys)] * len(keys)
    t = _table(rows, cw, num_cols=range(1, len(head)), total_row=True)
    extra = [('BACKGROUND', (5, 1), (5, -2), colors.HexColor('#fef2f2')),
             ('FONTNAME', (5, 1), (5, -1), _FONT_BOLD), ('FONTNAME', (7, 1), (7, -1), _FONT_BOLD)]
    for r in range(1, len(rows)):
        val = totals['result'] if r == len(rows) - 1 else None
        if val is None:
            cell = rows[r][7]
            if cell in ('-', ''):
                continue
            val = -1 if cell.startswith('-') else 1
        extra.append(('TEXTCOLOR', (7, r), (7, r), GREEN if val >= 0 else RED))
    for r in pending_rows:
        extra += [('SPAN', (1, r), (-1, r)), ('ALIGN', (1, r), (-1, r), 'CENTER'),
                  ('BACKGROUND', (0, r), (-1, r), AMBER_BG), ('TEXTCOLOR', (0, r), (-1, r), AMBER_FG)]
    t.setStyle(TableStyle(extra))
    story.append(Paragraph('Kwoty w PLN', st['note']))
    story.append(Spacer(1, 3))
    story.append(t)

    # Annual costs + yearly result
    annual = db.get_annual_costs(year)
    annual_total = sum(a['amount'] or 0 for a in annual)
    yearly_costs = totals['total_costs'] + annual_total
    yearly_result = totals['invoices'] - yearly_costs

    left = [['Koszty roczne', 'Kwota']]
    type_names = {'ubezpieczenie': 'Ubezpieczenie', 'podatek_drogowy': 'Podatek drogowy'}
    for a in annual:
        desc = a['description'] or ''
        left.append([f"{type_names.get(a['type'], a['type'])}{' — ' + desc if desc else ''}", fmt(a['amount'])])
    if len(left) == 1:
        left.append(['Brak kosztów rocznych', '-'])
    left.append(['Razem', fmt(annual_total)])

    right = [['Podsumowanie roku', ''],
             ['Przychody (faktury)', fmt(totals['invoices'])],
             ['Koszty miesięczne', fmt(totals['total_costs'])],
             ['Koszty roczne', fmt(annual_total)],
             ['Koszty łącznie', fmt(yearly_costs)],
             ['WYNIK ROCZNY', fmt(yearly_result)]]
    lt = _table(left, [width * 0.3, width * 0.15], num_cols=(1,), total_row=True)
    rt = _table(right, [width * 0.3, width * 0.15], num_cols=(1,), total_row=True)
    rt.setStyle(TableStyle([('TEXTCOLOR', (1, -1), (1, -1), GREEN if yearly_result >= 0 else RED),
                            ('FONTSIZE', (0, -1), (-1, -1), 10)]))
    pair = Table([[lt, rt]], colWidths=[width * 0.5, width * 0.5])
    pair.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story.append(Spacer(1, 10))
    story.append(KeepTogether(pair))

    if skipped:
        story.append(Spacer(1, 6))
        story.append(Paragraph('Pominięto niezaakceptowane miesiące z danymi: ' + ', '.join(skipped) +
                               '. Zaakceptuj je w aplikacji, aby trafiły do zestawienia.', st['note']))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
