@echo off
REM ============================================================
REM  Publicar uma versao compilada pelo GitHub Actions (Release em rascunho)
REM  1) descarrega o instalador e a versao portatil da Release v<versao>
REM  2) assina o instalador com o certificado de codigo, se estiver configurado (tools\finish_build.py codesign)
REM  3) cria as assinaturas das actualizacoes automaticas (.sig) com a chave privada deste PC
REM  4) envia o instalador e os .sig para a Release, poe as novidades (docs\NOVIDADES.md) e publica-a
REM  Uso: tools\publicar_release.bat 1.12.0
REM  Precisa do GitHub CLI (winget install GitHub.cli) com sessao iniciada (gh auth login).
REM ============================================================
cd /d "%~dp0\.."
set VER=%~1
if "%VER%"=="" (echo Uso: tools\publicar_release.bat ^<versao^> & exit /b 1)
set PY=.venv\Scripts\python.exe
if not exist %PY% (echo Corra primeiro o run.bat uma vez. & exit /b 1)
where gh >nul 2>nul || (echo Falta o GitHub CLI: winget install GitHub.cli e depois gh auth login & exit /b 1)
if not exist dist mkdir dist
set SETUP=dist\Setup_RootsAutoDoctor_%VER%.exe
set ZIP=dist\RootsAutoDoctor_%VER%_portatil.zip
gh release download v%VER% --pattern "Setup_RootsAutoDoctor_%VER%.exe" --dir dist --clobber || (echo Nao foi possivel descarregar o instalador da Release v%VER%. & exit /b 1)
gh release download v%VER% --pattern "RootsAutoDoctor_%VER%_portatil.zip" --dir dist --clobber || (echo Nao foi possivel descarregar a versao portatil da Release v%VER%. & exit /b 1)
%PY% tools\finish_build.py codesign %SETUP% || exit /b 1
if exist %SETUP%.sig del %SETUP%.sig
if exist %ZIP%.sig del %ZIP%.sig
%PY% tools\finish_build.py sign %SETUP% %VER% || exit /b 1
if not exist %SETUP%.sig (echo Sem a chave das actualizacoes neste PC: a Release NAO foi publicada. & exit /b 1)
%PY% tools\finish_build.py sign %ZIP% %VER% || exit /b 1
if not exist build mkdir build
%PY% tools\finish_build.py notes %VER% build\novidades_%VER%.md || exit /b 1
gh release upload v%VER% %SETUP% %SETUP%.sig %ZIP%.sig --clobber || (echo Nao foi possivel enviar os ficheiros. & exit /b 1)
gh release edit v%VER% --notes-file build\novidades_%VER%.md || exit /b 1
gh release edit v%VER% --draft=false || exit /b 1
echo.
echo Release v%VER% publicada: os programas instalados e portateis actualizam-se sozinhos.
