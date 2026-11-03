# Vazifalar rejalashtiruvchisi (Task Scheduler): sinxron har soatda, to'liq sinxron har kecha 03:02:30,
# zaxira har kecha 02:30. Administrator PowerShell'da:
#   powershell -ExecutionPolicy Bypass -File E:\AVPlatform\deploy\windows\vazifalar_ornatish.ps1
# Vazifalar SYSTEM nomidan ishlaydi (foydalanuvchi tizimdan chiqsa ham). Natija: E:\AVPlatform-malumot\loglar\*.log va panel «Sinxron jurnali».
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\sozlamalar.ps1"
New-Item -ItemType Directory -Force $Loglar, $Zaxira | Out-Null

function Vazifa($Nomi, $Tavsif, $Amal, $Trigger) {
    $sozlama = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    $kim = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $Nomi -TaskPath "\AV\" -Description $Tavsif -Action $Amal -Trigger $Trigger `
        -Settings $sozlama -Principal $kim -Force | Out-Null
    Write-Host "Ro'yxatga olindi: \AV\$Nomi"
}

function Manage($Buyruq, $Log) {
    # cmd orqali: chiqish logga qo'shiladi; 1C'ga faqat o'qish so'rovlari ketadi
    New-ScheduledTaskAction -Execute "cmd.exe" -WorkingDirectory $Ilova `
        -Argument "/c `"`"$Python`" manage.py $Buyruq >> `"$Loglar\$Log`" 2>&1`""
}

# Har soatda, soat boshida (00:00 dan boshlab, cheksiz)
$soatlik = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 1)
Vazifa "AV sinxron" "1C'dan sinxron (oddiy, 45 kunlik oyna), har soatda" (Manage "sinxron" "sinxron.log") $soatlik

# 03:00 dagi soatlik sinxron bilan to'qnashmasin — 2,5 daqiqa keyin; band bo'lsa buyruq o'zi 5 daqiqa qayta urinadi
Vazifa "AV sinxron toliq" "1C'dan to'liq sinxron (--toliq), har kecha" (Manage "sinxron --toliq" "sinxron-toliq.log") `
    (New-ScheduledTaskTrigger -Daily -At "03:02:30")

$zaxiraAmal = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $Ilova `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Ilova\deploy\windows\zaxira.ps1`""
Vazifa "AV zaxira" "PostgreSQL (pg_dump) + media zaxirasi, har kecha" $zaxiraAmal (New-ScheduledTaskTrigger -Daily -At "02:30")

Get-ScheduledTask -TaskPath "\AV\" | Get-ScheduledTaskInfo | Format-Table TaskName, NextRunTime -AutoSize
