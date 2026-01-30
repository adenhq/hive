@echo off
REM Hive Interactive CLI Launcher
REM ==============================

echo ======================================================================
echo HIVE INTERACTIVE CLI - Starting...
echo ======================================================================
echo.

REM Clear proxy settings that cause issues
set HTTP_PROXY=
set HTTPS_PROXY=

REM Navigate to Hive directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found
    echo Please create .env file with your API credentials
    pause
    exit /b 1
)

echo [OK] Environment ready
echo.

REM Run the CLI
python hive_cli.py

REM Pause if there was an error
if errorlevel 1 (
    echo.
    echo [ERROR] CLI exited with error
    pause
)
