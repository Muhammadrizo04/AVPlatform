# Asosiy vositalar platformasi — 2-bosqich: Reviziya (dizayn)

Sana: 2026-10-23. Asos: 1-bosqich spetsifikatsiyasi (`2026-10-17-av-platforma-1-bosqich-design.md`), §1 «Bosqichlar» jadvali.

## 1. Maqsad va muvaffaqiyat mezoni

Revizor oddiy Android telefonida (brauzer orqali) filial yoki bo'limdagi AV'larni xonama-xona belgilaydi; hisobchi
«topildi / kam-topilmadi / boshqa joyda / ortiqcha / holati boshqa» solishtirish vedomostini ko'radi va farqlarni
tanlab taqsimotga qo'llaydi; komissiya imzolaydigan **reviziya dalolatnomasi** (PDF) chiqadi.

### Kelishilgan qarorlar (foydalanuvchi bilan, 2026-10-23)

1. **Qurilma:** oddiy Android telefon, brauzerdagi mobil sahifa (APK emas). Alohida ilova, API yoki PWA yo'q —
   shu Django loyihasi ichida HTMX bilan.
2. **Aloqa:** joylarda Wi-Fi/internet bor — faqat onlayn rejim (oflayn navbat yo'q).
3. **HTTPS:** telefon kamerasi brauzerda faqat HTTPS (yoki `localhost`) da ishlaydi. HTTPS rejadagi VPS + domen +
   Let's Encrypt bosqichida beriladi; ungacha lokal sinov kompyuterda `localhost` orqali. HTTP'da kamera o'rniga
   qo'lda qidiruv ishlaydi (§4.4).
4. **Qamrov:** bitta reviziya — butun filial yoki bitta bo'lim (ichki bo'limlari bilan); 1+ revizor; komissiya a'zolari
   faqat dalolatnomada (ism, lavozim).
5. **Guruh AV:** har skan +1; topilgan sonni qo'lda tuzatish mumkin.
6. **Natija:** reviziya taqsimotni o'zi o'zgartirmaydi; hisobchi farqlarni tanlab «Qo'llash» bosadi.
7. **Filial o'zgarmaydi:** boshqa filialning AV'si topilsa — faqat «ortiqcha (boshqa filial)» qaydi; filialni o'zgartirish
   1C'da (1-bosqich qoidasi: platforma 1C'ga yozmaydi, filial faqat 1C'dan).
8. **QR'siz AV:** hozir ~2 022 AV yorliqsiz — inv. raqam / nom bo'yicha qidirib belgilash majburiy imkoniyat.

## 2. Ma'lumotlar modeli (yangi `reviziya` ilovasi)

### `Reviziya`
- `raqam` (PositiveInteger, noyob; ko'rinishi `RV-000001`; berishda advisory lock `7310003`).
- `filial` (FK Filial), `bolim` (FK Bolim, bo'sh = butun filial).
- `holat`: `ochiq` → `yakunlangan` → `qollangan`; `ochiq` → `bekor`.
- `revizorlar` (M2M User), `komissiya` (JSON ro'yxat: `[{"ism": ..., "lavozim": ...}]`), `izoh`.
- `ochdi`, `ochilgan_vaqt`, `yakunladi`, `yakunlangan_vaqt`, `qolladi`, `qollangan_vaqt`, `bekor_qildi`, `bekor_vaqti`.

### `ReviziyaKutilgan` (ochilgan paytdagi surat)
- `reviziya`, `av`, `bolim` (bo'sh = bo'limsiz), `mol`, `holat`, `soni`, `taqsimot_id` (qaysi qatordan olingani).
- Reviziya ochilganda qamrovdagi (filial; bo'lim tanlangan bo'lsa — u va ichki bo'limlari) **faol AV**larning taqsimot
  qatorlaridan bir tranzaksiyada nusxa olinadi. Reviziya davomida taqsimot o'zgarsa ham solishtirish asosi siljimaydi.

### `ReviziyaQayd` (revizorning belgilagani)
- `reviziya`, `bolim` (qaysi xonada topildi; bo'sh = bo'limsiz/umumiy joy), `av` (bo'sh = noma'lum QR),
  `qr_matn` (noma'lum yoki boshqa filialniki bo'lsa — xom matn), `soni_topilgan`, `holat`, `izoh`, `rasm` (ixtiyoriy),
  `usul` (`qr` | `qidiruv`), `kim`, `qachon`, `yangilangan`.
- Noyoblik: (`reviziya`, `bolim`, `av`, `holat`) — takror skan yangi yozuv yaratmaydi, mavjudining soni +1 bo'ladi.
  Noma'lum QR uchun kalit `qr_matn`.
- Ikki revizor bir xonada parallel ishlaganda son yo'qolmasligi uchun yangilash `select_for_update` bilan.

### `TaqsimotHarakat.Sabab` — yangi qiymat
- `REVIZIYA = "reviziya", "Reviziya"`; `hujjat_izoh` = `RV-000001`. AV tarixida ko'rinadi.

## 3. Hayotiy sikl va huquqlar

### 3.1. Holatlar
- **Ochish** (`reviziya_boshqarish`): filial, ixtiyoriy bo'lim, revizorlar (rol `revizor` yoki `reviziya_otkazish`
  huquqi bor foydalanuvchilar), komissiya. Surat olinadi (§2).
  Bir filialda qamrovi kesishgan (filial butunlay ↔ istalgan bo'lim; bo'lim ↔ uning ota/ichki bo'limlari) ikkinchi
  **ochiq** reviziya ochilmaydi.
- **Skanerlash** — faqat `ochiq` holatda, faqat biriktirilgan revizorlar (va `reviziya_boshqarish` huquqi borlar).
- **Yakunlash** (`reviziya_boshqarish`): qaydlar yopiladi; vedomost qotadi.
- **Qo'llash** — faqat `yakunlangan` holatda (§5.2). «Yopish» tugmasi yoki hamma kerakli qator qo'llangach — `qollangan`.
- **Bekor qilish** — faqat `ochiq` holatda; qaydlar saqlanadi, taqsimotga ta'sir yo'q.

### 3.2. Huquqlar (`hisoblar/huquqlar.py`)
- `reviziya_boshqarish`: admin, hisobchi.
- `reviziya_otkazish`: revizor, admin, hisobchi — faqat o'ziga biriktirilgan (admin/hisobchi — istalgan) ochiq reviziya.
- `reviziya_korish`: admin, hisobchi, rahbar, hr — ro'yxat, vedomost, dalolatnoma (pul — faqat `pul_korish` bilan).
- Filial cheklovi: hamma ro'yxat va bo'laklar `filial_bilan_chekla` orqali.
- **Revizor roli:** kirganda «Mening reviziyalarim» (`/reviziya/m/`) ochiladi; asosiy panel sahifalari 403. `korish`
  huquqi revizorga berilmaydi (1-bosqich qoidasi saqlanadi).

## 4. Revizorning mobil sahifalari (`/reviziya/m/...`)

Telefon uchun alohida yengil shablon (`reviziya/mobil_base.html`): yon menyusiz, katta tugmalar (≥44px), panel
tokenlari (DESIGN.md: indigo urg'u, holat pill'lari).

### 4.1. Oqim
1. **Reviziyalarim** — biriktirilgan ochiq reviziyalar: raqam, filial/bo'lim, progress (belgilangan / kutilgan dona).
2. **Xona tanlash** — qamrovdagi bo'limlar daraxti + «Bo'limsiz»; har birida progress. Tanlangan xona sahifa tepasida
   doim ko'rinadi (sessiyada saqlanadi).
3. **Skan ekrani** — «Kamera» tugmasi (§4.4), qidiruv maydoni (inv. raqam / nom), oxirgi belgilanganlar ro'yxati.
4. **AV kartochkasi (bottom-sheet)** — nom, inv., guruh bo'lsa «guruh × N»; **shu xonada kutilgan** soni;
   **topilgan** soni (har skan +1; − / + tugmalari va qo'lda kiritish); holat (standart — kutilgan qatordagi holat,
   bo'lmasa «Ishlatilmoqda»); ixtiyoriy rasm va izoh; «Saqlash».
5. **Qolganlar** — «Bu xonada kutilgan, lekin hali belgilanmagan» ro'yxati (qidiruv bilan); undan bosib qo'lda
   belgilash mumkin (usul `qidiruv`).

### 4.2. QR o'qish
- QR matni `DS|<filial kodi>|<inv>` (1-bosqich §QR). Filial kodi reviziya filialiga teng bo'lsa — AV
  `filial_rekvizit` + `inv_raqam` bo'yicha topiladi. Topilmasa yoki filial boshqa bo'lsa — «noma'lum» /
  «boshqa filial» qaydi (`qr_matn` bilan).
- Arxiv AV (qoldiq 0) skanerlansa — qayd qilinadi, vedomostda «ortiqcha (arxivda)».

### 4.3. Takror va parallel ish
- Bir xonada bir AV qayta skanerlansa — mavjud qayd +1 (§2). Ikki revizorning qaydlari bir yozuvga qo'shiladi.
- Qaydni tahrirlash/o'chirish — faqat o'z qaydini va faqat `ochiq` holatda.

### 4.4. Kamera
- Brauzerning `BarcodeDetector` API'si (`formats: ['qr_code']`) + `getUserMedia` orqa kamera.
- API yo'q yoki sahifa xavfsiz kontekstda emas (`window.isSecureContext === false`) — kamera tugmasi o'rniga izoh:
  «Kamera faqat HTTPS'da ishlaydi — inv. raqamni kiriting» va qidiruv maydoni. Tashqi kutubxona yuklanmaydi (oflayn
  ichki tarmoq qoidasi).

## 5. Solishtirish (vedomost) va qo'llash

### 5.1. Hisoblash (`reviziya/solishtir.py`, sof funksiya)
Kalit — (`av`, `bolim`, `holat`). Kutilgan = `ReviziyaKutilgan` yig'indisi; topilgan = `ReviziyaQayd` yig'indisi.
Avval har AV bo'yicha holat farqi, keyin joy farqi:

1. **Topildi** — kalit bo'yicha topilgan = kutilgan.
2. **Holati boshqa** — (av, bolim) bo'yicha soni teng, lekin holatlar bo'yicha taqsimlanishi boshqacha.
3. **Boshqa joyda** — AV bir xonada kam, boshqa xonada (shu filial) ortiqcha: ortiqchaning `min(kam, ortiqcha)`
   qismi «A xonadan B xonaga» juftligi bo'ladi.
4. **Kam / topilmadi** — juftlashtirilgandan keyin qolgan kamomad (0 topilgan — «topilmadi»).
5. **Ortiqcha** — juftlashtirilgandan keyin qolgan ortiqcha; shuningdek noma'lum QR, boshqa filial, arxiv AV.

Vedomost sahifasi: beshta guruh bo'yicha rangli ko'rsatkichlar, filtr (guruh, bo'lim, qidiruv), jadval. Ochiq reviziyada
joriy holat bo'yicha ko'rinadi (jonli).

### 5.2. Qo'llash (`reviziya_boshqarish`, faqat `yakunlangan`)
Hisobchi qatorlarni belgilaydi → «Qo'llash». Har qator alohida tranzaksiyada, mavjud amallar orqali
(`vositalar.amallar`, `sabab=REVIZIYA`, `hujjat_izoh=RV-…`):

| Guruh | Amal |
|---|---|
| Boshqa joyda | `kochir` — kutilgan taqsimot qatoridan topilgan xonaga, juftlik soni bilan |
| Holati boshqa | `holat_ozgartir` |
| Topilmadi / kam | `holat_ozgartir` → `topilmadi` (kamomad soni bilan) |
| Ortiqcha | faqat qayd (taqsimot soni 1C'dan keladi; 1C'da kirim/o'tkazish kerak) |

- Taqsimot reviziyadan keyin o'zgargan bo'lsa (masalan, МОЛ akti tasdiqlangan, 1C sinxron kamaytirgan) va kerakli qator
  yoki miqdor yo'q bo'lsa — o'sha qator xato bilan o'tkazib yuboriladi («Taqsimot o'zgargan: …»), qolganlari qo'llanadi.
- Qo'llangan qatorlar qayd qilinadi (`ReviziyaQollash`: qator kaliti, amal, soni, kim, qachon, natija/xato) — qayta
  qo'llash bo'lmaydi.

## 6. Hujjatlar

- **Vedomost:** Excel (`hisobotlar.excel.jadval_xlsx`) va chop etish ko'rinishi.
- **Reviziya dalolatnomasi** (PDF, WeasyPrint, `mol/pdf.py` uslubida): raqam, sana, filial/bo'lim, kompaniya nomi,
  komissiya (ism, lavozim, imzo joyi), revizorlar, beshta guruh bo'yicha jami (soni), farqlar ro'yxati.
  Summa ustunlari — faqat `pul_korish` huquqi bilan (1-bosqich qoidasi).

## 7. Panel tomoni

- Menyuda «Reviziyalar» bandi (yangi bo'lim rangi bilan) — ro'yxat (holat filtri), «Yangi reviziya», reviziya sahifasi:
  sarlavha, progress, revizorlar, vedomost, «Yakunlash», «Qo'llash», «Bekor qilish», hujjatlar.
- AV kartochkasi tarixida reviziya qaydlari («RV-000001: topildi, Kamera xona, 1 dona») va qo'llash harakatlari.

## 8. Xatolar

- Yopiq reviziyaga yoki biriktirilmagan revizordan qayd — 403 va tushunarli xabar (HTMX bo'lakda).
- Noto'g'ri soni (manfiy, juda katta, kasr — guruh bo'lmagan AV'da kasr ham ruxsat, chunki 1C soni kasr bo'lishi
  mumkin) — 400 va xabar.
- Rasm — 1-bosqich `rasmlar.rasm_saqla` cheklovlari (tur, hajm).
- Parallel qo'llash — reviziya qatori `select_for_update`; ikkinchi urinish «allaqachon qo'llangan».

## 9. Testlar

- Model/servis: surat olish (qamrov: filial / bo'lim + ichki bo'limlar), qamrov kesishmasi, takror skan (+1), noma'lum
  va boshqa filial QR, arxiv AV.
- `solishtir`: beshta guruh, juftlashtirish (boshqa joyda), holat farqi, guruh AV.
- Qo'llash: har guruh, taqsimot o'zgargan holat, qayta qo'llash taqiqi, AV tarixida yozuv.
- Huquqlar: revizor faqat biriktirilgan ochiq reviziya; revizor panelga kira olmaydi; filial cheklovi; HR/rahbar faqat
  ko'radi.
- Hujjatlar: PDF/Excel'da pul `pul_korish`siz yo'q.
- Mobil ko'rinishlar: oqim (xona → qidiruv → saqlash), HTTP'da kamera o'rniga izoh.
- Kamera — qo'lda (lokal `localhost`, keyin VPS HTTPS).

## 10. Ko'lamdan tashqari

Oflayn rejim, native APK, shtrix-kod skaneri qurilmalari, 1C'ga natija yozish, filialni platformada o'zgartirish,
QR-yorliqlarni reviziya davomida chop etish (1-bosqich «Yorliq chop etish» sahifasi ishlatiladi).
