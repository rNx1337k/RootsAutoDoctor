@echo off
REM Obsoleto: o executavel e o instalador oficiais sao gerados pelo build_release.bat (Nuitka + Inno Setup),
REM que tambem verifica o programa compilado. Este ficheiro so encaminha para la.
cd /d "%~dp0"
echo O build_exe.bat foi substituido pelo build_release.bat.
call build_release.bat
