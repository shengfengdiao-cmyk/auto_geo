@echo off
REM ========================================
REM AutoGeo Project Launcher
REM Maintainer: Xiao A
REM Version: v2.8.0
REM Updated: 2026-02-03
REM ========================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

cls

echo.
echo ========================================
echo    AutoGeo Launcher v2.7.0
echo ========================================
echo.

:menu_loop
echo.
echo Please select an option:
echo.
echo   [1] Start Backend Service
echo   [2] Start Frontend Electron App
echo   [3] Restart Backend Service
echo   [4] Restart Frontend Service
echo   [5] Cleanup Project
echo   [6] Exit (Close All Services)
echo.
echo ========================================
echo.

set /p choice="Enter option (1-6): "

if "%choice%"=="1" goto start_backend
if "%choice%"=="2" goto start_frontend
if "%choice%"=="3" goto restart_backend
if "%choice%"=="4" goto restart_frontend
if "%choice%"=="5" goto cleanup_menu
if "%choice%"=="6" goto exit_all

echo.
echo [ERROR] Invalid option, please try again!
echo.
timeout /t 2 /nobreak >nul
cls
goto menu_loop

REM ========================================
REM Start Backend Service
REM ========================================
:start_backend
echo.
echo ========================================
echo    Starting Backend Service
echo ========================================
echo.

REM Check if backend is already running
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Backend is already running!
    echo.
    set /p override="Restart anyway? (Y/N): "
    if /i not "%override%"=="Y" (
        goto menu_loop
    )
    echo.
    echo Stopping existing backend service...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM Check backend dependencies
echo Checking backend dependencies...
if not exist "backend\requirements.txt" (
    echo [ERROR] backend\requirements.txt not found!
    pause
    goto menu_loop
)

if not exist "backend\database" (
    echo [INFO] Creating backend\database directory...
    mkdir "backend\database" 2>nul
)

echo.
echo Starting backend service...
echo.
echo   - Backend: http://127.0.0.1:8001
echo   - API Docs: http://127.0.0.1:8001/docs
echo.

cd backend
start "AutoGeo-Backend" cmd /k "python main.py"
cd ..

echo.
echo [OK] Backend service started in new window!
echo.
timeout /t 3 /nobreak >nul
cls
goto menu_loop

REM ========================================
REM Start Frontend Service
REM ========================================
:start_frontend
echo.
echo ========================================
echo    Starting Frontend App
echo ========================================
echo.

REM Check if frontend is already running
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Frontend is already running!
    echo.
    set /p override="Restart anyway? (Y/N): "
    if /i not "%override%"=="Y" (
        goto menu_loop
    )
    echo.
    echo Stopping existing frontend service...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM Check frontend dependencies
echo Checking frontend dependencies...
if not exist "fronted\package.json" (
    echo [ERROR] fronted\package.json not found!
    pause
    goto menu_loop
)

if not exist "fronted\node_modules" (
    echo [WARNING] node_modules not found!
    echo.
    echo Frontend dependencies not installed.
    echo Please run manually: cd fronted ^&^& npm install
    echo.
    pause
    goto menu_loop
)

echo.
echo Starting frontend Electron app...
echo.
echo   - Frontend: http://127.0.0.1:5173
echo.

cd fronted
start "AutoGeo-Frontend" cmd /k "npm run dev"
cd ..

echo.
echo [OK] Frontend app started in new window!
echo.
timeout /t 3 /nobreak >nul
cls
goto menu_loop

REM ========================================
REM Restart Backend Service
REM ========================================
:restart_backend
echo.
echo ========================================
echo    Restarting Backend Service
echo ========================================
echo.

echo Stopping backend service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
if errorlevel 1 (
    echo [INFO] Backend service was not running
) else (
    echo [OK] Backend service stopped
)

timeout /t 2 /nobreak >nul
echo.
echo Starting backend service...
echo.

cd backend
start "AutoGeo-Backend" cmd /k "python main.py"
cd ..

timeout /t 3 /nobreak >nul
echo.
echo [OK] Backend service restarted!
echo.
timeout /t 2 /nobreak >nul
cls
goto menu_loop

REM ========================================
REM Restart Frontend Service
REM ========================================
:restart_frontend
echo.
echo ========================================
echo    Restarting Frontend Service
echo ========================================
echo.

echo Stopping frontend service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
if errorlevel 1 (
    echo [INFO] Frontend service was not running
) else (
    echo [OK] Frontend service stopped
)

timeout /t 2 /nobreak >nul
echo.
echo Starting frontend service...
echo.

cd fronted
start "AutoGeo-Frontend" cmd /k "npm run dev"
cd ..

timeout /t 3 /nobreak >nul
echo.
echo [OK] Frontend service restarted!
echo.
timeout /t 2 /nobreak >nul
cls
goto menu_loop

REM ========================================
REM Cleanup Menu
REM ========================================
:cleanup_menu
cls
echo.
echo ========================================
echo    Cleanup Project
echo ========================================
echo.
echo Select cleanup option:
echo.
echo   [1] Quick Cleanup (Safe)
echo   [2] Full Cleanup (Aggressive)
echo   [3] Back to Main Menu
echo.
echo ========================================
echo.

set /p cleanup_choice="Enter option (1-3): "

if "%cleanup_choice%"=="1" goto quick_cleanup
if "%cleanup_choice%"=="2" goto full_cleanup
if "%cleanup_choice%"=="3" goto menu_loop

echo.
echo [ERROR] Invalid option!
echo.
timeout /t 2 /nobreak >nul
goto cleanup_menu

REM ========================================
REM Quick Cleanup
REM ========================================
:quick_cleanup
cls
echo.
echo ========================================
echo    Quick Cleanup (Safe)
echo ========================================
echo.
echo This will remove:
echo   - Python cache files (__pycache__, *.pyc)
echo   - Node.js cache (.vite)
echo   - Database temporary files (.wal, .shm)
echo   - Log files (*.log)
echo   - OS temporary files (.DS_Store, Thumbs.db)
echo.
echo [SAFE] This will NOT delete:
echo   - node_modules (can be restored with npm install)
echo   - Database files (.db)
echo   - Configuration files
echo.
set /p confirm="Continue with quick cleanup? (Y/N): "
if /i not "%confirm%"=="Y" goto cleanup_menu

echo.
echo Starting quick cleanup...
echo.

REM Python cache
echo Cleaning Python cache...
for /d /r %%d in (__pycache__) do @if exist "%%d" (
    rd /s /q "%%d" 2>nul
)
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
echo   [OK] Python cache cleaned

REM Node.js cache
echo Cleaning Node.js cache...
if exist "fronted\.vite" (
    rd /s /q "fronted\.vite" 2>nul
    echo   [OK] Vite cache cleaned
)

REM Database temp files
echo Cleaning database temporary files...
if exist "backend\database\*.wal" del /s /q "backend\database\*.wal" 2>nul
if exist "backend\database\*.shm" del /s /q "backend\database\*.shm" 2>nul
echo   [OK] Database temp files cleaned

REM Log files
echo Cleaning log files...
if exist "logs\*.log" del /s /q "logs\*.log" 2>nul
echo   [OK] Log files cleaned

REM OS temporary files
echo Cleaning OS temporary files...
del /s /q .DS_Store 2>nul
del /s /q Thumbs.db 2>nul
del /s /q desktop.ini 2>nul
echo   [OK] OS temporary files cleaned

REM Test cache
echo Cleaning test cache...
for /d /r %%d in (.pytest_cache) do @if exist "%%d" (
    rd /s /q "%%d" 2>nul
)
del /s /q .coverage 2>nul
if exist "htmlcov" rd /s /q htmlcov 2>nul
echo   [OK] Test cache cleaned

echo.
echo ========================================
echo [OK] Quick cleanup completed!
echo ========================================
echo.
pause
goto cleanup_menu

REM ========================================
REM Full Cleanup
REM ========================================
:full_cleanup
cls
echo.
echo ========================================
echo    Full Cleanup (Aggressive)
echo ========================================
echo.
echo This will remove EVERYTHING that can be restored:
echo   - All Quick Cleanup items
echo   - node_modules (can be restored with: npm install)
echo   - Python virtual environments
echo   - Build artifacts (dist, build)
echo   - IDE cache (.idea)
echo.
echo [WARNING] After cleanup, you need to reinstall dependencies!
echo.
set /p confirm="Are you sure you want to continue? (Y/N): "
if /i not "%confirm%"=="Y" goto cleanup_menu

echo.
echo Starting full cleanup...
echo.

REM Run quick cleanup first
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
if exist "fronted\.vite" rd /s /q "fronted\.vite" 2>nul
if exist "backend\database\*.wal" del /s /q "backend\database\*.wal" 2>nul
if exist "backend\database\*.shm" del /s /q "backend\database\*.shm" 2>nul
if exist "logs\*.log" del /s /q "logs\*.log" 2>nul
del /s /q .DS_Store 2>nul
del /s /q Thumbs.db 2>nul
del /s /q desktop.ini 2>nul
for /d /r %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q .coverage 2>nul
if exist "htmlcov" rd /s /q htmlcov 2>nul

REM Node.js dependencies
echo.
echo Removing node_modules...
if exist "fronted\node_modules" (
    rd /s /q "fronted\node_modules" 2>nul
    echo   [OK] node_modules removed
)

REM Python cache and virtual env
echo Cleaning Python environments...
for /d /r %%d in (.venv venv env) do @if exist "%%d" (
    rd /s /q "%%d" 2>nul
)
echo   [OK] Python virtual environments cleaned

REM Build artifacts
echo Cleaning build artifacts...
if exist "fronted\dist" (
    rd /s /q "fronted\dist" 2>nul
    echo   [OK] dist folder removed
)
if exist "fronted\build" (
    rd /s /q "fronted\build" 2>nul
    echo   [OK] build folder removed
)

REM IDE cache
echo Cleaning IDE cache...
if exist ".idea" (
    rd /s /q ".idea" 2>nul
    echo   [OK] .idea folder removed
)

echo.
echo ========================================
echo [OK] Full cleanup completed!
echo ========================================
echo.
echo To restore dependencies, run:
echo   cd fronted ^&^& npm install
echo   cd ..\backend ^&^& pip install -r requirements.txt
echo   playwright install chromium
echo.
pause
goto cleanup_menu

REM ========================================
REM Exit (Close All Services)
REM ========================================
:exit_all
echo.
echo ========================================
echo    Exit Program
echo ========================================
echo.

set /p confirm="Close all services and windows? (Y/N): "
if /i not "%confirm%"=="Y" (
    cls
    goto menu_loop
)

echo.
echo Closing all services and windows...
echo.

REM Close backend by port
echo Closing backend service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Close frontend by port
echo Closing frontend service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Close windows by exact window title
echo Closing backend window...
taskkill /FI "WINDOWTITLE eq AutoGeo-Backend" /F >nul 2>&1

echo Closing frontend window...
taskkill /FI "WINDOWTITLE eq AutoGeo-Frontend" /F >nul 2>&1

timeout /t 2 /nobreak >nul

REM Force close any remaining windows
echo Force closing any remaining windows...
taskkill /IM cmd.exe /FI "WINDOWTITLE eq AutoGeo*" /F >nul 2>&1

echo.
echo [OK] All services and windows closed!
echo.
echo Press any key to exit...
pause >nul

exit
