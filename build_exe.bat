@echo off
REM Gera RootsAutoDoctor.exe (pasta dist\RootsAutoDoctor)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name RootsAutoDoctor --icon rad\assets\icon.ico --add-data "rad\assets;rad\assets" --add-data "rad\j2534_bridge.py;rad" --add-data "rad\d2xx_bridge.py;rad" main.py
echo.
echo Executavel em dist\RootsAutoDoctor\RootsAutoDoctor.exe
pause
