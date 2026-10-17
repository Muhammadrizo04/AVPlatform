<#
.SYNOPSIS
  AVSinxron kengaytmasini TestClaude bazasiga yuklaydi, tekshiradi va 4 ta endpoint javobini saqlaydi.

.DESCRIPTION
  1) TestClaude uchun ochiq Konfigurator (1cv8 DESIGNER) yo'qligini tekshiradi.
  2) /LoadConfigFromFiles -> /UpdateDBCfg -> /CheckModules -Server (har biri -Extension AVSinxron).
     Har qadam logi ekranga chiqariladi; xato bo'lsa skript to'xtaydi.
  3) /hs/av/ ning 4 ta endpointini chaqiradi va xom JSON'ni onec\tests\namunalar\*.raw.json ga saqlaydi.

  PowerShell 5.1 bilan mos. Fayl UTF-8 (BOM bilan) — o'zgartirganda kodlashni saqlang.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\1c\TestClaude_ornatish.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\1c\TestClaude_ornatish.ps1 -Parol "maxfiy" -FaqatEndpointlar
#>
[CmdletBinding()]
param(
    [string]$Platforma = 'C:\Program Files (x86)\1cv8\8.3.13.1690\bin\1cv8.exe',
    [string]$Server = 'localhost',
    [string]$Baza = 'TestClaude',
    [string]$KonfiguratorFoydalanuvchi = 'Claude',
    [string]$KonfiguratorParol = '',
    [string]$BazaUrl = 'http://localhost/TestClaude/hs/av',
    [string]$Login = 'AVSinxron',
    [string]$Parol = '',
    [switch]$FaqatEndpointlar,
    [switch]$EndpointlarsizYuklash
)

$ErrorActionPreference = 'Stop'

$Kengaytma = 'AVSinxron'
$SkriptPapka = $PSScriptRoot
if (-not $SkriptPapka) { $SkriptPapka = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Repo = (Resolve-Path (Join-Path $SkriptPapka '..')).Path
$KengaytmaPapka = Join-Path $SkriptPapka $Kengaytma
$LogPapka = Join-Path $env:TEMP 'AVSinxron_loglar'
$NamunaPapka = Join-Path $Repo 'onec\tests\namunalar'

function Yoz-Sarlavha([string]$Matn) {
    Write-Host ''
    Write-Host ('=' * 70) -ForegroundColor Cyan
    Write-Host $Matn -ForegroundColor Cyan
    Write-Host ('=' * 70) -ForegroundColor Cyan
}

function Toxta([string]$Matn) {
    Write-Host ''
    Write-Host "XATO: $Matn" -ForegroundColor Red
    exit 1
}

# 1C /Out logi UTF-8 (BOM bilan yoki BOMsiz) yoki ANSI (cp1251) bo'lishi mumkin — ikkalasini ham o'qiymiz.
function Oqi-Log([string]$Yol) {
    if (-not (Test-Path -LiteralPath $Yol)) { return '' }
    $Baytlar = [System.IO.File]::ReadAllBytes($Yol)
    if ($Baytlar.Length -eq 0) { return '' }
    try {
        $Utf8 = New-Object System.Text.UTF8Encoding($false, $true)
        $Matn = $Utf8.GetString($Baytlar)
        return $Matn.TrimStart([char]0xFEFF)
    } catch {
        return [System.Text.Encoding]::Default.GetString($Baytlar)
    }
}

function Tekshir-Konfigurator {
    Yoz-Sarlavha "1-qadam: $Baza uchun ochiq Konfigurator bor-yo'qligini tekshirish"
    $Jarayonlar = @(Get-CimInstance -ClassName Win32_Process -Filter "Name = '1cv8.exe'" -ErrorAction SilentlyContinue)
    $Konfiguratorlar = @($Jarayonlar | Where-Object { $_.CommandLine -and ($_.CommandLine -match '(?i)\bDESIGNER\b') })
    $BuBaza = @($Konfiguratorlar | Where-Object { $_.CommandLine -match ('(?i)' + [regex]::Escape($Baza)) })
    if ($BuBaza.Count -gt 0) {
        foreach ($J in $BuBaza) { Write-Host ("  PID {0}: {1}" -f $J.ProcessId, $J.CommandLine) -ForegroundColor Yellow }
        Toxta "$Baza bazasi uchun Konfigurator (1cv8 DESIGNER) ochiq. Uni yoping va skriptni qayta ishga tushiring."
    }
    if ($Konfiguratorlar.Count -gt 0) {
        Write-Host "  Diqqat: boshqa Konfigurator jarayonlari bor (buyruq satrida '$Baza' ko'rinmadi):" -ForegroundColor Yellow
        foreach ($J in $Konfiguratorlar) { Write-Host ("  PID {0}: {1}" -f $J.ProcessId, $J.CommandLine) -ForegroundColor Yellow }
        Write-Host "  Agar ulardan biri $Baza bo'lsa — yoping, aks holda yuklash bloklanishi mumkin." -ForegroundColor Yellow
    }
    Write-Host "  OK: $Baza uchun ochiq Konfigurator topilmadi." -ForegroundColor Green
}

function Ishga-Tushir([string]$Nomi, [string[]]$Buyruq) {
    Yoz-Sarlavha $Nomi
    if (-not (Test-Path -LiteralPath $LogPapka)) { New-Item -ItemType Directory -Path $LogPapka | Out-Null }
    $Log = Join-Path $LogPapka ("{0}_{1}.log" -f ($Nomi -replace '[^A-Za-z0-9]', '_'), (Get-Date -Format 'yyyyMMdd_HHmmss'))

    $Argumentlar = @('DESIGNER', '/S', ('"{0}\{1}"' -f $Server, $Baza), '/N', ('"{0}"' -f $KonfiguratorFoydalanuvchi))
    if ($KonfiguratorParol) { $Argumentlar += @('/P', ('"{0}"' -f $KonfiguratorParol)) }
    $Argumentlar += @('/DisableStartupDialogs', '/DisableStartupMessages')
    $Argumentlar += $Buyruq
    $Argumentlar += @('/Out', ('"{0}"' -f $Log))

    $Korinish = ($Argumentlar -join ' ')
    if ($KonfiguratorParol) { $Korinish = $Korinish.Replace(('"{0}"' -f $KonfiguratorParol), '"***"') }
    Write-Host "  > `"$Platforma`" $Korinish"

    $Jarayon = Start-Process -FilePath $Platforma -ArgumentList ($Argumentlar -join ' ') -Wait -PassThru -NoNewWindow
    $Kod = $Jarayon.ExitCode
    $LogMatn = Oqi-Log $Log
    Write-Host "  --- log ($Log) ---"
    if ($LogMatn.Trim()) { Write-Host $LogMatn } else { Write-Host '  (log bo''sh)' }
    Write-Host "  --- log oxiri ---"
    if ($Kod -ne 0) {
        Toxta "$Nomi muvaffaqiyatsiz (chiqish kodi $Kod). Yuqoridagi logni ko'ring."
    }
    Write-Host "  OK: $Nomi (chiqish kodi 0)." -ForegroundColor Green
}

function Ol-Parol {
    if ($Parol) { return $Parol }
    $Xavfsiz = Read-Host -AsSecureString "1C foydalanuvchisi '$Login' paroli"
    $Ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Xavfsiz)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr) }
}

function Chaqir-Endpoint([string]$Nomi, [string]$Url, [hashtable]$Sarlavhalar) {
    $Fayl = Join-Path $NamunaPapka ("{0}.raw.json" -f $Nomi)
    Write-Host ''
    Write-Host "  GET $Url"
    $Status = $null
    try {
        $Javob = Invoke-WebRequest -Uri $Url -Method Get -Headers $Sarlavhalar -UseBasicParsing `
            -TimeoutSec 600 -OutFile $Fayl -PassThru
        $Status = [int]$Javob.StatusCode
    } catch [System.Net.WebException] {
        $Xato = $_.Exception
        if ($Xato.Response) {
            $Status = [int]$Xato.Response.StatusCode
            try {
                $Oqim = $Xato.Response.GetResponseStream()
                $Fs = [System.IO.File]::Create($Fayl)
                try { $Oqim.CopyTo($Fs) } finally { $Fs.Close(); $Oqim.Close() }
            } catch { }
        } else {
            Write-Host "  $Nomi : ulanib bo'lmadi — $($Xato.Message)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "  $Nomi : so'rov xatosi — $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    $Hajm = 0
    if (Test-Path -LiteralPath $Fayl) { $Hajm = (Get-Item -LiteralPath $Fayl).Length }
    $Rang = 'Green'
    if ($Status -ne 200) { $Rang = 'Red' }
    Write-Host ("  {0} : HTTP {1}, {2} bayt -> {3}" -f $Nomi, $Status, $Hajm, $Fayl) -ForegroundColor $Rang
    if ($Hajm -ge 3) {
        $Bosh = New-Object byte[] 3
        $Fs = [System.IO.File]::OpenRead($Fayl)
        try { [void]$Fs.Read($Bosh, 0, 3) } finally { $Fs.Close() }
        if ($Bosh[0] -eq 0xEF -and $Bosh[1] -eq 0xBB -and $Bosh[2] -eq 0xBF) {
            Write-Host "    BOM: HA — javob EF BB BF bilan boshlanadi (modulda ИспользованиеByteOrderMark.НеИспользовать ishlamagan)" -ForegroundColor Yellow
        } else {
            Write-Host "    BOM: yo'q (EF BB BF bilan boshlanmaydi)"
        }
    }
    if ($Status -ne 200 -and $Hajm -gt 0 -and $Hajm -lt 4000) {
        Write-Host ("  javob: {0}" -f (Oqi-Log $Fayl))
    }
    if ($Status -eq 200) {
        try {
            $Json = (Oqi-Log $Fayl) | ConvertFrom-Json
            foreach ($P in $Json.PSObject.Properties) {
                if ($P.Value -is [System.Array]) {
                    Write-Host ("    {0}: {1} ta yozuv" -f $P.Name, $P.Value.Count)
                } else {
                    Write-Host ("    {0}: {1}" -f $P.Name, $P.Value)
                }
            }
        } catch {
            Write-Host "  Diqqat: javobni JSON sifatida o'qib bo'lmadi: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    return ($Status -eq 200)
}

function Chaqir-Endpointlar {
    Yoz-Sarlavha "3-qadam: /hs/av/ endpointlarini chaqirish ($BazaUrl)"
    if (-not (Test-Path -LiteralPath $NamunaPapka)) { New-Item -ItemType Directory -Path $NamunaPapka -Force | Out-Null }
    $P = Ol-Parol
    $Token = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes(("{0}:{1}" -f $Login, $P)))
    $Sarlavhalar = @{ Authorization = "Basic $Token" }

    $Hozir = Get-Date
    $Dan = $Hozir.AddYears(-10).ToString('yyyyMMddHHmmss')
    $Gacha = $Hozir.ToString('yyyyMMddHHmmss')
    $Asos = $BazaUrl.TrimEnd('/')

    $Natijalar = [ordered]@{}
    $Natijalar['versiya'] = Chaqir-Endpoint 'versiya' "$Asos/versiya" $Sarlavhalar
    $Natijalar['spravochniklar'] = Chaqir-Endpoint 'spravochniklar' "$Asos/spravochniklar" $Sarlavhalar
    $Natijalar['vositalar'] = Chaqir-Endpoint 'vositalar' "$Asos/vositalar" $Sarlavhalar
    $Natijalar['harakatlar'] = Chaqir-Endpoint 'harakatlar' "$Asos/harakatlar?dan=$Dan&gacha=$Gacha" $Sarlavhalar

    Write-Host ''
    $Hammasi = $true
    foreach ($K in $Natijalar.Keys) { if (-not $Natijalar[$K]) { $Hammasi = $false } }
    if ($Hammasi) {
        Write-Host "Hammasi OK: 4 ta endpoint 200 qaytardi. Xom javoblar: $NamunaPapka" -ForegroundColor Green
        Write-Host "Eslatma: *.raw.json fayllarida haqiqiy ma'lumot bor — ularni git'ga qo'shmang." -ForegroundColor Yellow
    } else {
        Write-Host "Ba'zi endpointlar 200 qaytarmadi. 404 bo'lsa — 1c\README.md dagi '404 bo'lsa' bo'limini ko'ring." -ForegroundColor Red
        exit 2
    }
}

# ===================== ASOSIY =====================

if (-not $FaqatEndpointlar) {
    if (-not (Test-Path -LiteralPath $Platforma)) { Toxta "1C platformasi topilmadi: $Platforma (-Platforma parametri bilan ko'rsating)." }
    if (-not (Test-Path -LiteralPath (Join-Path $KengaytmaPapka 'Configuration.xml'))) { Toxta "Kengaytma fayllari topilmadi: $KengaytmaPapka" }

    Tekshir-Konfigurator
    Ishga-Tushir '2a LoadConfigFromFiles' @('/LoadConfigFromFiles', ('"{0}"' -f $KengaytmaPapka), '-Extension', $Kengaytma)
    Ishga-Tushir '2b UpdateDBCfg' @('/UpdateDBCfg', '-Extension', $Kengaytma)
    Ishga-Tushir '2c CheckModules' @('/CheckModules', '-Server', '-Extension', $Kengaytma)
}

if (-not $EndpointlarsizYuklash) {
    Chaqir-Endpointlar
}
