@echo off
setlocal enabledelayedexpansion
title Agent Arvyn - Diagnostic Bootloader

:: ==========================================
:: 1. ADMINISTRATIVE PRIVILEGE CHECK
:: ==========================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] WARNING: Running without Administrative privileges. 
    echo [!] SAPI5 Offline Voice may have limited functionality.
    echo.
)

:: ==========================================
:: 2. ENVIRONMENT PRE-FLIGHT CHECKS
:: ==========================================
echo [SYSTEM] Scanning local environment...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ is required but not found in PATH.
    pause
    exit /b
)

:: Check for .env file
if not exist ".env" (
    echo [ERROR] .env file missing! Create one with your GEMINI_API_KEY.
    pause
    exit /b
)

:: ==========================================
:: 3. DEPENDENCY SYNCING (Clean Install)
:: ==========================================
echo [SYSTEM] Syncing Neuro-Symbolic dependencies...
:: Ensure pip is up to date
python -m pip install --upgrade pip --quiet

:: Use the explicit requirements list
python -m pip install -r requirements.txt --quiet

:: Force install specific SDKs to avoid SyntaxErrors
python -m pip install google-genai qasync --upgrade --quiet

:: ==========================================
:: 4. KINETIC LAYER INITIALIZATION
:: ==========================================
echo [SYSTEM] Initializing Playwright (The "Hands")...
python -m playwright install chromium

:: ==========================================
:: 5. MISSION START
:: ==========================================
echo.
echo [SUCCESS] Systems Validated. 
echo [SYSTEM] Launching Arvyn GUI...
echo.

:: Run with detailed console logging as requested
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [CRITICAL] Arvyn exited with Error Code: %errorlevel%
    echo [DEBUG] Check logs/arvyn_debug.log for details.
    pause
)

exit /b