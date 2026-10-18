@echo off
REM Gera RootsAutoDoctor.exe (pasta dist\RootsAutoDoctor)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name RootsAutoDoctor --icon rad\assets\icon.ico --add-data "rad\assets;rad\assets" main.py
echo.
echo Executavel em dist\RootsAutoDoctor\RootsAutoDoctor.exe
pause
