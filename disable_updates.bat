@echo off
chcp 65001 > nul
echo ==================================================
echo   Deshabilitando Actualizaciones de Windows Update
echo ==================================================
echo.

:: Verificar permisos de Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Este script debe ejecutarse como ADMINISTRADOR.
    echo Por favor, haz clic derecho sobre este archivo y selecciona "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)

echo [1/3] Deteniendo y deshabilitando servicio Windows Update (wuauserv)...
sc config wuauserv start= disabled > nul 2>&1
net stop wuauserv > nul 2>&1

echo [2/3] Deteniendo y deshabilitando servicio Update Orchestrator (UsoSvc)...
sc config UsoSvc start= disabled > nul 2>&1
net stop UsoSvc > nul 2>&1

echo [3/3] Aplicando directiva en el Registro de Windows...
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v "NoAutoUpdate" /t REG_DWORD /d 1 /f > nul 2>&1

echo.
echo ==================================================
echo ✅ ¡Actualizaciones de Windows deshabilitadas!
echo ==================================================
echo.
pause
