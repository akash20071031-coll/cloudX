@echo off
title SecureX Launcher

cd /d C:\Users\akash\Desktop\SecureX

call venv\Scripts\activate

cd backend

start "SecureX Backend" cmd /k "python -m uvicorn main:app --reload"

timeout /t 4 /nobreak >nul

start "" "C:\Users\akash\Desktop\SecureX\frontend\index.html"

exit