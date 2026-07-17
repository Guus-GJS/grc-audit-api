@echo off
cd /d "%~dp0"

echo.
echo ==========================================
echo   GRC Audit Database Update
echo ==========================================
echo.

python maak_database.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo UPDATE MISLUKT
    echo Controleer de foutmelding hierboven.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ==========================================
echo UPDATE SUCCESVOL
echo De nieuwe grc_audit.db staat in de hoofdmap.
echo ==========================================
pause