@echo off
title MEGA-ULTRA-ROBOTER-KI - PayPal Webhook Server
cd /d "%~dp0"

echo ========================================================
echo   START PAYPAL WEBHOOK SERVER (FastAPI)
echo ========================================================
echo.
echo Webhook URL (for PayPal dashboard):
echo   http://YOUR_PUBLIC_URL/paypal/webhook
echo.
echo Local health check:
echo   http://127.0.0.1:8503/health
echo.

python webhook_server.py

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: Webhook server stopped.
  pause
)
