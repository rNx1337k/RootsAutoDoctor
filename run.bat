@echo off
REM Abre o Roots Auto Doctor. Na primeira vez instala o Python necessario (PySide6, pyserial).
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
    echo A preparar o Roots Auto Doctor pela primeira vez, aguarde...
    python -m venv .venv || (echo Instale o Python 3.10+ e marque "Add Python to PATH". & pause & exit /b 1)
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt || (pause & exit /b 1)
)
REM Python portatil de 32/64 bits para os cabos com driver de 32 bits (HEX-USB, J2534).
REM Sem internet o programa abre na mesma; so essas interfaces ficam sem funcionar.
.venv\Scripts\python.exe tools\get_runtime.py --check >nul 2>&1 || (
    echo A preparar o componente para interfaces de 32 bits...
    .venv\Scripts\python.exe tools\get_runtime.py
)
REM pythonw abre so a janela do programa, sem a consola preta
start "" ".venv\Scripts\pythonw.exe" main.py
