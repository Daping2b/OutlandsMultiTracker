@echo off
:: Outlands Multi Tracker — Auto Updater
:: Launched by the app after download, runs after exe closes

title O-MT Updater
set "BASE=%~dp0"
set "ZIP=%BASE%_update.zip"
set "TMP=%BASE%_update_tmp"
set "VBS=%BASE%_extract.vbs"

:: Wait for main exe to fully close
timeout /t 3 /nobreak >nul

:: Write VBScript extractor (works on all Windows, no policy restrictions)
echo Set fso = CreateObject("Scripting.FileSystemObject") > "%VBS%"
echo Set shell = CreateObject("Shell.Application") >> "%VBS%"
echo zipFile = "%ZIP%" >> "%VBS%"
echo outFolder = "%TMP%" >> "%VBS%"
echo If Not fso.FolderExists(outFolder) Then fso.CreateFolder(outFolder) End If >> "%VBS%"
echo Set zip = shell.NameSpace(zipFile) >> "%VBS%"
echo Set dest = shell.NameSpace(outFolder) >> "%VBS%"
echo dest.CopyHere zip.Items(), 4 + 16 >> "%VBS%"
echo WScript.Sleep 3000 >> "%VBS%"

:: Run VBScript extractor
cscript //nologo "%VBS%"
del /f /q "%VBS%" 2>nul

:: Find source folder inside extracted zip
set "SRC=%TMP%"
for /d %%i in ("%TMP%\*") do set "SRC=%%i"

:: Copy all files except data/ and config/settings.json using robocopy
robocopy "%SRC%" "%BASE%" /E /XD "%SRC%\data" /XF "%SRC%\config\settings.json" /NFL /NDL /NJH /NJS /NP

:: Cleanup
rmdir /s /q "%TMP%" 2>nul
del /f /q "%ZIP%" 2>nul

:: Relaunch exe
for %%f in ("%BASE%OutlandsMultiTracker.exe") do (
    if exist "%%f" (
        start "" "%%f"
        goto :done
    )
)
:: Fallback: find any exe
for %%f in ("%BASE%*.exe") do (
    start "" "%%f"
    goto :done
)
:done

:: Self-delete
(goto) 2>nul & del "%~f0"
