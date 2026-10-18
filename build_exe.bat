@echo off
REM Gera RootsAutoDoctor.exe (pasta dist\RootsAutoDoctor)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name RootsAutoDoctor main.py
echo.
echo Executavel em dist\RootsAutoDoctor\RootsAutoDoctor.exe
pause
