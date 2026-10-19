"""Prepara os Python portáteis que correm as pontes D2XX / J2534 (pasta runtime/).

O driver dos clones HEX-USB (RT-USB.DLL) e muitos drivers J2534 são de 32 bits, e o programa é de 64 bits:
as pontes correm num processo à parte com um Python do mesmo número de bits da DLL. Em vez de pedir a cada
pessoa que instale um Python de 32 bits, o programa leva consigo a distribuição "embeddable" oficial da
python.org (só a biblioteca padrão, ~10 MB cada).

    .venv\\Scripts\\python.exe tools\\get_runtime.py            descarrega e verifica (run.bat e build_release.bat)
    .venv\\Scripts\\python.exe tools\\get_runtime.py --check    só verifica o que já existe

Os zips são verificados pelo SHA-256 fixo abaixo (calculado sobre os ficheiros oficiais, cujo python.exe,
python313.dll e _ctypes.pyd têm assinatura digital válida da Python Software Foundation).
"""
import argparse
import hashlib
import io
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "3.13.15"
FILES = {
    "py32": ("win32", "3f5506367943d16dffa89f0ea140ebf04481a80611eb119e76e95aea8c79f5ce"),
    "py64": ("amd64", "d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf"),
}
URL = "https://www.python.org/ftp/python/{v}/python-{v}-embed-{arch}.zip"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "runtime")
STAMP = "roots_runtime.txt"


def is_ready(folder):
    """A pasta tem um runtime completo desta versão (python.exe + marca escrita no fim da extracção)."""
    try:
        with open(os.path.join(folder, STAMP), encoding="utf-8") as fh:
            return fh.read().strip() == VERSION and os.path.exists(os.path.join(folder, "python.exe"))
    except OSError:
        return False


def install(name, dest_dir, log=print):
    arch, sha = FILES[name]
    folder = os.path.join(dest_dir, name)
    if is_ready(folder):
        log(f"{name}: já está pronto ({VERSION})")
        return folder
    url = URL.format(v=VERSION, arch=arch)
    log(f"{name}: a descarregar {url}")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise RuntimeError(f"{name}: SHA-256 não confere (esperado {sha}, veio {got}) — ficheiro recusado")
    os.makedirs(dest_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=f"{name}_", dir=dest_dir)       # extrai ao lado e troca no fim
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for m in z.namelist():                                   # nada fora da pasta
                if m.startswith(("/", "\\")) or ".." in m.replace("\\", "/").split("/"):
                    raise RuntimeError(f"{name}: caminho inválido no zip: {m}")
            z.extractall(tmp)
        with open(os.path.join(tmp, STAMP), "w", encoding="utf-8") as fh:
            fh.write(VERSION)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.replace(tmp, folder)
    finally:
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
    log(f"{name}: pronto em {folder}")
    return folder


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=DEFAULT_DIR, help="pasta de destino (por omissão runtime/ do projecto)")
    ap.add_argument("--check", action="store_true", help="só verifica, não descarrega")
    ap.add_argument("--only", choices=sorted(FILES), help="só um dos runtimes")
    args = ap.parse_args()
    names = [args.only] if args.only else sorted(FILES)
    if args.check:
        missing = [n for n in names if not is_ready(os.path.join(args.dest, n))]
        print("Runtimes prontos." if not missing else f"Em falta: {', '.join(missing)}")
        return 1 if missing else 0
    try:
        for n in names:
            install(n, args.dest)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
