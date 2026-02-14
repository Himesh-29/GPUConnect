@echo off
REM ============================================
REM  GPU Connect Agent — macOS Package Builder
REM  Run this on Windows to create a zip package
REM  that you transfer to any Mac.
REM  Usage: build_macos.bat
REM ============================================

echo.
echo ========================================
echo   Packaging GPU Connect Agent for macOS
echo ========================================
echo.

cd /d "%~dp0"

REM Clean previous builds
if exist dist rmdir /s /q dist
mkdir dist\gpu-connect-agent-macos

REM Copy files into package
copy /Y ..\agent_ollama.py       dist\gpu-connect-agent-macos\ >nul
copy /Y requirements.txt         dist\gpu-connect-agent-macos\ >nul
copy /Y install.sh               dist\gpu-connect-agent-macos\ >nul
copy /Y uninstall.sh             dist\gpu-connect-agent-macos\ >nul
copy /Y README.md                dist\gpu-connect-agent-macos\ >nul

REM Create zip using PowerShell
powershell -Command "Compress-Archive -Path 'dist\gpu-connect-agent-macos\*' -DestinationPath 'dist\gpu-connect-agent-macos.zip' -Force"

if exist dist\gpu-connect-agent-macos.zip (
    echo.
    echo [OK] Package built: dist\gpu-connect-agent-macos.zip
    echo.
    echo Transfer to your Mac:
    echo   scp dist\gpu-connect-agent-macos.zip user@^<mac-ip^>:~/
    echo.
    echo Then on the Mac:
    echo   unzip gpu-connect-agent-macos.zip -d gpu-connect-agent
    echo   cd gpu-connect-agent
    echo   chmod +x install.sh uninstall.sh
    echo   ./install.sh
    echo.
) else (
    echo [FAIL] Package build failed!
    exit /b 1
)

echo ========================================
echo   Package Complete!
echo ========================================
echo.
