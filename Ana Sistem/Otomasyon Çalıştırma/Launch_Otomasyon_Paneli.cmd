@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "VBS_FILE=%SCRIPT_DIR%Launch_Otomasyon_Paneli.vbs"
if exist "%VBS_FILE%" (
    wscript.exe "%VBS_FILE%"
) else (
    start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT_DIR%Launch_Otomasyon_Paneli.ps1"
)
endlocal
exit /b
