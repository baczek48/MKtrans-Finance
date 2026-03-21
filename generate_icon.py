"""Generate MKtrans Finance logo and icon."""
from PIL import Image, ImageDraw, ImageFont
import os

DIR = os.path.dirname(os.path.abspath(__file__))


def create_logo(size=256):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background - rounded rectangle (dark blue)
    pad = int(size * 0.04)
    radius = int(size * 0.15)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad],
                           radius=radius, fill='#1e3a8a')

    # Inner accent stripe (lighter blue band across middle-bottom)
    stripe_y = int(size * 0.55)
    stripe_h = int(size * 0.12)
    draw.rounded_rectangle([pad, stripe_y, size - pad, stripe_y + stripe_h],
                           radius=0, fill='#2563eb')

    # Road/highway lines (white dashes in the stripe)
    dash_w = int(size * 0.08)
    dash_h = int(size * 0.025)
    dash_y = stripe_y + stripe_h // 2 - dash_h // 2
    gap = int(size * 0.05)
    x = int(size * 0.15)
    while x + dash_w < size - pad:
        draw.rounded_rectangle([x, dash_y, x + dash_w, dash_y + dash_h],
                               radius=dash_h // 2, fill='#ffffff')
        x += dash_w + gap

    # Truck silhouette (simplified) above the stripe
    truck_color = '#60a5fa'
    # Truck body
    bx1 = int(size * 0.15)
    by1 = int(size * 0.32)
    bx2 = int(size * 0.65)
    by2 = stripe_y - int(size * 0.02)
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=int(size * 0.03), fill=truck_color)

    # Truck cab
    cx1 = bx2 - int(size * 0.02)
    cy1 = int(size * 0.38)
    cx2 = int(size * 0.82)
    cy2 = by2
    draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=int(size * 0.03), fill=truck_color)

    # Cab window
    wx1 = cx1 + int(size * 0.05)
    wy1 = cy1 + int(size * 0.03)
    wx2 = cx2 - int(size * 0.04)
    wy2 = cy1 + int(size * 0.10)
    draw.rounded_rectangle([wx1, wy1, wx2, wy2], radius=int(size * 0.02), fill='#1e3a8a')

    # Wheels
    wheel_r = int(size * 0.045)
    wheel_y = stripe_y + stripe_h // 2
    for wx in [int(size * 0.28), int(size * 0.42), int(size * 0.72)]:
        draw.ellipse([wx - wheel_r, wheel_y - wheel_r, wx + wheel_r, wheel_y + wheel_r],
                     fill='#1e3a8a', outline='#94a3b8', width=2)
        inner_r = wheel_r // 2
        draw.ellipse([wx - inner_r, wheel_y - inner_r, wx + inner_r, wheel_y + inner_r],
                     fill='#94a3b8')

    # "MK" text (large, top area)
    try:
        font_mk = ImageFont.truetype("segoeuib.ttf", int(size * 0.18))
    except (OSError, IOError):
        try:
            font_mk = ImageFont.truetype("arialbd.ttf", int(size * 0.18))
        except (OSError, IOError):
            font_mk = ImageFont.load_default()

    mk_x = int(size * 0.50)
    mk_y = int(size * 0.08)
    draw.text((mk_x, mk_y), "MK", fill='#ffffff', font=font_mk, anchor='mt')

    # "trans" text (gold, below MK)
    try:
        font_trans = ImageFont.truetype("segoeuib.ttf", int(size * 0.09))
    except (OSError, IOError):
        try:
            font_trans = ImageFont.truetype("arialbd.ttf", int(size * 0.09))
        except (OSError, IOError):
            font_trans = ImageFont.load_default()

    draw.text((mk_x, mk_y + int(size * 0.18)), "trans", fill='#fbbf24', font=font_trans, anchor='mt')

    # "FINANCE" text (bottom area)
    try:
        font_fin = ImageFont.truetype("segoeuib.ttf", int(size * 0.09))
    except (OSError, IOError):
        try:
            font_fin = ImageFont.truetype("arialbd.ttf", int(size * 0.09))
        except (OSError, IOError):
            font_fin = ImageFont.load_default()

    fin_y = int(size * 0.76)
    draw.text((size // 2, fin_y), "FINANCE", fill='#e2e8f0', font=font_fin, anchor='mt')

    # Coin/money symbol (small, bottom-right corner accent)
    coin_x = int(size * 0.80)
    coin_y = int(size * 0.82)
    coin_r = int(size * 0.07)
    draw.ellipse([coin_x - coin_r, coin_y - coin_r, coin_x + coin_r, coin_y + coin_r],
                 fill='#fbbf24', outline='#f59e0b', width=2)
    try:
        font_pln = ImageFont.truetype("segoeuib.ttf", int(size * 0.07))
    except (OSError, IOError):
        font_pln = ImageFont.load_default()
    draw.text((coin_x, coin_y), "zł", fill='#1e3a8a', font=font_pln, anchor='mm')

    return img


def main():
    # Generate at high resolution and scale down for sharp results
    master = create_logo(512)

    logo = master.resize((256, 256), Image.LANCZOS)
    logo.save(os.path.join(DIR, 'logo.png'))
    print('Saved logo.png (256x256)')

    # Generate .ico — all sizes scaled from 512px master
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [master.resize((s, s), Image.LANCZOS) for s in sizes]

    ico_path = os.path.join(DIR, 'icon.ico')
    icons[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes],
                  append_images=icons[1:])
    print(f'Saved icon.ico ({len(sizes)} sizes)')

    # Header logo (smaller, for app header bar)
    header = master.resize((48, 48), Image.LANCZOS)
    header.save(os.path.join(DIR, 'logo_small.png'))
    print('Saved logo_small.png (48x48)')


if __name__ == '__main__':
    main()
