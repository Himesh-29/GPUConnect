@echo off
REM ============================================
REM  GPU Connect Agent — Linux Package Builder
REM  Run this on Windows to create a zip package
REM  that you transfer to any Linux machine.
REM  Usage: build_linux.bat
REM ============================================

echo.
echo ========================================
echo   Packaging GPU Connect Agent for Linux
echo ========================================
echo.

cd /d "%~dp0"

REM Clean previous builds
if exist dist rmdir /s /q dist
mkdir dist\gpu-connect-agent-linux

REM Copy files into package
copy /Y ..\agent_ollama.py       dist\gpu-connect-agent-linux\ >nul
copy /Y requirements.txt         dist\gpu-connect-agent-linux\ >nul
copy /Y install.sh               dist\gpu-connect-agent-linux\ >nul
copy /Y uninstall.sh             dist\gpu-connect-agent-linux\ >nul
copy /Y README.md                dist\gpu-connect-agent-linux\ >nul

REM Create zip using PowerShell
powershell -Command "Compress-Archive -Path 'dist\gpu-connect-agent-linux\*' -DestinationPath 'dist\gpu-connect-agent-linux.zip' -Force"

if exist dist\gpu-connect-agent-linux.zip (
    echo.
    echo [OK] Package built: dist\gpu-connect-agent-linux.zip
    echo.
    echo Transfer to your Linux machine:
    echo   scp dist\gpu-connect-agent-linux.zip user@^<host-ip^>:~/
    echo.
    echo Then on the machine:
    echo   unzip gpu-connect-agent-linux.zip -d gpu-connect-agent
    echo   cd gpu-connect-agent
    echo   chmod +x install.sh uninstall.sh
    echo   sudo ./install.sh
    echo.
) else (
    echo [FAIL] Package build failed!
    exit /b 1
)

echo ========================================
echo   Package Complete!
echo ========================================
echo.
