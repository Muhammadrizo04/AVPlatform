# AV zaxirasi (Windows): PostgreSQL (pg_dump -Fc) + MEDIA_ROOT (zip) -> C:\av\zaxira\YYYY-MM-DD.*; 14 kundan eskisi o'chadi.
# DB manzili/paroli .env dagi DATABASE_URL dan olinadi (skriptda yozilmagan, buyruq qatorida ko'rinmaydi).
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"

$envFayl = "$Ilova\.env"
if (-not (Test-Path $envFayl)) { throw "zaxira: $envFayl topilmadi" }
$q = @{}
foreach ($qator in Get-Content $envFayl -Encoding UTF8) {
    $qator = $qator.Trim()
    if ($qator -and -not $qator.StartsWith("#") -and $qator.Contains("=")) {
        $k, $v = $qator.Split("=", 2)
        $q[$k.Trim()] = $v.Trim().Trim("'", '"')
    }
}
if (-not $q["DATABASE_URL"]) { throw "zaxira: .env da DATABASE_URL yo'q" }
$u = [Uri]$q["DATABASE_URL"]
$login, $parol = $u.UserInfo.Split(":", 2)
$env:PGHOST = if ($u.Host) { $u.Host } else { "localhost" }
$env:PGPORT = if ($u.Port -gt 0) { "$($u.Port)" } else { "5432" }
$env:PGUSER = [Uri]::UnescapeDataString($login)
$env:PGPASSWORD = [Uri]::UnescapeDataString($parol)
$env:PGDATABASE = $u.AbsolutePath.TrimStart("/")
$mediaPapka = if ($q["MEDIA_ROOT"]) { $q["MEDIA_ROOT"] } else { $Media }

New-Item -ItemType Directory -Force $Zaxira | Out-Null
$sana = Get-Date -Format "yyyy-MM-dd"

# Yarim qolgan fayl zaxira bo'lib qolmasin: avval .tmp ga, so'ng nomini almashtiramiz
& "$PgBin\pg_dump.exe" -Fc -f "$Zaxira\$sana.dump.tmp"
if ($LASTEXITCODE -ne 0) { throw "zaxira: pg_dump xato bilan tugadi ($LASTEXITCODE)" }
Move-Item "$Zaxira\$sana.dump.tmp" "$Zaxira\$sana.dump" -Force

$zip = "$Zaxira\$sana.media.zip"
Remove-Item "$zip.tmp.zip" -ErrorAction SilentlyContinue
if ((Test-Path $mediaPapka) -and (Get-ChildItem $mediaPapka -Recurse -File | Select-Object -First 1)) {
    Compress-Archive -Path "$mediaPapka\*" -DestinationPath "$zip.tmp.zip" -Force
    Move-Item "$zip.tmp.zip" $zip -Force
}

Get-ChildItem $Zaxira -File | Where-Object { ($_.Name -like "*.dump" -or $_.Name -like "*.media.zip") -and $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
    Remove-Item -Force
Write-Host "zaxira: tayyor -> $Zaxira\$sana.*"
