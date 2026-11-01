@echo off
REM ============================================================
REM  Roots Auto Doctor - build de venda
REM  1) compila com Nuitka (codigo maquina, dificil de copiar)
REM  2) completa e verifica a pasta (runtime do Visual C++, plugins do Qt, pontes)
REM  3) verifica o programa compilado com o auto-teste (--selftest)
REM  4) cria a versao portatil (zip) e o instalador com Inno Setup (https://jrsoftware.org/isdl.php)
REM  Resultado: dist\Setup_RootsAutoDoctor_<versao>.exe e dist\RootsAutoDoctor_<versao>_portatil.zip
REM  Assinatura de codigo (opcional, tira o aviso do SmartScreen): ver "codesign" em tools\finish_build.py
REM  No GitHub Actions (variavel CI definida) nao para a pedir teclas.
REM  Os dois levam tudo (Python, Qt, Visual C++, pontes): no PC da oficina nao e preciso instalar nada.
REM  Driver dos cabos FTDI (opcional): ver installer\drivers\LEIA-ME.txt
REM  Actualizacoes automaticas: uma vez, "python tools\update_key.py genkey"; depois cada instalador sai
REM  assinado (Setup_...exe.sig) - publique os dois na Release do GitHub.
REM ============================================================
cd /d "%~dp0"
REM "cd ." nao faz nada (rem nao serve: comentaria o resto da linha, incluindo o "exit")
if defined CI (set "PAUSE=cd .") else (set "PAUSE=pause")
if not exist .venv\Scripts\python.exe (echo Corra primeiro o run.bat uma vez. & %PAUSE% & exit /b 1)
set PY=.venv\Scripts\python.exe
for /f "delims=" %%v in ('%PY% -c "import rad; print(rad.VERSION)"') do set VER=%%v
%PY% -c "from rad.update_pubkey import UPDATE_PUBLIC_KEY as K; import sys; sys.exit(0 if K else 1)" || echo AVISO: actualizacoes automaticas desligadas nesta versao (falta "python tools\update_key.py genkey").
echo A preparar o Python portatil para as pontes D2XX/J2534...
%PY% tools\get_runtime.py
if errorlevel 1 (echo Nao foi possivel preparar a pasta runtime. & %PAUSE% & exit /b 1)
echo A instalar as ferramentas de build (versoes fixas em requirements-build.txt)...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 (echo Nao foi possivel instalar as ferramentas de build. & %PAUSE% & exit /b 1)
REM Apaga o resultado do build anterior: assim nunca sobra um ficheiro de uma versao antiga.
if exist build\main.dist rmdir /s /q build\main.dist
if exist build\main.dist (echo Nao foi possivel apagar build\main.dist: feche o programa compilado. & %PAUSE% & exit /b 1)
echo A compilar a versao %VER%...
%PY% -m nuitka main.py --standalone --enable-plugin=pyside6 ^
  --windows-console-mode=disable --windows-icon-from-ico=rad\assets\icon.ico ^
  --include-data-dir=rad\assets=rad\assets ^
  --output-dir=build --output-filename=RootsAutoDoctor.exe ^
  --company-name="Roots" --product-name="Roots Auto Doctor" ^
  --file-version=%VER% --product-version=%VER% --file-description="Roots Auto Doctor" ^
  --assume-yes-for-downloads --remove-output
if errorlevel 1 (echo A compilacao falhou. & %PAUSE% & exit /b 1)
copy /y LICENSES\THIRD_PARTY.txt build\main.dist\ >nul
REM Pontes D2XX/J2534: correm no Python portatil (runtime\py32 ou py64), por isso vao como ficheiros .py,
REM com o simulador ao lado (portas simuladas). O Python portatil vai inteiro para a pasta runtime.
if not exist build\main.dist\rad mkdir build\main.dist\rad
for %%f in (__init__.py simulator.py d2xx_bridge.py j2534_bridge.py) do copy /y rad\%%f build\main.dist\rad\ >nul
xcopy /e /i /y /q runtime build\main.dist\runtime >nul
if errorlevel 1 (echo Falhou a copia da pasta runtime. & %PAUSE% & exit /b 1)
echo A completar e verificar a pasta compilada...
%PY% tools\finish_build.py check build\main.dist
if errorlevel 1 (echo A pasta compilada esta incompleta: o instalador NAO foi criado. & %PAUSE% & exit /b 1)
echo A verificar o programa compilado (auto-teste)...
if exist build\autoteste_build.txt del build\autoteste_build.txt
start "" /wait build\main.dist\RootsAutoDoctor.exe --selftest "%CD%\build\autoteste_build.txt"
if errorlevel 1 (
  if exist build\autoteste_build.txt type build\autoteste_build.txt
  echo O auto-teste do programa compilado falhou: o instalador NAO foi criado.
  %PAUSE% & exit /b 1
)
type build\autoteste_build.txt
%PY% tools\finish_build.py codesign build\main.dist\RootsAutoDoctor.exe
if errorlevel 1 (echo A assinatura de codigo falhou. & %PAUSE% & exit /b 1)
%PY% tools\finish_build.py sandbox build\main.dist
if exist dist\RootsAutoDoctor_%VER%_portatil.zip del dist\RootsAutoDoctor_%VER%_portatil.zip
%PY% tools\finish_build.py portable build\main.dist %VER%
if errorlevel 1 (echo Nao foi possivel criar a versao portatil. & %PAUSE% & exit /b 1)
if not exist installer\drivers\ftdi\ftdibus.inf echo AVISO: sem o driver FTDI em installer\drivers\ftdi - o instalador sai sem ele (ver installer\drivers\LEIA-ME.txt).
REM Inno Setup 6: instalacao para todos os utilizadores ou so para o utilizador actual
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Programa compilado e verificado em build\main.dist\RootsAutoDoctor.exe
  echo Versao portatil pronta em dist\RootsAutoDoctor_%VER%_portatil.zip
  echo Para criar o instalador instale o Inno Setup 6 e volte a correr este ficheiro.
  %PAUSE% & exit /b 0
)
%ISCC% /DAppVersion=%VER% installer\RootsAutoDoctor.iss
if errorlevel 1 (echo A criacao do instalador falhou. & %PAUSE% & exit /b 1)
%PY% tools\finish_build.py codesign dist\Setup_RootsAutoDoctor_%VER%.exe
if errorlevel 1 (echo A assinatura de codigo do instalador falhou. & %PAUSE% & exit /b 1)
REM A assinatura das actualizacoes (.sig) vem depois da Authenticode: cobre o ficheiro final
%PY% tools\finish_build.py sign dist\Setup_RootsAutoDoctor_%VER%.exe %VER%
if errorlevel 1 (echo Nao foi possivel assinar o instalador. & %PAUSE% & exit /b 1)
echo.
echo Instalador pronto em dist\Setup_RootsAutoDoctor_%VER%.exe
if exist dist\Setup_RootsAutoDoctor_%VER%.exe.sig echo Assinatura em dist\Setup_RootsAutoDoctor_%VER%.exe.sig - publique-a na Release junto com o instalador.
echo Versao portatil pronta em dist\RootsAutoDoctor_%VER%_portatil.zip
echo Teste num Windows limpo (opcional): abra build\teste_pc_limpo.wsb
%PAUSE%
