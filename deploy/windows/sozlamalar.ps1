# Windows Server o'rnatish skriptlari uchun umumiy yo'llar. Ilova va venv skript turgan joydan aniqlanadi
# (ishchi serverda E:\AVPlatform va E:\AVPlatform\venv); ma'lumot papkalarini kerak bo'lsa shu yerda o'zgartiring.
$Ilova     = (Resolve-Path "$PSScriptRoot\..\..").Path   # git clone qilingan papka
$Venv      = "$Ilova\venv"
$Python    = "$Venv\Scripts\python.exe"
$Ildiz     = "$(Split-Path $Ilova -Qualifier)\AVPlatform-malumot"   # masalan E:\AVPlatform-malumot
$Media     = "$Ildiz\media"                  # .env dagi MEDIA_ROOT ustun (zaxira.ps1 uni o'qiydi)
$Zaxira    = "$Ildiz\zaxira"
$Loglar    = "$Ildiz\loglar"
$IisPapka  = "$Ildiz\iis"                    # IIS sayti ildizi (faqat web.config)
$Domen     = "av.dsyuksak.uz"
$Port      = 8092                            # routerdagi 15-qoida 8090-8092 ga kengaytiriladi
$IchkiPort = 8000                            # waitress, faqat 127.0.0.1
# PostgreSQL bin: o'rnatilganlarning eng yangisi (ishchi serverda 14)
$PgBin     = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe" -ErrorAction SilentlyContinue |
    Sort-Object { [int]$_.Directory.Parent.Name } -Descending | Select-Object -First 1 | ForEach-Object { $_.DirectoryName }
$Xizmat    = "AV-platforma"
