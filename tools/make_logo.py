"""Gera o logo do Roots Auto Doctor: rad/assets/logo.svg, logo.png, logo_64.png, icon.ico.

Conceito: um mostrador de painel VAG (anel com escala azul iluminada), atravessado
por uma linha de pulso (ECG, o "doctor") cujo pico faz de ponteiro vermelho;
do ponto mais baixo do pulso nascem raízes em forma de pistas de circuito (o "roots").
Correr:  python tools/make_logo.py
"""
import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "rad", "assets")

NAVY_IN = (27, 42, 77)
NAVY_OUT = (12, 19, 36)
BLUE = (79, 141, 255)
RED = (232, 52, 58)
WHITE = (234, 240, 255)

C = 128
R_RING = 112
PULSE = [(50, 136), (84, 136), (100, 104), (122, 172), (144, 60), (162, 136), (206, 136)]
ROOT_ORIGIN = (122, 172)
ROOTS = [
    [(122, 172), (122, 214)],
    [(122, 180), (104, 198), (88, 198)],
    [(122, 180), (140, 198), (156, 198)],
]
PADS = [(122, 220), (82, 198), (162, 198)]


def ticks():
    """Escala de 240° (de 210° a -30°), 13 traços, os pares maiores."""
    out = []
    for i in range(13):
        ang = math.radians(210 - i * 20)
        major = i % 2 == 0
        r1, r2 = 98, (82 if major else 88)
        out.append(((C + r1 * math.cos(ang), C - r1 * math.sin(ang)),
                    (C + r2 * math.cos(ang), C - r2 * math.sin(ang)), major))
    return out


def svg():
    hexc = lambda c: "#%02X%02X%02X" % c
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">',
        '<defs><radialGradient id="g" cx="50%" cy="42%" r="60%">'
        f'<stop offset="0" stop-color="{hexc(NAVY_IN)}"/><stop offset="1" stop-color="{hexc(NAVY_OUT)}"/>'
        '</radialGradient></defs>',
        f'<circle cx="{C}" cy="{C}" r="{R_RING}" fill="url(#g)" stroke="{hexc(BLUE)}" stroke-width="9"/>',
    ]
    for (x1, y1), (x2, y2), major in ticks():
        w = 6 if major else 3.5
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{hexc(BLUE)}" stroke-width="{w}" stroke-linecap="round"/>')
    for r in ROOTS:
        pts = " ".join(f"{x},{y}" for x, y in r)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{hexc(BLUE)}" stroke-width="7" '
                     'stroke-linecap="round" stroke-linejoin="round"/>')
    for x, y in PADS:
        parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{hexc(NAVY_OUT)}" stroke="{hexc(BLUE)}" stroke-width="5"/>')
    pts = " ".join(f"{x},{y}" for x, y in PULSE)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{hexc(RED)}" stroke-width="12" '
                 'stroke-linecap="round" stroke-linejoin="round"/>')
    parts.append(f'<circle cx="{PULSE[4][0]}" cy="{PULSE[4][1]}" r="9" fill="{hexc(WHITE)}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def render(size):
    S = 4                                    # super-amostragem
    W = 256 * S
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = lambda p: (p[0] * S, p[1] * S)
    # fundo com gradiente radial
    steps = 60
    for i in range(steps, 0, -1):
        t = i / steps
        col = tuple(int(NAVY_IN[j] + (NAVY_OUT[j] - NAVY_IN[j]) * t) for j in range(3))
        r = R_RING * t * S
        cy = (C - 12 * (1 - t)) * S
        d.ellipse([C * S - r, cy - r, C * S + r, cy + r], fill=col)
    rr = R_RING * S
    d.ellipse([C * S - rr, C * S - rr, C * S + rr, C * S + rr], outline=BLUE, width=9 * S)

    def line(pts, col, w):
        pts = [k(p) for p in pts]
        d.line(pts, fill=col, width=int(w * S), joint="curve")
        for p in (pts[0], pts[-1]):
            rad = w * S / 2
            d.ellipse([p[0] - rad, p[1] - rad, p[0] + rad, p[1] + rad], fill=col)

    for p1, p2, major in ticks():
        line([p1, p2], BLUE, 6 if major else 3.5)
    for r in ROOTS:
        line(r, BLUE, 7)
    for x, y in PADS:
        r1, r2 = 8.5 * S, 3.8 * S
        d.ellipse([x * S - r1, y * S - r1, x * S + r1, y * S + r1], fill=BLUE)
        d.ellipse([x * S - r2, y * S - r2, x * S + r2, y * S + r2], fill=NAVY_OUT)
    line(PULSE, RED, 12)
    x, y = PULSE[4]
    d.ellipse([(x - 9) * S, (y - 9) * S, (x + 9) * S, (y + 9) * S], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "logo.svg"), "w") as f:
        f.write(svg())
    big = render(512)
    big.save(os.path.join(OUT, "logo.png"))
    render(64).save(os.path.join(OUT, "logo_64.png"))
    big.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("logo gerado em", OUT)


if __name__ == "__main__":
    main()
