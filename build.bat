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
    pause & exit /b 1
)
echo  [OK] Python:
python --version

echo.
echo  [1/5] Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter Pillow matplotlib numpy pystray tkcalendar pyinstaller babel --quiet
if errorlevel 1 (echo [ERROR] & pause & exit /b 1)
echo  [OK] Dependencies installed.

echo.
echo  [2/5] Building main app...
if exist "dist\OutlandsMultiTracker" rmdir /s /q "dist\OutlandsMultiTracker"
if exist "build" rmdir /s /q "build"
python -m PyInstaller OMT.spec --noconfirm
if errorlevel 1 (echo [ERROR] Main build failed. & pause & exit /b 1)
echo  [OK] Main app built.

echo.
echo  [3/5] Building Updater.exe...
if exist "dist\Updater" rmdir /s /q "dist\Updater"
python -m PyInstaller Updater.spec --noconfirm
if errorlevel 1 (echo [ERROR] Updater build failed. & pause & exit /b 1)
echo  [OK] Updater built.

echo.
echo  [4/5] Copying required files into OutlandsMultiTracker...
set "DIST=dist\OutlandsMultiTracker"

if not exist "%DIST%\data" mkdir "%DIST%\data"
xcopy /E /I /Y "assets"   "%DIST%\assets"   >nul
xcopy /E /I /Y "config"   "%DIST%\config"   >nul
xcopy /E /I /Y "scripts"  "%DIST%\scripts"  >nul

:: Copy Updater.exe directly into OutlandsMultiTracker (not as subfolder)
copy /Y "dist\Updater\Updater.exe" "%DIST%\Updater.exe" >nul

echo  [OK] Files copied.

echo.
echo  ================================================
echo  [5/5] Build complete!
echo.
echo  Your portable dist is in: %DIST%\
echo.
echo  Zip it as OutlandsMultiTracker.zip
echo  Upload to GitHub Releases
echo  ================================================
echo.
pause
