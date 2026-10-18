"""Gera docs/banner.png (cabeçalho do README no GitHub). Correr: python tools/make_banner.py"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, S = 1280, 400, 2
NAVY_A, NAVY_B = (24, 38, 74), (9, 14, 28)
BLUE, RED, WHITE, MUTED = (79, 141, 255), (232, 52, 58), (240, 245, 255), (124, 139, 173)
FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size * S)
    except OSError:
        return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W * S, H * S))
    d = ImageDraw.Draw(img)
    for y in range(H * S):                       # gradiente diagonal
        t = y / (H * S)
        d.line([(0, y), (W * S, y)], fill=tuple(int(NAVY_A[i] + (NAVY_B[i] - NAVY_A[i]) * t) for i in range(3)))
    # escala de mostrador gigante no lado direito
    cx, cy, r = 1010 * S, 330 * S, 250 * S
    for i in range(41):
        ang = math.radians(180 - i * 4.5)
        major = i % 5 == 0
        r1, r2 = r, r - (34 if major else 18) * S
        col = RED if i >= 34 else BLUE
        alpha = 0.55 if major else 0.3
        c = tuple(int(NAVY_B[k] * (1 - alpha) + col[k] * alpha) for k in range(3))
        d.line([(cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)),
                (cx + r2 * math.cos(ang), cy - r2 * math.sin(ang))], fill=c, width=(5 if major else 3) * S)
    # linha de ECG ao longo do banner, com brilho
    base = 318
    x0 = 900
    pts = [(0, base), (x0, base), (x0 + 20, base - 14), (x0 + 38, base), (x0 + 58, base), (x0 + 70, base + 16),
           (x0 + 96, base - 150), (x0 + 118, base + 34), (x0 + 136, base), (x0 + 166, base),
           (x0 + 184, base - 18), (x0 + 202, base), (W, base)]
    pts = [(x * S, y * S) for x, y in pts]
    glow = Image.new("RGB", img.size, (0, 0, 0))
    ImageDraw.Draw(glow).line(pts, fill=RED, width=16 * S, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(14 * S))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.55)
    d = ImageDraw.Draw(img)
    d.line(pts, fill=RED, width=5 * S, joint="curve")
    # logo
    logo = Image.open(os.path.join(ROOT, "rad", "assets", "logo.png")).resize((220 * S, 220 * S), Image.LANCZOS)
    img.paste(logo, (70 * S, 60 * S), logo)
    # texto
    d.text((330 * S, 92 * S), "Roots Auto Doctor", font=font("InterDisplay-Bold.otf", 64), fill=WHITE)
    d.text((333 * S, 178 * S), "Workshop diagnostics for VW, Audi, Seat and Škoda",
           font=font("InterDisplay-Medium.otf", 26), fill=(205, 216, 240))
    d.text((333 * S, 218 * S), "K-line  ·  KW1281  ·  KWP2000  ·  Windows",
           font=font("InterDisplay-Medium.otf", 20), fill=BLUE)
    img.resize((W, H), Image.LANCZOS).save(os.path.join(ROOT, "docs", "banner.png"), optimize=True)
    print("docs/banner.png")


if __name__ == "__main__":
    main()
