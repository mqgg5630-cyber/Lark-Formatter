@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO_ROOT=%~dp0..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

set "ENV_NAME=lark-f"
if defined LARK_FORMATTER_ENV_NAME set "ENV_NAME=%LARK_FORMATTER_ENV_NAME%"

rem Official channels by default: conda uses Anaconda's official "defaults"
rem channel, pip uses the official PyPI index. No mirrors are involved.
set "CHANNEL_ARGS=--override-channels -c defaults"
if defined LARK_FORMATTER_CONDA_CHANNEL_ARGS set "CHANNEL_ARGS=%LARK_FORMATTER_CONDA_CHANNEL_ARGS%"
set "PIP_INDEX_ARGS=-i https://pypi.org/simple"
if defined LARK_FORMATTER_PIP_INDEX_URL set "PIP_INDEX_ARGS=-i %LARK_FORMATTER_PIP_INDEX_URL%"

echo [1/5] Locating conda...
call "%~dp0conda_env.bat"
if "%LARK_CONDA_STATUS%"=="NO_CONDA" (
    echo [ERROR] conda was not found on PATH or in common install locations.
    echo         Open "Anaconda Prompt ^(base^)" and run this script again, or set
    echo         LARK_FORMATTER_CONDA_EXE to the full path of conda.exe.
    pause
    exit /b 1
)
echo [INFO] conda: %LARK_CONDA_EXE%
echo [INFO] conda base: %LARK_CONDA_ROOT%

if "%LARK_CONDA_STATUS%"=="READY" (
    echo [2/5] Conda environment "%ENV_NAME%" already exists: %LARK_CONDA_PREFIX%
) else (
    echo [2/5] Creating conda environment "%ENV_NAME%" ^(python 3.12, channel: defaults^)...
    call "%LARK_CONDA_EXE%" create -y %CHANNEL_ARGS% -n "%ENV_NAME%" python=3.12 pip
    if errorlevel 1 (
        echo [ERROR] Failed to create conda environment "%ENV_NAME%".
        echo         If conda reported a prefix that already exists, remove the broken
        echo         environment first with: conda env remove -n "%ENV_NAME%"
        echo         If conda printed a Terms-of-Service prompt above, run the suggested
        echo         "conda tos accept" command once, then retry.
        echo         To install from different channels, set LARK_FORMATTER_CONDA_CHANNEL_ARGS.
        pause
        exit /b 1
    )
    call "%~dp0conda_env.bat"
    if not "%LARK_CONDA_STATUS%"=="READY" (
        echo [ERROR] The environment was created but its location could not be resolved.
        echo         Ask conda directly with: conda env list
        pause
        exit /b 1
    )
)

echo [3/5] Environment path: %LARK_CONDA_PREFIX%
> "%REPO_ROOT%\.conda_env_path.txt" echo %LARK_CONDA_PREFIX%

echo [4/5] Installing dependencies from official PyPI ^(https://pypi.org/simple^)...
"%LARK_CONDA_PY%" -m pip install -r requirements.txt %PIP_INDEX_ARGS%
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [5/5] Verifying installation...
"%LARK_CONDA_PY%" -c "import sys; print('[INFO] ' + sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The environment interpreter is not working.
    pause
    exit /b 1
)
"%LARK_CONDA_PY%" -c "import PySide6, docx, lxml, latex2mathml, olefile, win32api" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency verification failed. Detailed import errors:
    "%LARK_CONDA_PY%" -c "import PySide6, docx, lxml, latex2mathml, olefile, win32api"
    pause
    exit /b 1
)

if exist ".venv" echo [NOTE] A legacy ".venv" folder exists in the repo root; it is no longer used and can be deleted.

echo [OK] Conda environment "%ENV_NAME%" is ready. Run "start_app.bat" to start the app.
exit /b 0
