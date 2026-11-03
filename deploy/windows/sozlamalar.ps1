# Windows Server o'rnatish skriptlari uchun umumiy yo'llar. Boshqa diskka qo'ysangiz — faqat shu yerda o'zgartiring.
$Ildiz     = "C:\av"
$Ilova     = "$Ildiz\app"                    # git clone shu yerga
$Venv      = "$Ildiz\venv"
$Python    = "$Venv\Scripts\python.exe"
$Media     = "$Ildiz\media"
$Zaxira    = "$Ildiz\zaxira"
$Loglar    = "$Ildiz\loglar"
$IisPapka  = "$Ildiz\iis"                    # IIS sayti ildizi (faqat web.config)
$Domen     = "av.dsyuksak.uz"
$Port      = 8092                            # routerdagi 15-qoida 8090-8092 ga kengaytiriladi
$IchkiPort = 8000                            # waitress, faqat 127.0.0.1
$PgBin     = "C:\Program Files\PostgreSQL\16\bin"
$Xizmat    = "AV-platforma"
