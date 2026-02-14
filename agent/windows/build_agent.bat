@echo off
REM ============================================
REM  GPU Connect Agent — Build Script (Windows)
REM  Usage: build_agent.bat
REM ============================================

echo.
echo ========================================
echo   Building GPU Connect Agent...
echo ========================================
echo.

cd /d "%~dp0"

REM Build standalone .exe with PyInstaller
pyinstaller --clean --onefile --name gpu-connect-agent ..\agent_ollama.py --distpath . --noconfirm

REM Copy to frontend downloads folder for web distribution
if exist gpu-connect-agent.exe (
    echo.
    echo [OK] gpu-connect-agent.exe built successfully
    copy /Y gpu-connect-agent.exe ..\..\frontend\public\downloads\gpu-connect.exe >nul 2>&1
    echo [OK] Copied to frontend/public/downloads/gpu-connect.exe
) else (
    echo [FAIL] Build failed!
    exit /b 1
)

REM Cleanup PyInstaller artifacts
if exist build rmdir /s /q build
if exist gpu-connect-agent.spec del gpu-connect-agent.spec

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
