# IIS: «AV» sayti (https://av.dsyuksak.uz:8092) -> waitress. Administrator PowerShell'da, xizmat_ornatish.ps1 dan keyin.
# Oldindan o'rnating: IIS URL Rewrite 2.1 va Application Request Routing 3.0 (Microsoft sahifasidan).
# HTTPS bog'lanishini (8092) sertifikat bilan win-acme qo'shadi — docs\ishga-tushirish-windows.md, 6-bo'lim.
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"
Import-Module WebAdministration
$AppCmd = "$env:windir\System32\inetsrv\appcmd.exe"

if (-not (Test-Path "$env:windir\System32\inetsrv\rewrite.dll")) { throw "URL Rewrite o'rnatilmagan" }
if (-not (Get-WebConfiguration -Filter "system.webServer/proxy" -PSPath "MACHINE/WEBROOT/APPHOST" -ErrorAction SilentlyContinue)) {
    throw "Application Request Routing (ARR) o'rnatilmagan"
}

# ARR proksi: Host sarlavhasi saqlanadi (Django ALLOWED_HOSTS/CSRF uchun), X-Forwarded-For portsiz, kutish 120 s
& $AppCmd set config -section:system.webServer/proxy /enabled:"True" /preserveHostHeader:"True" `
    /includePortInXForwardedFor:"False" /reverseRewriteHostInResponseHeaders:"False" /timeout:"00:02:00" /commit:apphost
$bor = & $AppCmd list config -section:system.webServer/rewrite/allowedServerVariables
if (-not ($bor -match "HTTP_X_FORWARDED_PROTO")) {
    & $AppCmd set config -section:system.webServer/rewrite/allowedServerVariables /+"[name='HTTP_X_FORWARDED_PROTO']" /commit:apphost
}

# Statik fayllarni siqish moduli (web.config: urlCompression)
if ((Get-Command Install-WindowsFeature -ErrorAction SilentlyContinue) -and -not (Get-WindowsFeature Web-Stat-Compression).Installed) {
    Install-WindowsFeature Web-Stat-Compression | Out-Null
}

New-Item -ItemType Directory -Force $IisPapka | Out-Null
Copy-Item "$PSScriptRoot\web.config" "$IisPapka\web.config" -Force

if (-not (Test-Path "IIS:\AppPools\AV")) { New-WebAppPool -Name "AV" | Out-Null }
Set-ItemProperty "IIS:\AppPools\AV" -Name managedRuntimeVersion -Value ""   # .NET kerak emas
if (-not (Get-Website -Name "AV")) {
    # Vaqtinchalik HTTP bog'lanish faqat localhost uchun (tashqariga ochilmaydi); HTTPS 8092 ni win-acme qo'shadi
    New-Website -Name "AV" -PhysicalPath $IisPapka -ApplicationPool "AV" -IPAddress "127.0.0.1" -Port 8093 -HostHeader $Domen | Out-Null
}
if (-not (Get-WebVirtualDirectory -Site "AV" -Name "static")) {
    New-WebVirtualDirectory -Site "AV" -Name "static" -PhysicalPath "$Ilova\staticfiles" | Out-Null
}

# IIS ishchi jarayoni statik fayllarni o'qiy olsin
icacls "$Ilova\staticfiles" /grant "IIS AppPool\AV:(OI)(CI)RX" | Out-Null
icacls $IisPapka /grant "IIS AppPool\AV:(OI)(CI)RX" | Out-Null

if (-not (Get-NetFirewallRule -DisplayName "AV platformasi $Port" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "AV platformasi $Port" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
}
Write-Host "IIS sayti «AV» tayyor. Endi win-acme bilan sertifikat oling (HTTPS $Port)."
