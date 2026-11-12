"""Gera a identidade visual do Roots Auto Doctor (v4): ícone, logótipo da aplicação e banner do README.

Conceito: o "R" de Roots cuja perna é o ponteiro de um conta-rotações a entrar na zona vermelha — a marca (R), o
carro (o mostrador) e o diagnóstico (a zona vermelha, onde está a avaria). Fundo azul-noite em quadrado
arredondado. Abaixo de 48 px usa-se uma variante com traços mais grossos, para se ler na barra de tarefas.

Saídas:
    rad/assets/logo.svg, logo.png (512), logo_64.png, logo_32.png, logo_16.png, icon.ico (16–256)
    docs/banner.png (1600×520, README)
Só precisa do PySide6 do programa (sem ferramentas externas). Correr:  .venv\\Scripts\\python.exe tools\\make_brand.py
"""
import math
import os
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "rad", "assets")
DOCS = os.path.join(ROOT, "docs")

DEFS = '''<defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#17295E"/><stop offset="0.55" stop-color="#0A1330"/><stop offset="1" stop-color="#04070E"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.40" r="0.6">
      <stop offset="0" stop-color="#2B6BFF" stop-opacity="0.30"/><stop offset="1" stop-color="#2B6BFF" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.24"/><stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.03"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0.10"/>
    </linearGradient>
    <linearGradient id="blue" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#2F5BFF"/><stop offset="0.55" stop-color="#3FA2FF"/><stop offset="1" stop-color="#22E0D2"/>
    </linearGradient>
    <linearGradient id="red" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFB547"/><stop offset="0.45" stop-color="#FF5A4A"/><stop offset="1" stop-color="#FF2E4D"/>
    </linearGradient>
    <linearGradient id="white" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C9DBFF"/>
    </linearGradient>
  </defs>'''

TILE = ('<rect x="16" y="16" width="480" height="480" rx="112" fill="url(#bg)"/>'
        '<rect x="16" y="16" width="480" height="480" rx="112" fill="url(#halo)"/>'
        '<rect x="17.5" y="17.5" width="477" height="477" rx="110.5" fill="none" stroke="url(#rim)" stroke-width="3"/>')


def pt(cx, cy, r, a):
    return cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))


def arc(cx, cy, r, a0, a1):
    """Arco SVG de a0 a a1 (graus; 0 = direita, sentido dos ponteiros porque o y cresce para baixo)."""
    x0, y0 = pt(cx, cy, r, a0)
    x1, y1 = pt(cx, cy, r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f}"


def mark(simple=False):
    """O desenho (sem o fundo): anel azul que acaba na zona vermelha, o R e o ponteiro (a perna do R).
    simple=True: traços mais grossos e sem o furo do eixo, para 16–32 px."""
    cx, cy, r = 256, 262, 176
    ring_w, r_w, n_w, hub = (46, 54, 42, 26) if simple else (34, 40, 30, 20)
    ring = arc(cx, cy, r, 135, 360 + 14)
    redz = arc(cx, cy, r, 360 + 26, 360 + 45)
    x, top, bottom, bw, bh = 198, 164, 356, 130, 112
    rr = bh / 2
    letter = f"M{x} {bottom} V{top} H{x + bw - rr} A{rr} {rr} 0 0 1 {x + bw - rr} {top + bh} H{x}"
    px, py = x + bw - rr - 6, top + bh
    nx, ny = pt(px, py, 150, 40)
    hole = "" if simple else f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{hub * 0.4:.1f}" fill="#0A1330"/>'
    return (f'<path d="{ring}" fill="none" stroke="url(#blue)" stroke-width="{ring_w}" stroke-linecap="round"/>'
            f'<path d="{redz}" fill="none" stroke="url(#red)" stroke-width="{ring_w}" stroke-linecap="round"/>'
            f'<path d="{letter}" fill="none" stroke="url(#white)" stroke-width="{r_w}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
            f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="url(#red)" stroke-width="{n_w}" '
            f'stroke-linecap="round"/>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{hub}" fill="#FF4D63"/>{hole}')


def svg(body, tile=True):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">{DEFS}'
            f'{TILE if tile else ""}{body}</svg>')


def svg_file(body):
    """O logo.svg para quem o abrir noutro programa: com o brilho em filtro SVG (o Qt não desenha filtros; as imagens
    PNG/ICO recebem o brilho em render())."""
    glow = ('<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
            '<feGaussianBlur in="SourceGraphic" stdDeviation="12" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">'
            f'{DEFS.replace("</defs>", glow + "</defs>")}{TILE}<g filter="url(#glow)">{body}</g></svg>\n')


def _raster(svg_text, size):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg_text.encode())).render(p, QRectF(0, 0, size, size))
    p.end()
    return img


def render(size, simple=None, glow=0.85):
    """Ícone final em size×size: fundo, brilho (o desenho desfocado, recortado ao quadrado) e o desenho nítido."""
    simple = size < 48 if simple is None else simple
    body = mark(simple)
    base = _raster(svg(""), size)
    sharp = _raster(svg(body, tile=False), size)
    small = max(1, size // 14)
    blur = sharp.scaled(small, small, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) \
                .scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    clip = _raster('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect x="16" y="16" width="480" '
                   'height="480" rx="112" fill="#fff"/></svg>', size)
    gp = QPainter(blur)
    gp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    gp.drawImage(0, 0, clip)
    gp.end()
    p = QPainter(base)
    p.setOpacity(glow if size >= 48 else glow * 0.6)
    p.drawImage(0, 0, blur)
    p.setOpacity(1)
    p.drawImage(0, 0, sharp)
    p.end()
    return base


def png_bytes(img):
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path, images):
    """Ficheiro .ico com várias imagens PNG (formato aceite pelo Windows desde o Vista)."""
    entries = [(img.width(), png_bytes(img)) for img in images]
    head = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    table, data = b"", b""
    for size, blob in entries:
        dim = 0 if size >= 256 else size
        table += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset + len(data))
        data += blob
    with open(path, "wb") as fh:
        fh.write(head + table + data)


# ------------------------------------------------------------------- banner
W, H = 1600, 520


def banner(sub, pills, out):
    bg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="bbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0E1C44"/><stop offset="0.5" stop-color="#080F26"/><stop offset="1" stop-color="#04070F"/>
    </linearGradient>
    <radialGradient id="bhalo" cx="0.17" cy="0.45" r="0.45">
      <stop offset="0" stop-color="#2B6BFF" stop-opacity="0.30"/><stop offset="1" stop-color="#2B6BFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="rhalo" cx="0.86" cy="0.9" r="0.45">
      <stop offset="0" stop-color="#FF2E4D" stop-opacity="0.10"/><stop offset="1" stop-color="#FF2E4D" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bbg)"/>
  {"".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#FFFFFF" stroke-opacity="0.025"/>' for x in range(0, W, 40))}
  {"".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#FFFFFF" stroke-opacity="0.025"/>' for y in range(0, H, 40))}
  <rect width="{W}" height="{H}" fill="url(#bhalo)"/>
  <rect width="{W}" height="{H}" fill="url(#rhalo)"/>
</svg>'''
    img = _raster_rect(bg, W, H)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    # logótipo
    p.drawImage(QRectF(70, 84, 358, 358), render(716))
    # textos
    p.setPen(QColor("#22E0D2"))
    f = QFont("Bahnschrift", 15)
    f.setBold(True)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 6)
    p.setFont(f)
    p.drawText(QPointF(520, 168), "WORKSHOP DIAGNOSTIC SOFTWARE")
    f = QFont("Bahnschrift", 70)
    f.setBold(True)
    p.setFont(f)
    g = QLinearGradient(514, 0, 1300, 0)
    g.setColorAt(0, QColor("#FFFFFF"))
    g.setColorAt(1, QColor("#BFD6FF"))
    p.setPen(QPen(g, 1))
    p.drawText(QPointF(514, 262), "Roots Auto Doctor")
    p.setPen(QColor("#A9B8DA"))
    p.setFont(QFont("Segoe UI", 20))
    p.drawText(QPointF(520, 322), sub)
    x = 520
    pf = QFont("Segoe UI", 14)
    pf.setWeight(QFont.DemiBold)
    p.setFont(pf)
    for text in pills:
        w = p.fontMetrics().horizontalAdvance(text) + 62
        p.setPen(QPen(QColor(127, 178, 255, 90), 1.5))
        p.setBrush(QColor(255, 255, 255, 15))
        p.drawRoundedRect(QRectF(x, 372, w, 46), 23, 23)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#22E0D2"))
        p.drawEllipse(QPointF(x + 24, 395), 5, 5)
        p.setPen(QColor("#DCE6FF"))
        p.drawText(QRectF(x + 38, 372, w - 44, 46), int(Qt.AlignVCenter | Qt.AlignLeft), text)
        x += w + 14
    p.end()
    img.save(out)


def _raster_rect(svg_text, w, h):
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg_text.encode())).render(p, QRectF(0, 0, w, h))
    p.end()
    return img


def main():
    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    with open(os.path.join(ASSETS, "logo.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg_file(mark()))
    render(512).save(os.path.join(ASSETS, "logo.png"))
    render(64).save(os.path.join(ASSETS, "logo_64.png"))
    for size in (16, 32):
        render(size).save(os.path.join(ASSETS, f"logo_{size}.png"))
    write_ico(os.path.join(ASSETS, "icon.ico"), [render(s) for s in (16, 24, 32, 48, 64, 128, 256)])
    banner("Full diagnostics for the VW Group — and fault reading for every make.",
           ["Auto-Scan", "Live data", "Coding & adaptation", "Customer reports"],
           os.path.join(DOCS, "banner.png"))
    print("Identidade gerada em rad/assets e docs/banner.png")


if __name__ == "__main__":
    main()
