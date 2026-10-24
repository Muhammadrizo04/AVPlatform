# 1C farazlari — TestClaude'da tekshiruv natijalari

Manba: spec §13 (`docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md`), reja Task 1 Step 5.
Tekshiruvchi: foydalanuvchi (1C) + Claude (javoblar tahlili) · Sana: 2026-10-18 · Baza: TestClaude · Kengaytma: AVSinxron 1.0.0

Natija ustunida ✔ yoki ✖. **Biror faraz ✖ bo'lsa — to'xtang**: keyingi tasklarga o'tilmaydi,
spec foydalanuvchi bilan qayta kelishiladi.

| # | Faraz | Tekshiruv usuli | Natija | Izoh |
|---|---|---|---|---|
| 1 | `ОсновныеСредства.Филиал` rekviziti filiallararo o'tkazishda o'zgarmaydi (faqat УчетОС o'lchami o'zgaradi) | Sinov ПеремещениеОС urinildi; TestClaude `/vositalar` va `/harakatlar` haqiqiy javoblari tahlil qilindi | ✔ (o'zgartirilgan shaklda) | Bu konfiguratsiyada filiallararo ПеремещениеОС **ruxsat etilmaydi** (1C xabari: balanslar filial bo'yicha alohida, jo'natuvchi va qabul qiluvchi filial bir xil bo'lishi kerak). Filiallararo o'tkazish = **РеализацияОС** (A, `chiqim`) + **ПоступлениеОС** (B, `kirim`), **bir xil AV yozuvi (ref)**: 117 ta holat (91 tasi bir kunda). O'tkazilgan va hozir boshqa filialda turgan 60 ta AV'ning rekviziti eski filialda qolgan → rekvizit o'zgarmaydi. Platforma buni o'zgarishsiz qo'llab-quvvatlaydi: A'da qoldiq 0 → `1c_nolga_tushdi`, B'da taqsimlanmagan qator. Butun bazada ПеремещениеОС — 1 ta, filial ichida, soni 0. |
| 2 | Barcha ОС hujjatlari УчетОС'ga harakat yozadi | `/harakatlar` (oxirgi 10 yil, 47 380 qator) hujjat turlari bo'yicha sanaldi | ✔ | ПоступлениеОС (842 hujjat), ВводНачальныхОстатковОС (23), РеализацияОС (216), СписаниеОС (13), ПереоценкаОС (419; soni 0, summa o'zgaradi — 44 355 qator), РасходыНаОС (127; asosan soni 0), ОприходованиеОС (6), ПеремещениеОС (1). |
| 3 | «Ходимлар» spravochnigi to'ldirilgan va МОЛ sifatida yaroqli | `/spravochniklar` → `xodimlar` | ✔ | 483 xodim; hammasida `ism`, 482 tasida `filial`; 183 tasi ishdan bo'shatilgan. |
| 4 | Yangi kengaytma HTTP-servisi publikatsiyada ishlaydi (404 muammosi) | `1c\TestClaude_ornatish.ps1 -FaqatEndpointlar` | ✔ | 4 ta endpoint HTTP 200, BOM yo'q. MobilOstatka'ga ko'chirish shart bo'lmadi. |
| 5 | Kengaytma xavfsiz rejimda so'rovlarni bajara oladi | AVSinxron uchun «Безопасный режим» yoqilgan holda endpointlar chaqirildi | ✔ | Foydalanuvchi tasdiqladi: «Безопасный режим» yoqilgan, 4 ta endpoint 200. |

## Ma'lumot sifati (TestClaude, 2026-10-18)

- 22 filial, 1 tashkilot, 41 AV turi (ГруппаОС), 2383 AV yozuvi, 2130 qoldiq qatori (jami ≈4170 dona).
- 30 AV bir nechta filialda; 132 AV'ning qoldiq filiali rekvizitdan farq qiladi.
- Tozalash kerak: filial rekviziti bo'sh — 23, inv. raqam bo'sh — 3, turi bo'sh — 321.
- Qoldiqda soni 0, summa ≠ 0 — 69 qator (Review Focus 1 holati haqiqatda bor).

## Spetsifikatsiyaga ta'siri

- Spec §6.3 «boshqa filialga o'tkazish» — amalda Реализация + Поступление juftligi; mexanizm o'zgarmaydi.
- QR-yorliqdagi filial (`filial_rekvizit`) o'tkazilgan AV'da eski filial bo'lib qoladi (kalit barqaror, yorliq qayta
  chop etilmaydi). Yorliqda joriy filial kerak bo'lsa — alohida kelishiladi.
- To'liq sinxronda `/harakatlar` javobi ≈16 MB (asosan ПереоценкаОС qatorlari); 60 s timeout ichida qaytdi.

## Namunalar

`onec/tests/namunalar/{spravochniklar,vositalar,harakatlar}.json` — haqiqiy javoblardan qisqartirilgan va
anonimlashtirilgan (23 AV: guruh, bir donali, ko'p filialli, inv bo'sh, turi bo'sh, rekvizit bo'sh, soni 0 summa ≠ 0,
filiallararo o'tkazilgan, arxiv; 77 harakat; 8 xodim). Barcha UUID'lar yangi, nomlar/ismlar almashtirilgan,
telefonlar o'chirilgan, summalar o'zgarmas koeffitsient bilan o'zgartirilgan. Xom javoblar (`*.raw.json`) git'ga kirmaydi.
