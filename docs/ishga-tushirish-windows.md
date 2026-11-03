# Ishchi serverga o'rnatish (Windows Server, 192.168.100.30)

Manzil: **https://av.dsyuksak.uz:8092**. 1C bilan aloqa **faqat o'qish**: kengaytma «AVSinxron» faqat `Запрос`
bilan o'qiydi, platforma 1C'ga hech narsa yozmaydi. Sinxron **har soatda**, to'liq sinxron har kecha 03:02:30,
zaxira har kecha 02:30.

Tuzilma:

```
Internet -> router 87.192.241.38:8092 -> 192.168.100.30:8092 (IIS, HTTPS, win-acme sertifikati)
         -> http://127.0.0.1:8000 (waitress, «AV-platforma» xizmati) -> PostgreSQL 16 (localhost)
Platforma -> http://localhost:8090/<1C publikatsiyasi>/hs/av/ (shu serverdagi IIS, 1C ishchi bazasi)
```

Papkalar (`deploy\windows\sozlamalar.ps1` da o'zgartiriladi): ilova `C:\av\app`, venv `C:\av\venv`,
media `C:\av\media`, zaxira `C:\av\zaxira`, loglar `C:\av\loglar`, IIS sayti `C:\av\iis`.
Parol va kalitlar quyida faqat `<...>` o'rin belgisi.

## 1. Tarmoq: router va DNS

**Router (Virtual Servers).** 16 ta joyning hammasi band. Yangi qoida qo'shmaymiz: shu serverga qarab turgan
**15-qoida «1c 8090»** ni kengaytiramiz:

| | Hozir | Yangi |
|---|---|---|
| External Port | 8090-8091 | **8090-8092** |
| Internal IP | 192.168.100.30 | 192.168.100.30 |
| Internal Port | 8090-8091 | **8090-8092** |
| Protocol | TCP | TCP |

8090-8091 (1C) avvalgidek ishlaydi.

**DNS (ahost.uz paneli, `dsyuksak.uz` zonasi):**

- `A` yozuv: `av` → `87.192.241.38` (ofisning tashqi IP'si; u o'zgarsa yozuvni ham yangilang).
- Sertifikat uchun `CNAME`: `_acme-challenge.av` → win-acme bergan `<...>.auth.acme-dns.io` manzili (6-bo'lim).

**Ichki tarmoqdagi kompyuterlar.** Router «hairpin NAT» ni qo'llamasa, ofis ichidan tashqi IP orqali kirib bo'lmaydi.
Unda ichki DNS'da (yoki har kompyuterning `C:\Windows\System32\drivers\etc\hosts` faylida)
`192.168.100.30  av.dsyuksak.uz` yozuvini qo'shing. Manzil o'zgarmaydi: `https://av.dsyuksak.uz:8092`.

## 2. Dasturlar (serverda bir marta)

1. **Python 3.12** (64-bit, python.org). O'rnatishda «Add python.exe to PATH» belgisini qo'ying.
2. **Git for Windows**.
3. **PostgreSQL 16** (EDB o'rnatuvchisi). Port 5432, faqat localhost. Agar serverda 1C uchun PostgreSQL allaqachon
   bo'lsa, o'shanga alohida rol va baza qo'shsangiz ham bo'ladi (1C bazasiga tegilmaydi). Unda 3-bo'limdagi port
   va `sozlamalar.ps1` dagi `$PgBin` ni o'shanga moslang.
4. **MSYS2** (msys2.org) va Pango: MSYS2 terminalida `pacman -S mingw-w64-x86_64-pango`. WeasyPrint (PDF yorliq va
   hisobotlar) shuni ishlatadi.
5. **IIS** allaqachon bor (1C publikatsiyasi). Qo'shimcha: **URL Rewrite 2.1** va **Application Request Routing 3.0**
   (Microsoft sahifasidan), so'ng IIS'ni qayta ishga tushiring (`iisreset`).
6. **NSSM** (nssm.cc): arxivdagi `win64\nssm.exe` ni `C:\av\nssm\nssm.exe` ga qo'ying.
7. **win-acme** (win-acme.com): `C:\av\win-acme\` ga oching.

## 3. Ma'lumotlar bazasi

`psql` (PostgreSQL 16 → SQL Shell) da `postgres` nomidan:

```sql
CREATE ROLE av LOGIN PASSWORD '<DB_PAROL>';
CREATE DATABASE av OWNER av ENCODING 'UTF8';
```

## 4. Kod, `.env`, migratsiya

Administrator PowerShell:

```powershell
New-Item -ItemType Directory -Force C:\av, C:\av\media, C:\av\zaxira, C:\av\loglar
git clone <REPO_MANZILI> C:\av\app
py -3.12 -m venv C:\av\venv
C:\av\venv\Scripts\python.exe -m pip install -r C:\av\app\requirements.txt
```

`C:\av\app\.env` (Bloknotda, UTF-8):

```ini
SECRET_KEY=<uzun-tasodifiy-kalit>
DEBUG=False
ALLOWED_HOSTS=av.dsyuksak.uz,127.0.0.1,localhost
PROXY_ORQASIDA=True
HTTPS=True
CSRF_TRUSTED_ORIGINS=https://av.dsyuksak.uz:8092
DATABASE_URL=postgresql://av:<DB_PAROL>@localhost:5432/av
ONEC_URL=http://localhost:8090/<1C_PUBLIKATSIYA>/hs/av
ONEC_LOGIN=<1C texnik foydalanuvchi>
ONEC_PAROL=<uning paroli>
MEDIA_ROOT=C:\av\media
WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
```

- `SECRET_KEY`: `C:\av\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`
- `CSRF_TRUSTED_ORIGINS` da **port bilan** yozing: port standart (443) bo'lmagani uchun kirish formasi shusiz
  CSRF tekshiruvidan o'tmaydi.
- DB parolida `@`, `:`, `/` bo'lsa, URL-kodlang (`@` → `%40`).
- `.env` ga faqat Administratorlar va SYSTEM kirsin: `icacls C:\av\app\.env /inheritance:r /grant:r Administrators:F SYSTEM:F`.

```powershell
cd C:\av\app
C:\av\venv\Scripts\python.exe manage.py check --deploy
C:\av\venv\Scripts\python.exe manage.py migrate
C:\av\venv\Scripts\python.exe manage.py collectstatic --noinput
C:\av\venv\Scripts\python.exe manage.py createsuperuser
```

Birinchi administratorga rol bering (`<login>` — yuqorida kiritilgan nom):

```powershell
C:\av\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; from hisoblar.models import Profil, Rol; u = get_user_model().objects.get(username='<login>'); print(Profil.objects.update_or_create(user=u, defaults={'rol': Rol.ADMIN})[0])"
```

## 5. waitress xizmati va IIS sayti

```powershell
powershell -ExecutionPolicy Bypass -File C:\av\app\deploy\windows\xizmat_ornatish.ps1 -Nssm C:\av\nssm\nssm.exe
powershell -ExecutionPolicy Bypass -File C:\av\app\deploy\windows\iis_sozla.ps1
```

Birinchisi «AV-platforma» Windows xizmatini (waitress, `127.0.0.1:8000`, avtomatik ishga tushadi) o'rnatadi.
Ikkinchisi quyidagilarni qiladi:

- ARR proksini yoqadi (Host saqlanadi, kutish 120 s);
- `C:\av\iis\web.config` ni qo'yadi;
- «AV» saytini va `/static/` virtual papkasini yaratadi;
- Windows Firewall'da 8092 portni ochadi.

## 6. HTTPS sertifikati (win-acme, DNS orqali)

80/443 portlar boshqa serverga (192.168.100.69) band, shuning uchun Let's Encrypt tekshiruvi DNS orqali
(**acme-dns**) o'tadi. Bir marta CNAME qo'shiladi, keyin yangilash avtomatik.

```powershell
cd C:\av\win-acme
.\wacs.exe --source manual --host av.dsyuksak.uz --validation acme-dns --acmednsserver https://auth.acme-dns.io/ `
  --installation iis --installationsiteid <AV_SAYT_ID> --sslport 8092 --store certificatestore
```

- `<AV_SAYT_ID>` ni `Get-Website AV` buyrug'i ko'rsatadi.
- win-acme `_acme-challenge.av.dsyuksak.uz` uchun CNAME manzilini chiqaradi. Uni ahost.uz panelida qo'shing,
  bir necha daqiqa kuting va Enter bosing.
- win-acme sertifikatni oladi va «AV» saytiga `https *:8092 (SNI)` bog'lanishini qo'shadi.
- Yangilash uchun Task Scheduler'ga o'z vazifasini qo'yadi (har 60 kunda, avtomatik).

Tekshiruv (serverda): `curl.exe -I https://av.dsyuksak.uz:8092/static/panel/htmx.min.js --resolve av.dsyuksak.uz:8092:127.0.0.1`
→ `200`.

## 7. 1C ishchi bazasi (faqat o'qish)

1. 1C ishchi bazasidan `.dt` zaxira oling.
2. Kengaytma `.cfe` ni ishchi bazaga **siz o'zingiz** Konfigurator orqali o'rnatasiz: Конфигурация → Расширения
   конфигурации → Добавить. Kengaytma faqat `Запрос` bilan o'qiydi, ma'lumot yozmaydi.
3. Kengaytmalar ro'yxatining «Версия» ustunida yuklangan versiya turganini ko'ring.
4. HTTP-servis publikatsiyasini tekshiring: brauzerda `http://localhost:8090/<1C_PUBLIKATSIYA>/hs/av/versiya`
   → JSON javob.
5. 1C'da **texnik foydalanuvchi** yarating, faqat «AVSinxron» HTTP-servisiga kirish huquqi bilan (tahrirlash
   huquqlarisiz). Uning login va parolini `.env` ga yozing (`ONEC_LOGIN`, `ONEC_PAROL`) va xizmatni qayta ishga
   tushiring: `Restart-Service AV-platforma`.

## 8. Sinxron va zaxira vazifalari

```powershell
powershell -ExecutionPolicy Bypass -File C:\av\app\deploy\windows\vazifalar_ornatish.ps1
```

Task Scheduler'da `\AV\` papkasida uchta vazifa paydo bo'ladi. Hammasi SYSTEM nomidan ishlaydi:

| Vazifa | Qachon | Log |
|---|---|---|
| AV sinxron | har soatda, soat boshida | `C:\av\loglar\sinxron.log` |
| AV sinxron toliq | har kecha 03:02:30 | `C:\av\loglar\sinxron-toliq.log` |
| AV zaxira | har kecha 02:30 | `C:\av\zaxira\YYYY-MM-DD.dump` + `.media.zip`, 14 kun saqlanadi |

Birinchi to'liq sinxronni hoziroq ishga tushiring:

```powershell
Start-ScheduledTask -TaskPath "\AV\" -TaskName "AV sinxron toliq"
```

So'ng logni va paneldagi «Sinxron jurnali»ni tekshiring: natija «Muvaffaqiyatli» bo'lishi kerak.

Agar ketma-ket 3 ta sinxron xato bilan tugasa (taxminan 3 soat), panelda 1C aloqasi haqida ogohlantirish chiqadi.
Zaxirani vaqti-vaqti bilan boshqa diskka yoki kompyuterga nusxalang.

**Tiklash:**

```powershell
Stop-Service AV-platforma; Disable-ScheduledTask -TaskPath "\AV\" -TaskName "AV sinxron"
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" -U av -d av --clean --if-exists --no-owner C:\av\zaxira\<SANA>.dump
Expand-Archive C:\av\zaxira\<SANA>.media.zip -DestinationPath C:\av\media -Force
Enable-ScheduledTask -TaskPath "\AV\" -TaskName "AV sinxron"; Start-Service AV-platforma
```

## 9. Yangilash (yangi versiya chiqqanda)

```powershell
cd C:\av\app
git pull
C:\av\venv\Scripts\python.exe -m pip install -r requirements.txt
C:\av\venv\Scripts\python.exe manage.py migrate
C:\av\venv\Scripts\python.exe manage.py collectstatic --noinput
Restart-Service AV-platforma
```

## 10. Tekshiruv ro'yxati

- [ ] Router 15-qoidasi `8090-8092`. 1C (8090) avvalgidek ochiladi.
- [ ] `av.dsyuksak.uz` → `87.192.241.38`. Tashqaridan (masalan, telefonda mobil internet orqali)
  `https://av.dsyuksak.uz:8092` ochiladi, sertifikat haqida ogohlantirish chiqmaydi.
- [ ] Ofis ichidan ham shu manzil ochiladi (kerak bo'lsa `hosts` yozuvi bilan).
- [ ] Kirish ishlaydi. 5 marta noto'g'ri parol kiritilsa, 15 daqiqa blok bo'ladi; bunda boshqa foydalanuvchilar
  bloklanmaydi (mijoz IP'si to'g'ri olinyapti).
- [ ] Admin «Hozir sinxronlash» → «Muvaffaqiyatli». Soat boshida jurnalda yangi yozuv paydo bo'ladi.
- [ ] PDF yorliq ochiladi (WeasyPrint/Pango ishlayapti); AV kartochkasidagi rasm yuklanadi va ko'rinadi.
- [ ] Ertasi kuni `C:\av\zaxira` da `.dump` fayli bor.
- [ ] Rollarni tekshiring: `docs/ishga-tushirish.md`, 10-bo'lim.
