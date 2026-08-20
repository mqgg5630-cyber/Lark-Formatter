@echo off
setlocal
call "%~dp0start_app.bat" %*
exit /b %errorlevel%
