# Asosiy vositalar platformasi

Kompaniyaning **asosiy vositalari (AV)** — kompyuterlar, mebel, texnika, transport va boshqa mulk — qayerda
turgani, kimning javobgarligida ekani va qanday holatda ekanini kuzatadigan ichki veb-platforma.

Platforma 1C «КСБ» buxgalteriya bazasi bilan ishlaydi. Undan ma'lumotlarni **faqat o'qiydi**, 1C'ga hech qachon
hech narsa yozmaydi. 1C'da yo'q jismoniy hisobni esa o'zi yuritadi.

---

## Nima uchun kerak

1C buxgalteriya uchun yaxshi: unda AV qaysi filial balansida turgani, uning qiymati va soni bor. Lekin kundalik
ishda boshqa savollar tug'iladi, 1C esa ularga javob bermaydi:

- 5 dona stolning 3 tasi qaysi xonada, 2 tasi qayerda?
- Shu noutbuk kimda? U ishdan ketsa, unga biriktirilgan narsalar kimga o'tadi?
- Qaysi AV buzilgan, ta'mirda yoki topilmayapti?
- Reviziyada nimalar topildi, nimalar kam chiqdi?
- 1C'dagi ma'lumotlarning qayeri noto'g'ri (Javobgarsiz, bo'limsiz, dublikat, nolga tushgan)?

Bu savollarga odatda Excel jadvallari, qog'oz ro'yxatlar va xotira bilan javob berishga to'g'ri keladi. Natijada
ular 1C bilan mos kelmay qoladi. Platforma shu bo'shliqni yopadi. 1C buxgalteriya manbai bo'lib qolaveradi,
platforma esa uning ustidagi **jismoniy hisob qatlami** bo'ladi.

## Ishni qanday osonlashtiradi

| Avval | Platforma bilan |
|---|---|
| AV qayerdaligi Excel'da yoki xotirada, 1C bilan mos kelmaydi | Har dona AV bo'lim, javobgar shaxs va holat bo'yicha taqsimlanadi. Taqsimot doim 1C qoldig'iga teng bo'ladi, farq bo'lsa darhol ko'rinadi |
| Javobgar shaxs almashsa, akt qo'lda yoziladi | Topshirish-qabul akti tuziladi, chop etiladi (PDF), tasdiqlangach Javobgar shaxs avtomatik almashadi |
| Reviziya qog'ozda, natijalarni qo'lda solishtirish kerak | Revizor telefonda QR-kodni skanerlaydi. Vedomost o'zi tuziladi, farqlar yakunlashda taqsimotga yoziladi |
| 1C'dagi xatolarni topish qiyin | «Javobgarsiz», «bo'limsiz», «1C bilan mos emas» kabi belgilar va tozalash ro'yxatlari bor |
| Filiallararo o'tkazishni kuzatish qiyin | 1C chiqimlari platformaga keladi, hisobchi ularni bir bosishda tasdiqlaydi |
| Hisobot uchun ma'lumotni qo'lda yig'ish kerak | Kesim, Javobgar va bo'lim qaydnomalari, xizmat muddati hisobotlari tayyor. Ularni Excel'ga yuklash yoki chop etish mumkin |
| AV'ning texnik ma'lumoti hech qayerda yo'q | AV turiga qarab qo'shimcha maydonlar (masalan, kompyuterlar uchun CPU, RAM, Storage). Ular bo'yicha qidirish ham mumkin |
| Kim nimani o'zgartirgani noma'lum | Har o'zgarish jurnalga yoziladi, AV kartochkasida uning to'liq tarixi ko'rinadi |

## Asosiy imkoniyatlar

- **1C sinxroni.** Har 5 daqiqada o'zgarishlar, har kecha to'liq ma'lumot olinadi. Aloqa uzilsa, panelda ogohlantirish chiqadi.
- **AV ro'yxati va kartochkasi.** Filtrlar, qidiruv, saralash, sahifalash va Excel. Kartochkada rasmlar, amortizatsiya, taqsimot va tarix bor.
- **Taqsimot.** AV'ni bo'limlar (xonalar) o'rtasida ko'chirish va holatini o'zgartirish. Holatlar: ishlatilmoqda, zaxirada, ta'mirda, nosoz, hisobdan chiqarishga, topilmadi.
- **Javobgar shaxslar (МОЛ).** Kimda nima borligi, ishdan ketganlarda qolgan AV'lar, topshirish-qabul aktlari.
- **Reviziya (inventarizatsiya).** Revizorlar telefonda QR orqali sanaydi. Vedomost, bo'limlar kesimi va dalolatnoma (PDF) tayyorlanadi.
- **QR-yorliqlar.** Har AV uchun yorliq chop etiladi, o'lchamlari sozlanadi.
- **1C chiqimlari.** Sotish, filialga o'tkazish va hisobdan chiqarish 1C'dan keladi, taqsimotda tasdiqlanadi.
- **Hisobotlar.** Kesim, qaydnomalar, xizmat muddati, 1C ma'lumotlarini tozalash ro'yxatlari.
- **«Kutayotgan ishlar».** Tasdiq kutayotgan aktlar va chiqimlar, sizga biriktirilgan ochiq reviziyalar.

## Rollar

Huquqlar server tomonida tekshiriladi. Har foydalanuvchi faqat o'ziga biriktirilgan filiallarni ko'radi.

| Rol | Nima qiladi |
|---|---|
| **Admin** | Hamma narsa: foydalanuvchilar, sozlamalar, 1C ulanishi |
| **Hisobchi** | Asosiy foydalanuvchi: taqsimot, aktlar, 1C chiqimlarini tasdiqlash, reviziya, hisobotlar, yorliqlar |
| **HR** | Javobgar shaxslar va aktlar. Pul summalarini ko'rmaydi |
| **Rahbar** | Kuzatadi (soni, qiymat, hisobotlar), hech narsani o'zgartirmaydi |
| **Revizor** | Faqat reviziya: telefonda skanerlaydi |

## Texnologiyalar

- Python 3.12, Django 5.2, PostgreSQL 16
- HTMX, CoreUI 5 (Bootstrap 5). Barcha statik fayllar loyihaning o'zida, internet yoki CDN talab qilinmaydi
- WeasyPrint (PDF), openpyxl (Excel), segno (QR), django-axes (kirishni bloklash)
- 1C tomoni: «AVSinxron» kengaytmasi, HTTP-servis (faqat `Запрос` orqali o'qiydi) — [1c/README.md](1c/README.md)

---

## O'rnatish

### Talablar

- Python **3.12**
- PostgreSQL **16**
- WeasyPrint uchun Pango kutubxonasi:
  - Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0`
  - Windows: MSYS2 orqali `pacman -S mingw-w64-x86_64-pango`
- 1C serverida «AVSinxron» kengaytmasi o'rnatilgan bo'lishi kerak. Qanday o'rnatish [1c/README.md](1c/README.md) da yozilgan, kengaytmani ishchi bazaga faqat mas'ul xodim o'rnatadi.

### Lokal ishga tushirish (dasturchi uchun)

1. Kodni yuklab oling va virtual muhit yarating:

   ```bash
   git clone <REPO_MANZILI> asosiy_vositalar
   cd asosiy_vositalar
   python -m venv venv
   venv/Scripts/activate          # Windows; Linux/macOS: source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. PostgreSQL'da baza va foydalanuvchi yarating. Foydalanuvchiga testlar uchun `CREATEDB` huquqini ham bering:

   ```sql
   CREATE ROLE av LOGIN PASSWORD '<DB_PAROL>' CREATEDB;
   CREATE DATABASE av OWNER av ENCODING 'UTF8';
   ```

3. `.env.example` dan `.env` nusxasini oling va to'ldiring. `.env` git'ga kirmaydi, maxfiy qiymatlar faqat shu faylda saqlanadi:

   ```ini
   SECRET_KEY=<uzun-tasodifiy-kalit>
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=postgresql://av:<DB_PAROL>@localhost:5432/av
   ONEC_URL=<1C HTTP-servis manzili, .../hs/av>
   ONEC_LOGIN=<1C texnik foydalanuvchisi>
   ONEC_PAROL=<uning paroli>
   ```

4. Bazani tayyorlang va birinchi administratorni yarating:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

   `createsuperuser` rol bermaydi. Administratorga `admin` rolini bering (`<login>` o'rniga yaratgan foydalanuvchi nomingizni yozing):

   ```bash
   python manage.py shell -c "from django.contrib.auth import get_user_model; from hisoblar.models import Profil, Rol; u = get_user_model().objects.get(username='<login>'); Profil.objects.update_or_create(user=u, defaults={'rol': Rol.ADMIN})"
   ```

5. 1C'dan birinchi ma'lumotni oling va serverni ishga tushiring:

   ```bash
   python manage.py sinxron --toliq
   python manage.py runserver
   ```

   Brauzerda `http://localhost:8000` manzilini oching. Boshqa foydalanuvchilar **Sozlamalar → Foydalanuvchilar** bo'limida yaratiladi.

### Server (ishlab chiqarish) o'rnatish

Ubuntu 24.04 serverga o'rnatish bosqichma-bosqich [docs/ishga-tushirish.md](docs/ishga-tushirish.md) da yozilgan.
U quyidagilarni o'z ichiga oladi:

- gunicorn, nginx va systemd. Tayyor fayllar `deploy/` papkasida.
- Sinxron taymerlari: har 5 daqiqada va har kecha to'liq.
- Har kecha avtomatik zaxira (`pg_dump` va rasmlar), 14 kun saqlanadi. Zaxiradan tiklash tartibi ham shu yerda.
- HTTPS (VPS uchun).

## Testlar

Testlar ham PostgreSQL'da ishlaydi. Test bazasi avtomatik yaratiladi, `.env` shart emas:

```bash
python -m pytest -q
```

Haqiqiy 1C bazasiga ulanadigan jonli testlar alohida ishga tushiriladi: `python -m pytest -m jonli -q`
(bu haqda [docs/ishga-tushirish.md](docs/ishga-tushirish.md) ga qarang).

## Loyiha tuzilishi

| Papka | Vazifasi |
|---|---|
| `onec/` | 1C ma'lumotlari modeli (AV, filiallar, xodimlar, qoldiqlar) va sinxron |
| `vositalar/` | AV ro'yxati, kartochka, taqsimot, bo'limlar, tarix |
| `mol/` | Javobgar shaxslar va topshirish-qabul aktlari |
| `reviziya/` | Inventarizatsiya: panel va revizorning telefon sahifalari |
| `chiqimlar/` | 1C chiqimlarini tasdiqlash |
| `hisobotlar/` | Hisobotlar, qaydnomalar, tozalash ro'yxatlari |
| `yorliqlar/` | QR-yorliqlar |
| `hisoblar/` | Kirish, rollar va huquqlar |
| `jurnal/` | O'zgarishlar jurnali |
| `panel/` | Umumiy shablonlar, bosh sahifa, sozlamalar |
| `1c/` | 1C kengaytmasi «AVSinxron» |
| `deploy/` | Server sozlama fayllari (systemd, nginx, zaxira) |
| `docs/` | Spetsifikatsiya, rejalar, o'rnatish yo'riqnomasi |

## Muhim qoidalar

- **1C'ga hech narsa yozilmaydi.** Kengaytma faqat o'qiydi. 1C'dan kelgan maydonlar (nomi, inv. raqam, qiymat, filial, soni) panelda tahrirlanmaydi.
- **Maxfiy qiymatlar** (`SECRET_KEY`, `DATABASE_URL`, `ONEC_*`) faqat `.env` da saqlanadi.
- **Taqsimot invarianti:** har (AV, filial) uchun taqsimotdagi sonlar yig'indisi 1C qoldig'iga teng bo'ladi.
- **Kirish himoyasi:** 5 marta noto'g'ri parol kiritilsa, 15 daqiqaga bloklanadi. Sessiya 8 soat harakatsizlikdan keyin tugaydi.
