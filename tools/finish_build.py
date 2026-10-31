"""Últimos passos do build de venda (chamado pelo build_release.bat). O objectivo é um só: o programa compilado
tem de abrir à primeira em qualquer PC com Windows 10/11 de 64 bits, sem instalar mais nada.

    python tools\\finish_build.py check    <pasta>          completa e verifica a pasta compilada
    python tools\\finish_build.py portable <pasta> <versão> cria dist\\RootsAutoDoctor_<versão>_portatil.zip
    python tools\\finish_build.py sandbox  <pasta>          cria build\\teste_pc_limpo.wsb (Windows Sandbox)

check: copia para a pasta as DLL do Visual C++ (vcruntime/msvcp) que o Python e o Qt usam, se o compilador não
as tiver posto lá (num PC limpo não existem e o programa não abria), e confirma que estão lá todos os ficheiros
de que o programa precisa. Sai com código 1 se faltar alguma coisa.
"""
import glob
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
    <Command>cmd /c start "" /wait C:\\RootsAutoDoctor\\RootsAutoDoctor.exe --selftest C:\\Resultado\\autoteste.txt</Command>
  </LogonCommand>
</Configuration>
"""


def sandbox(dist, log=print):
    dist = os.path.abspath(dist)
    result = os.path.join(ROOT, "build", "pc_limpo")
    os.makedirs(result, exist_ok=True)
    path = os.path.join(ROOT, "build", "teste_pc_limpo.wsb")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SANDBOX.format(dist=dist, result=result))
    log(f"Teste em PC limpo: abra {path} (precisa do Windows Sandbox activo).")
    return path


def main(argv):
    if len(argv) < 2 or argv[0] not in ("check", "portable", "sandbox"):
        print(__doc__)
        return 2
    cmd, dist = argv[0], argv[1]
    if cmd == "check":
        return 0 if check(dist) else 1
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
