@echo off
REM ============================================================
REM  Passa uma versao de teste (publicada com publicar_release.bat <versao> teste) para todos os clientes.
REM  Uso: tools\promover_release.bat 1.13.0
REM ============================================================
cd /d "%~dp0\.."
set VER=%~1
if "%VER%"=="" (echo Uso: tools\promover_release.bat ^<versao^> & exit /b 1)
where gh >nul 2>nul || (echo Falta o GitHub CLI: winget install GitHub.cli e depois gh auth login & exit /b 1)
gh release edit v%VER% --draft=false --prerelease=false --latest || (echo Nao foi possivel promover a v%VER%. & exit /b 1)
echo.
echo v%VER% publicada para todos: os programas instalados e portateis actualizam-se sozinhos.
