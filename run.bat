@echo off
REM Abre o Roots Auto Doctor a partir do codigo-fonte (desenvolvimento).
REM Para usar noutros PCs instale com o instalador gerado pelo build_release.bat: nao precisa de Python nem de internet.
cd /d "%~dp0"
set PREPARAR=0
set ATUALIZAR=0
if not exist .venv\Scripts\pythonw.exe set PREPARAR=1
REM Um .venv copiado de outro computador aponta para um Python que aqui nao existe: testa-se antes de usar.
if "%PREPARAR%"=="0" (
    .venv\Scripts\python.exe -c "import PySide6, serial" >nul 2>&1 || set PREPARAR=1
)
REM requirements.txt mudou desde a ultima instalacao: actualiza as dependencias.
if "%PREPARAR%"=="0" (
    fc /b requirements.txt .venv\requirements.instalado >nul 2>&1 || set ATUALIZAR=1
)
if "%PREPARAR%"=="1" (
    echo A preparar o Roots Auto Doctor neste PC, aguarde ^(alguns minutos, precisa de internet^)...
    if exist .venv rmdir /s /q .venv
    if exist .venv (echo Nao foi possivel apagar a pasta .venv antiga: feche as janelas do programa ou reinicie o PC. & pause & exit /b 1)
    py -3.13-64 -m venv .venv >nul 2>&1 || py -3-64 -m venv .venv >nul 2>&1 || python -m venv .venv || (echo Instale o Python 3.13 de 64 bits ^(python.org^) e marque "Add Python to PATH". & pause & exit /b 1)
    set ATUALIZAR=1
)
.venv\Scripts\python.exe -c "import struct, sys; sys.exit(struct.calcsize('P') != 8)" || (echo O Python usado e de 32 bits: instale o Python 3.13 de 64 bits ^(python.org^). & pause & exit /b 1)
if "%ATUALIZAR%"=="1" (
    echo A instalar as dependencias do programa...
    .venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt && copy /y requirements.txt .venv\requirements.instalado >nul || (
        if "%PREPARAR%"=="1" (echo Nao foi possivel instalar as dependencias ^(sem internet?^). & pause & exit /b 1)
        echo Nao foi possivel actualizar as dependencias ^(sem internet?^): o programa abre com as que ja estao instaladas.
    )
)
REM Python portatil de 32/64 bits para os cabos com driver de 32 bits (HEX-USB, J2534).
REM Sem internet o programa abre na mesma; so essas interfaces ficam sem funcionar.
.venv\Scripts\python.exe tools\get_runtime.py --check >nul 2>&1 || (
    echo A preparar o componente para interfaces de 32 bits...
    .venv\Scripts\python.exe tools\get_runtime.py
)
REM pythonw abre so a janela do programa, sem a consola preta
start "" ".venv\Scripts\pythonw.exe" main.py
