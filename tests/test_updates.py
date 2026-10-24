"""Verificação de actualizações: compara versões, usa a release do GitHub (ou as tags) e nunca rebenta sem
internet. Sem rede: o GitHub é simulado."""
import io
import json
import os
import sys
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
    assert r["notes"] == "Novidades" and r["url"].endswith("v1.9.0")
    assert not updates.check("1.9.0", opener=_opener({"/releases/latest": rel}))["available"]


def test_without_releases_uses_highest_tag():
    tags = [{"name": "v1.7.0"}, {"name": "v1.10.0"}, {"name": "v1.9.2"}, {"name": "experimental"}]
    r = updates.check("1.7.0", opener=_opener({"/releases/latest": _http(404), "/tags": tags}))
    assert r["available"] and r["version"] == "1.10.0" and r["download"] is None
    assert r["url"] == updates.RELEASES_PAGE + "/tag/v1.10.0"


def test_failures_become_update_errors():
    cases = [({"/releases/latest": urllib.error.URLError("offline")}, "internet"),
             ({"/releases/latest": _http(403)}, "403"),
             ({"/releases/latest": _http(404), "/tags": []}, "nenhuma versão"),
             ({"/releases/latest": TimeoutError()}, "internet"),
             ({"/releases/latest": ["não", "é", "um", "objecto"]}, "inesperada")]
    for routes, text in cases:
        try:
            updates.check("1.0.0", opener=_opener(routes))
            assert False, routes
        except updates.UpdateError as e:
            assert text in str(e), (text, str(e))
