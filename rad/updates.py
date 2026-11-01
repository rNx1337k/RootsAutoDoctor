"""Verificação de actualizações no GitHub.

Diz se há uma versão nova. A descarga e a instalação automáticas (versão instalada, com assinatura válida)
estão em rad/autoupdate.py. Funciona sem internet: falha em silêncio no arranque e explica o erro quando se
procura à mão.

Usa só a última release publicada do repositório, com o instalador e a sua assinatura .sig como anexos. Uma tag
sem release não conta: não há nada para o cliente descarregar, por isso não se anuncia (antes avisava e mandava
o cliente para uma página vazia)."""
import json
import logging
import re
import urllib.error
import urllib.request

from . import APP_NAME, VERSION
from .i18n import tr

log = logging.getLogger(__name__)

REPO = "rNx1337k/RootsAutoDoctor"
API = "https://api.github.com/repos/" + REPO
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
TIMEOUT = 6


class UpdateError(Exception):
    """Não foi possível saber se há uma versão nova (sem internet, GitHub indisponível...)."""


def parse_version(text):
    """"v1.7.0" → (1, 7, 0). None se não for uma versão."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", (text or "").strip())
    if not m:
        return None
    return tuple(int(x or 0) for x in m.groups())


def is_newer(candidate, current=VERSION):
    a, b = parse_version(candidate), parse_version(current)
    return a is not None and b is not None and a > b


def _get_json(url, opener):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": f"{APP_NAME.replace(' ', '')}/{VERSION}"})
    with opener(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def latest(opener=None):
    """Devolve {"version", "url", "download", "notes"} da versão mais recente publicada."""
    opener = opener or urllib.request.urlopen
    try:
        try:
            rel = _get_json(API + "/releases/latest", opener)
        except urllib.error.HTTPError as e:
            if e.code == 404:            # o repositório ainda não tem nenhuma release publicada
                raise UpdateError(tr("Ainda não há nenhuma versão publicada.")) from e
            raise
        version = rel.get("tag_name", "")
        if not parse_version(version):
            raise UpdateError(tr("Ainda não há nenhuma versão publicada."))
        assets = {str(a.get("name", "")): a.get("browser_download_url") for a in rel.get("assets") or []}
        exe_name = next((n for n in assets if n.lower().startswith("setup") and n.lower().endswith(".exe")),
                        next((n for n in assets if n.lower().endswith(".exe")), None))
        if exe_name is None:
            log.warning("Release %s sem instalador anexado: não é anunciada", version)
            raise UpdateError(tr("Ainda não há nenhuma versão publicada."))
        return {"version": version.lstrip("v"), "url": rel.get("html_url") or RELEASES_PAGE,
                "download": assets.get(exe_name), "signature": assets.get(f"{exe_name}.sig"),
                "notes": (rel.get("body") or "").strip()}
    except UpdateError:
        raise
    except urllib.error.HTTPError as e:
        raise UpdateError(tr("O servidor de actualizações respondeu com o erro {code}.", code=e.code)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError(tr("Sem ligação à internet ou o servidor de actualizações não respondeu.")) from e
    except (ValueError, AttributeError, TypeError) as e:
        raise UpdateError(tr("Resposta inesperada do servidor de actualizações.")) from e


def check(current=VERSION, opener=None):
    """{"available": bool, "current", "version", "url", "download", "notes"}. Lança UpdateError."""
    info = latest(opener)
    return dict(info, available=is_newer(info["version"], current), current=current)
