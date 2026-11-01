"""Verificação de actualizações no GitHub.

Diz se há uma versão nova. A descarga e a instalação automáticas (versão instalada, com assinatura válida)
estão em rad/autoupdate.py. Funciona sem internet: falha em silêncio no arranque e explica o erro quando se
procura à mão.

Usa só a última release publicada do repositório, com o instalador e a sua assinatura .sig como anexos (e a
versão portátil, também com .sig). Uma tag sem release não conta: não há nada para o cliente descarregar, por isso
não se anuncia (antes avisava e mandava o cliente para uma página vazia).

As novidades mostradas ao cliente vêm do texto da release, só da parte marcada para clientes (docs/NOVIDADES.md,
juntas pelo tools/finish_build.py notes): o resto do texto (notas para o fornecedor) nunca aparece no programa."""
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


NOTES_MARK = "<!-- novidades:{lang} -->"
NOTES_END = "<!-- fim das novidades -->"


def customer_notes(body, lang=None):
    """Novidades para o cliente, no idioma da interface (ou em português), tiradas do texto da release.
    Sem as marcas de novidades devolve "" (texto técnico ou para o fornecedor não se mostra)."""
    from .i18n import language
    body = (body or "").replace("\r\n", "\n")
    for code in (lang or language(), "pt"):
        mark = NOTES_MARK.format(lang=code)
        if mark not in body:
            continue
        text = body.split(mark, 1)[1]
        cut = min([i for i in (text.find("<!-- novidades:"), text.find(NOTES_END)) if i >= 0] or [len(text)])
        lines = []
        for raw in text[:cut].strip().splitlines():
            line = raw.strip().replace("**", "")
            if line.startswith(("- ", "* ")):
                lines.append("• " + line[2:].strip())
            elif line and raw[:1].isspace() and lines and lines[-1]:   # continuação da linha anterior
                lines[-1] += " " + line
            else:
                lines.append(line)
        return "\n".join(lines).strip()
    return ""


def _pick(assets, start, ext):
    """Nome do anexo que acaba em ext, preferindo o que começa por start."""
    names = [n for n in assets if n.lower().endswith(ext)]
    return next((n for n in names if n.lower().startswith(start)), names[0] if names else None)


STABLE, BETA = "stable", "beta"


def _release_info(rel):
    """O que o programa precisa de uma release do GitHub, ou None se não tiver versão ou instalador."""
    version = str(rel.get("tag_name", ""))
    if not parse_version(version) or rel.get("draft"):
        return None
    assets = {str(a.get("name", "")): a.get("browser_download_url") for a in rel.get("assets") or []}
    exe_name = _pick(assets, "setup", ".exe")
    zip_name = next((n for n in assets if n.lower().endswith("_portatil.zip")), None)
    if exe_name is None:
        log.warning("Release %s sem instalador anexado: não é anunciada", version)
        return None
    return {"version": version.lstrip("v"), "url": rel.get("html_url") or RELEASES_PAGE,
            "download": assets.get(exe_name), "signature": assets.get(f"{exe_name}.sig"),
            "portable": assets.get(zip_name) if zip_name else None,
            "portable_signature": assets.get(f"{zip_name}.sig") if zip_name else None,
            "notes": customer_notes(rel.get("body")), "prerelease": bool(rel.get("prerelease"))}


def latest(opener=None, channel=STABLE):
    """Devolve {"version", "url", "download", "signature", "portable", "portable_signature", "notes", "prerelease"}
    da versão mais recente publicada. notes = novidades para o cliente (pode ser "").
    channel=BETA (só o PC do fornecedor ou de quem testa, escolhido no modo técnico): conta também as pré-versões
    ("versões de teste"), para experimentar uma versão antes de ela chegar aos clientes."""
    opener = opener or urllib.request.urlopen
    try:
        if channel == BETA:
            found = [i for i in map(_release_info, _get_json(API + "/releases?per_page=20", opener) or []) if i]
            if not found:
                raise UpdateError(tr("Ainda não há nenhuma versão publicada."))
            return max(found, key=lambda i: parse_version(i["version"]))
        try:
            rel = _get_json(API + "/releases/latest", opener)
        except urllib.error.HTTPError as e:
            if e.code == 404:            # o repositório ainda não tem nenhuma release publicada
                raise UpdateError(tr("Ainda não há nenhuma versão publicada.")) from e
            raise
        info = _release_info(rel)
        if info is None:
            raise UpdateError(tr("Ainda não há nenhuma versão publicada."))
        return info
    except UpdateError:
        raise
    except urllib.error.HTTPError as e:
        raise UpdateError(tr("O servidor de actualizações respondeu com o erro {code}.", code=e.code)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError(tr("Sem ligação à internet ou o servidor de actualizações não respondeu.")) from e
    except (ValueError, AttributeError, TypeError) as e:
        raise UpdateError(tr("Resposta inesperada do servidor de actualizações.")) from e


def release_for(version, opener=None):
    """A release publicada de uma versão concreta (para voltar à versão anterior), ou None."""
    opener = opener or urllib.request.urlopen
    try:
        return _release_info(_get_json(f"{API}/releases/tags/v{version}", opener))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, AttributeError, TypeError):
        return None


def check(current=VERSION, opener=None, channel=STABLE):
    """{"available": bool, "current", "version", "url", "download", "notes"}. Lança UpdateError."""
    info = latest(opener, channel)
    return dict(info, available=is_newer(info["version"], current), current=current)
