# Asosiy vositalar platformasi

1C ma'lumotlarining **faqat o'qiladigan** nusxasi + AV platforma maydonlari (Django 5.2, PostgreSQL 16, Python 3.12).

## Qoidalar
- 1C'ga hech narsa yozilmaydi. Kengaytma faqat `Запрос` bilan o'qiydi; SQL'ga to'g'ridan-to'g'ri yozish taqiqlangan.
  Ishchi baza doms2021'ga kengaytmani faqat foydalanuvchi o'zi, aniq so'rovdan keyin o'rnatadi.
- 1C'dan kelgan maydonlar (nomi, inv. raqam, qiymat, filial, soni) panelda tahrirlanmaydi.
- Interfeys matnlari — o'zbek (lotin). Kod identifikatorlari — spetsifikatsiyadagi o'zbekcha nomlar.
- Maxfiy qiymatlar (`SECRET_KEY`, `DATABASE_URL`, `ONEC_URL`, `ONEC_LOGIN`, `ONEC_PAROL`) faqat `.env` da; `.env` git'ga kirmaydi.
- Testlar ham PostgreSQL'da. Celery ishlatilmaydi.
- Rollar: `admin`, `hisobchi`, `hr`, `rahbar`, `revizor` (revizor panelda faqat «Reviziyalar» ni ko'radi va `/reviziya/m/` mobil sahifalariga kiradi; hisobchida bosh sahifa yo'q — `bosh_sahifa` huquqi admin/hr/rahbarda, hisobchi AV ro'yxatiga o'tadi). Rol va filial cheklovi har so'rovda,
  queryset darajasida (`hisoblar.huquqlar`) — faqat sahifalarda emas: Excel, PDF, HTMX bo'laklar, rasm URL'larida ham.
- Kirish: 5 noto'g'ri urinish -> 15 daqiqa blok; sessiya 8 soat harakatsizlikdan keyin tugaydi.
- Holatlar: `ishlatilmoqda`, `zaxirada`, `tamirda`, `nosoz`, `hisobdan_chiqarishga`, `topilmadi`.
- Sinxron: har soatda, harakatlar oynasi 45 kun, har kecha 03:02:30 to'liq, HTTP timeout 60 s, bitta tranzaksiya,
  bir vaqtda bitta sinxron (PostgreSQL advisory lock, kalit `7310001`).
- Sinxron himoyasi: shubhali 1C javobi (qoldiq qatorlari 20% dan ko'p kamaysa, taqsimoti bor filial yo'q bo'lsa) hech narsa yozmay xato bilan tugaydi (`--majburiy` chetlab o'tadi); qoldig'i 0 bo'lgan qatorlar faqat to'liq sinxronda o'chiriladi (`moslashtir(toliq=False)` kechiktiradi).
- Dona narxi filial bo'yicha (`vositalar.narx.filial_narxlari`), umumiy o'rtacha emas: hisobot, qaydnoma, akt va dalolatnoma shundan oladi.
- Taqsimot invarianti: har (AV, filial) uchun Σ `Taqsimot.soni` = `AVQoldiq.soni`.
- Python 3.12 bilan mos kod yozing (3.13'ga xos imkoniyatlar yo'q).

## Reviziya (2-bosqich)
- Ilova `reviziya`: inventarizatsiya hujjati `RV-%06d`, raqam advisory lock bilan (kalit `7310003`). Panel: `/reviziya/` (`reviziya_boshqarish`, `reviziya_korish`).
- Huquqlar: `reviziya_boshqarish` (admin, hisobchi, revizor), `reviziya_otkazish` (admin, hisobchi, revizor), `reviziya_korish` (admin, hisobchi, hr, rahbar, revizor). Revizor — faqat o'z filiallarida (`filial_bilan_chekla`).
- Revizor kirgach `/reviziya/m/` ga yo'naltiriladi: QR (`DS|<filial kodi>|<inv>`) skanerlaydi yoki inv bo'yicha qidiradi; qaydlar `+soni` bilan birlashadi.
- Oqim: ochiq -> «Yakunlash» (farqlar avtomatik taqsimotga yoziladi, `qollash.yakunla_va_yoz`) -> yakunlangan; «Ochiqqa qaytarish» yozilganlarni teskari amal bilan qaytaradi. Holatlar: `ochiq`, `yakunlangan`, `bekor`.
- Yakunlash to'siqlari: sanalmagan xona bor bo'lsa rad etiladi (`sanalmagan_xonalar`; bo'sh xona — «Xona tugadi»); reviziya ochilgandan keyin (МОЛ aktidan tashqari) amal bo'lgan AV farqi yozilmaydi, jurnalda «xato» qoladi. Ochiqqa qaytarish kesishgan ochiq yoki keyingi yakunlangan reviziya bo'lsa rad etiladi (`qaytarishni_tekshir`).
- Reviziyada МОЛ biriktirish faqat shu xonadagi donalarni aktga qo'shadi (`mobil._biriktiriladigan`); yakunlash va qaytarish `akt_izohi` li qoralama akt qatorlarini ham ko'chiradi (`qollash._aktni_ergashtir`).
- Reviziyani o'zgartirish: `reviziya.ruxsat` (`ozgartira_oladi`, `ozgartiradigan_shart`); `Sozlama.reviziya_faqat_ozimniki` yoqilsa — faqat admin, ochgan kishi va revizorlari.
- Reviziya qaydlari AV tarixida (`tur="reviziya"`) filial cheklovi bilan chiqadi (`vositalar/tarix.py`).

## Buyruqlar
- Testlar (Windows, lokal): `venv\Scripts\python.exe -m pytest -q` (`.env` shart emas; `config.settings_test`; PostgreSQL rol `av`/`av`, CREATEDB)
- Sinxron: `python manage.py sinxron` (to'liq: `--toliq`)
- Tekshiruv: `python manage.py check`
- Sahifa tezligi: `python manage.py sahifa_tezligi <login>`
- Mahalliy ishga tushirish uchun `.env.example` dan `.env` yarating (dev: `DEBUG=True`).

## Hujjatlar
- Spetsifikatsiya: `docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md`
- Reja: `docs/superpowers/plans/2026-10-17-av-platforma-1-bosqich.md`
- 1C farazlari: `docs/1c-farazlar.md`
- Ishchi server (Windows, av.dsyuksak.uz:8092): `docs/ishga-tushirish-windows.md`, skriptlar `deploy/windows/`
- Administrator qo'llanmasi: `docs/admin-qollanma.md` (video va rasmli PDF: `D:/claude/video/out`, git'ga kirmaydi)
