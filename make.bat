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
if "%1"=="test-backend" goto test-backend
if "%1"=="test-frontend" goto test-frontend
if "%1"=="test-cov" goto test-cov
if "%1"=="test-backend-cov" goto test-backend-cov
if "%1"=="test-frontend-cov" goto test-frontend-cov
if "%1"=="lint" goto lint
if "%1"=="lint-backend" goto lint-backend
if "%1"=="lint-frontend" goto lint-frontend
if "%1"=="migrate" goto migrate
if "%1"=="makemigrations" goto makemigrations
if "%1"=="celery" goto celery
if "%1"=="help" goto help
echo Unknown target: %1
goto help

:agent
echo Building GPU Connect Agent (Windows)...
cd agent\windows
pyinstaller --clean --onefile --name gpu-connect-agent ..\agent_ollama.py --distpath . --noconfirm
if exist gpu-connect-agent.exe (
    copy /Y gpu-connect-agent.exe ..\..\frontend\public\downloads\gpu-connect.exe >nul 2>&1
    echo ✅ Agent built: agent/windows/gpu-connect-agent.exe
    echo ✅ Copied to frontend/public/downloads/gpu-connect.exe
) else (
    echo ❌ Build failed!
    cd ..\..
    exit /b 1
)
if exist build rmdir /s /q build
if exist gpu-connect-agent.spec del gpu-connect-agent.spec
cd ..\..

echo Building Linux package...
cd agent\linux
call build_linux.bat
if exist dist\gpu-connect-agent-linux.zip (
    copy /Y dist\gpu-connect-agent-linux.zip ..\..\frontend\public\downloads\ >nul 2>&1
    echo ✅ Linux package copied to frontend/public/downloads/
)
cd ..\..

echo Building macOS package...
cd agent\macos
call build_macos.bat
if exist dist\gpu-connect-agent-macos.zip (
    copy /Y dist\gpu-connect-agent-macos.zip ..\..\frontend\public\downloads\ >nul 2>&1
    echo ✅ macOS package copied to frontend/public/downloads/
)
cd ..\..
goto end

:clean
cd agent\windows
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist gpu-connect-agent.spec del gpu-connect-agent.spec
cd ..
if exist __pycache__ rmdir /s /q __pycache__
cd linux
if exist dist rmdir /s /q dist
cd ..\macos
if exist dist rmdir /s /q dist
cd ..\..
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
call "%~f0" test-backend
call "%~f0" test-frontend
goto end

:test-backend
echo Running backend tests...
cd backend
uv run pytest -v
cd ..
goto end

:test-frontend
echo Running frontend tests...
cd frontend
call npm run test
cd ..
goto end

:test-cov
call "%~f0" test-backend-cov
call "%~f0" test-frontend-cov
goto end

:test-backend-cov
echo Running backend tests with coverage...
cd backend
uv run pytest --cov=. --cov-report=term-missing --cov-report=html
cd ..
goto end

:test-frontend-cov
echo Running frontend tests with coverage...
cd frontend
call npm run test:coverage
cd ..
goto end

:lint
call "%~f0" lint-backend
call "%~f0" lint-frontend
goto end

:lint-backend
echo Linting backend...
cd backend
uv run pylint computing core payments config
cd ..
goto end

:lint-frontend
echo Linting frontend...
cd frontend
call npm run lint
cd ..
goto end

:migrate
echo Applying database migrations...
cd backend
uv run python manage.py migrate
cd ..
goto end

:makemigrations
echo Creating database migrations...
cd backend
uv run python manage.py makemigrations
cd ..
goto end

:celery
echo Starting Celery worker...
start cmd /k "cd backend && uv run celery -A config worker -l info"
goto end

:help
echo.
echo  GPU Connect - Build Commands
echo  ============================
echo  make agent             Build standalone agent .exe
echo  make clean             Remove build artifacts
echo  make dev               Start backend + frontend servers
echo  make help              Show this message
echo.
echo  Testing Commands:
echo  make test              Run all tests
echo  make test-backend      Run backend tests
echo  make test-frontend     Run frontend tests
echo  make test-cov          Run all tests with coverage
echo  make test-backend-cov  Run backend tests with coverage
echo  make test-frontend-cov Run frontend tests with coverage
echo.
echo  Linting Commands:
echo  make lint              Run all linters
echo  make lint-backend      Run backend linter
echo  make lint-frontend     Run frontend linter
echo.
echo  Database & Tools:
echo  make migrate           Apply complete migrations
echo  make makemigrations    Create new migrations
echo  make celery            Start celery worker
echo.
goto end

:end
