"""Últimos passos do build de venda (chamado pelo build_release.bat). O objectivo é um só: o programa compilado
tem de abrir à primeira em qualquer PC com Windows 10/11 de 64 bits, sem instalar mais nada.

    python tools\\finish_build.py check    <pasta>          completa e verifica a pasta compilada
    python tools\\finish_build.py portable <pasta> <versão> cria dist\\RootsAutoDoctor_<versão>_portatil.zip
    python tools\\finish_build.py sandbox  <pasta>          cria build\\teste_pc_limpo.wsb (Windows Sandbox)
    python tools\\finish_build.py sign     <setup.exe> <versão> cria <setup.exe>.sig (actualizações automáticas)
    python tools\\finish_build.py codesign <ficheiro.exe>     assinatura Authenticode (tira o aviso do SmartScreen)

codesign: só assina se houver um certificado configurado; sem ele avisa e continua (o programa funciona na mesma,
o Windows mostra "O Windows protegeu o seu PC" na primeira vez). Configura-se com variáveis de ambiente:
    RAD_CODESIGN_PFX + RAD_CODESIGN_PASSWORD   certificado num ficheiro .pfx (fora do repositório)
    RAD_CODESIGN_THUMBPRINT                    ou o certificado instalado no Windows / pen USB (EV), pela impressão
    RAD_CODESIGN_TIMESTAMP                     servidor de carimbo de tempo (por omissão o da DigiCert)

check: copia para a pasta as DLL do Visual C++ (vcruntime/msvcp) que o Python e o Qt usam, se o compilador não
as tiver posto lá (num PC limpo não existem e o programa não abria), e confirma que estão lá todos os ficheiros
de que o programa precisa. Sai com código 1 se faltar alguma coisa.
"""
import glob
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ficheiros sem os quais o programa não abre ou não fala com nenhum cabo.
REQUIRED = [
    "RootsAutoDoctor.exe",
    os.path.join("rad", "assets", "icon.ico"),
    os.path.join("rad", "assets", "logo.png"),
    os.path.join("rad", "d2xx_bridge.py"),
    os.path.join("rad", "j2534_bridge.py"),
    os.path.join("rad", "simulator.py"),
    os.path.join("runtime", "py32", "python.exe"),
    os.path.join("runtime", "py64", "python.exe"),
    "THIRD_PARTY.txt",
]
# Runtime do Visual C++ 2015-2022 (64 bits): o Python e o Qt dependem destas DLL. Num PC sem o "Visual C++
# Redistributable" instalado só existem se forem com o programa.
MSVC_RUNTIME = ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll"]


def _msvc_sources():
    """Pastas onde estão as DLL do Visual C++ que vêm com o Python e com o PySide6 desta máquina de build."""
    dirs = [sys.base_prefix, os.path.dirname(sys.executable)]
    try:
        import PySide6
        dirs.append(os.path.dirname(PySide6.__file__))
    except ImportError:
        pass
    try:
        import shiboken6
        dirs.append(os.path.dirname(shiboken6.__file__))
    except ImportError:
        pass
    return [d for d in dirs if os.path.isdir(d)]


def complete_msvc_runtime(dist, log=print):
    """Copia para a pasta compilada as DLL do Visual C++ que lá faltarem. Devolve as que continuam em falta."""
    missing = []
    for name in MSVC_RUNTIME:
        if os.path.exists(os.path.join(dist, name)):
            continue
        src = next((os.path.join(d, name) for d in _msvc_sources() if os.path.exists(os.path.join(d, name))), None)
        if src:
            shutil.copy2(src, os.path.join(dist, name))
            log(f"  + {name} (copiada de {os.path.dirname(src)})")
        else:
            missing.append(name)
    # As três primeiras são obrigatórias; as msvcp140_1/_2 só existem em algumas versões do Qt.
    return [n for n in missing if n in MSVC_RUNTIME[:3]]


def check(dist, log=print):
    if not os.path.isdir(dist):
        log(f"A pasta {dist} não existe.")
        return False
    log("A completar o runtime do Visual C++…")
    still = complete_msvc_runtime(dist, log)
    ok = True
    for name in still:
        log(f"  FALTA {name}: instale o 'Microsoft Visual C++ Redistributable' de 64 bits NO PC DE BUILD e repita.")
        ok = False
    for rel in REQUIRED:
        if not os.path.exists(os.path.join(dist, rel)):
            log(f"  FALTA {rel}")
            ok = False
    qt_platform = glob.glob(os.path.join(dist, "**", "platforms", "qwindows*.dll"), recursive=True)
    if not qt_platform:
        log("  FALTA o plugin do Qt para Windows (platforms\\qwindows.dll): a janela não abriria.")
        ok = False
    log("Pasta compilada completa." if ok else "A pasta compilada está incompleta: o instalador NÃO deve ser criado.")
    return ok


PORTABLE_README = """Roots Auto Doctor {version} — versão portátil

PORTUGUÊS
1. Extraia esta pasta para onde quiser (Ambiente de trabalho, Documentos ou uma pen USB).
2. Abra RootsAutoDoctor.exe. Não é preciso instalar nada.
3. Se o Windows mostrar "O Windows protegeu o seu PC", carregue em "Mais informações" e depois em
   "Executar mesmo assim".
Os diagnósticos, a licença e o logótipo da oficina ficam guardados neste PC (pasta %APPDATA%\\RootsAutoDoctor).
Para criar atalhos no menu Iniciar e no ambiente de trabalho, use o instalador (Setup_RootsAutoDoctor_{version}.exe).

ENGLISH
1. Extract this folder anywhere (Desktop, Documents or a USB stick).
2. Open RootsAutoDoctor.exe. Nothing else needs to be installed.
3. If Windows shows "Windows protected your PC", click "More info" and then "Run anyway".
Diagnostics, the licence and the workshop logo are stored on this PC (%APPDATA%\\RootsAutoDoctor folder).
For Start menu and desktop shortcuts, use the installer (Setup_RootsAutoDoctor_{version}.exe).
"""


def portable(dist, version, out_dir=None, log=print):
    """Zip com a pasta "Roots Auto Doctor" pronta a usar (extrair e abrir o .exe)."""
    out_dir = out_dir or os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"RootsAutoDoctor_{version}_portatil.zip")
    top = "Roots Auto Doctor"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, _dirs, files in os.walk(dist):
            for name in files:
                full = os.path.join(folder, name)
                z.write(full, os.path.join(top, os.path.relpath(full, dist)))
        z.writestr(f"{top}/LEIA-ME.txt", PORTABLE_README.format(version=version).replace("\n", "\r\n"))
    log(f"Versão portátil pronta em {path} ({os.path.getsize(path) / 1e6:.0f} MB)")
    return path


SANDBOX = """<Configuration>
  <!-- Teste num Windows limpo (Windows Sandbox, Windows 10/11 Pro): abre um Windows acabado de instalar,
       sem Python, sem Visual C++ e sem drivers, com o programa compilado e corre o auto-teste.
       O resultado fica em build\\pc_limpo\\autoteste.txt. Depois pode abrir o programa à mão na janela. -->
  <MappedFolders>
    <MappedFolder>
      <HostFolder>{dist}</HostFolder>
      <SandboxFolder>C:\\RootsAutoDoctor</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>{result}</HostFolder>
      <SandboxFolder>C:\\Resultado</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>{command}</Command>
  </LogonCommand>
</Configuration>
"""


SANDBOX_COMMAND = ('cmd /c start "" /wait C:\\RootsAutoDoctor\\RootsAutoDoctor.exe '
                   '--selftest C:\\Resultado\\autoteste.txt')


def sandbox(dist, log=print):
    dist = os.path.abspath(dist)
    result = os.path.join(ROOT, "build", "pc_limpo")
    os.makedirs(result, exist_ok=True)
    path = os.path.join(ROOT, "build", "teste_pc_limpo.wsb")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SANDBOX.format(dist=dist, result=result, command=SANDBOX_COMMAND))
    log(f"Teste em PC limpo: abra {path} (precisa do Windows Sandbox activo).")
    return path


def sign(setup, version, secret=None, log=print):
    """Assina o instalador para as actualizações automáticas: cria <setup>.sig ao lado. Sem a chave privada
    (tools/update_key.py genkey) não assina e avisa: os clientes recebem só o aviso de versão nova."""
    sys.path.insert(0, ROOT)
    from rad import autoupdate
    import update_key
    secret = secret or update_key.read_secret()
    if secret is None:
        log(f"AVISO: sem chave de actualizações ({update_key.key_path()}): o instalador não foi assinado e os "
            "programas instalados não se vão actualizar sozinhos com esta versão (só avisam).")
        return None
    sig = autoupdate.make_signature(secret, setup, version)
    if not autoupdate.verify_file(setup, sig, version, autoupdate.ed25519.public_key(secret)):
        raise RuntimeError("A assinatura criada não se verifica")
    path = setup + ".sig"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sig, fh, indent=1)
    log(f"Instalador assinado: {path}")
    return path


TIMESTAMP_URL = "http://timestamp.digicert.com"


def find_signtool(environ=None):
    """signtool.exe do Windows SDK (o mais recente instalado), ou None."""
    environ = os.environ if environ is None else environ
    if environ.get("RAD_SIGNTOOL"):
        return environ["RAD_SIGNTOOL"] if os.path.exists(environ["RAD_SIGNTOOL"]) else None
    found = shutil.which("signtool")
    if found:
        return found
    roots = [environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             environ.get("ProgramFiles", r"C:\Program Files")]
    candidates = []
    for root in roots:
        candidates += glob.glob(os.path.join(root, "Windows Kits", "10", "bin", "*", "x64", "signtool.exe"))
    return sorted(candidates)[-1] if candidates else None


def codesign_command(path, environ=None, signtool=None):
    """A linha de comando do signtool para este ficheiro, ou None se não houver certificado configurado."""
    environ = os.environ if environ is None else environ
    pfx, thumb = environ.get("RAD_CODESIGN_PFX"), environ.get("RAD_CODESIGN_THUMBPRINT")
    if not pfx and not thumb:
        return None
    cmd = [signtool or "signtool", "sign", "/fd", "SHA256",
           "/tr", environ.get("RAD_CODESIGN_TIMESTAMP") or TIMESTAMP_URL, "/td", "SHA256", "/d", "Roots Auto Doctor"]
    if pfx:
        cmd += ["/f", pfx]
        if environ.get("RAD_CODESIGN_PASSWORD"):
            cmd += ["/p", environ["RAD_CODESIGN_PASSWORD"]]
    else:
        cmd += ["/sha1", thumb]
    return cmd + [path]


def codesign(path, environ=None, run=None, log=print):
    """Assina o .exe com Authenticode. Devolve True (assinado), None (sem certificado: não assina) ou levanta
    RuntimeError se o certificado está configurado mas a assinatura falhou (o build não pode continuar)."""
    import subprocess
    environ = os.environ if environ is None else environ
    if not (environ.get("RAD_CODESIGN_PFX") or environ.get("RAD_CODESIGN_THUMBPRINT")):
        log(f"AVISO: sem certificado de assinatura de código: {os.path.basename(path)} não foi assinado "
            "(o Windows mostra o aviso do SmartScreen na primeira vez).")
        return None
    tool = find_signtool(environ)
    if tool is None:
        raise RuntimeError("Certificado configurado, mas o signtool.exe não foi encontrado (instale o Windows SDK "
                           "ou indique-o em RAD_SIGNTOOL).")
    cmd = codesign_command(path, environ, tool)
    res = (run or subprocess.run)(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        output = (res.stdout or "") + (res.stderr or "")
        raise RuntimeError(f"A assinatura de {os.path.basename(path)} falhou: {output}")
    log(f"{os.path.basename(path)} assinado (Authenticode).")
    return True


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "portable", "sandbox", "sign", "codesign"):
        print(__doc__)
        return 2
    cmd, dist = argv[0], argv[1]
    if cmd == "codesign":
        try:
            codesign(dist)
        except RuntimeError as e:
            print(e)
            return 1
        return 0
    if cmd == "check":
        return 0 if check(dist) else 1
    if cmd == "sign":
        if len(argv) < 3:
            print("Falta a versão.")
            return 2
        sign(dist, argv[2])
        return 0
    if cmd == "portable":
        if len(argv) < 3:
            print("Falta a versão.")
            return 2
        portable(dist, argv[2])
        return 0
    sandbox(dist)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
