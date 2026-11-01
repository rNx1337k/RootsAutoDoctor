"""Verificação de actualizações: compara versões, usa só a release publicada no GitHub (com instalador) e nunca
rebenta sem internet. Sem rede: o GitHub é simulado."""
import io
import json
import os
import sys
import tempfile
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import updates


def _opener(routes):
    def opener(req, timeout=None):
        url = req.full_url
        for key, value in routes.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return io.BytesIO(json.dumps(value).encode())
        raise AssertionError(f"pedido inesperado: {url}")
    return opener


def _http(code):
    return urllib.error.HTTPError("https://api.github.com", code, "x", {}, None)


def test_versions():
    assert updates.parse_version("v1.7.0") == (1, 7, 0) == updates.parse_version("1.7")
    assert updates.parse_version("latest") is None and updates.parse_version("v1.7.0-beta") is None
    assert updates.is_newer("v1.10.0", "1.9.3") and not updates.is_newer("1.7.0", "1.7.0")
    assert not updates.is_newer("1.6.9", "1.7.0") and not updates.is_newer("lixo", "1.0.0")


def test_release_with_installer():
    rel = {"tag_name": "v1.9.0", "html_url": "https://github.com/x/releases/tag/v1.9.0", "body": "Novidades",
           "assets": [{"name": "notas.txt", "browser_download_url": "a"},
                      {"name": "Setup_RootsAutoDoctor_1.9.0.exe", "browser_download_url": "https://dl/setup.exe"}]}
    r = updates.check("1.7.0", opener=_opener({"/releases/latest": rel}))
    assert r["available"] and r["version"] == "1.9.0" and r["download"] == "https://dl/setup.exe"
    assert r["notes"] == "" and r["url"].endswith("v1.9.0")          # texto sem as marcas de novidades: não aparece
    assert not updates.check("1.9.0", opener=_opener({"/releases/latest": rel}))["available"]


def test_tags_without_a_published_installer_are_not_announced():
    # só tags (sem release) ou uma release sem instalador: o cliente não tinha nada para descarregar
    for routes in ({"/releases/latest": _http(404)},
                   {"/releases/latest": {"tag_name": "v1.12.0", "assets": [{"name": "notas.txt",
                                                                           "browser_download_url": "a"}]}}):
        try:
            updates.check("1.7.0", opener=_opener(routes))
            assert False, routes
        except updates.UpdateError as e:
            assert "nenhuma versão" in str(e)


def test_failures_become_update_errors():
    cases = [({"/releases/latest": urllib.error.URLError("offline")}, "internet"),
             ({"/releases/latest": _http(403)}, "403"),
             ({"/releases/latest": _http(404)}, "nenhuma versão"),
             ({"/releases/latest": TimeoutError()}, "internet"),
             ({"/releases/latest": ["não", "é", "um", "objecto"]}, "inesperada")]
    for routes, text in cases:
        try:
            updates.check("1.0.0", opener=_opener(routes))
            assert False, routes
        except updates.UpdateError as e:
            assert text in str(e), (text, str(e))


def test_only_the_customer_notes_of_a_release_are_shown():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "tools"))
    import finish_build
    path = os.path.join(tempfile.mkdtemp(), "NOVIDADES.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Novidades\n\n## 9.0.0\n\n### pt\n- Mais **rápido**.\n- Uma linha longa\n  que continua.\n\n"
                 "### en\n- Faster.\n\n## 8.0.0\n\n### pt\n- Antiga.\n")
    body = finish_build.release_notes("9.0.0", path, log=lambda m: None)
    assert updates.customer_notes(body, "pt") == "• Mais rápido.\n• Uma linha longa que continua."
    assert updates.customer_notes(body, "en") == "• Faster."
    assert "Antiga" not in body
    assert updates.customer_notes(body + "\nNotas para o fornecedor: assinar o instalador.", "pt").count("•") == 2
    msgs = []
    assert updates.customer_notes(finish_build.release_notes("7.0.0", path, log=msgs.append), "pt") == ""
    assert msgs and "7.0.0" in msgs[0]
    assert updates.customer_notes("Versão 1.12.0 — ver CHANGELOG.md. Antes de publicar: assinar.") == ""


def test_release_offers_the_signed_portable_zip_and_the_repository_has_notes_for_this_version():
    from rad import VERSION
    rel = {"tag_name": "v9.0.0", "html_url": "h", "body": "",
           "assets": [{"name": "Setup_RootsAutoDoctor_9.0.0.exe", "browser_download_url": "https://dl/s.exe"},
                      {"name": "Setup_RootsAutoDoctor_9.0.0.exe.sig", "browser_download_url": "https://dl/s.sig"},
                      {"name": "RootsAutoDoctor_9.0.0_portatil.zip", "browser_download_url": "https://dl/p.zip"},
                      {"name": "RootsAutoDoctor_9.0.0_portatil.zip.sig", "browser_download_url": "https://dl/p.sig"}]}
    r = updates.latest(opener=_opener({"releases/latest": rel}))
    assert r["portable"] == "https://dl/p.zip" and r["portable_signature"] == "https://dl/p.sig"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "tools"))
    import finish_build
    notes = finish_build.customer_notes(VERSION)
    assert notes.get("pt") and notes.get("en"), "docs/NOVIDADES.md não tem a versão actual"
