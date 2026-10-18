"""Gera o logo do Roots Auto Doctor (v2).

Conceito: o mostrador de um conta-rotações VAG — escala azul iluminada com a zona
vermelha no fim — atravessado por um electrocardiograma (o "doctor"). O pico do ECG
faz de ponteiro; do vale mais fundo nascem raízes que acabam em pads de circuito
(o "roots": a ligação à electrónica do carro).

Saídas em rad/assets: logo.svg, logo.png (512), logo_64.png, icon.ico (com uma
variante simplificada para 16–32 px, onde os detalhes finos não se vêem).
Correr:  python tools/make_logo.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "rad", "assets")

NAVY_IN = (30, 48, 92)
NAVY_OUT = (10, 16, 32)
BLUE = (79, 141, 255)
BLUE_DIM = (42, 74, 140)
RED = (232, 52, 58)
WHITE = (240, 245, 255)

C = 128
R_RING = 114
R_INNER = 101

# ECG: onda P, complexo QRS (R = ponteiro, S = origem das raízes), onda T
PULSE = [(54, 138), (70, 138), (78, 126), (86, 138), (98, 138), (106, 148),
         (118, 50), (128, 170), (138, 138), (150, 138), (160, 122), (172, 138), (202, 138)]
TIP = (118, 50)
ROOTS = [
    [(128, 170), (128, 206)],
    [(128, 180), (106, 202), (92, 202)],
    [(128, 180), (150, 202), (164, 202)],
]
PADS = [(128, 213), (85, 202), (171, 202)]


def ticks():
    """Escala de 240° com 13 traços; os 3 últimos formam a zona vermelha."""
    out = []
    for i in range(13):
        ang = math.radians(210 - i * 20)
        major = i % 2 == 0
        r1, r2 = 94, (78 if major else 85)
        col = RED if i >= 10 else BLUE
        out.append(((C + r1 * math.cos(ang), C - r1 * math.sin(ang)),
                    (C + r2 * math.cos(ang), C - r2 * math.sin(ang)), major, col))
    return out


def hexc(c):
    return "#%02X%02X%02X" % c


def svg():
    p = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">',
        '<defs>'
        '<radialGradient id="bg" cx="50%" cy="40%" r="62%">'
        f'<stop offset="0" stop-color="{hexc(NAVY_IN)}"/><stop offset="1" stop-color="{hexc(NAVY_OUT)}"/></radialGradient>'
        '<linearGradient id="gl" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.10"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
        '</defs>',
        f'<circle cx="{C}" cy="{C}" r="{R_RING}" fill="url(#bg)"/>',
        f'<circle cx="{C}" cy="{C}" r="{R_RING}" fill="none" stroke="{hexc(BLUE)}" stroke-width="7"/>',
        f'<circle cx="{C}" cy="{C}" r="{R_INNER}" fill="none" stroke="{hexc(BLUE_DIM)}" stroke-width="1.5"/>',
    ]
    for (x1, y1), (x2, y2), major, col in ticks():
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{hexc(col)}" '
                 f'stroke-width="{5 if major else 3}" stroke-linecap="round"/>')
    for r in ROOTS:
        pts = " ".join(f"{x},{y}" for x, y in r)
        p.append(f'<polyline points="{pts}" fill="none" stroke="{hexc(BLUE)}" stroke-width="6" '
                 'stroke-linecap="round" stroke-linejoin="round"/>')
    for x, y in PADS:
        p.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{hexc(NAVY_OUT)}" stroke="{hexc(BLUE)}" stroke-width="4.5"/>')
    pts = " ".join(f"{x},{y}" for x, y in PULSE)
    p.append(f'<polyline points="{pts}" fill="none" stroke="{hexc(RED)}" stroke-width="11" '
             'stroke-linecap="round" stroke-linejoin="round"/>')
    p.append(f'<circle cx="{TIP[0]}" cy="{TIP[1]}" r="8" fill="{hexc(WHITE)}"/>')
    p.append("</svg>")
    return "\n".join(p)


class Canvas:
    S = 4

    def __init__(self):
        self.W = 256 * self.S
        self.img = Image.new("RGBA", (self.W, self.W), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def k(self, p):
        return (p[0] * self.S, p[1] * self.S)

    def circle(self, c, r, fill=None, outline=None, width=0):
        S = self.S
        self.d.ellipse([c[0] * S - r * S, c[1] * S - r * S, c[0] * S + r * S, c[1] * S + r * S],
                       fill=fill, outline=outline, width=int(width * S))

    def line(self, pts, col, w):
        pts = [self.k(p) for p in pts]
        self.d.line(pts, fill=col, width=int(w * self.S), joint="curve")
        for p in pts:                                    # pontas e juntas redondas
            r = w * self.S / 2
            self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    def background(self, glare=True):
        steps = 70
        for i in range(steps, 0, -1):
            t = i / steps
            col = tuple(int(NAVY_IN[j] + (NAVY_OUT[j] - NAVY_IN[j]) * t) for j in range(3))
            self.circle((C, C - 14 * (1 - t)), R_RING * t, fill=col)
        if not glare:
            return
        # reflexo de vidro do mostrador
        glare = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glare)
        S = self.S
        for i in range(30):
            a = int(26 * (1 - i / 30))
            gd.ellipse([(C - 86 + i) * S, (26 + i * 0.8) * S, (C + 86 - i) * S, (130 - i * 1.2) * S],
                       fill=(255, 255, 255, a // 3))
        mask = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(mask).ellipse([(C - R_INNER) * S, (C - R_INNER) * S, (C + R_INNER) * S, (C + R_INNER) * S], fill=255)
        glare.putalpha(Image.composite(glare.getchannel("A"), Image.new("L", self.img.size, 0), mask))
        self.img.alpha_composite(glare)


def render_full(size):
    cv = Canvas()
    cv.background(glare=False)
    cv.circle((C, C), R_RING, outline=BLUE, width=7)
    cv.circle((C, C), R_INNER, outline=BLUE_DIM, width=1.5)
    for p1, p2, major, col in ticks():
        cv.line([p1, p2], col, 5 if major else 3)
    for r in ROOTS:
        cv.line(r, BLUE, 6)
    for pad in PADS:
        cv.circle(pad, 8.25, fill=BLUE)
        cv.circle(pad, 3.75, fill=NAVY_OUT)
    # brilho suave por baixo do ECG
    glow = Image.new("RGBA", cv.img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line([cv.k(p) for p in PULSE], fill=RED + (150,), width=26 * cv.S, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(10 * cv.S))
    cv.img.alpha_composite(glow)
    cv.line(PULSE, RED, 11)
    cv.circle(TIP, 8, fill=WHITE)
    return cv.img.resize((size, size), Image.LANCZOS)


def render_small(size):
    """Para 16–32 px: só anel, zona vermelha e ECG grosso."""
    cv = Canvas()
    cv.circle((C, C), R_RING, fill=NAVY_OUT)
    cv.circle((C, C), R_RING - 2, outline=BLUE, width=20)
    simple = [(40, 140), (88, 140), (112, 44), (134, 186), (156, 140), (216, 140)]
    cv.line(simple, RED, 26)
    return cv.img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "logo.svg"), "w") as f:
        f.write(svg())
    big = render_full(512)
    big.save(os.path.join(OUT, "logo.png"))
    render_full(64).save(os.path.join(OUT, "logo_64.png"))
    frames = [render_small(s) for s in (16, 24, 32)] + [render_full(s) for s in (48, 64, 128, 256)]
    frames[-1].save(os.path.join(OUT, "icon.ico"), format="ICO",
                    sizes=[(f.width, f.height) for f in frames], append_images=frames[:-1])
    for s in (16, 32):
        render_small(s).save(os.path.join(OUT, f"logo_{s}.png"))
    print("logo gerado em", OUT)


if __name__ == "__main__":
    main()
