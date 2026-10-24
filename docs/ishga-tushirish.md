# Ishga tushirish (VM, zaxira, jonli sinov)

Maqsad: ichki Ubuntu 24.04 VM (PostgreSQL 16, gunicorn + nginx + systemd timer), keyin VPS.
Barcha parol va kalitlar quyida faqat o'rin belgisi (`<...>`) sifatida berilgan.

Joylashuv: ilova `/opt/av/app`, virtual muhit `/opt/av/venv`, tizim foydalanuvchisi `av`,
media `/var/lib/av/media`, zaxira `/var/backups/av`.

## 1. VM'ni tayyorlash (Ubuntu 24.04)

```bash
sudo apt update
sudo apt install -y python3.12-venv python3-pip git nginx postgresql postgresql-contrib \
    libpango-1.0-0 libpangoft2-1.0-0        # WeasyPrint (PDF yorliq/hisobot) uchun tizim kutubxonalari
psql --version                              # 16.x bo'lishi kerak (Ubuntu 24.04 standarti)

sudo useradd --system --create-home --home-dir /opt/av --shell /bin/bash av
sudo mkdir -p /var/lib/av/media /var/backups/av
sudo chown av:av /var/lib/av/media /var/backups/av
sudo chmod 700 /var/backups/av             # zaxira faqat av uchun o'qiladigan
sudo chmod 755 /opt/av                     # nginx (www-data) /opt/av/app/staticfiles ga yetib borishi uchun (Ubuntu 24.04 da home 0750)
```

Ma'lumotlar bazasi:

```bash
sudo -u postgres psql -c "CREATE ROLE av LOGIN PASSWORD '<DB_PAROL>';"
sudo -u postgres psql -c "CREATE DATABASE av OWNER av ENCODING 'UTF8';"
```

Kod va bog'liqliklar:

```bash
sudo -u av git clone <REPO_MANZILI> /opt/av/app
sudo chmod 755 /opt/av/app
sudo -u av python3 -m venv /opt/av/venv
sudo -u av /opt/av/venv/bin/pip install -r /opt/av/app/requirements.txt gunicorn
```

## 2. `.env`

`/opt/av/app/.env` (egasi `av`, ruxsat `chmod 600`):

```ini
SECRET_KEY=<uzun-tasodifiy-kalit>
DEBUG=False
ALLOWED_HOSTS=av.example.uz,<VM_IP>
# nginx ortida SHART (mijoz IP'si X-Forwarded-For dan olinadi); nginx'siz False qoldiring
PROXY_ORQASIDA=True
DATABASE_URL=postgresql://av:<DB_PAROL>@localhost:5432/av
ONEC_URL=<1C HTTP-servis manzili>
ONEC_LOGIN=<texnik foydalanuvchi>
ONEC_PAROL=<texnik foydalanuvchi paroli>
MEDIA_ROOT=/var/lib/av/media
# Ichki VM (HTTP) — False; VPS'da (nginx TLS'ni tugatadi) True, 8-bo'limdagi «HTTPS (VPS)» ga qarang
HTTPS=False
```

`SECRET_KEY` hosil qilish:

```bash
/opt/av/venv/bin/python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

DB paroli maxsus belgilarga ega bo'lsa, `DATABASE_URL` da URL-kodlang (`@` -> `%40`).

## 3. Migratsiya, statik fayllar, birinchi administrator

```bash
cd /opt/av/app
sudo -u av /opt/av/venv/bin/python manage.py migrate
sudo -u av /opt/av/venv/bin/python manage.py collectstatic --noinput     # -> /opt/av/app/staticfiles
sudo -u av /opt/av/venv/bin/python manage.py createsuperuser
```

`createsuperuser` Profil yaratmaydi, rol berilmaguncha panelga kirib bo'lmaydi. Rolni `admin` qiling
(`<login>` — yuqorida kiritilgan foydalanuvchi nomi):

```bash
sudo -u av /opt/av/venv/bin/python manage.py shell -c "from django.contrib.auth import get_user_model; from hisoblar.models import Profil, Rol; u = get_user_model().objects.get(username='<login>'); p, _ = Profil.objects.update_or_create(user=u, defaults={'rol': Rol.ADMIN}); print(p)"
```

Boshqa foydalanuvchilar (hisobchi, HR, rahbar, revizor) keyin admin panelidan yaratiladi.

## 4. gunicorn, nginx, timerlar

```bash
cd /opt/av/app/deploy
# MAJBURIY tekshiruv (Windows'da bajarib bo'lmaydi): xatosiz tugashi kerak
systemd-analyze verify av-*.service av-*.timer

sudo cp av-*.service av-*.timer /etc/systemd/system/
sudo chmod +x /opt/av/app/deploy/backup.sh
sudo systemctl daemon-reload
sudo systemctl enable --now av-gunicorn.service
sudo systemctl enable --now av-sinxron.timer av-sinxron-toliq.timer av-backup.timer

sudo cp nginx-av.conf /etc/nginx/sites-available/av     # server_name ni o'zgartiring
sudo ln -s /etc/nginx/sites-available/av /etc/nginx/sites-enabled/av
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Statik fayllar tekshiruvi: 200 bo'lishi kerak (403 bo'lsa /opt/av va /opt/av/app ruxsatini (chmod 755) tekshiring)
curl -I http://<host>/static/panel/htmx.min.js
```

Jadval: sinxron har 5 daqiqada (`*:0/5`), to'liq sinxron (`--toliq`) har kecha 03:02:30, zaxira har kecha 02:30.
To'liq sinxron 03:00 dagi 5 daqiqalik sinxron bilan to'qnashmasligi uchun 2,5 daqiqa keyin boshlanadi; baribir band
bo'lsa (`sinxron --toliq` advisory lock ololmasa), har 15 s da qayta urinadi, 5 daqiqadan keyin to'xtaydi
(`journalctl -u av-sinxron-toliq.service` da «Sinxron band» yozuvi). Oddiy (5 daqiqalik) sinxron band bo'lsa kutmaydi.
Holatni ko'rish:

```bash
systemctl list-timers 'av-*'
sudo systemctl start av-sinxron.service && journalctl -u av-sinxron.service -n 20 --no-pager
```

Eslatma: gunicorn `--timeout 120` va nginx `proxy_read_timeout 120s` — admin «Hozir sinxronlash» tugmasi
sinxronni so'rov ichida bajaradi (1C kutish vaqti 60 s). `/media/` nginx orqali ochilmagan: rasmlarni Django
ruxsat tekshiruvi bilan beradi. `client_max_body_size 16m` — rasm yuklash chegarasi.

## 5. Zaxira va tiklash

`backup.sh` har kecha `/var/backups/av/YYYY-MM-DD.dump` (`pg_dump -Fc`) va `YYYY-MM-DD.media.tar.gz` yaratadi,
14 kundan eskilarini o'chiradi. DB ma'lumotlari `.env` dagi `DATABASE_URL` dan olinadi. Qo'lda ishga tushirish:
`sudo -u av /opt/av/app/deploy/backup.sh`. Zaxirani ba'zan VM'dan tashqariga (boshqa mashina/disk) nusxalang.

Tiklash (yangi yoki buzilgan VM'da, 1-3 bo'limlar bajarilgandan keyin):

```bash
sudo systemctl stop av-gunicorn.service av-sinxron.timer av-sinxron-toliq.timer
SANA=2026-10-17                                   # tiklanadigan zaxira sanasi
sudo -u postgres dropdb av && sudo -u postgres createdb -O av -E UTF8 av
sudo -u postgres pg_restore --no-owner --role=av -d av /var/backups/av/$SANA.dump
sudo -u av tar -xzf /var/backups/av/$SANA.media.tar.gz -C /var/lib/av/media
sudo systemctl start av-gunicorn.service av-sinxron.timer av-sinxron-toliq.timer
```

Tekshiring: panelga kirish, AV soni, kartochkadagi rasmlar.

## 6. Jonli sinov (TestClaude)

`.env` da TestClaude manzili va logini bo'lganda (test bazasida ishlaydi, lekin 1C'ga haqiqiy so'rov yuboradi):

```bash
venv/bin/python -m pytest -m jonli -q
```

Tekshiradi: `sinxronla()` natijasi `ok`, AV soni > 0, har (AV, filial) uchun `farq == 0` yoki «mos emas»
(`farq < 0`). Oddiy `pytest -q` jonli testlarni o'tkazib yuboradi.

## 7. doms2021'ga o'tish (spec §12)

1. 1C ishchi bazasidan `.dt` zaxira oling (Konfigurator -> Администрирование -> Выгрузить информационную базу).
2. Kengaytma `.cfe` ni ishchi bazaga foydalanuvchining o'zi Konfigurator orqali o'rnatadi (Конфигурация ->
   Расширения конфигурации -> Добавить); HTTP-servis `/hs/av/` publikatsiyasini tekshiring (`versiya` so'rovi 200).
3. 1C'da texnik foydalanuvchi yarating (faqat kengaytma HTTP-servisiga huquqli).
4. `.env` da `ONEC_URL`, `ONEC_LOGIN`, `ONEC_PAROL` ni doms2021 qiymatlariga almashtiring, so'ng
   `sudo systemctl restart av-gunicorn.service`.
5. `sudo systemctl start av-sinxron-toliq.service` -> `journalctl -u av-sinxron-toliq.service` va panelda sinxron
   natijasi `ok` ekanini tekshiring. Sinovdan keyin xodimlarga ochiladi.

## 8. VPS / online 1C'ga o'tishdan oldin UUID tekshiruvi (spec §6.4)

Majburiy: kamida 20 ta AV va 5 ta xodimning UUID'i ikkala bazada bir xil bo'lishi kerak (РИБ). Mos kelmasa
ko'chish TO'XTATILADI (kalit — filial + inv. raqam — bo'yicha bog'lash rejasi alohida ishlab chiqiladi).

Joriy (doms2021 bilan sinxronlangan) bazadagi 20 AV va 5 xodim UUID'lari online 1C javobi bilan solishtiriladi.

```bash
cd /opt/av/app
# 1) Joriy bazadan UUID'larni oling (hozirgi .env):
sudo -u av /opt/av/venv/bin/python manage.py shell -c "import json; from onec.models import AV, Xodim; json.dump({'av': [str(r) for r in AV.objects.order_by('id').values_list('ref_1c', flat=True)[:20]], 'xodim': [str(r) for r in Xodim.objects.order_by('id').values_list('ref_1c', flat=True)[:5]]}, open('/tmp/uuid_eski.json', 'w'))"

# 2) Online 1C'ga qarshi solishtiring (ONEC_* faqat shu buyruq uchun almashtiriladi, .env o'zgarmaydi):
sudo -u av env ONEC_URL='<ONLINE_URL>' ONEC_LOGIN='<LOGIN>' ONEC_PAROL='<PAROL>' /opt/av/venv/bin/python manage.py shell -c "import json; from onec.client import OneCClient; e = json.load(open('/tmp/uuid_eski.json')); c = OneCClient.settingsdan(); av = {q['ref'].lower() for q in c.vositalar()['vositalar']}; xd = {q['ref'].lower() for q in c.spravochniklar()['xodimlar']}; yoq_av = [r for r in e['av'] if r.lower() not in av]; yoq_xd = [r for r in e['xodim'] if r.lower() not in xd]; print('AV tekshirildi:', len(e['av']), 'topilmadi:', yoq_av); print('Xodim tekshirildi:', len(e['xodim']), 'topilmadi:', yoq_xd); print('NATIJA:', 'MOS' if len(e['av']) >= 20 and len(e['xodim']) >= 5 and not yoq_av and not yoq_xd else 'MOS EMAS, KOCHISH TOXTATILSIN')"
```

`NATIJA: MOS` bo'lsa davom eting; `MOS EMAS` bo'lsa ko'chmang. Tekshiruv uchun bazada kamida 20 AV va 5 xodim
bo'lishi kerak (aks holda natija «MOS EMAS» chiqadi).

Mos bo'lsa: `backup.sh` natijasi (`.dump` + `media.tar.gz`) VPS'ga ko'chiriladi, 5-bo'limdagi tartib bilan
tiklanadi, `.env` online qiymatlarga almashtiriladi, HTTPS yoqiladi.

### HTTPS (VPS)

VPS internetga ochiq: faqat HTTPS. `sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d <domen>`,
so'ng `.env` da quyidagilarni o'rnating va `sudo systemctl restart av-gunicorn.service`; nginx 80 -> 443 yo'naltiradi.

```ini
ALLOWED_HOSTS=<domen>
PROXY_ORQASIDA=True
HTTPS=True
# ixtiyoriy: bo'sh bo'lsa ALLOWED_HOSTS dan https://<domen> olinadi
# CSRF_TRUSTED_ORIGINS=https://<domen>
```

`HTTPS=True` quyidagilarni yoqadi: `SECURE_PROXY_SSL_HEADER` (`X-Forwarded-Proto: https`), secure sessiya va CSRF
cookie, HSTS (1 yil) va `CSRF_TRUSTED_ORIGINS`. Busiz TLS ortida kirish formasi CSRF tekshiruvidan o'tmaydi.
nginx `proxy_set_header X-Forwarded-Proto $scheme;` o'rnatishi shart (`deploy/nginx-av.conf` da bor) —
certbot qo'shgan 443 `server` blokida ham shu `location /` sozlamasi qolganini tekshiring.
`ufw` bilan faqat 22/80/443 ochiq qoldiring; PostgreSQL tashqariga ochilmasin.

## 9. Windows'da lokal ishlab chiqish

- WeasyPrint uchun MSYS2 Pango: MSYS2'da `pacman -S mingw-w64-x86_64-pango`; `WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin`
  (`config/settings_test.py` bu papka mavjud bo'lsa buni o'zi o'rnatadi).
- PostgreSQL: lokal serverda `av` rol (parol `av`, test bazasi yaratish huquqi bilan):
  `CREATE ROLE av LOGIN PASSWORD 'av' CREATEDB;`; `DATABASE_URL` mos bo'lsin.
- Testlar: `venv\Scripts\python.exe -m pytest -q` (jonli testlar o'tkazib yuboriladi).
- `systemd-analyze` Windows'da yo'q: `deploy/tests/test_deploy.py` birliklarning asosiy kalitlarini tekshiradi,
  lekin VM'da `systemd-analyze verify` baribir majburiy (4-bo'lim).

## 10. Qabul qilish ro'yxati

Har bir ssenariy foydalanuvchi bilan qo'lda tekshiriladi (belgi qo'ying).

**Administrator**
- [ ] Login/parol bilan kiradi; 5 marta noto'g'ri parol -> 15 daqiqa blok.
- [ ] Yangi foydalanuvchi yaratib, rol (hisobchi/HR/rahbar/revizor) va filial biriktiradi.
- [ ] «Hozir sinxronlash» ishlaydi, natija «Muvaffaqiyatli», jurnalda yangi yozuv paydo bo'ladi.
- [ ] Sozlamalar sahifasi ochiladi va o'zgarish saqlanadi.
- [ ] Sahifa dizayni to'liq yuklanadi; `curl -I http://<host>/static/panel/htmx.min.js` -> 200 (403 emas).
- [ ] Zaxira fayllari `/var/backups/av` da bor (`dump` + `media.tar.gz`).

**Hisobchi**
- [ ] AV ro'yxatida qidiradi va filtrlaydi (filial, bo'lim, tur, bayroq); Excel eksport ochiladi.
- [ ] Ko'p donali AV'ni bo'limlar/MOL bo'yicha bo'ladi; yig'indi 1C qoldig'iga teng bo'lib qoladi.
- [ ] «Taqsimot 1C bilan mos emas» AV'da kamaytirish qatorini tanlaydi, harakat tarixda ko'rinadi.
- [ ] AV yorlig'ini (QR) PDF qilib chop etadi.
- [ ] Tozalash ro'yxatlari va hisobotlar ochiladi, bo'lim kesimi yig'indisi 1C summasiga teng.

**HR**
- [ ] Ketgan xodimdagi AV'lar ro'yxatini ko'radi («Ketgan xodimda» bayrog'i).
- [ ] AV uchun yangi МОЛ tayinlaydi (MolAkt jarayoni).
- [ ] Faqat o'ziga ruxsat etilgan sahifalarni ko'radi; hisobchi amallari (taqsimot) yopiq.

**Rahbar**
- [ ] Bosh sahifada filiallar bo'yicha AV soni va qiymati hamda «Diqqat talab qiladi» kartochkalarini ko'radi.
- [ ] Faqat o'z filiallari ma'lumotlarini ko'radi (boshqa filial AV'si ko'rinmaydi).
- [ ] Hisobotlarni ko'radi/eksport qiladi; o'zgartirish tugmalari yo'q.

**Revizor**
- [ ] Revizor login/parol bilan kira olmaydi: kirish rad etiladi, «Panelga kirish huquqi yo'q» xabari chiqadi
  (spec §4: 1-bosqichda revizor panelga kirmaydi).

**Umumiy**
- [ ] QR yorliq matni (`DS|<filial kodi>|<inv. raqam>`) kartochkadagi kalitga mos.
- [ ] 8 soat harakatsizlikdan keyin sessiya tugaydi va qayta login so'raydi.
