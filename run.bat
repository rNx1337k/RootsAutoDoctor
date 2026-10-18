@echo off
REM Abre o Roots Auto Doctor. Na primeira vez instala o Python necessario (PySide6, pyserial).
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
    echo A preparar o Roots Auto Doctor pela primeira vez, aguarde...
    python -m venv .venv || (echo Instale o Python 3.10+ e marque "Add Python to PATH". & pause & exit /b 1)
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt || (pause & exit /b 1)
)
REM pythonw abre so a janela do programa, sem a consola preta
start "" ".venv\Scripts\pythonw.exe" main.py
