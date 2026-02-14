@echo off
REM ============================================
REM  GPU Connect — Windows Make Script
REM  Usage: make agent | clean | dev | test
REM ============================================

if "%1"=="" goto help
if "%1"=="agent" goto agent
if "%1"=="clean" goto clean
if "%1"=="dev" goto dev
if "%1"=="test" goto test
if "%1"=="help" goto help
echo Unknown target: %1
goto help

:agent
echo Building GPU Connect Agent...
cd agent
pyinstaller --clean --onefile --name gpu-connect-agent agent_ollama.py --distpath . --noconfirm
if exist gpu-connect-agent.exe (
    copy /Y gpu-connect-agent.exe ..\frontend\public\downloads\gpu-connect.exe >nul 2>&1
    echo ✅ Agent built: agent/gpu-connect-agent.exe
    echo ✅ Copied to frontend/public/downloads/gpu-connect.exe
) else (
    echo ❌ Build failed!
    cd ..
    exit /b 1
)
if exist build rmdir /s /q build
if exist gpu-connect-agent.spec del gpu-connect-agent.spec
cd ..
goto end

:clean
cd agent
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist gpu-connect-agent.spec del gpu-connect-agent.spec
if exist __pycache__ rmdir /s /q __pycache__
cd ..
echo 🧹 Cleaned build artifacts
goto end

:dev
echo Starting backend...
start cmd /k "cd backend && uv run python manage.py runserver 0.0.0.0:8000"
echo Starting frontend...
start cmd /k "cd frontend && npm run dev"
echo 🚀 Dev servers started
goto end

:test
cd backend
uv run pytest -v
cd ..
goto end

:help
echo.
echo  GPU Connect — Build Commands
echo  ============================
echo  make agent    Build standalone agent .exe
echo  make clean    Remove build artifacts
echo  make dev      Start backend + frontend servers
echo  make test     Run backend test suite
echo  make help     Show this message
echo.
goto end

:end
