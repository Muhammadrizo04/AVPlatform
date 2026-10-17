# Asosiy vositalar platformasi — 1-bosqich: Asos (dizayn spetsifikatsiyasi)

Sana: 2026-10-17 · Holat: foydalanuvchi ko'rib chiqishi kutilmoqda (guruh AV taqsimoti bilan yangilangan)
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

Ko'lam: 1C'da ~2129 AV yozuvi, ~4200 dona, 20 filial. Guruh yozuvlari (bitta inv. raqam × N dona) hozircha
saqlanib qoladi; keyinchalik 1C'da bo'linishi mumkin.

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
2. **Guruh AV saqlanadi, soni bo'yicha taqsimlanadi** (2026-10-17 qayta kelishildi). 1C'dagi yozuv (masalan,
   «Ofis stuli» × 20) o'zgarmaydi; platformada u **taqsimot qatorlariga** bo'linadi: joriy filial × bo'lim × МОЛ × holat →
   soni. Har AV × filial uchun qatorlar yig'indisi = 1C qoldig'i. Keyinchalik 1C'da guruhlar bo'linsa — shu mexanizm
   o'zgarishsiz ishlaydi (§6.3).
3. **Inventar raqam faqat filial ichida noyob.** AV kaliti = `ОсновныеСредства.Филиал` (rekvizit) + `ИнвентарныйНомер`.
4. **Filial 1C'dan, bo'lim platformadan.** Filial ichidagi bo'limlar daraxti platformada yuritiladi.
5. **МОЛ = 1C «Ходимлар» (Корхона ходимлари).** МОЛ faqat topshirish-qabul akti orqali o'zgaradi.
6. **Amortizatsiya — faqat ma'lumot uchun** (chiziqli), 1C'ga yozilmaydi.
7. **QR-yorliqlar platformada**, termo-printer uchun; o'lchamlar sozlamada qo'shiladi va o'zgartiriladi. Kalit
   o'zgarsa — yorliq almashtiriladi.
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
Platforma maydonlari: taqsimot (bo'lim, МОЛ, holat — soni bilan), rasm, ishga tushgan sana, xizmat muddati,
qo'shimcha maydonlar, izoh.

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
- `filiallar` — qoldig'i > 0 bo'lgan filial(lar); guruh AV bir necha filialda bo'lishi normal holat.
- `soni`, `summa` — barcha filiallar bo'yicha jami qoldiq; `dona_narxi = summa / soni`. Jami qoldiq 0 → **arxiv**.
- `kalit` = (filial_rekvizit.kod, inv_raqam).

### 5.2. Platforma ma'lumotlari

- **`Bolim`** — filial, ota-bo'lim (daraxt: bo'lim → xona/joy), nomi, faol.
- **`Taqsimot`** — AV, `filial` (1C'dagi joriy filial), `bolim` (shu filialdan; bo'sh = taqsimlanmagan), `mol`
  (Xodim; bo'sh mumkin), `holat`, `soni` (> 0). Unikal: (AV, filial, bolim, mol, holat) — bir xil qatorlar birlashadi.
  **Invariant:** har (AV, filial) uchun Σ soni = AVQoldiq.soni; buzilsa — «Taqsimot 1C bilan mos emas» (§6.3).
  `holat`: `ishlatilmoqda` · `zaxirada` · `tamirda` · `nosoz` · `hisobdan_chiqarishga` · `topilmadi`.
- **`AVKartochka`** (AV'ga 1:1, butun guruh uchun umumiy):
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
  **`MolAktQator`** — akt, AV, manba (filial, bo'lim, holat), soni.
- **`TaqsimotHarakat`** — har bir taqsimot o'zgarishi: AV, filial, eski (bo'lim, МОЛ, holat) → yangi (bo'lim, МОЛ,
  holat), soni, sana, kim, sabab (`kochirish` / `holat` / `mol_akt` / `1c_kopaydi` / `1c_kamaydi` / `1c_nolga_tushdi`),
  1C hujjati (bo'lsa).
- **`Jurnal`** — kim (foydalanuvchi yoki «1C sinxron»), qachon, obyekt, maydon, eski qiymat, yangi qiymat.
- **`Foydalanuvchi`** — Django User + rol + ruxsat berilgan filiallar.
- **`YorliqOlchami`** — nomi, eni (mm), bo'yi (mm), faol, standart. Administrator yangi o'lcham qo'shadi yoki
  mavjudini o'zgartiradi (eni 20–120 mm, bo'yi 15–120 mm). Boshlang'ich: 40×30 (standart) va 58×40.
- **`Sozlama`** — kompaniya nomi (yorliq/aktlar uchun) va h.k.

### 5.3. Hisoblanadigan (saqlanmaydi)

- **Amortizatsiya (chiziqli):** `oylar` = ishga_tushgan_sana dan bugungacha to'liq oylar;
  `qoldiq_qiymat = summa × max(0, 1 − oylar / xizmat_muddati_oy)`; `eskirish_% = min(100, oylar / xizmat_muddati_oy × 100)`;
  `tugash_sanasi = ishga_tushgan_sana + xizmat_muddati_oy`. Asos — 1C'dagi **joriy** summa (ПереоценкаОС'dan keyingi).
  Xizmat muddati yoki sana noma'lum bo'lsa — «hisoblab bo'lmaydi».
- **Qator qiymati** (taqsimot, МОЛ qaydnomasi, hisobotlar) = soni × dona_narxi (boshlang'ich va qoldiq qiymat uchun).
- **AV tarixi** — Harakat1C + TaqsimotHarakat + MolAkt + Jurnal + rasmlar — sana bo'yicha yagona vaqt chizig'i.

### 5.4. Bayroqlar (tozalash va nazorat ro'yxatlari)

| Bayroq | Shart | Kim tuzatadi |
|---|---|---|
| Inv. raqam bo'sh | inv_raqam bo'sh | hisobchi, 1C'da |
| Inv. raqam takror | bir filial_rekvizit ichida bir xil inv_raqam | hisobchi, 1C'da |
| Filial rekviziti bo'sh | filial_rekvizit bo'sh | hisobchi, 1C'da |
| Taqsimot 1C bilan mos emas | biror (AV, filial) uchun Σ taqsimot ≠ 1C qoldig'i | hisobchi, platformada |
| Bo'limga joylash kerak | bo'limi bo'sh taqsimot qatori bor (soni bilan) | hisobchi, platformada |
| МОЛ'siz | МОЛ'i bo'sh taqsimot qatori bor (soni bilan) | HR, platformada |
| Ketgan xodimda | qator МОЛ'i ishdan bo'shatilgan / neaktiv / 1C'da yo'q (soni bilan) | HR, platformada |

«Guruh AV» (soni > 1) — xato emas, oddiy filtr.
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

Har (AV, filial) uchun `d = 1C qoldig'i − Σ taqsimot`:

- **d > 0 (ko'paydi:** kirim, boshqa filialdan kelish, 1C'da guruhdan ajratilgan yangi yozuv) → d dona shu filialdagi
  **taqsimlanmagan** qatorga (bo'lim va МОЛ bo'sh, holat `ishlatilmoqda`) qo'shiladi → «Bo'limga joylash kerak».
- **d < 0 (kamaydi:** hisobdan chiqarish, sotish, boshqa filialga o'tkazish, 1C'da guruhni bo'lish) → avval
  taqsimlanmagan qatordan ayiriladi; yetmasa qolgan farq uchun AV **«Taqsimot 1C bilan mos emas»** ga tushadi.
  Hisobchi oynada «N dona chiqarilishi kerak» va sababchi 1C hujjati(lari)ni (Harakat1C'dan) ko'radi, qaysi
  qatorlardan kamaytirishni tanlaydi → TaqsimotHarakat (`1c_kamaydi`, hujjat bilan).
- **1C qoldig'i shu filialda 0** → shu filialdagi barcha qatorlar avtomatik o'chiriladi (`1c_nolga_tushdi`) —
  noaniqlik yo'q. Barcha filiallarda 0 → **arxiv**: faol ro'yxatlardan chiqadi, tarix saqlanadi.
- **Xodim ishdan bo'shatildi / neaktiv / 1C'da yo'q** → u МОЛ bo'lgan taqsimot qatorlari «Ketgan xodimda».
- **Kalit o'zgardi** (inv. raqam yoki filial rekviziti) → «Yorliqni almashtirish kerak».
- **Yangi AV** → AVKartochka yaratiladi, butun soni taqsimlanmagan qatorga tushadi.

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
   «Guruh AV» filtri, sahifalash, Excel eksport. Ommaviy amallar (1 donali AV'lar uchun): bo'limga ko'chirish,
   holatni o'zgartirish; hamma AV uchun: yorliq chop etish.
4. **AV kartochkasi** — 1C bloki (o'zgarmaydi; filiallar bo'yicha soni) · **taqsimot jadvali** (soni, bo'lim, МОЛ,
   holat, qiymat; jami = 1C soni ✔/✖) va amallar **soni bilan**: bo'limga ko'chirish, holat o'zgartirish, «1C bilan
   moslash» (kamaygan sonni qatorlardan ayirish) · umumiy platforma maydonlari · tur bo'yicha qo'shimcha maydonlar ·
   rasmlar (yuklash, asosiy qilish; telefon brauzerida kameradan) · amortizatsiya · tarix vaqt chizig'i · yorliq chop etish.
5. **Bo'limlar** — filial tanlash, daraxt (qo'shish, nomini o'zgartirish, nofaol qilish — ichida AV bo'lsa nofaol
   qilib bo'lmaydi), bo'lim AV ro'yxati.
6. **МОЛ nazorati** — xodimlar ro'yxati (AV soni, qiymati), xodim sahifasi, «Ketgan xodimlarda qolgan AV»,
   **topshirish-qabul aktlari**: yangi akt (topshiruvchi → qabul qiluvchi; topshiruvchining taqsimot qatorlaridan:
   hammasi yoki tanlab, guruh AV'da soni bilan) → qoralama →
   tasdiqlash (МОЛ o'zgaradi) → chop etish / PDF (kompaniya, sana, raqam, AV jadvali, imzo joylari).
   Tasdiqlangan akt o'zgartirilmaydi; xato bo'lsa — teskari akt tuziladi.
7. **Tozalash ro'yxatlari** — §5.4'dagi 1C bayroqlari, Excel eksport.
8. **QR-yorliqlar** — AV ro'yxatidan / bo'lim bo'yicha / «chop etilmagan» / «almashtirish kerak» filtri bo'yicha.
   Chop etishda o'lcham faol `YorliqOlchami`lardan tanlanadi (standart oldindan tanlangan). Har yorliq — PDF'ning
   bitta sahifasi, sahifa aynan tanlangan o'lchamda; matn uzunligi yorliq eniga moslanadi. Tarkibi: QR, inv. raqam (katta), filial nomi (`filial_rekvizit` —
   QR kaliti bilan bir xil), AV nomi (qisqa, 2 qator). **QR matni:** `DS|<filial kodi>|<inv raqam>`. Guruh AV'ning
   barcha donalariga bir xil yorliq; nusxalar soni standart = AV soni (o'zgartirish mumkin). Chop etilganda
   `yorliq_kaliti`, `yorliq_sana` yoziladi.
9. **Hisobotlar** — AV filial / bo'lim / tur kesimida (soni, boshlang'ich, qoldiq qiymat); МОЛ bo'yicha qaydnoma;
   xizmat muddati tugagan va 6 oyda tugaydiganlar. Excel va chop etish.
10. **Sozlamalar (administrator)** — foydalanuvchilar, rollar va filiallar; AV turlari (xizmat muddati, qo'shimcha
    maydonlar); yorliq o'lchamlari (qo'shish, o'zgartirish, standartni tanlash); kompaniya nomi; 1C ulanishi holati va «Hozir sinxronlash»; sinxron jurnali; harakatlar jurnali.

## 8. Xatolarga chidamlilik va tekshiruvlar

- MolAkt tasdiqlash — bitta tranzaksiya: qabul qiluvchi faol va ishdan bo'shatilmagan; har akt qatori uchun
  topshiruvchida shu joyda kamida shuncha dona bor (topshiruvchi bo'sh bo'lsa — МОЛ'siz qatordan); AV arxivda emas.
  Bitta shart buzilsa — hech narsa o'zgarmaydi.
- Taqsimot amallari (ko'chirish, holat, akt, 1C bilan moslash) — tranzaksiyada, qator `select_for_update` bilan;
  soni 1..qator soni oralig'ida; amaldan keyin Σ invariant tekshiriladi.
- Bo'lim faqat taqsimot qatorining filialidagi bo'limlardan tanlanadi.
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
  - sinxron mantiqi — TestClaude'dan yozib olingan haqiqiy JSON namunalari bilan: yangi AV, soni ko'payishi,
    kamayishi (taqsimlanmagandan yetadi / yetmaydi), qisman filiallararo o'tkazish, filialda 0, arxiv, xodim ketishi,
    kalit o'zgarishi, 1C'da yo'qolish, xato javobda rollback;
  - taqsimot amallari: bo'lish, birlashish, invariant, chegaraviy soni;
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
