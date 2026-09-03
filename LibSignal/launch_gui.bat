@echo off
chcp 65001 > nul
title SUMO Traffic Signal Control - GUI Launcher

cd /d "%~dp0"

echo ========================================================
echo   SUMO Traffic Signal Control - Giao dien dieu khien
echo ========================================================
echo Dang kiem tra moi truong va khoi dong giao dien...

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" gui.py
    if errorlevel 1 (
        ".venv\Scripts\python.exe" gui.py
    )
) else (
    start "" pythonw gui.py
    if errorlevel 1 (
        python gui.py
    )
)
exit
