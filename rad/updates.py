"""Verificação de actualizações no GitHub.

Só verifica e avisa: não descarrega nem instala nada sozinho (o instalador corre-se à mão, como sempre).
Funciona sem internet: falha em silêncio no arranque e explica o erro quando se procura à mão.

Usa a última release publicada do repositório (com o instalador como anexo); se não houver releases,
usa a tag de versão mais alta."""
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
            version = rel.get("tag_name", "")
            if parse_version(version):
                exe = next((a.get("browser_download_url") for a in rel.get("assets") or []
                            if str(a.get("name", "")).lower().endswith(".exe")), None)
                return {"version": version.lstrip("v"), "url": rel.get("html_url") or RELEASES_PAGE,
                        "download": exe, "notes": (rel.get("body") or "").strip()}
        except urllib.error.HTTPError as e:
            if e.code != 404:            # 404 = o repositório ainda não tem releases: usa as tags
                raise
        tags = _get_json(API + "/tags?per_page=100", opener)
        versions = [t.get("name", "") for t in tags if parse_version(t.get("name", ""))]
        if not versions:
            raise UpdateError(tr("O repositório não tem nenhuma versão publicada."))
        best = max(versions, key=parse_version)
        return {"version": best.lstrip("v"), "url": f"{RELEASES_PAGE}/tag/{best}", "download": None, "notes": ""}
    except UpdateError:
        raise
    except urllib.error.HTTPError as e:
        raise UpdateError(tr("O GitHub respondeu com o erro {code}.", code=e.code)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError(tr("Sem ligação à internet ou o GitHub não respondeu.")) from e
    except (ValueError, AttributeError, TypeError) as e:
        raise UpdateError(tr("Resposta inesperada do GitHub.")) from e


def check(current=VERSION, opener=None):
    """{"available": bool, "current", "version", "url", "download", "notes"}. Lança UpdateError."""
    info = latest(opener)
    return dict(info, available=is_newer(info["version"], current), current=current)
