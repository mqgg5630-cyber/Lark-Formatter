@echo off
setlocal EnableExtensions
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

call "%~dp0conda_env.bat"
if not "%LARK_CONDA_STATUS%"=="READY" goto :missing_env

if defined LARK_CONDA_PYW (
    start "" /B "%LARK_CONDA_PYW%" main.py
    exit /b 0
)

rem pythonw.exe missing: fall back to python.exe (a console window stays open)
"%LARK_CONDA_PY%" main.py
exit /b %errorlevel%

:missing_env
echo [ERROR] Conda environment "%LARK_CONDA_ENV%" was not found.
echo Run "install_env.bat" first.
pause
exit /b 1
