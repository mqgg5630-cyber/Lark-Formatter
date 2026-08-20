@echo off
setlocal
call "%~dp0install_env.bat" %*
exit /b %errorlevel%
