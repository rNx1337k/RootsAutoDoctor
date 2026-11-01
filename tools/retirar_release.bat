@echo off
REM ============================================================
REM  Retira uma versao com problemas: volta a ser um rascunho, que os programas nao veem.
REM  - Os programas que ainda nao a instalaram deixam de a receber (a versao publicada anterior volta a ser a
REM    mais recente, e e mais antiga do que a deles ou igual, por isso nao fazem nada).
REM  - Os que ja a instalaram ficam com ela ate sair uma versao nova: corrija, suba o numero da versao e publique.
REM    (Se a versao nao abrir num PC, esse programa volta sozinho a versao anterior.)
REM  Uso: tools\retirar_release.bat 1.13.0
REM ============================================================
cd /d "%~dp0\.."
set VER=%~1
if "%VER%"=="" (echo Uso: tools\retirar_release.bat ^<versao^> & exit /b 1)
where gh >nul 2>nul || (echo Falta o GitHub CLI: winget install GitHub.cli e depois gh auth login & exit /b 1)
gh release edit v%VER% --draft=true || (echo Nao foi possivel retirar a v%VER%. & exit /b 1)
echo.
echo v%VER% retirada: os programas deixam de a receber. Publique uma versao corrigida com um numero novo.
