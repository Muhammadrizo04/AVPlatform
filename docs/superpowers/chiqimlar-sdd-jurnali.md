# SDD ledger — plan: docs/superpowers/plans/2026-10-19-1c-chiqim-hujjatlari.md

Spec: docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md §6.5
Branch: feat/chiqimlar (base 013e214, main'dan). Push — foydalanuvchi o'zi; controller faqat lokal commit.
Muhit: Windows, venv/Scripts/python.exe, PostgreSQL 18 lokal (av/av). Test: venv/Scripts/python.exe -m pytest -q (~2 daq).

## Pre-flight scan
| Juftlik / task | Ishlab chiqaradi ↔ iste'mol | Topilgan |
|---|---|---|
| T1 → T2/T3/T4/T5 | ChiqimHujjat, Sabab, Sozlama.chiqim_boshlanishi | mos |
| T1 o'zi | data-migratsiya «hozir» ↔ T2 sinxron testi namunadagi eski sanalar | T2 testi chiqim_boshlanishi'ni o'zi o'rnatadi (rejada) |
| T2 → T3 | T2 sinxronda yozuv yaratadi, T3 gacha moslash K'ni bilmaydi | oraliq holat faqat branch ichida; T3 tugaguncha ishchi bazaga chiqmaydi |
| T2 o'zi | 45 kunlik oyna ↔ bekor qilish | faqat [dan, gacha] ichida bekor (Review Focus 1) |
| T3 → T4 | farq() K bilan ↔ amallar.kamaytir | kamaytir ortiqchasi K'ni hisobga oladi — to'g'ri |
| T3 ↔ vositalar.filtrlar | yangi bayroq modeli ChiqimHujjat ↔ av_filtrla(bayroq=) Taqsimot/AV/list kutadi | MUAMMO → Ruling 1 |
| T4 ↔ moslashtir | tasdiqla A qatorlari, keyin kochir B qatorlari (alohida qulf) ↔ moslashtir butun jadval pk tartibida | deadlock xavfi → Ruling 2 |
| T4 ↔ amallar | kochir ichida _tekshir_arxiv (B) | B'da Поступление bo'lsa qoldiq > 0 — OK; B'da qator yo'q bo'lsa kochir chaqirilmaydi |
| T5 ↔ panel bosh | bayroq kartochkasi havolasi vositalar:royxat?bayroq= | chiqim_kutilmoqda uchun chiqimlar:royxat (rejada) |
| T5 o'zi | parametr o'qish hisoblar.parametrlar.son | mavjud (hisoblar/parametrlar.py:9) |

Ruling 1: av_filtrla `bayroq=chiqim_kutilmoqda` uchun ChiqimHujjat natijasini av_id larga aylantiradi (T3 da) — AV ro'yxati ham shu bayroq bilan ishlaydi — narxi yo'q.
Ruling 2: tasdiqla A va (otkazish bo'lsa) B juftlarining barcha Taqsimot qatorlarini BITTA select_for_update so'rovida pk tartibida qulflaydi, keyin kochir chaqiradi (kochir ichidagi qayta qulf o'sha tranzaksiyada — bloklanmaydi) — moslashtir bilan bir tartib — narxi yo'q.
Ruling 3: TaqsimotHarakat.sabab max_length=20: "hisobdan_chiqarildi" = 19 belgi — sig'adi.

Task 1: dispatched (base 013e214, sonnet)
Task 1: implementer DONE (commit 9e5c251; 428 passed)
Task 1: minor (deferred): apps.py default_auto_field yo'q (settings'da bor); taxmin_tur default yo'q — T2 doim to'ldirsin
Task 1: complete (commits 013e214..9e5c251, review clean)
Task 2: dispatched (base 9e5c251, sonnet)
Task 2: implementer DONE (commit ace22be; 441 passed). TDD: servis testlari kod bilan birga yozilgan.
Ruling (T2/T5): taxmin qilingan B filial saqlanmaydi; T5 forma ochilganda taxmin_qil() qayta chaqiriladi va B oldindan tanlanadi — narxi: forma ochilishida 1 qo'shimcha so'rov.
Task 2: review Needs fixes — taxmin: kirim soni>0 filtri yo'q; oyna faqat oldinga (spec ±3 kun).
Ruling (T2): spec «±3 kun» — ikki tomonlama [sana−3k, sana+3k], soni>0, boshqa filial; testlar shunga — narxi yo'q.
Task 2: minor (deferred): yangi guruh uchun 2 so'rov + bittalab create; filial ko'chishi/sana boshlanishdan oldinga/kirim soni 0/shu filial kirimi testlari yo'q (fix'da qo'shiladi qismi); quyi chegarani kesib o'tgan hujjat qisman yig'indi; filial null bo'lsa bekor.
Task 2: fix round 1/5 (2 addressed, 0 open — ikki tomonlama oyna, soni>0; commits ace22be..c0fdb5b)
Task 2: minor (deferred): taxminda eng erta kirim tanlanadi (eng yaqin emas)
Task 2: complete (commits 9e5c251..c0fdb5b, review clean)
Task 3: dispatched (base c0fdb5b, opus)
Task 3: implementer DONE (commit cfe5353; 460 passed). Concerns: bayroqlar chiqimlar.models modul darajasida import; taqsimot 0 juftda K paydo bo'lsa taqsimlanmaganga qo'shiladi; bayroq arxiv AV chiqimlarini ham sanaydi
Task 3: review Needs fixes — Important: K Taqsimot qulfidan oldin o'qiladi (tasdiqlash bilan poyga → soxta birlik).
Ruling (T3): moslashtir avval kutilmoqda ChiqimHujjat qatorlarini pk tartibida select_for_update qiladi, keyin Taqsimot (T4 bilan bir tartib: ChiqimHujjat → Taqsimot), K qulflangan qatorlardan hisoblanadi.
Ruling (T3, review minor 4 → load-bearing invariant): chiqimlarni_yangila `bekor` yozuvni 1C'da qayta topsa → `kutilmoqda` ga qaytaradi (jurnal bilan) — aks holda tasdiqlanmagan chiqim taqsimotni o'chiradi (§6.3 buziladi). Shu fix round'ga qo'shildi.
Task 3: minor (deferred): o'tkazishda tasdiqlanguncha AV A (kutilmoqda) va B (taqsimlanmagan) da ikki marta sanaladi — dizayn bo'yicha, T4 B joylash shu birlikni oladi; farq() xom qoldiq vs max(q,0); docstring uzun qator; bayroq soni arxiv AV'larni ham sanaydi — T5 havolani chiqimlar:royxat ga yo'naltirsin.
Task 3: fix round 1/5 (3 addressed, 0 open — K qulfdan keyin, bekor qaytadi, docstring; commits cfe5353..05e4265)
Task 3: minor (deferred): oyna tashqarisidagi fallback qidiruv qulfsiz; bekor-oyna-tashqarisi qaytish testi yo'q
Task 3: complete (commits c0fdb5b..05e4265, review clean)
Task 4: dispatched (base 05e4265, opus)
Task 4: implementer DONE (commit 75717da; 481 passed)
Task 4: minor (deferred): bekor chiqimga «allaqachon tasdiqlangan» xabari (alohida xabar kerak); b_bolim.faol oldindan tekshirilmaydi (ba'zan jim o'tadi); B tomon harakatlarida hujjat_izoh yo'q; testlar: B merge, nofaol b_bolim, noto'g'ri son, bekor rad; kutilgan_soni qat'iy turi — T5 Decimal bersin
Task 4: complete (commits 05e4265..75717da, review clean)
Task 5: dispatched (base 75717da, sonnet)
Task 5: implementer DONE (commit d0c4f0d; controller full suite run below)
Task 5: controller full suite 503 passed. Review Needs fixes — Important: HR/rahbar kutilayotgan chiqim sahifasida 403 (spec «faqat ko'rish»).
Ruling (T5): taqsimot huquqisiz foydalanuvchiga kutilayotgan chiqim — faqat o'qish sahifasi (forma yo'q); 403 faqat POST'da. Kutilmoqda bo'lmagan chiqimga POST → ogohlantirish xabari (jim 200 emas).
Task 5: minor (deferred): vakuum assert test_tasdiqlash_oqimi; nishon soni/filial testi; xatodan keyin kiritma saqlanishi testi; B bo'lim ro'yxati tanlangan B bo'yicha filtrlanmaydi; o'qish sahifasida ruxsatsiz B nomi; _decimal eksponentni qabul qiladi; context processor qo'shimcha so'rov
Task 5: fix round 1/5 (3 addressed, 0 open — HR faqat ko'rish, eskirgan POST ogohlantirish, vakuum assert; commits d0c4f0d..f0695c4)
Task 5: minor (deferred): kutilmoqda bo'lmagan chiqimga hr/rahbar POST → 200 ogohlantirish (403 emas), yozuv yo'q
Task 5: complete (commits 75717da..f0695c4, review clean)
FINAL review dispatched (013e214..f0695c4, opus)
FINAL REVIEW (013e214..f0695c4): With fixes. Important: (1) B filial ruxsat etilganlar bilan cheklangan — spec faqat B'ga joylash uchun talab qiladi; (2) taxmin faqat yaratishda — kech kelgan B kirimi hisobga olinmaydi.
Ruling (final): bitta fix dispatch — Important 1-2 + farq() max(q,0) + B joylash 0/qisman bo'lsa ogohlantirish + ko'rinmas AV havolasi matn + kutilgan_soni bo'sh → forma xatosi. Plan qatori (B ruxsat) spec ustunligi bilan bekor qilindi.
Parked (final): bekor/tiklanish 45 kunlik oyna tashqarisiga ko'chgan sana — o'z-o'zini tuzatadi, hujjatlashtiriladi — Ruling: kutadi.
FINAL fix: commit 38c8054 (515 passed)
FINAL fix re-review: 6 addressed, 0 open. Parked: taxmin qayta hisoblash har sinxronda kutilayotgan qator boshiga 1 so'rov; uzun OR so'rov to'liq sinxronda; ogohlantirish matni qisman joylashda aniq emas — Ruling: kutadi.
