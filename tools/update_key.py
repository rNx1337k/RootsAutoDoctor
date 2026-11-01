"""Chave das actualizações automáticas (só o fornecedor; NÃO vai no instalador).

    python tools/update_key.py genkey     cria o par de chaves (uma vez só)
    python tools/update_key.py show       mostra onde está a chave privada e a chave pública

A chave privada fica FORA do repositório (por omissão %USERPROFILE%\\RootsAutoDoctor_licencas\\update.key, ou a
indicada na variável RAD_UPDATE_KEY) e a pública vai para rad/update_pubkey.py. O build_release.bat usa a
privada para assinar cada instalador (Setup_...exe.sig); o programa só se actualiza sozinho com instaladores
assinados por ela. Faça cópia de segurança: se a perder, os programas já instalados deixam de se actualizar
sozinhos (passam a só avisar) até instalarem à mão uma versão com a chave nova.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rad import ed25519  # noqa: E402

PUBKEY_FILE = os.path.join(ROOT, "rad", "update_pubkey.py")


def _inside(path, folder):
    """True se path fica dentro de folder. Em discos diferentes (C: e D:) nunca fica."""
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(folder)]) == os.path.abspath(folder)
    except ValueError:
        return False


def key_path():
    return os.environ.get("RAD_UPDATE_KEY") or os.path.join(os.path.expanduser("~"), "RootsAutoDoctor_licencas",
                                                            "update.key")


def read_secret(path=None):
    """Chave privada (32 bytes) ou None se não existir."""
    path = path or key_path()
    try:
        with open(path, encoding="ascii") as fh:
            secret = bytes.fromhex(fh.read().strip())
    except (OSError, ValueError):
        return None
    return secret if len(secret) == 32 else None


def write_pubkey(public_hex, path=None):
    with open(path or PUBKEY_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('"""Chave pública das actualizações automáticas (Ed25519, 32 bytes em hexadecimal).\n\n'
                 'Gerada por `python tools/update_key.py genkey`, que guarda a chave privada FORA do repositório. '
                 'O programa só\ninstala sozinho um instalador cuja assinatura (.sig, criada pelo build_release.bat) '
                 'bate certo com esta chave.\nNone = actualizações automáticas desligadas: o programa só avisa que '
                 'há uma versão nova."""\n'
                 f'UPDATE_PUBLIC_KEY = "{public_hex}"\n')


def genkey(path=None):
    path = path or key_path()
    if os.path.exists(path):
        sys.exit(f"Já existe uma chave de actualizações em {path}. Não foi alterada.")
    if _inside(path, ROOT):
        sys.exit("A chave privada não pode ficar dentro da pasta do projecto (iria parar ao GitHub).")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    secret = os.urandom(32)
    with open(path, "w", encoding="ascii") as fh:
        fh.write(secret.hex() + "\n")
    write_pubkey(ed25519.public_key(secret).hex())
    print(f"Chave privada: {path}  (faça cópia de segurança e NUNCA a envie a ninguém)")
    print(f"Chave pública escrita em: {PUBKEY_FILE}  (faça commit deste ficheiro)")


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "genkey":
        genkey()
        return 0
    if cmd == "show":
        secret = read_secret()
        print(f"Chave privada: {key_path()} ({'encontrada' if secret else 'NÃO encontrada'})")
        if secret:
            print(f"Chave pública: {ed25519.public_key(secret).hex()}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
