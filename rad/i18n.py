"""Idioma da interface (Português / English).

O texto de origem é o português que está no código; tr() devolve a tradução do catálogo do idioma escolhido
(rad/i18n_en.py) ou o próprio texto se ainda não houver tradução. Textos com valores usam marcadores:
    tr("Ligar a {addr:02X}", addr=0x17)
O idioma escolhe-se em Opções e aplica-se ao abrir o programa (antes de criar a janela)."""
import logging
import re
import string

log = logging.getLogger(__name__)

LANGUAGES = {"pt": "Português", "en": "English"}
DEFAULT = "pt"

_lang = DEFAULT
_catalog = {}
_missing = set()


def _load_catalog(code):
    if code == "en":
        from .i18n_en import EN
        return EN
    return {}


def set_language(code):
    """Muda o idioma das traduções. Códigos desconhecidos ficam em português."""
    global _lang, _catalog
    code = code if code in LANGUAGES else DEFAULT
    _lang = code
    _catalog = _load_catalog(code)
    _missing.clear()
    return code


def language():
    return _lang


# Ponto decimal entre dois algarismos (1.4, 12.40). Em português o ponto separa milhares: "1.400 V" lê-se mil e
# quatrocentos volts. No ecrã e nos relatórios em português os decimais saem com vírgula; os dados gravados (CSV,
# histórico, gravações) ficam sempre com ponto.
_DECIMAL_POINT = re.compile(r"(?<=\d)\.(?=\d)")
_FLOAT_SPECS = "eEfFgG%"


def decimal(text):
    """Texto de um número para mostrar: com vírgula decimal em português, igual em inglês."""
    if _lang == "pt" and isinstance(text, str):
        return _DECIMAL_POINT.sub(",", text)
    return text


class _Formatter(string.Formatter):
    """str.format, mas os números decimais saem com vírgula em português ({v:.1f} → 12,4)."""

    def format_field(self, value, format_spec):
        out = super().format_field(value, format_spec)
        is_float = isinstance(value, float) or (
            isinstance(value, int) and not isinstance(value, bool) and format_spec[-1:] in tuple(_FLOAT_SPECS))
        return decimal(out) if is_float else out


_formatter = _Formatter()


def tr(text, /, **values):
    """Traduz text (o português do código) e preenche os marcadores {nome} com values. text é só posicional:
    um valor pode chamar-se "text" (ex.: tr("Saúde: {text}", text=...))."""
    if _lang != DEFAULT:
        translated = _catalog.get(text)
        if translated is None:
            if text not in _missing:
                _missing.add(text)
                log.debug("Sem tradução (%s): %r", _lang, text)
        else:
            text = translated
    return _formatter.format(text, **values) if values else text


def tr_data(text):
    """Para textos que vêm de tabelas de dados (descrições de avarias, nomes de módulos): traduz sem
    interpretar chavetas."""
    if _lang != DEFAULT and text:
        return _catalog.get(text, text)
    return text


def load_from_settings(settings=None):
    """Lê o idioma das definições (Opções) e aplica-o. Devolve o código aplicado."""
    try:
        from .settings import app_settings
        value = str((settings or app_settings()).value("ui/language", DEFAULT))
    except Exception:
        value = DEFAULT
    return set_language(value)
