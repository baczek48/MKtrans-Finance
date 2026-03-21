"""Generate MKtrans Finance logo and icon."""
from PIL import Image, ImageDraw, ImageFont
import os

DIR = os.path.dirname(os.path.abspath(__file__))


def _get_font(size, bold=True):
    """Get best available font."""
    names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def create_icon(size=512):
    """Create a clean, bold icon that reads well at any size.
    Simple design: dark blue rounded square, big white 'MK', gold accent bar."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = int(size * 0.03)
    radius = int(size * 0.18)

    # Background — dark blue rounded rectangle
    draw.rounded_rectangle([pad, pad, size - pad, size - pad],
                           radius=radius, fill='#1e3a8a')

    # Gold accent bar at bottom
    bar_h = int(size * 0.08)
    bar_y = size - pad - int(size * 0.22)
    draw.rectangle([pad, bar_y, size - pad, bar_y + bar_h], fill='#fbbf24')

    # "MK" — large, bold, centered above the bar
    font_mk = _get_font(int(size * 0.38))
    cx = size // 2
    mk_y = int(size * 0.08)
    draw.text((cx, mk_y), "MK", fill='#ffffff', font=font_mk, anchor='mt')

    # "trans" — gold, smaller, just below MK
    font_trans = _get_font(int(size * 0.14))
    draw.text((cx, mk_y + int(size * 0.36)), "trans", fill='#fbbf24',
              font=font_trans, anchor='mt')

    # "zł" — white, bottom area below the bar
    font_zl = _get_font(int(size * 0.13))
    draw.text((cx, bar_y + bar_h + int(size * 0.02)), "FINANCE",
              fill='#93c5fd', font=_get_font(int(size * 0.10)), anchor='mt')

    return img


def create_logo(size=512):
    """Create detailed logo for larger display (app header, about screen)."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = int(size * 0.03)
    radius = int(size * 0.15)

    # Background
    draw.rounded_rectangle([pad, pad, size - pad, size - pad],
                           radius=radius, fill='#1e3a8a')

    # Accent stripe
    stripe_y = int(size * 0.55)
    stripe_h = int(size * 0.10)
    draw.rectangle([pad, stripe_y, size - pad, stripe_y + stripe_h], fill='#2563eb')

    # Road dashes
    dash_w = int(size * 0.07)
    dash_h = int(size * 0.02)
    dash_y = stripe_y + stripe_h // 2 - dash_h // 2
    x = int(size * 0.12)
    while x + dash_w < size - pad:
        draw.rounded_rectangle([x, dash_y, x + dash_w, dash_y + dash_h],
                               radius=dash_h // 2, fill='#ffffff')
        x += dash_w + int(size * 0.05)

    # Truck body
    truck_color = '#60a5fa'
    bx1, by1 = int(size * 0.13), int(size * 0.30)
    bx2, by2 = int(size * 0.62), stripe_y - int(size * 0.02)
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=int(size * 0.03), fill=truck_color)

    # Truck cab
    cx1, cy1 = bx2 - int(size * 0.02), int(size * 0.36)
    cx2, cy2 = int(size * 0.82), by2
    draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=int(size * 0.03), fill=truck_color)

    # Cab window
    draw.rounded_rectangle(
        [cx1 + int(size * 0.04), cy1 + int(size * 0.03),
         cx2 - int(size * 0.03), cy1 + int(size * 0.10)],
        radius=int(size * 0.02), fill='#1e3a8a')

    # Wheels
    wheel_r = int(size * 0.04)
    wheel_y = stripe_y + stripe_h // 2
    for wx in [int(size * 0.26), int(size * 0.42), int(size * 0.72)]:
        draw.ellipse([wx - wheel_r, wheel_y - wheel_r, wx + wheel_r, wheel_y + wheel_r],
                     fill='#1e3a8a', outline='#94a3b8', width=max(1, size // 128))
        ir = wheel_r // 2
        draw.ellipse([wx - ir, wheel_y - ir, wx + ir, wheel_y + ir], fill='#94a3b8')

    # "MK" text
    cx = size // 2
    font_mk = _get_font(int(size * 0.17))
    draw.text((cx, int(size * 0.08)), "MK", fill='#ffffff', font=font_mk, anchor='mt')

    # "trans"
    font_trans = _get_font(int(size * 0.09))
    draw.text((cx, int(size * 0.25)), "trans", fill='#fbbf24', font=font_trans, anchor='mt')

    # "FINANCE"
    font_fin = _get_font(int(size * 0.09))
    draw.text((cx, int(size * 0.74)), "FINANCE", fill='#e2e8f0', font=font_fin, anchor='mt')

    # Coin accent
    coin_x, coin_y = int(size * 0.80), int(size * 0.82)
    coin_r = int(size * 0.06)
    draw.ellipse([coin_x - coin_r, coin_y - coin_r, coin_x + coin_r, coin_y + coin_r],
                 fill='#fbbf24', outline='#f59e0b', width=max(1, size // 128))
    font_zl = _get_font(int(size * 0.06))
    draw.text((coin_x, coin_y), "zł", fill='#1e3a8a', font=font_zl, anchor='mm')

    return img


def main():
    # Icon — simple, bold design that looks good even at 16x16
    master_icon = create_icon(512)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [master_icon.resize((s, s), Image.LANCZOS) for s in sizes]

    ico_path = os.path.join(DIR, 'icon.ico')
    icons[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes],
                  append_images=icons[1:])
    print(f'Saved icon.ico ({len(sizes)} sizes)')

    # Logo — detailed version for app header
    master_logo = create_logo(512)

    logo = master_logo.resize((256, 256), Image.LANCZOS)
    logo.save(os.path.join(DIR, 'logo.png'))
    print('Saved logo.png (256x256)')

    header = master_logo.resize((48, 48), Image.LANCZOS)
    header.save(os.path.join(DIR, 'logo_small.png'))
    print('Saved logo_small.png (48x48)')


if __name__ == '__main__':
    main()
