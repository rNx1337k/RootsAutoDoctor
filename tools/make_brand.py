"""Gera a identidade visual do Roots Auto Doctor (v3): ícone, logo da aplicação e banner do README.

Conceito: o arco de um conta-rotações (azul → ciano, com a zona vermelha no fim) atravessado por um
electrocardiograma em néon — o pico do ECG faz de ponteiro. Fundo azul-noite em quadrado arredondado, legível
de 16 px (variante simplificada) a 512 px.

Saídas:
    rad/assets/logo.svg, logo.png (512), logo_64.png, logo_32.png, logo_16.png, icon.ico (16–256)
    docs/banner.png (1600×520, README)
Precisa do rsvg-convert (librsvg) e do Pillow. Correr:  python tools/make_brand.py
"""
import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "rad", "assets")
DOCS = os.path.join(ROOT, "docs")

def arc(cx, cy, r, a0, a1):
    """SVG arc path from angle a0 to a1 (degrees, 0 = right, clockwise positive since y goes down)."""
    x0, y0 = cx + r*math.cos(math.radians(a0)), cy + r*math.sin(math.radians(a0))
    x1, y1 = cx + r*math.cos(math.radians(a1)), cy + r*math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f}"

def mark(cx=256, cy=276, r=168, sw=36, simple=False):
    blue = arc(cx, cy, r, 135, 345)
    red = arc(cx, cy, r, 357, 405)
    pts = [(104,300),(174,300),(198,262),(220,300),(240,300),(268,134),(298,366),(322,300),(344,300),(364,274),(384,300),(408,300)]
    if simple:
        pts = [(104,300),(214,300),(262,130),(304,372),(338,300),(408,300)]
    poly = " ".join(f"{x},{y}" for x, y in pts)
    ticks = ""
    if not simple:
        for i in range(1, 6):
            a = 135 + i*35
            if a > 340: break
            r1, r2 = r - 46, r - 30
            x1, y1 = cx + r1*math.cos(math.radians(a)), cy + r1*math.sin(math.radians(a))
            x2, y2 = cx + r2*math.cos(math.radians(a)), cy + r2*math.sin(math.radians(a))
            ticks += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#7FA8FF" stroke-opacity="0.55" stroke-width="9" stroke-linecap="round"/>'
    return f'''
  <g filter="url(#softglow)">
    <path d="{blue}" fill="none" stroke="url(#gauge)" stroke-width="{sw}" stroke-linecap="round"/>
    <path d="{red}" fill="none" stroke="url(#redline)" stroke-width="{sw}" stroke-linecap="round"/>
  </g>
  {ticks}
  <polyline points="{poly}" fill="none" stroke="#FF2E4D" stroke-width="{30 if simple else 26}" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)" opacity="0.9"/>
  <polyline points="{poly}" fill="none" stroke="#FF4D63" stroke-width="{30 if simple else 24}" stroke-linecap="round" stroke-linejoin="round"/>
  <polyline points="{poly}" fill="none" stroke="#FFD5DC" stroke-width="{9 if simple else 6}" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>'''

DEFS = '''
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16285A"/><stop offset="0.55" stop-color="#0A1330"/><stop offset="1" stop-color="#05080F"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.42" r="0.55">
      <stop offset="0" stop-color="#2B6BFF" stop-opacity="0.35"/><stop offset="1" stop-color="#2B6BFF" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="gauge" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#2F5BFF"/><stop offset="0.6" stop-color="#3FA2FF"/><stop offset="1" stop-color="#22E0D2"/>
    </linearGradient>
    <linearGradient id="redline" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFB547"/><stop offset="0.45" stop-color="#FF6A3D"/><stop offset="1" stop-color="#FF2E4D"/>
    </linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.22"/><stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.04"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0.10"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter>
    <filter id="softglow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>'''

def icon(simple=False):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">{DEFS}
  <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#bg)"/>
  <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#halo)"/>
  <rect x="17.5" y="17.5" width="477" height="477" rx="110.5" fill="none" stroke="url(#rim)" stroke-width="3"/>
  {mark(simple=simple)}
</svg>'''



W, H = 1600, 520

def pill(x, y, text, w):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="23" fill="#FFFFFF" fill-opacity="0.06" '
            f'stroke="#7FB2FF" stroke-opacity="0.35" stroke-width="1.5"/>'
            f'<circle cx="{x+24}" cy="{y+23}" r="5" fill="#22E0D2"/>'
            f'<text x="{x+40}" y="{y+30.5}" font-family="Inter" font-weight="600" font-size="19" fill="#DCE6FF">{text}</text>')

def banner(sub, pills, out):
    big = arc(1530, 650, 400, 210, 335)
    big2 = arc(1530, 650, 330, 210, 335)
    ticks = ""
    for i in range(26):
        a = 212 + i*5
        r1, r2 = (282, 304) if i % 4 == 0 else (292, 304)
        x1, y1 = 1530 + r1*math.cos(math.radians(a)), 650 + r1*math.sin(math.radians(a))
        x2, y2 = 1530 + r2*math.cos(math.radians(a)), 650 + r2*math.sin(math.radians(a))
        col = "#FF4D63" if a > 310 else "#5B8CFF"
        ticks += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-opacity="0.45" stroke-width="{4 if i%4==0 else 2}" stroke-linecap="round"/>'
    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#FFFFFF" stroke-opacity="0.025"/>' for x in range(0, W, 40))
    grid += "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#FFFFFF" stroke-opacity="0.025"/>' for y in range(0, H, 40))
    ecg = "0,470 1330,470 1352,446 1372,470 1390,470 1418,372 1446,512 1468,470 1490,470 1508,452 1526,470 1600,470"
    px, s = 520, ""
    for text, w in pills:
        s += pill(px, 372, text, w)
        px += w + 14
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{DEFS}
  <defs>
    <linearGradient id="bbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0E1C44"/><stop offset="0.5" stop-color="#080F26"/><stop offset="1" stop-color="#04070F"/>
    </linearGradient>
    <radialGradient id="bhalo" cx="0.17" cy="0.45" r="0.45">
      <stop offset="0" stop-color="#2B6BFF" stop-opacity="0.30"/><stop offset="1" stop-color="#2B6BFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="rhalo" cx="0.83" cy="0.95" r="0.5">
      <stop offset="0" stop-color="#22E0D2" stop-opacity="0.16"/><stop offset="1" stop-color="#22E0D2" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="title" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#BFD6FF"/>
    </linearGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#FF2E4D" stop-opacity="0"/><stop offset="0.6" stop-color="#FF2E4D" stop-opacity="0.55"/><stop offset="0.88" stop-color="#FF2E4D" stop-opacity="1"/><stop offset="1" stop-color="#FF2E4D" stop-opacity="0.3"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bbg)"/>
  {grid}
  <rect width="{W}" height="{H}" fill="url(#bhalo)"/>
  <rect width="{W}" height="{H}" fill="url(#rhalo)"/>
  <path d="{big}" fill="none" stroke="#3F7BFF" stroke-opacity="0.18" stroke-width="3"/>
  <path d="{big2}" fill="none" stroke="#3F7BFF" stroke-opacity="0.10" stroke-width="2"/>
  {ticks}
  <polyline points="{ecg}" fill="none" stroke="#FF2E4D" stroke-width="10" stroke-linejoin="round" filter="url(#glow)" opacity="0.6"/>
  <polyline points="{ecg}" fill="none" stroke="url(#fade)" stroke-width="4" stroke-linejoin="round"/>
  <g transform="translate(70,84) scale(0.70)">
    <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#bg)"/>
    <rect x="16" y="16" width="480" height="480" rx="112" fill="url(#halo)"/>
    <rect x="17.5" y="17.5" width="477" height="477" rx="110.5" fill="none" stroke="url(#rim)" stroke-width="3"/>
    {mark()}
  </g>
  <text x="520" y="168" font-family="Inter" font-weight="700" font-size="20" letter-spacing="6" fill="#22E0D2">WORKSHOP DIAGNOSTIC SOFTWARE</text>
  <text x="514" y="262" font-family="Inter Display" font-weight="800" font-size="92" letter-spacing="-1.5" fill="url(#title)">Roots Auto Doctor</text>
  <text x="520" y="322" font-family="Inter" font-weight="400" font-size="27" fill="#A9B8DA">{sub}</text>
  {s}
</svg>'''
    open(out, "w").write(svg)



def render(svg_text, width, out):
    exe = shutil.which("rsvg-convert")
    if not exe:
        raise SystemExit("Falta o rsvg-convert (librsvg) para gerar as imagens.")
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as fh:
        fh.write(svg_text)
    try:
        subprocess.run([exe, "-w", str(width), fh.name, "-o", out], check=True)
    finally:
        os.remove(fh.name)


def main():
    full, simple = icon(), icon(simple=True)
    with open(os.path.join(ASSETS, "logo.svg"), "w", encoding="utf-8") as fh:
        fh.write(full)
    render(full, 512, os.path.join(ASSETS, "logo.png"))
    render(full, 64, os.path.join(ASSETS, "logo_64.png"))
    for size in (16, 32):
        render(simple, size, os.path.join(ASSETS, f"logo_{size}.png"))
    tmp = tempfile.mkdtemp()
    frames = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        path = os.path.join(tmp, f"{size}.png")
        render(simple if size <= 32 else full, size, path)
        frames.append(Image.open(path).convert("RGBA"))
    frames[-1].save(os.path.join(ASSETS, "icon.ico"), format="ICO", sizes=[f.size for f in frames],
                    append_images=frames[:-1])
    banner("Full diagnostics for the VW Group — and fault reading for every make.",
           [("Auto-Scan", 150), ("Live data", 142), ("Coding &amp; adaptation", 236), ("Customer reports", 210)],
           os.path.join(tmp, "banner.svg"))
    with open(os.path.join(tmp, "banner.svg"), encoding="utf-8") as fh:
        render(fh.read(), 1600, os.path.join(DOCS, "banner.png"))
    print("Identidade gerada em rad/assets e docs/banner.png")


if __name__ == "__main__":
    main()
