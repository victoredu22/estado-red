# Script para deshabilitar las actualizaciones automáticas de Windows Update
Write-Host "Deshabilitando servicios de Windows Update..." -ForegroundColor Yellow

# 1. Detener y deshabilitar wuauserv
Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
Set-Service -Name wuauserv -StartupType Disabled -ErrorAction SilentlyContinue

# 2. Detener y deshabilitar UsoSvc
Stop-Service -Name UsoSvc -Force -ErrorAction SilentlyContinue
Set-Service -Name UsoSvc -StartupType Disabled -ErrorAction SilentlyContinue

# 3. Aplicar política en el Registro de Windows
$registryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
if (-not (Test-Path $registryPath)) {
    New-Item -Path $registryPath -Force | Out-Null
}
Set-ItemProperty -Path $registryPath -Name "NoAutoUpdate" -Value 1 -Type DWord

Write-Host "✅ Actualizaciones de Windows deshabilitadas correctamente." -ForegroundColor Green
Start-Sleep -Seconds 3
