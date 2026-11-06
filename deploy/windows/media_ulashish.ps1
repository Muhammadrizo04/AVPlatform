# Agentlar kompyuteri (192.168.100.37) uchun rasmlar papkasini FAQAT O'QISH uchun tarmoqqa ochadi: \\192.168.100.30\av-media
# Administrator PowerShell'da, serverda. Parolni skript so'raydi — o'zingiz kiriting (hech qayerga yozilmaydi).
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"
$Ulush    = "av-media"
$Hisob    = "av_media"
$Agentlar = "192.168.100.37"

# Rasmlar aslida qayerda — .env dagi MEDIA_ROOT (zaxira.ps1 kabi), bo'lmasa sozlamalar.ps1 dagi yo'l
$mediaQator = Get-Content "$Ilova\.env" -Encoding UTF8 -ErrorAction SilentlyContinue |
    Where-Object { $_.Trim() -match '^MEDIA_ROOT\s*=' } | Select-Object -First 1
if ($mediaQator) { $Media = $mediaQator.Split("=", 2)[1].Trim().Trim("'", '"') }
if (-not (Test-Path $Media)) { throw "Media papkasi topilmadi: $Media" }
Write-Host "Media papkasi: $Media"

# 1. Alohida mahalliy hisob: faqat shu ulush uchun, serverga kira olmaydi (Users guruhiga qo'shilmaydi)
if (-not (Get-LocalUser -Name $Hisob -ErrorAction SilentlyContinue)) {
    $parol = Read-Host "«$Hisob» uchun yangi parol" -AsSecureString
    New-LocalUser -Name $Hisob -Password $parol -PasswordNeverExpires -UserMayNotChangePassword `
        -Description "AV agentlar: media faqat o'qish" | Out-Null
    # «Users» guruhi ruscha Windows'da «Пользователи» — SID bilan
    Remove-LocalGroupMember -SID "S-1-5-32-545" -Member $Hisob -ErrorAction SilentlyContinue
}

# 2. Papkaga faqat o'qish (NTFS)
icacls $Media /grant "${env:COMPUTERNAME}\${Hisob}:(OI)(CI)RX" | Out-Null

# 3. Tarmoq ulushi — faqat o'qish
if (-not (Get-SmbShare -Name $Ulush -ErrorAction SilentlyContinue)) {
    New-SmbShare -Name $Ulush -Path $Media -ReadAccess "${env:COMPUTERNAME}\$Hisob" -Description "AV media (agentlar, faqat o'qish)" | Out-Null
}

# 4. Firewall: SMB (445) faqat agentlar kompyuteridan
if (-not (Get-NetFirewallRule -DisplayName "AV media agentlar" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "AV media agentlar" -Direction Inbound -Protocol TCP -LocalPort 445 `
        -RemoteAddress $Agentlar -Action Allow | Out-Null
}

Get-SmbShareAccess -Name $Ulush | Format-Table AccountName, AccessRight -AutoSize
Write-Host "Tayyor: \\192.168.100.30\$Ulush (faqat o'qish, faqat $Agentlar dan)"
