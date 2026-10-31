@echo off
REM Gera as capturas de ecra do README (docs\screenshots) com o simulador, em portugues e em ingles.
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (echo Abra primeiro o run.bat uma vez para preparar o programa. & pause & exit /b 1)
.venv\Scripts\python.exe tools\screenshots.py > build\capturas.txt 2>&1
.venv\Scripts\python.exe tools\screenshots.py --en >> build\capturas.txt 2>&1
echo Terminado. Resultado em build\capturas.txt
