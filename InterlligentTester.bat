@echo off
setlocal enabledelayedexpansion
set "CONTROLLER_IP=192.168.1.100"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please run this script as Administrator!
    pause
)


echo --- Final Remote Update Setup (GPO Aware) ---
echo.

for /f "tokens=4-5 delims=. " %%i in ('ver') do set "WIN_VER=%%i.%%j"
echo [INFO] Detected Windows Version: %WIN_VER%
set "PS_TLS=[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;"

echo [1/6] Changing Network Category to Private...
powershell -Command "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private"

echo [2/6] Configuring WinRM...
powershell -Command "Enable-PSRemoting -SkipNetworkProfileCheck -Force"
powershell -Command "Start-Service WinRM" 2>nul

echo [3/6] Setting TrustedHosts and CredSSP...
powershell -Command "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '%CONTROLLER_IP%' -Force"
powershell -Command "Enable-WSManCredSSP -Role Server -Force"

echo [4/6] Configuring Firewall...
powershell -Command "Enable-NetFirewallRule -DisplayGroup 'Windows Remote Management'"

echo [5/6] Setting TokenFilterPolicy (UAC Bypass)...
powershell -Command "if (-not (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System')) { New-Item -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Force }"
powershell -Command "New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name 'LocalAccountTokenFilterPolicy' -Value 1 -PropertyType DWord -Force" >nul 2>&1

echo [6/6] Verifying PSWindowsUpdate module...
powershell -Command "%PS_TLS% if (-not (Get-Module -ListAvailable PSWindowsUpdate)) { Write-Host 'Installing NuGet and PSWindowsUpdate...'; Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force; Install-Module -Name PSWindowsUpdate -Force -AllowClobber -Scope AllUsers } else { Write-Host 'Module already installed.' }"

echo.
echo --- Setup Finished! ---
echo IMPORTANT: Use CredSSP in your Python script to bypass Access Denied.
timeout /t 10
exit
