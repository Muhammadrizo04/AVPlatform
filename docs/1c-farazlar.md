# 1C farazlari — TestClaude'da tekshiruv natijalari

Manba: spec §13 (`docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md`), reja Task 1 Step 5.
Tekshiruvchi: ______ · Sana: ______ · Baza: TestClaude · Kengaytma: AVSinxron 1.0.0

Natija ustuniga ✔ yoki ✖ yozing. **Biror faraz ✖ bo'lsa — to'xtang**: keyingi tasklarga o'tilmaydi,
spec foydalanuvchi bilan qayta kelishiladi.

| # | Faraz | Tekshiruv usuli | Natija | Izoh |
|---|---|---|---|---|
| 1 | `ОсновныеСредства.Филиал` rekviziti ПеремещениеОС'da o'zgarmaydi (faqat УчетОС o'lchami o'zgaradi) | TestClaude'da sinov `ПеремещениеОС`: filial A → B, bitta AV, qisman soni bilan. Oldin va keyin `/vositalar`: shu AV'ning `filial` (rekvizit) o'zgarmagan; `qoldiqlar`da A kamaygan, B paydo bo'lgan. `/harakatlar`da shu hujjat bo'yicha ikki qator: `chiqim` A, `kirim` B | kutilmoqda | |
| 2 | Barcha ОС hujjatlari УчетОС'ga harakat yozadi | ПоступлениеОС, СписаниеОС, ВводНачальныхОстатковОС, ПереоценкаОС hujjatlarining har biri bo'yicha `/harakatlar` qator beradi (`hujjat_turi` shu nom bilan) | kutilmoqda | |
| 3 | «Ходимлар» spravochnigi to'ldirilgan va МОЛ sifatida yaroqli | `/spravochniklar` → `xodimlar` ro'yxati bo'sh emas, `ism` va `filial` to'ldirilgan | kutilmoqda | |
| 4 | Yangi kengaytma HTTP-servisi publikatsiyada ishlaydi (404 muammosi) | `curl -u "AVSinxron:<parol>" http://<host>/TestClaude/hs/av/versiya` → 200 va `"versiya":"1.0.0"` (yoki `1c\TestClaude_ornatish.ps1` natijasi) | kutilmoqda | 404 bo'lsa — qaysi yechim qo'llangani (`1c/README.md`, «404 bo'lsa») |
| 5 | Kengaytma xavfsiz rejimda so'rovlarni bajara oladi | Konfigurator → Конфигурация → Расширения конфигурации: AVSinxron uchun «Безопасный режим» belgilangan; shu holatda 4 ta endpoint 200 qaytaradi | kutilmoqda | |
