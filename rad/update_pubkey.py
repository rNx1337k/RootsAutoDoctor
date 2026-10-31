"""Chave pública das actualizações automáticas (Ed25519, 32 bytes em hexadecimal).

Gerada por `python tools/update_key.py genkey`, que guarda a chave privada FORA do repositório. O programa só
instala sozinho um instalador cuja assinatura (.sig, criada pelo build_release.bat) bate certo com esta chave.
None = actualizações automáticas desligadas: o programa só avisa que há uma versão nova."""
UPDATE_PUBLIC_KEY = "7c0c9a5e0aa269121f2d82604a15adaea2478d6a284ab680910da4826b2c181a"
