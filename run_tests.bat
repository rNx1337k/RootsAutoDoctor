@echo off
REM Corre todos os testes automáticos (não precisa de carro)
REM Para correr só alguns: run_tests.bat history   (filtra pelo nome)
cd /d "%~dp0"
if exist .venv call .venv\Scripts\activate.bat
python tests\run_all.py %1
echo.
pause
