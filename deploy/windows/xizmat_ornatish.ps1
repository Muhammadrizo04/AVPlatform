# waitress'ni Windows xizmati (AV-platforma) qilib o'rnatadi. Administrator PowerShell'da:
#   powershell -ExecutionPolicy Bypass -File E:\AVPlatform\deploy\windows\xizmat_ornatish.ps1 -Nssm E:\AVPlatform-malumot\nssm\nssm.exe
# NSSM (https://nssm.cc) win64\nssm.exe ni oldindan E:\AVPlatform-malumot\nssm\ ga qo'ying.
param([Parameter(Mandatory = $true)][string]$Nssm)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"

if (-not (Test-Path $Nssm)) { throw "NSSM topilmadi: $Nssm" }
if (-not (Test-Path "$Venv\Scripts\waitress-serve.exe")) { throw "waitress yo'q: $Venv da 'pip install -r requirements.txt' bajaring" }
New-Item -ItemType Directory -Force $Loglar | Out-Null

if (Get-Service $Xizmat -ErrorAction SilentlyContinue) {
    & $Nssm stop $Xizmat | Out-Null
    & $Nssm remove $Xizmat confirm | Out-Null
}
# Parametrlar (port, oqimlar, timeout, ishonchli proksi 127.0.0.1) — waitress_xizmat.py da
& $Nssm install $Xizmat $Python "deploy\windows\waitress_xizmat.py"
& $Nssm set $Xizmat AppDirectory $Ilova
& $Nssm set $Xizmat AppEnvironmentExtra "AV_ICHKI_PORT=$IchkiPort"
& $Nssm set $Xizmat DisplayName "AV platformasi (waitress)"
& $Nssm set $Xizmat Start SERVICE_AUTO_START
& $Nssm set $Xizmat AppStdout "$Loglar\waitress.log"
& $Nssm set $Xizmat AppStderr "$Loglar\waitress.log"
& $Nssm set $Xizmat AppRotateFiles 1
& $Nssm set $Xizmat AppRotateBytes 10485760
& $Nssm set $Xizmat AppExit Default Restart
& $Nssm start $Xizmat

# Kirish sahifasi yo'naltirishsiz 200 qaytaradi (PowerShell 5.1 da -MaximumRedirection 0 302 ni tushunarsiz xatoga aylantiradi)
Start-Sleep -Seconds 5
try {
    $j = Invoke-WebRequest "http://127.0.0.1:$IchkiPort/kirish/" -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    Write-Host "waitress ishlayapti: /kirish/ -> $($j.StatusCode)"
} catch {
    throw "waitress javob bermadi: $($_.Exception.Message). Holat: $((Get-Service $Xizmat).Status). Logni ko'ring: $Loglar\waitress.log"
}
