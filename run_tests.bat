@echo off
REM Corre todos os testes automáticos (não precisa de carro)
cd /d "%~dp0"
if exist .venv call .venv\Scripts\activate.bat
python tests\test_simulator.py && python tests\test_history.py && python tests\test_guided.py && python tests\test_license.py && python tests\test_cable.py && python tests\test_robustness.py
echo.
pause
