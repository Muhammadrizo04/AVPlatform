# Asosiy vositalar platformasi — 1-bosqich: Asos (dizayn spetsifikatsiyasi)

Sana: 2026-10-17 · Holat: foydalanuvchi ko'rib chiqishi kutilmoqda
Loyiha papkasi: `D:\claude\asosiy_vositalar\`

---

## 1. Maqsad va kontekst

Dom Stroy kompaniyasida asosiy vositalar (AV) 1C «КСБ» (KSB SOFT v1.0.24.02, platforma 8.3.13, moslik rejimi 8.3.9) da
yuritiladi, lekin:

- AV faqat **filial** kesimida hisobga olinadi — filial ichida qaysi **bo'limda** turgani noma'lum;
- **javobgar shaxs (МОЛ)** yo'q — kimda qanday AV borligi, xodim ketganda nima qolgani nazorat qilinmaydi;
- bir xil AV'lar ko'pincha **guruh** bo'lib kiritilgan (bitta yozuv × 20 dona), inventar raqamlari tartibsiz;
- AV'ning rasmi, holati, xizmat muddati, eskirishi, tarixi bir joyda yo'q;
- QR-yorliqlarni chop etish imkoniyati amalda yo'q.

**Yechim:** Snipe-IT'ga o'xshash, lekin IT'ga bog'lanmagan (bino, mebel, transport, uskuna va h.k. — 1C'dagi 17 ta
ГруппаОС), ortiqchasiz, **1C bilan integratsiyalashgan** veb-platforma (Django) + reviziya uchun telefon ilovasi (APK).

Ko'lam: 1C'da ~2129 AV yozuvi, ~4200 dona, 20 filial. Tozalashdan keyin ~4200 ta alohida inventar raqam.

### Bosqichlar (har biri alohida spetsifikatsiya → reja → amalga oshirish)

| Bosqich | Tarkibi |
|---|---|
| **1. Asos** (shu hujjat) | 1C sinxronlash, Django bazasi, veb-panel: AV kartochkasi, bo'limlar, МОЛ va topshirish-qabul aktlari, holat, rasm, amortizatsiya, QR-yorliqlar, tozalash ro'yxatlari, hisobotlar, jurnal |
| 2. Reviziya | Panelda reviziya ochish (filial/bo'lim, revizor), telefon APK (QR skan: topildi / topilmadi / ortiqcha / boshqa joyda, rasm, holat), solishtirish vedomosti, **reviziya dalolatnomasi** (chop etish/PDF) |
| 3. Nazorat va hisobotlar | Dashboard kengaytmasi, tekshiruv va xizmat muddati eslatmalari, ta'mir jurnali, Telegram |

## 2. Asosiy qarorlar (foydalanuvchi bilan kelishilgan)

1. **1C → platforma, faqat o'qish.** Platforma 1C'ga hech narsa yozmaydi. Kirim, filiallararo ko'chirish, hisobdan
   chiqarish, sotish faqat 1C'da qilinadi va platformaga sinxron orqali keladi. 1C'dan yangi ma'lumot kerak bo'lsa —
   1C servisiga maydon + Django modeliga maydon qo'shiladi.
2. **Bitta inventar raqam = bitta buyum.** Guruh yozuvlari 1C'da hisobchi tomonidan bo'linadi; platforma o'tish davrida
   ularni «1C'da bo'linishi kerak» deb belgilaydi.
3. **Inventar raqam faqat filial ichida noyob.** AV kaliti = `ОсновныеСредства.Филиал` (rekvizit) + `ИнвентарныйНомер`.
4. **Filial 1C'dan, bo'lim platformadan.** Filial ichidagi bo'limlar daraxti platformada yuritiladi.
5. **МОЛ = 1C «Ходимлар» (Корхона ходимлари).** МОЛ faqat topshirish-qabul akti orqali o'zgaradi.
6. **Amortizatsiya — faqat ma'lumot uchun** (chiziqli), 1C'ga yozilmaydi.
7. **QR-yorliqlar platformada**, termo-printer uchun. Kalit o'zgarsa — yorliq almashtiriladi.
8. **Qo'shimcha maydonlar AV turiga qarab.** Holatlar — 6 ta (§5.2).
9. **Arxitektura A:** Django + PostgreSQL alohida serverda, 1C'dan HTTP orqali tortib oladi. Panel — Django templates +
   HTMX. Avval ichki Linux VM (↔ doms2021), keyin VPS (↔ online 1C).

## 3. Arxitektura

```
 1C: TestClaude (ishlab chiqish) → doms2021 (VM bosqichi) → online 1C (VPS bosqichi)
   └─ kengaytma «AVSinxron»: HTTP-servis /hs/av/  — faqat o'qish, JSON
            ▲  har 5 daqiqada + har kecha to'liq (HTTP Basic, texnik login)
            │
 Django serveri (Ubuntu 24.04)
   ├─ sinxron moduli (management command, systemd timer)
   ├─ PostgreSQL 16 — 1C nusxasi + platforma ma'lumotlari
   ├─ media/ — AV rasmlari
   ├─ veb-panel — Django templates + HTMX
   └─ REST API — telefon ilovasi uchun (2-bosqichda)
            ▲
 Telefon APK (2-bosqich) — faqat Django API bilan ishlaydi, 1C'ga ulanmaydi
```

**Asosiy qoida:** 1C'dan kelgan maydonlar (nomi, inv. raqam, qiymat, filial, soni) panelda **o'zgartirilmaydi**.
Platforma maydonlari: bo'lim, МОЛ, holat, rasm, ishga tushgan sana, xizmat muddati, qo'shimcha maydonlar, izoh.

## 4. Rollar va huquqlar

Platformaning o'z foydalanuvchilari (login + parol). Har foydalanuvchiga **ruxsat berilgan filiallar** ro'yxati
(bo'sh = hammasi). Rol va filial cheklovi har so'rovda server tomonida, queryset darajasida tekshiriladi.

| Rol | Huquqlar |
|---|---|
| **Administrator** | Hammasi + foydalanuvchilar, rollar, AV turlari sozlamalari, 1C ulanishi, «Hozir sinxronlash», jurnallar |
| **Hisobchi** | AV platforma maydonlari (bo'lim, holat, rasm, xizmat muddati, qo'shimcha maydonlar, izoh), bo'limlar daraxti, МОЛ aktlari, yorliqlar, tozalash ro'yxatlari, hisobotlar |
| **HR** | МОЛ nazorati: xodimlar va ulardagi AV, topshirish-qabul aktlari (yaratish, tasdiqlash, chop etish), «Ketgan xodimlarda qolgan AV», hisobotlar. Holat, bo'lim, narx — faqat ko'rish |
| **Rahbar** | Hammasini ko'rish va hisobotlar, hech narsani o'zgartirmaydi |
| **Revizor** | 1-bosqichda panelga kirmaydi; 2-bosqichda telefon ilovasi |

## 5. Ma'lumotlar modeli

### 5.1. 1C nusxasi (faqat sinxron yozadi)

Har jadvalda `ref_1c` (UUID, unique), `sinx_vaqti`, `1c_da_yoq` (bool) bor. 1C'da yo'qolgan yozuv o'chirilmaydi.

| Model | 1C manbasi | Maydonlar |
|---|---|---|
| `Tashkilot` | Справочник.Организация | nomi |
| `Filial` | Справочник.Филиал | kod, nomi |
| `AVTuri` | Справочник.ГруппаОС | nomi, tip (Перечисление.ГруппыОС) |
| `Xodim` | Справочник.Ходимлар | ism, filial, telefon, ishdan_bushagan, neaktiv, o'chirish belgisi |
| `AV` | Справочник.ОсновныеСредства | kod, nomi, to'liq nomi, inv_raqam, chiqarilgan_sana, turi, tashkilot, **filial_rekvizit** (Филиал), izoh_1c, o'chirish belgisi |
| `AVQoldiq` | РегистрНакопления.УчетОС (остатки) | AV, tashkilot, filial, soni, summa |
| `Harakat1C` | РегистрНакопления.УчетОС (движения) | sana, hujjat_turi, hujjat_raqami, hujjat_ref, AV, filial, tashkilot, kirim/chiqim, soni, summa |
| `SinxronJurnal` | — | boshlanish, tugash, natija, xato matni, o'zgarishlar soni |

**Hosilaviy qiymatlar (AV darajasida):**
- `joriy_filial` — qoldig'i > 0 bo'lgan filial; bir nechta bo'lsa — bayroq.
- `soni`, `summa` — joriy qoldiq bo'yicha. Qoldiq 0 → **arxiv**.
- `kalit` = (filial_rekvizit.kod, inv_raqam).

### 5.2. Platforma ma'lumotlari

- **`Bolim`** — filial, ota-bo'lim (daraxt: bo'lim → xona/joy), nomi, faol.
- **`AVKartochka`** (AV'ga 1:1):
  - `bolim` (faqat joriy filialdagi bo'lim), `mol` (Xodim);
  - `holat`: `ishlatilmoqda` · `zaxirada` · `tamirda` · `nosoz` · `hisobdan_chiqarishga` · `topilmadi`;
  - `ishga_tushgan_sana` — standart: AV'ning 1C'dagi birinchi kirim harakati sanasi;
  - `xizmat_muddati_oy` — bo'sh bo'lsa AV turi sozlamasidan;
  - `qoshimcha` (JSON — AV turi maydonlari bo'yicha qiymatlar), `izoh`;
  - `yorliq_kaliti` (oxirgi chop etilgan QR kaliti), `yorliq_sana`;
  - `versiya` (optimistik blokirovka uchun).
- **`AVTuriSozlama`** — AVTuri'ga 1:1: standart xizmat muddati (oy), qo'shimcha maydonlar ro'yxati
  (`kalit`, `nomi`, `tip`: matn / son / sana / tanlov, `tanlov_qiymatlari`, `majburiy`).
- **`Rasm`** — AV, fayl, miniatyura, asosiy (bool), kim, qachon.
- **`MolAkt`** — raqam (avtomatik), sana, topshiruvchi (Xodim yoki «yo'q» — birinchi biriktirish), qabul qiluvchi
  (Xodim), izoh, holat (`qoralama` / `tasdiqlangan`), kim tuzdi, kim tasdiqladi.
  **`MolAktQator`** — akt, AV.
- **`BolimKochirish`** — AV, eski bo'lim, yangi bo'lim, sana, kim, sabab (`qolda` / `1c_filial_ozgardi`).
- **`Jurnal`** — kim (foydalanuvchi yoki «1C sinxron»), qachon, obyekt, maydon, eski qiymat, yangi qiymat.
- **`Foydalanuvchi`** — Django User + rol + ruxsat berilgan filiallar.
- **`Sozlama`** — yorliq o'lchami (40×30 / 58×40), kompaniya nomi (yorliq/aktlar uchun) va h.k.

### 5.3. Hisoblanadigan (saqlanmaydi)

- **Amortizatsiya (chiziqli):** `oylar` = ishga_tushgan_sana dan bugungacha to'liq oylar;
  `qoldiq_qiymat = summa × max(0, 1 − oylar / xizmat_muddati_oy)`; `eskirish_% = min(100, oylar / xizmat_muddati_oy × 100)`;
  `tugash_sanasi = ishga_tushgan_sana + xizmat_muddati_oy`. Asos — 1C'dagi **joriy** summa (ПереоценкаОС'dan keyingi).
  Xizmat muddati yoki sana noma'lum bo'lsa — «hisoblab bo'lmaydi».
- **AV tarixi** — Harakat1C + BolimKochirish + MolAkt + holat o'zgarishlari (Jurnal) + rasmlar — sana bo'yicha
  yagona vaqt chizig'i.

### 5.4. Bayroqlar (tozalash va nazorat ro'yxatlari)

| Bayroq | Shart | Kim tuzatadi |
|---|---|---|
| 1C'da bo'linishi kerak | soni > 1 | hisobchi, 1C'da |
| Inv. raqam bo'sh | inv_raqam bo'sh | hisobchi, 1C'da |
| Inv. raqam takror | bir filial_rekvizit ichida bir xil inv_raqam | hisobchi, 1C'da |
| Filial rekviziti bo'sh | filial_rekvizit bo'sh | hisobchi, 1C'da |
| Bir nechta filialda | qoldiq > 0 bo'lgan filiallar > 1 | hisobchi, 1C'da |
| Bo'limga joylash kerak | faol AV, bo'lim bo'sh | hisobchi, platformada |
| МОЛ'siz | faol AV, МОЛ bo'sh | HR, platformada |
| Ketgan xodimda | МОЛ ishdan bo'shatilgan / neaktiv / 1C'da yo'q | HR, platformada |
| Yorlig'i chop etilmagan | yorliq_kaliti bo'sh | hisobchi |
| Yorliqni almashtirish kerak | yorliq_kaliti ≠ joriy kalit | hisobchi |
| Xizmat muddati tugagan / 6 oyda tugaydi | amortizatsiya bo'yicha | ma'lumot uchun |

## 6. 1C bilan sinxronlash

### 6.1. 1C kengaytmasi «AVSinxron»

- Yangi, MobilOstatka'dan mustaqil kengaytma, o'z versiyasi bilan. Faqat so'rovlar (Запрос), yozuv yo'q.
  Iloji bo'lsa **xavfsiz rejim yoqilgan** holda ishlaydi (привилегированный режим kerak emas).
- HTTP-servis, kontekst `/hs/av/`, barcha javoblar `application/json; charset=utf-8`:

| Metod | Javob |
|---|---|
| `GET /versiya` | `{versiya, baza, server_vaqti}` |
| `GET /spravochniklar` | `{tashkilotlar[], filiallar[], av_turlari[], xodimlar[]}` — to'liq; har yozuvda `ref` (UUID) |
| `GET /vositalar` | `{vositalar[], qoldiqlar[]}` — barcha ОсновныеСредства va УчетОС qoldiqlari |
| `GET /harakatlar?dan=YYYYMMDDhhmmss&gacha=...` | УчетОС harakatlari: `sana, hujjat_turi, hujjat_raqami, hujjat_ref, av, tashkilot, filial, vid (kirim/chiqim), soni, summa` |

- 1C'da texnik foydalanuvchi (`AVSinxron`), faqat o'qish huquqi. Publikatsiyada `reuseSessions="autouse"`.
- **Xavf:** noldan yasalgan kengaytma avval 404 bergan (CLAUDE.md). Avval TestClaude'da tekshiriladi; muammo qaytsa —
  servis MobilOstatka ichida alohida HTTP-servis sifatida joylanadi.

### 6.2. Django sinxron jarayoni

- `manage.py sinxron` — systemd timer har **5 daqiqada**:
  1. `/spravochniklar` va `/vositalar` to'liq → UUID bo'yicha upsert; kelmaganlar `1c_da_yoq = True`;
  2. `/harakatlar` — **oxirgi 45 kun** oynasi qayta olinadi va shu davrdagi Harakat1C almashtiriladi;
  3. hosilaviy qiymatlar, bayroqlar va avtomatik oqibatlar (§6.3).
- `manage.py sinxron --toliq` — har kecha (03:00): barcha harakatlar to'liq qayta olinadi.
- Paneldagi «Hozir sinxronlash» (administrator) — xuddi shu buyruq; bir vaqtda faqat bitta sinxron (DB advisory lock).
- Har sinxron **bitta tranzaksiyada**. 1C javob bermasa / xato bersa / JSON buzilgan bo'lsa → rollback, eski ma'lumot
  saqlanadi, SinxronJurnal'ga xato yoziladi.
- Panel sarlavhasida: «Oxirgi muvaffaqiyatli sinxron: HH:MM». 3 marta ketma-ket xato → qizil ogohlantirish.
- HTTP: timeout 60 s, 1C manzili/login/parol — `.env`.

### 6.3. Sinxronning avtomatik oqibatlari (har biri Jurnal'ga «1C sinxron» nomidan)

- **Joriy filial o'zgardi** → `bolim = null`, BolimKochirish (sabab `1c_filial_ozgardi`) → «Bo'limga joylash kerak».
- **Qoldiq 0** → arxiv: faol ro'yxatlardan chiqadi, МОЛ va tarix saqlanadi.
- **Xodim ishdan bo'shatildi / neaktiv / 1C'da yo'q** → uning AV'lari «Ketgan xodimda».
- **Kalit o'zgardi** (inv. raqam yoki filial rekviziti) → «Yorliqni almashtirish kerak».
- **Yangi AV** → AVKartochka yaratiladi (holat `ishlatilmoqda`, bo'lim va МОЛ bo'sh).

### 6.4. Bazani almashtirish

TestClaude → doms2021 → online 1C: faqat `.env` dagi manzil va login o'zgaradi. Konfiguratsiyada «Полный» almashuv
rejasi `DistributedInfoBase = true` (РИБ) — UUID'lar bazalar o'rtasida bir xil bo'lishi kutiladi. **Ko'chishdan oldin
majburiy tekshiruv:** kamida 20 ta AV va 5 ta xodimning UUID'i ikkala bazada solishtiriladi; mos kelmasa — ko'chish
to'xtatiladi va kalit (filial + inv) bo'yicha bog'lash rejasi alohida ishlab chiqiladi.

## 7. Veb-panel (o'zbekcha, lotin; kompyuter va planshet)

1. **Kirish** — login/parol; 5 noto'g'ri urinish → 15 daqiqa blok; sessiya 8 soat harakatsizlikdan keyin tugaydi.
2. **Bosh sahifa** — filiallar bo'yicha AV soni, boshlang'ich va qoldiq qiymat; «Diqqat talab qiladi» kartochkalari
   (§5.4 bayroqlari soni, bosilsa — ro'yxat); oxirgi sinxron.
3. **AV ro'yxati** — qidiruv (inv. raqam, nom), filtrlar (filial, bo'lim, tur, holat, МОЛ, arxiv, bayroqlar),
   sahifalash, Excel eksport. Ommaviy amallar: bo'limga ko'chirish, holatni o'zgartirish, yorliq chop etish.
4. **AV kartochkasi** — 1C bloki (o'zgarmaydi) · platforma bloki (tahrir) · tur bo'yicha qo'shimcha maydonlar ·
   rasmlar (yuklash, asosiy qilish; telefon brauzerida kameradan) · amortizatsiya · tarix vaqt chizig'i · yorliq chop etish.
5. **Bo'limlar** — filial tanlash, daraxt (qo'shish, nomini o'zgartirish, nofaol qilish — ichida AV bo'lsa nofaol
   qilib bo'lmaydi), bo'lim AV ro'yxati.
6. **МОЛ nazorati** — xodimlar ro'yxati (AV soni, qiymati), xodim sahifasi, «Ketgan xodimlarda qolgan AV»,
   **topshirish-qabul aktlari**: yangi akt (topshiruvchi → qabul qiluvchi, AV: hammasi yoki tanlab) → qoralama →
   tasdiqlash (МОЛ o'zgaradi) → chop etish / PDF (kompaniya, sana, raqam, AV jadvali, imzo joylari).
   Tasdiqlangan akt o'zgartirilmaydi; xato bo'lsa — teskari akt tuziladi.
7. **Tozalash ro'yxatlari** — §5.4'dagi 1C bayroqlari, Excel eksport.
8. **QR-yorliqlar** — AV ro'yxatidan / bo'lim bo'yicha / «chop etilmagan» / «almashtirish kerak» filtri bo'yicha.
   Har yorliq — PDF'ning bitta sahifasi (40×30 yoki 58×40 mm). Tarkibi: QR, inv. raqam (katta), filial nomi, AV nomi
   (qisqa, 2 qator). **QR matni:** `DS|<filial kodi>|<inv raqam>`. Chop etilganda `yorliq_kaliti`, `yorliq_sana` yoziladi.
9. **Hisobotlar** — AV filial / bo'lim / tur kesimida (soni, boshlang'ich, qoldiq qiymat); МОЛ bo'yicha qaydnoma;
   xizmat muddati tugagan va 6 oyda tugaydiganlar. Excel va chop etish.
10. **Sozlamalar (administrator)** — foydalanuvchilar, rollar va filiallar; AV turlari (xizmat muddati, qo'shimcha
    maydonlar); yorliq o'lchami; 1C ulanishi holati va «Hozir sinxronlash»; sinxron jurnali; harakatlar jurnali.

## 8. Xatolarga chidamlilik va tekshiruvlar

- MolAkt tasdiqlash — bitta tranzaksiya: qabul qiluvchi faol va ishdan bo'shatilmagan; har AV haqiqatan topshiruvchida
  (topshiruvchi bo'sh bo'lsa — AV'da МОЛ yo'q); AV arxivda emas. Bitta shart buzilsa — hech narsa o'zgarmaydi.
- Bo'lim faqat AV'ning joriy filialidagi bo'limlardan tanlanadi.
- AVKartochka tahriri — `versiya` bilan optimistik blokirovka: «Ma'lumot boshqa foydalanuvchi tomonidan o'zgartirildi,
  sahifani yangilang».
- Rasm: jpg/png, ≤ 15 MB; serverda max 1600 px gacha kichraytiriladi + miniatyura.
- Qo'shimcha maydonlar AV turi sozlamasi bo'yicha tekshiriladi (tip, majburiylik).
- Filial cheklovi: ruxsatsiz filial AV'siga to'g'ridan URL bilan kirish → 404.

## 9. Texnologiyalar

Ubuntu 24.04 · Python 3.12 · Django 5.2 LTS · PostgreSQL 16 · HTMX · gunicorn + nginx · systemd timer ·
openpyxl (Excel) · WeasyPrint (PDF: aktlar, hisobotlar, yorliqlar) · segno (QR) · Pillow · requests ·
pytest-django. Celery ishlatilmaydi.

## 10. Xavfsizlik va zaxira

- Parollar Django hash; brute-force himoyasi; CSRF; sessiya muddati.
- 1C texnik login va DB paroli — `.env` (git'ga kirmaydi).
- VPS'da HTTPS majburiy; VM bosqichida panel faqat ichki tarmoqda.
- Har kecha `pg_dump` + `media/` zaxirasi, 14 kun saqlanadi; tiklash tartibi hujjatlashtiriladi.

## 11. Sinov

- **Avtomatik (pytest-django):**
  - amortizatsiya formulasi (chegaraviy holatlar: muddat 0/bo'sh, sana kelajakda, muddati o'tgan);
  - sinxron mantiqi — TestClaude'dan yozib olingan haqiqiy JSON namunalari bilan: yangi AV, filial o'zgarishi →
    bo'lim tozalanadi, arxiv, xodim ketishi, kalit o'zgarishi, 1C'da yo'qolish, xato javobda rollback;
  - bayroqlar (§5.4);
  - rol va filial cheklovlari (har rol × har sahifa/amal);
  - MolAkt jarayoni va uning tekshiruvlari;
  - QR matni va yorliq kaliti.
- **Integratsiya:** Django ↔ TestClaude `/hs/av/` jonli.
- **Qabul qilish:** foydalanuvchi bilan qo'lda tekshirish ro'yxati (har rol uchun asosiy ssenariylar).

## 12. Ishga tushirish

1. **Ishlab chiqish:** Django ↔ TestClaude. Kengaytma faqat TestClaude'ga o'rnatiladi.
2. **Ichki VM ↔ doms2021:** `.dt` zaxira → kengaytma .cfe ishchi bazaga (foydalanuvchi o'zi, Konfigurator orqali) →
   texnik foydalanuvchi → sinov → xodimlarga ochiladi; 1C tozalash ishlari boshlanadi.
3. **VPS ↔ online 1C** (2-bosqich tayyor bo'lgach): UUID tekshiruvi (§6.4) → `pg_dump` + `media/` ko'chirish →
   `.env` almashtirish → HTTPS.

## 13. Amalga oshirishdan oldin tekshiriladigan farazlar (TestClaude'da)

1. `ОсновныеСредства.Филиал` rekviziti ПеремещениеОС'da o'zgarmaydi (faqat УчетОС o'lchami o'zgaradi).
2. Barcha ОС hujjatlari УчетОС'ga harakat yozadi (kod obfuskatsiyalangan — haqiqiy hujjatlar bilan tekshiriladi).
3. «Ходимлар» spravochnigi ishchi bazada to'ldirilgan va МОЛ sifatida yaroqli.
4. Yangi kengaytma HTTP-servisi publikatsiyada ishlaydi (404 muammosi).
5. Kengaytma xavfsiz rejimda so'rovlarni bajara oladi.

Biror faraz noto'g'ri chiqsa — dizaynning tegishli qismi foydalanuvchi bilan qayta kelishiladi.

## 14. 1-bosqichga kirmaydi

Reviziya va dalolatnoma, telefon APK, revizor ishi (2-bosqich); ta'mir jurnali, eslatmalar, Telegram, kengaytirilgan
dashboard (3-bosqich); 1C'ga har qanday yozuv; rasmiy buxgalteriya amortizatsiyasi; litsenziya, komponent, sarflov
materiallari, bron qilish (Snipe-IT'ning IT-ga xos qismlari).
