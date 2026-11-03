# waitress'ni Windows xizmati (AV-platforma) qilib o'rnatadi. Administrator PowerShell'da:
#   powershell -ExecutionPolicy Bypass -File E:\AVPlatform\deploy\windows\xizmat_ornatish.ps1 -Nssm E:\AVPlatform-malumot\nssm\nssm.exe
# NSSM (https://nssm.cc) win64\nssm.exe ni oldindan E:\AVPlatform-malumot\nssm\ ga qo'ying.
param([Parameter(Mandatory = $true)][string]$Nssm)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"

if (-not (Test-Path $Nssm)) { throw "NSSM topilmadi: $Nssm" }
$Waitress = "$Venv\Scripts\waitress-serve.exe"
if (-not (Test-Path $Waitress)) { throw "waitress yo'q: $Venv da 'pip install -r requirements.txt' bajaring" }
New-Item -ItemType Directory -Force $Loglar | Out-Null

if (Get-Service $Xizmat -ErrorAction SilentlyContinue) {
    & $Nssm stop $Xizmat | Out-Null
    & $Nssm remove $Xizmat confirm | Out-Null
}
# --channel-timeout 130: admin «Hozir sinxronlash» so'rov ichida ishlaydi (1C kutish 60 s, IIS proksi 120 s)
& $Nssm install $Xizmat $Waitress "--listen=127.0.0.1:$IchkiPort" "--threads=8" "--channel-timeout=130" "config.wsgi:application"
& $Nssm set $Xizmat AppDirectory $Ilova
& $Nssm set $Xizmat DisplayName "AV platformasi (waitress)"
& $Nssm set $Xizmat Start SERVICE_AUTO_START
& $Nssm set $Xizmat AppStdout "$Loglar\waitress.log"
& $Nssm set $Xizmat AppStderr "$Loglar\waitress.log"
& $Nssm set $Xizmat AppRotateFiles 1
& $Nssm set $Xizmat AppRotateBytes 10485760
& $Nssm set $Xizmat AppExit Default Restart
& $Nssm start $Xizmat

Start-Sleep -Seconds 3
try {
    $j = Invoke-WebRequest "http://127.0.0.1:$IchkiPort/" -UseBasicParsing -MaximumRedirection 0 -ErrorAction Stop
    Write-Host "waitress javob berdi: $($j.StatusCode)"
} catch {
    $kod = $_.Exception.Response.StatusCode.value__
    if ($kod -in 301, 302, 400) { Write-Host "waitress ishlayapti (javob $kod)" } else { throw "waitress javob bermadi: $($_.Exception.Message). Logni ko'ring: $Loglar\waitress.log" }
}
