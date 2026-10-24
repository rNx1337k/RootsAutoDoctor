"""Licenças: chaves assinadas por PC, verificação offline, modo demonstração que bloqueia escritas em carros
reais (o simulador funciona sempre). Corre sem Qt e sem carro."""
import datetime
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import ed25519, licensing, license_pubkey

SECRET = bytes(range(32))
PUBLIC = ed25519.public_key(SECRET)
PC = "ABCD-EFGH-JKLM"


def test_ed25519_rfc8032_vector():
    sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    assert ed25519.public_key(sk).hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    sig = ed25519.sign(sk, b"")
    assert sig.hex().startswith("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a3")
    assert ed25519.verify(ed25519.public_key(sk), b"", sig)
    assert not ed25519.verify(ed25519.public_key(sk), b"x", sig)


def test_valid_key_for_this_pc():
    key = licensing.make_key(SECRET, "Oficina Silva", PC)
    r = licensing.check_key(key, PC, public=PUBLIC)
    assert r["valid"] and r["workshop"] == "Oficina Silva" and r["expires"] is None


def test_key_survives_spaces_and_line_breaks_from_email():
    key = licensing.make_key(SECRET, "Oficina", PC)
    pasted = "  " + key[:30] + "\n" + key[30:60] + " \r\n" + key[60:] + "\n"
    assert licensing.check_key(pasted, "abcd efgh jklm", public=PUBLIC)["valid"]


def test_key_from_another_pc_is_refused():
    key = licensing.make_key(SECRET, "Oficina", PC)
    r = licensing.check_key(key, "ZZZZ-ZZZZ-ZZZZ", public=PUBLIC)
    assert not r["valid"] and "outro PC" in r["reason"] and "ZZZZ-ZZZZ-ZZZZ" in r["reason"]


def test_tampered_or_forged_key_is_refused():
    key = licensing.make_key(SECRET, "Oficina", PC)
    body, sig = key[len(licensing.PREFIX):].split(".")
    import base64, json
    data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    data["expires"] = None
    data["workshop"] = "Outra"
    forged_body = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    assert not licensing.check_key(licensing.PREFIX + forged_body + "." + sig, PC, public=PUBLIC)["valid"]
    other = licensing.make_key(bytes(32), "Oficina", PC)        # assinada com outra chave privada
    assert "assinatura" in licensing.check_key(other, PC, public=PUBLIC)["reason"]
    for junk in ("", "abc", "RAD1-", "RAD1-xx.yy", "RAD1-!!!.???"):
        assert not licensing.check_key(junk, PC, public=PUBLIC)["valid"]


def test_expiry():
    key = licensing.make_key(SECRET, "Oficina", PC, expires=datetime.date(2027, 1, 31))
    assert licensing.check_key(key, PC, today=datetime.date(2027, 1, 31), public=PUBLIC)["valid"]
    r = licensing.check_key(key, PC, today=datetime.date(2027, 2, 1), public=PUBLIC)
    assert not r["valid"] and "31/01/2027" in r["reason"]


def test_machine_id_format_is_stable_and_readable():
    a = licensing.format_machine_id("guid-1")
    assert a == licensing.format_machine_id("guid-1") and a != licensing.format_machine_id("guid-2")
    assert len(a) == 14 and a[4] == a[9] == "-" and not set(a) & set("01IO")
    assert licensing.normalize_machine_id(a.lower().replace("-", " ")) == a
    assert len(licensing.machine_id()) == 14


def _with_key(public_hex, fn):
    old_key, old_dir = license_pubkey.PUBLIC_KEY, licensing.DIRECTORY
    license_pubkey.PUBLIC_KEY = public_hex
    licensing.DIRECTORY = tempfile.mkdtemp()
    try:
        fn()
    finally:
        license_pubkey.PUBLIC_KEY, licensing.DIRECTORY = old_key, old_dir


def test_status_unconfigured_demo_and_licensed():
    def run():
        st = licensing.status(PC)
        assert st["state"] == "demo" and not st["licensed"]
        bad = licensing.install(licensing.make_key(SECRET, "Oficina", "ZZZZ-ZZZZ-ZZZZ"), PC)
        assert not bad["valid"] and licensing.stored_key() == ""              # inválida: não é guardada
        assert licensing.install(licensing.make_key(SECRET, "Oficina Silva", PC), PC)["valid"]
        st = licensing.status(PC)
        assert st["state"] == "licensed" and st["licensed"] and "Oficina Silva" in st["message"]
        licensing.remove()
        assert licensing.status(PC)["state"] == "demo"
    _with_key(PUBLIC.hex(), run)
    _with_key(None, lambda: licensing.status(PC)["state"] == "unconfigured" or (_ for _ in ()).throw(AssertionError))


def test_expired_installed_license_falls_back_to_demo():
    def run():
        licensing.install(licensing.make_key(SECRET, "Oficina", PC, expires=datetime.date(2027, 1, 1)), PC)
        st = licensing.status(PC, today=datetime.date(2027, 6, 1))
        assert st["state"] == "demo" and "expirou" in st["message"]
    _with_key(PUBLIC.hex(), run)


def test_license_tool_issues_keys_that_the_program_accepts():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import io
    import contextlib
    import license_tool
    d = tempfile.mkdtemp()
    keyfile = os.path.join(d, "private.key")
    pub = os.path.join(d, "license_pubkey.py")
    old = license_tool.PUBKEY_FILE
    license_tool.PUBKEY_FILE = pub
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            license_tool.main(["--key", keyfile, "genkey"])
        ns = {}
        exec(open(pub, encoding="utf-8").read(), ns)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            license_tool.main(["--key", keyfile, "issue", "--machine", "abcd efgh jklm", "--workshop", "Oficina X",
                               "--expires", "2030-12-31"])
        key = out.getvalue().strip()
        r = licensing.check_key(key, PC, public=bytes.fromhex(ns["PUBLIC_KEY"]))
        assert r["valid"] and r["expires"] == datetime.date(2030, 12, 31)
        assert os.path.exists(os.path.join(d, "licencas_emitidas.csv"))
        from rad import license_pubkey as real
        assert real.PUBLIC_KEY is None or real.PUBLIC_KEY != ns["PUBLIC_KEY"]   # o ficheiro real não foi tocado
        try:                                         # nunca substitui uma chave privada existente
            with contextlib.redirect_stdout(io.StringIO()):
                license_tool.main(["--key", keyfile, "genkey"])
            assert False
        except SystemExit:
            pass
    finally:
        license_tool.PUBKEY_FILE = old


def test_shipped_public_key_is_none_or_valid_hex():
    k = license_pubkey.PUBLIC_KEY
    assert k is None or (len(bytes.fromhex(k)) == 32)
