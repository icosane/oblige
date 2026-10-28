@echo off
chcp 65001 >nul
rem ---------------------------------------------------------------
rem  Replaces JP lines in script_jp with EN lines from script_en.
rem  Result goes into a NEW folder: script_out
rem  Put this .bat and replace_jp_with_en.py next to the two folders
rem  (or pass paths:  replace_jp_with_en.bat jp_dir en_dir out_dir)
rem ---------------------------------------------------------------
setlocal
set "JP=%~1"
set "EN=%~2"
set "OUT=%~3"
if "%JP%"=="" set "JP=script_jp"
if "%EN%"=="" set "EN=script_en"
if "%OUT%"=="" set "OUT=script_out"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)

python "%~dp0replace_jp_with_en.py" "%JP%" "%EN%" "%OUT%"
echo.
pause
