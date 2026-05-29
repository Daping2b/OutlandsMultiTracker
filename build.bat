@echo off
title Outlands Multi Tracker — Build
color 0E
echo.
echo  ================================================
echo   Outlands Multi Tracker  —  Build Script
echo   by Daping
echo  ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Please install Python 3.11+ from: https://www.python.org/downloads/
    echo  IMPORTANT: Check "Add Python to PATH" during install
    echo.
    pause & exit /b 1
)
echo  [OK] Python found:
python --version
echo.

echo  [1/4] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter Pillow matplotlib numpy pystray tkcalendar pyinstaller babel --quiet
if errorlevel 1 (echo  [ERROR] Failed to install dependencies. & pause & exit /b 1)
echo  [OK] Dependencies installed.
echo.

echo  [2/4] Building .exe with PyInstaller...
if exist "dist\OutlandsMultiTracker" rmdir /s /q "dist\OutlandsMultiTracker"
if exist "build" rmdir /s /q "build"

python -m PyInstaller OMT.spec --noconfirm
if errorlevel 1 (echo. & echo  [ERROR] Build failed. & pause & exit /b 1)

echo.
echo  [3/4] Copying required files to dist...
set "DIST=dist\OutlandsMultiTracker"

if not exist "%DIST%\data" mkdir "%DIST%\data"

xcopy /E /I /Y "assets"   "%DIST%\assets"   >nul
xcopy /E /I /Y "config"   "%DIST%\config"   >nul
xcopy /E /I /Y "scripts"  "%DIST%\scripts"  >nul
copy /Y "_update_apply.bat" "%DIST%\_update_apply.bat" >nul

echo  [OK] Files copied.
echo.
echo  ================================================
echo  [4/4] Build complete!
echo.
echo  Your portable dist is in:
echo  %DIST%\
echo.
echo  Rename the folder to OutlandsMultiTrackerV{version}
echo  Zip it and upload to GitHub Releases as OutlandsMultiTracker.zip
echo  ================================================
echo.
pause
