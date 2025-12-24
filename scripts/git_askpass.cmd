@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0git_askpass.ps1" %*
exit /b %ERRORLEVEL%
