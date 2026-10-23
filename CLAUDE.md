# Asosiy vositalar platformasi

1C ma'lumotlarining **faqat o'qiladigan** nusxasi + AV platforma maydonlari (Django 5.2, PostgreSQL 16, Python 3.12).

## Qoidalar
- 1C'ga hech narsa yozilmaydi. Kengaytma faqat `Запрос` bilan o'qiydi; SQL'ga to'g'ridan-to'g'ri yozish taqiqlangan.
  Ishchi baza doms2021'ga kengaytmani faqat foydalanuvchi o'zi, aniq so'rovdan keyin o'rnatadi.
- 1C'dan kelgan maydonlar (nomi, inv. raqam, qiymat, filial, soni) panelda tahrirlanmaydi.
- Interfeys matnlari — o'zbek (lotin). Kod identifikatorlari — spetsifikatsiyadagi o'zbekcha nomlar.
- Maxfiy qiymatlar (`SECRET_KEY`, `DATABASE_URL`, `ONEC_URL`, `ONEC_LOGIN`, `ONEC_PAROL`) faqat `.env` da; `.env` git'ga kirmaydi.
- Testlar ham PostgreSQL'da. Celery ishlatilmaydi.
- Rollar: `admin`, `hisobchi`, `hr`, `rahbar`, `revizor` (revizor panelga kirmaydi, faqat `/reviziya/m/` mobil sahifalariga). Rol va filial cheklovi har so'rovda,
  queryset darajasida (`hisoblar.huquqlar`) — faqat sahifalarda emas: Excel, PDF, HTMX bo'laklar, rasm URL'larida ham.
- Kirish: 5 noto'g'ri urinish -> 15 daqiqa blok; sessiya 8 soat harakatsizlikdan keyin tugaydi.
- Holatlar: `ishlatilmoqda`, `zaxirada`, `tamirda`, `nosoz`, `hisobdan_chiqarishga`, `topilmadi`.
- Sinxron: har 5 daqiqada, harakatlar oynasi 45 kun, har kecha 03:00 to'liq, HTTP timeout 60 s, bitta tranzaksiya,
  bir vaqtda bitta sinxron (PostgreSQL advisory lock, kalit `7310001`).
- Taqsimot invarianti: har (AV, filial) uchun Σ `Taqsimot.soni` = `AVQoldiq.soni`.
- Python 3.12 bilan mos kod yozing (3.13'ga xos imkoniyatlar yo'q).

## Reviziya (2-bosqich)
- Ilova `reviziya`: inventarizatsiya hujjati `RV-%06d`, raqam advisory lock bilan (kalit `7310003`). Panel: `/reviziya/` (`reviziya_boshqarish`, `reviziya_korish`).
- Huquqlar: `reviziya_boshqarish` (admin, hisobchi), `reviziya_otkazish` (admin, hisobchi, revizor), `reviziya_korish` (admin, hisobchi, hr, rahbar).
- Revizor kirgach `/reviziya/m/` ga yo'naltiriladi: QR (`DS|<filial kodi>|<inv>`) skanerlaydi yoki inv bo'yicha qidiradi; qaydlar `+soni` bilan birlashadi.
- Oqim: hisobchi yakunlaydi -> vedomost -> qo'llash -> yopish. Holatlar: `ochiq`, `yakunlangan`, `qollangan`, `bekor`.
- Reviziya qaydlari AV tarixida (`tur="reviziya"`) filial cheklovi bilan chiqadi (`vositalar/tarix.py`).

## Buyruqlar
- Testlar (Windows, lokal): `venv\Scripts\python.exe -m pytest -q` (`.env` shart emas; `config.settings_test`; PostgreSQL rol `av`/`av`, CREATEDB)
- Sinxron: `python manage.py sinxron` (keyingi tasklarda qo'shiladi)
- Tekshiruv: `python manage.py check`
- Mahalliy ishga tushirish uchun `.env.example` dan `.env` yarating (dev: `DEBUG=True`).

## Hujjatlar
- Spetsifikatsiya: `docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md`
- Reja: `docs/superpowers/plans/2026-10-17-av-platforma-1-bosqich.md`
- 1C farazlari: `docs/1c-farazlar.md`
