"""Gerador de chaves de licença do Roots Auto Doctor — USO EXCLUSIVO DO VENDEDOR.

A chave privada (keys/roots_private.key) NUNCA vai para o GitHub nem para os clientes.
Guarde uma cópia num sítio seguro: sem ela não consegue gerar mais licenças.

Uso:
  python tools/keygen.py <código do PC> "<nome da oficina>" [AAAA-MM-DD]

Exemplos:
  python tools/keygen.py 1A2B-3C4D-5E6F-7A8B "Oficina Silva"              (vitalícia)
  python tools/keygen.py 1A2B-3C4D-5E6F-7A8B "Oficina Silva" 2027-10-31   (anual)
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rad import ed25519, license  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    machine, holder = sys.argv[1].strip().upper(), sys.argv[2].strip()
    expires = sys.argv[3].strip() if len(sys.argv) > 3 else ""
    key_path = os.environ.get("RAD_PRIVATE_KEY", os.path.join(ROOT, "keys", "roots_private.key"))
    with open(key_path) as fh:
        secret = base64.b64decode(fh.read().strip())
    if ed25519.public_key(secret) != license.PUBLIC_KEY:
        sys.exit("A chave privada não corresponde à chave pública do programa.")
    key = license.make_key(secret, machine, holder, expires)
    check = license.check_key(key, machine=machine)
    assert check["status"] in ("valid", "expired"), check
    print(f"\nLicença para: {holder}\nPC: {machine}\nValidade: {expires or 'vitalícia'}\n")
    print(key)
    print()


if __name__ == "__main__":
    main()
