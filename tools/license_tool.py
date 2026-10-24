"""Ferramenta do fornecedor para as licenças do Roots Auto Doctor. NÃO vai no instalador.

1) Uma vez só — criar o par de chaves:
       python tools/license_tool.py genkey
   Guarda a chave privada FORA do repositório (por omissão em %USERPROFILE%\\RootsAutoDoctor_licencas) e
   escreve a chave pública em rad/license_pubkey.py. Faça cópia de segurança da chave privada: se a perder,
   as licenças já vendidas continuam a funcionar, mas não pode gerar novas para esta chave pública.

2) Por cada oficina — gerar a licença a partir do ID do PC (Opções → Licença no programa da oficina):
       python tools/license_tool.py issue --machine ABCD-EFGH-JKLM --workshop "Oficina Silva"
       python tools/license_tool.py issue --machine ABCD-EFGH-JKLM --workshop "Oficina Silva" --expires 2027-12-31
   Imprime a chave para enviar à oficina e acrescenta uma linha a licencas_emitidas.csv, ao lado da chave privada.

3) Ver o ID deste PC:
       python tools/license_tool.py machine
"""
import argparse
import csv
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rad import ed25519, licensing  # noqa: E402

DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "RootsAutoDoctor_licencas")
PUBKEY_FILE = os.path.join(ROOT, "rad", "license_pubkey.py")


def _key_path(args):
    return args.key or os.path.join(DEFAULT_DIR, "private.key")


def _read_secret(path):
    try:
        with open(path, encoding="ascii") as fh:
            secret = bytes.fromhex(fh.read().strip())
    except OSError:
        sys.exit(f"Chave privada não encontrada: {path}\nCrie-a primeiro com: python tools/license_tool.py genkey")
    if len(secret) != 32:
        sys.exit(f"Chave privada inválida: {path}")
    return secret


def write_pubkey(public_hex, path=None):
    with open(path or PUBKEY_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('"""Chave pública das licenças (Ed25519, 32 bytes em hexadecimal).\n\n'
                 'Gerada por `python tools/license_tool.py genkey`, que guarda a chave privada FORA do repositório.\n'
                 'None = licenciamento por configurar: o programa funciona sem limites '
                 '(versão de desenvolvimento)."""\n'
                 f'PUBLIC_KEY = "{public_hex}"\n')


def cmd_genkey(args):
    path = _key_path(args)
    if os.path.exists(path):
        sys.exit(f"Já existe uma chave privada em {path}.\nNão foi alterada: substituí-la invalidava as "
                 "licenças futuras. Apague-a à mão só se tiver a certeza.")
    if os.path.commonpath([os.path.abspath(path), ROOT]) == ROOT:
        sys.exit("A chave privada não pode ficar dentro da pasta do projecto (iria parar ao GitHub).")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    secret = os.urandom(32)
    with open(path, "w", encoding="ascii") as fh:
        fh.write(secret.hex() + "\n")
    public_hex = ed25519.public_key(secret).hex()
    write_pubkey(public_hex)
    print(f"Chave privada: {path}  (faça cópia de segurança e NUNCA a envie a ninguém)")
    print(f"Chave pública escrita em: {PUBKEY_FILE}")
    print("A partir do próximo build, o programa precisa de licença para escrever em carros reais.")


def cmd_issue(args):
    secret = _read_secret(_key_path(args))
    machine = licensing.normalize_machine_id(args.machine)
    if len(machine) != 14:
        sys.exit("ID do PC inválido: deve ter 12 caracteres, ex.: ABCD-EFGH-JKLM")
    expires = datetime.date.fromisoformat(args.expires) if args.expires else None
    key = licensing.make_key(secret, args.workshop, machine, expires)
    r = licensing.check_key(key, machine, public=ed25519.public_key(secret))
    assert r["valid"], r
    log = os.path.join(os.path.dirname(_key_path(args)), "licencas_emitidas.csv")
    new = not os.path.exists(log)
    with open(log, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        if new:
            w.writerow(["data", "oficina", "id_pc", "expira", "chave"])
        w.writerow([datetime.date.today().isoformat(), args.workshop, machine, args.expires or "", key])
    print(key)


def cmd_machine(_args):
    print(licensing.machine_id())


def main(argv=None):
    p = argparse.ArgumentParser(description="Licenças do Roots Auto Doctor")
    p.add_argument("--key", help="caminho da chave privada (por omissão: %(default)s)",
                   default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("genkey", help="criar o par de chaves (uma vez só)")
    i = sub.add_parser("issue", help="gerar a licença de uma oficina")
    i.add_argument("--machine", required=True, help="ID do PC da oficina (Opções → Licença)")
    i.add_argument("--workshop", required=True, help="nome da oficina")
    i.add_argument("--expires", help="data de fim AAAA-MM-DD (opcional)")
    sub.add_parser("machine", help="mostrar o ID deste PC")
    args = p.parse_args(argv)
    {"genkey": cmd_genkey, "issue": cmd_issue, "machine": cmd_machine}[args.cmd](args)


if __name__ == "__main__":
    main()
