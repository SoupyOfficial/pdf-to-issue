@echo off
REM GitLab Issue Queue Bot - Windows Batch Runner
REM This script makes it easy to run the bot on Windows

setlocal enabledelayedexpansion

echo 🤖 GitLab Issue Queue Bot
echo =========================

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found. Please run setup.ps1 first.
    echo    powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
    pause
    exit /b 1
)

REM Load environment variables from .env file
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%%"=="#" (
        set %%a=%%b
    )
)

REM Check if required variables are set
if "%GITLAB_TOKEN%"=="" (
    echo ❌ GITLAB_TOKEN not set in .env file
    pause
    exit /b 1
)

if "%PROJECT_ID%"=="" (
    echo ❌ PROJECT_ID not set in .env file
    pause
    exit /b 1
)

echo ✅ Configuration loaded
echo 📋 Project ID: %PROJECT_ID%
echo 🏷️  Label: %LABEL%

REM Check command line arguments
if "%1"=="test" (
    echo 🧪 Running connection test...
    python scripts\test_gitlab.py
    pause
    exit /b
)

if "%1"=="continuous" (
    echo 🔄 Starting continuous mode...
    echo Press Ctrl+C to stop
    python scripts\promote_next.py --continuous
    exit /b
)

if "%1"=="daemon" (
    echo 🔄 Starting daemon mode...
    echo Press Ctrl+C to stop  
    python scripts\promote_next.py --daemon
    exit /b
)

REM Default: single run
echo 🚀 Running single promotion check...
python scripts\promote_next.py

echo.
echo ✅ Done! Check logs\promote_next.log for details
pause
