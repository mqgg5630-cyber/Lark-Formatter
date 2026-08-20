@echo off
rem =====================================================================
rem Lark-Formatter conda environment resolver (shared helper).
rem Invoked with `call` from the other scripts in this folder.
rem
rem Sets the following variables for the caller:
rem   LARK_CONDA_ENV     environment name (default: lark-f; override with LARK_FORMATTER_ENV_NAME)
rem   LARK_CONDA_EXE     conda executable (empty when LARK_CONDA_STATUS=NO_CONDA)
rem   LARK_CONDA_ROOT    conda base installation directory
rem   LARK_CONDA_PREFIX  environment prefix (empty when LARK_CONDA_STATUS=NO_ENV)
rem   LARK_CONDA_PY      python.exe inside the environment (empty unless READY)
rem   LARK_CONDA_PYW     pythonw.exe inside the environment (may stay empty)
rem   LARK_CONDA_STATUS  READY | NO_CONDA | NO_ENV
rem
rem Prefix lookup order:
rem   1. LARK_FORMATTER_ENV_DIR environment variable (explicit override)
rem   2. .conda_env_path.txt next to the repo root (cache written by install_env.bat)
rem   3. `conda env list` output (handles any custom envs_dirs configuration)
rem   4. Well-known locations under the conda base and the user profile
rem
rem No setlocal here: the variables must propagate to the calling script.

set "LARK_CONDA_ENV=lark-f"
if defined LARK_FORMATTER_ENV_NAME set "LARK_CONDA_ENV=%LARK_FORMATTER_ENV_NAME%"
set "LARK_CONDA_EXE="
set "LARK_CONDA_ROOT="
set "LARK_CONDA_PREFIX="
set "LARK_CONDA_PY="
set "LARK_CONDA_PYW="
set "LARK_CONDA_STATUS=NO_CONDA"

set "LARK_REPO_ROOT=%~dp0..\.."
for %%I in ("%LARK_REPO_ROOT%") do set "LARK_REPO_ROOT=%%~fI"

rem ---- 1) Locate the conda executable ----------------------------------
for /f "delims=" %%C in ('where conda 2^>nul') do if not defined LARK_CONDA_EXE set "LARK_CONDA_EXE=%%C"
if not defined LARK_CONDA_EXE if defined LARK_FORMATTER_CONDA_EXE if exist "%LARK_FORMATTER_CONDA_EXE%" set "LARK_CONDA_EXE=%LARK_FORMATTER_CONDA_EXE%"
if not defined LARK_CONDA_EXE if defined CONDA_EXE if exist "%CONDA_EXE%" set "LARK_CONDA_EXE=%CONDA_EXE%"
if not defined LARK_CONDA_EXE for %%R in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%USERPROFILE%\miniforge3" "%ProgramData%\anaconda3" "%ProgramData%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%LOCALAPPDATA%\miniconda3" "%LOCALAPPDATA%\miniforge3") do (
    if not defined LARK_CONDA_EXE if exist "%%~R\Scripts\conda.exe" set "LARK_CONDA_EXE=%%~R\Scripts\conda.exe"
)

if not defined LARK_CONDA_EXE goto :eof

rem ---- 2) Derive the conda base directory ------------------------------
for %%I in ("%LARK_CONDA_EXE%") do set "LARK_CONDA_BIN_DIR=%%~dpI"
for %%I in ("%LARK_CONDA_BIN_DIR%..") do set "LARK_CONDA_ROOT=%%~fI"

set "LARK_CONDA_STATUS=NO_ENV"

rem ---- 3) Resolve the environment prefix -------------------------------
rem 3a) explicit override
if defined LARK_FORMATTER_ENV_DIR call :check_prefix "%LARK_FORMATTER_ENV_DIR%"
rem 3b) cached prefix written by install_env.bat
if not defined LARK_CONDA_PREFIX if exist "%LARK_REPO_ROOT%\.conda_env_path.txt" for /f "usebackq delims=" %%P in ("%LARK_REPO_ROOT%\.conda_env_path.txt") do call :check_prefix "%%P"
rem 3c) ask conda (handles any custom envs_dirs configuration).
rem     Each matching line ends with the environment path; iterating the line's
rem     whitespace tokens keeps only the last one (the path itself).
if not defined LARK_CONDA_PREFIX for /f "usebackq delims=" %%L in (`call "%LARK_CONDA_EXE%" env list 2^>nul ^| findstr /r /i /c:"^%LARK_CONDA_ENV% "`) do for %%P in (%%L) do set "LARK_CONDA_CANDIDATE=%%P"
if not defined LARK_CONDA_PREFIX if defined LARK_CONDA_CANDIDATE call :check_prefix "%LARK_CONDA_CANDIDATE%"
set "LARK_CONDA_CANDIDATE="
if not defined LARK_CONDA_PREFIX for /f "usebackq delims=" %%L in (`call "%LARK_CONDA_EXE%" env list 2^>nul ^| findstr /r /i /c:"\%LARK_CONDA_ENV%$"`) do for %%P in (%%L) do set "LARK_CONDA_CANDIDATE=%%P"
if not defined LARK_CONDA_PREFIX if defined LARK_CONDA_CANDIDATE call :check_prefix "%LARK_CONDA_CANDIDATE%"
set "LARK_CONDA_CANDIDATE="
rem 3d) well-known locations
if not defined LARK_CONDA_PREFIX for %%D in ("%LARK_CONDA_ROOT%\envs\%LARK_CONDA_ENV%" "%LARK_CONDA_ROOT%\Library\envs\%LARK_CONDA_ENV%" "%USERPROFILE%\.conda\envs\%LARK_CONDA_ENV%") do call :check_prefix "%%~D"

if not defined LARK_CONDA_PREFIX goto :eof

rem ---- 4) Resolve the interpreters -------------------------------------
if exist "%LARK_CONDA_PREFIX%\Scripts\python.exe" (
    set "LARK_CONDA_PY=%LARK_CONDA_PREFIX%\Scripts\python.exe"
) else (
    set "LARK_CONDA_PY=%LARK_CONDA_PREFIX%\python.exe"
)
if exist "%LARK_CONDA_PREFIX%\Scripts\pythonw.exe" (
    set "LARK_CONDA_PYW=%LARK_CONDA_PREFIX%\Scripts\pythonw.exe"
) else (
    if exist "%LARK_CONDA_PREFIX%\pythonw.exe" set "LARK_CONDA_PYW=%LARK_CONDA_PREFIX%\pythonw.exe"
)
if not exist "%LARK_CONDA_PY%" (
    set "LARK_CONDA_PY="
    set "LARK_CONDA_PREFIX="
    goto :eof
)
set "LARK_CONDA_STATUS=READY"
goto :eof

:check_prefix
rem %1 = candidate environment prefix; accept it when it holds a python.exe
if defined LARK_CONDA_PREFIX goto :eof
if not exist "%~1\python.exe" if not exist "%~1\Scripts\python.exe" goto :eof
set "LARK_CONDA_PREFIX=%~1"
goto :eof
