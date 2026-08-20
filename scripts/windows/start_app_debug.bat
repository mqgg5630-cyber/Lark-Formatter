@echo off
setlocal EnableExtensions
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

call "%~dp0conda_env.bat"
if not "%LARK_CONDA_STATUS%"=="READY" (
    echo [ERROR] Conda environment "%LARK_CONDA_ENV%" was not found.
    echo Run "install_env.bat" first.
    pause
    exit /b 1
)

echo [INFO] Starting app in debug mode (console output enabled)...
echo [INFO] Python: %LARK_CONDA_PY%
"%LARK_CONDA_PY%" main.py
exit /b %errorlevel%
