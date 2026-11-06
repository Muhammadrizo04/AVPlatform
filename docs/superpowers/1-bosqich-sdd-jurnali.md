# SDD ledger — plan: docs/superpowers/plans/2026-10-17-av-platforma-1-bosqich.md

Spec: docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md
Note: oldingi ledger konteynerda qolgan (yo'qolgan). Holat git log'dan tiklandi (2026-10-17, Windows lokal).

## Tiklangan holat
Task 1: files complete (commits be00cb0, d364f32, a32fde7, review clean). Windows qismi OCHIQ: endpointlar (-FaqatEndpointlar), sinov ПеремещениеОС, docs/1c-farazlar.md, namunalar (Step 5–7) — foydalanuvchi bajaradi.
Task 2: complete (commits a456b92..21405ce, review clean; 14 test Windows'da PASS, 42b31da docs).

## Muhit
Windows 11, venv Python 3.12.15, PostgreSQL 18.3 (rol av/av, CREATEDB). Test: venv\Scripts\python.exe -m pytest -q
GitHub push — foydalanuvchi o'zi qiladi; controller faqat lokal commit qiladi.

## Pre-flight scan (Task 3–17)
| Juftlik / task | Ishlab chiqaradi ↔ iste'mol qiladi | Topilgan |
|---|---|---|
| T1 → T3 | namunalar/*.json ↔ test_client | namunalar hali yo'q (T1 Step 6 ochiq) |
| T2 → T3 | onec/models.py (OneCModel, Filial) ↔ T3 kengaytiradi | mos; OneCModel allaqachon bor |
| T3 o'zi | spec `1c_da_yoq` ↔ plan `onec_da_yoq` | Python nomi raqamdan boshlanmaydi → plan nomi |
| T3 o'zi | client.harakatlar → list ↔ kontrakt `{"harakatlar":[...]}` | mijoz ochib qaytaradi; mos |
| T3 → T5 | OneCClient, OneCXato ↔ sinxronla | mos |
| T4 → T5/T6 | vositalar modellari ↔ moslash | T5 moslash stub yaratadi; T6 to'ldiradi; mos |
| T4 o'zi | UniqueConstraint nulls_distinct=False | PG15+ kerak; lokal 18, prod 16 — mos |
| T3 ↔ T8 | onec/models.py AV ↔ T8 manager/kalit qo'shadi | ikkalasi bir faylni o'zgartiradi, ketma-ket — mos |
| T7 → T9 | mol_ozgartir, AmalXato ↔ akt_tasdiqla | mos |
| T9/T14 o'zi | WeasyPrint | Windows'da GTK/Pango kerak — T9 da hal qilinadi |
| T14 o'zi | pyzbar/zxing-cpp QR dekod | Windows: zxing-cpp wheel afzal |
| T17 o'zi | systemd-analyze verify | Windows'da yo'q — T17 da hal qilinadi |
| T5–T17 | spec PostgreSQL 16 ↔ lokal 18 | 18'ga xos imkoniyat ishlatilmaydi |

Ruling: T3 uchun namunalar hali yo'q → implementer kontraktga (va 1c/AVSinxron_HTTP_modul.bsl JSON formatiga) mos SINTETIK `onec/tests/namunalar/{spravochniklar,vositalar,harakatlar}.json` yaratadi; testlar sonlarni fayldan o'qiydi (qattiq kodlanmaydi) — T1 Step 6 haqiqiy namunalar bilan almashtirganda testlar o'zgarmay ishlaydi — xato bo'lsa: T1 Step 6 da test yoki namuna moslashtiriladi.
Ruling: spec `1c_da_yoq` → kodda `onec_da_yoq` — Python identifikatori raqamdan boshlana olmaydi — narxi yo'q.
Ruling: lokal PostgreSQL 18 bilan test, 16'da yo'q imkoniyatlar ishlatilmaydi — VM'da 16 bilan qayta pytest — farq chiqsa kichik tuzatish.

Task 3: dispatched (base 42b31da, sonnet)
Task 3: implementer DONE_WITH_CONCERNS (commit 4310723; 32 passed). Concerns noted for T5: AVQoldiq unique yo'q; Harakat1C.sana naive datetime; requests requirements.txt ga qo'shildi.
Task 3: review dispatched (42b31da..4310723, sonnet)
Task 3: minor (deferred): client.py:84 — 1C {"xato":...} matni OneCXato'ga qo'shilmaydi (jurnalda faqat "HTTP 500")
Task 3: minor (deferred): client.py:64 — harakatlar list ekani tekshirilmaydi
Task 3: minor (deferred): client.py:62 — tz-aware dan/gacha o'zgartirilmaydi; T5 naive 1C-local vaqt bersin
Task 3: minor (deferred): AVQoldiq.filial NOT NULL, BSL null berishi mumkin — T5 bunday qatorni o'tkazib yuborsin/jurnalga yozsin
Task 3: minor (deferred): Harakat1C.sana/hujjat_ref NOT NULL, BSL null berishi mumkin — T5 xabardor bo'lsin
Task 3: minor (deferred): 400/401 status testi yo'q
Task 3: complete (commits 42b31da..4310723, review clean)
Task 4: dispatched (base 4310723, sonnet)
Task 4: implementer DONE (commit 39072be; 48 passed)
Task 4: minor (deferred): AVKartochka/TaqsimotHarakat/Rasm/AVTuriSozlama/Bolim sikl himoyasi uchun test yo'q
Task 4: minor (deferred): YorliqOlchami.standarti() standart yo'q bo'lsa DoesNotExist — T14 hal qilsin
Task 4: minor (deferred): Sozlama ikkinchi qatorni (pk≠1) to'smaydi
Task 4: minor (deferred): Taqsimot/TaqsimotHarakat/Rasm __str__ yo'q
Task 4: minor (deferred): bolim.filial == taqsimot.filial va ota bir filialda — model darajasida tekshirilmaydi (T7/T12 servisda)
Task 4: minor (deferred): Bolim.toliq_nomi N+1
Task 4: minor (deferred): yoz() saqlanmagan obyekt uchun obyekt_id "None"
Task 4: complete (commits 4310723..39072be, review clean)
Ruling (T5): 1C sanalari naive Toshkent vaqti → Harakat1C.sana uchun make_aware(TIME_ZONE); client'ga dan/gacha naive local (localtime().replace(tzinfo=None)) — T3 minor #3 shu bilan yopiladi — xato bo'lsa harakatlar oynasi soatlar bilan siljiydi.
Ruling (T5): qoldiq qatori filial=null yoki noma'lum av, harakat sana/hujjat_ref=null yoki noma'lum av → qator o'tkazib yuboriladi va SinxronJurnal.ozgarishlar ga soni yoziladi (sinxron yiqilmaydi, spec Review Focus 2) — xato bo'lsa bunday qoldiq Σ ga kirmaydi va «mos emas» chiqadi (ko'rinadigan).
Ruling (T5): AV/xodim noma'lum filial/tur/tashkilot ref'iga ishora qilsa → FK null — narxi: rekvizit bo'sh deb bayroqlanadi.
Task 5: dispatched (base 39072be, opus)
Task 5: implementer DONE_WITH_CONCERNS (commit 231f8d5; 63 passed). Concerns: kelajak sanali harakatlar o'chiriladi lekin qayta olinmaydi; band ketma-ket xatoga ta'sir qilmaydi; sinx_vaqti faqat o'zgarganda; buzilgan asosiy ma'lumot → xato
Task 5: review Approved (spec ✅), minors only.
Ruling (T5 minor 1, plan-mandated `sana >= hozir−45` o'chirish): harakatlar `gacha` = uzoq kelajak (3999-12-31 23:59:59) — oyna va to'liq sinxronda; o'chirish oralig'i = olish oralig'i; olingan, lekin [dan, gacha] dan tashqaridagi qatorlar tashlanadi va sanaladi — spec §6.2 "shu davrdagi Harakat1C almashtiriladi" ma'nosiga mos, AVQoldiq (Остатки(), davrsiz) bilan kelishadi, T6 hujjat_izoh to'g'ri bo'ladi — xato bo'lsa: 1C kelajak sanali so'rovni rad etsa xato jurnali chiqadi (ko'rinadi).
Ruling (T5 minor 2): vid null/noma'lum → qator o'tkazib yuboriladi, harakat_otkazildi ga sanaladi — ruling 2 bilan izchil — narxi yo'q.
Task 5: minor (deferred): _maxfiysiz login'ni oddiy substring sifatida almashtiradi (qisqa login matnni buzadi)
Task 5: minor (deferred): xato/band qatori real autocommit'da saqlanishi transaction=True testi bilan isbotlanmagan; tashqi atomic() ichida chaqirish xavfi
Task 5: minor (deferred): ketma_ket_xatolar band'ni hisobga olmaydi; sinx_vaqti = oxirgi yaratilgan/o'zgargan (qabul qilinadi)
Task 5: fix round 1/5 (2 addressed, 0 open — harakat oralig'i, noma'lum vid; commits 231f8d5..8a056b9)
Task 5: minor (deferred): 1C tz-aware ISO sana qaytarsa TypeError → xato jurnali (regressiya emas)
Task 5: complete (commits 39072be..8a056b9, review clean)
Ruling (T6): spec §6.3 "har biri Jurnal'ga «1C sinxron» nomidan" — plan faqat TaqsimotHarakat deydi, lekin Consumes'da jurnal.yoz bor → har o'zgarish uchun TaqsimotHarakat VA jurnal.yoz(None, ...) — narxi: jurnalda ko'proq qator.
Ruling (T6): AVQoldiq bir (av, filial) uchun bir nechta qator (tashkilot bo'yicha) bo'lishi mumkin → soni yig'iladi — narxi yo'q.
Ruling (T6): AVKartochka kartochkasi yo'q har AV uchun yaratiladi (qoldig'i 0 bo'lsa ham) — kartochka 1:1 — narxi: arxiv AV'lar uchun bo'sh kartochka.
Task 6: dispatched (base 8a056b9, sonnet)
Task 6: implementer DONE (commit 594dbec; 81 passed). Concerns: ishga_tushgan_sana 45 kunlik oynadan noto'g'ri to'lishi mumkin; statistika juftlik bo'yicha
Task 6: review Needs fixes — Important: (1) ishga_tushgan_sana 45 kunlik oynadan noto'g'ri qotib qoladi; (2) select_for_update yo'q, invariant tekshiruvi yo'q (spec §8).
Ruling (T6 #1): sinxronla'da muvaffaqiyatli to'liq sinxron hali bo'lmagan bo'lsa toliq=True majburan (jurnalda toliq=True yoziladi); sana to'ldirilishi jurnal.yoz(None, kartochka, "ishga_tushgan_sana", None, sana) bilan yoziladi — tarix to'liq bo'lgandagina sana to'ldiriladi — narxi: birinchi 5-daqiqalik sinxron uzoqroq.
Ruling (T6 #2): moslashtir boshida Taqsimot qatorlari select_for_update bilan olinadi, yig'indi Python'da; oxirida mos_emas bo'lmagan har juftlik uchun Σ == qoldiq tekshiriladi, buzilsa istisno → sinxron rollback/xato — narxi: sinxron vaqtida foydalanuvchi amallari qisqa kutadi.
Task 6: minor (deferred): AVKartochka yaratilishi jurnalga yozilmaydi (shovqin kamaytirish uchun qabul)
Task 6: minor (deferred): birinchi sinxronda ~3 INSERT/juftlik, bulk emas
Task 6: minor (deferred): yangi qator jurnal eski="0" vs "20.000" formati
Task 6: minor (deferred): [:255] keraksiz kesish; _hujjat_izohlari kesishma filtri testsiz; manfiy 1C qoldig'i 0 deb olinadi — izoh yo'q
Task 6: fix round 1/5 (2 addressed, 0 open — ishga_tushgan_sana/majburiy to'liq, select_for_update+invariant; commits 594dbec..ce9b300)
Task 6: minor (deferred): yangi Taqsimot qatori qo'shilishi (concurrent insert) qulfga tushmaydi — faqat yakuniy invariant tutadi, sinxron qayta urinadi
Task 6: minor (deferred): butun Taqsimot pk tartibida qulflanadi — T7 amallari ham pk tartibida qulflasin (deadlock oldini olish)
Task 6: complete (commits 8a056b9..ce9b300, review clean)
Ruling (T7): bir xil bo'lim/holat/mol'ga "o'zgartirish" → AmalXato; arxiv = jami 1C qoldig'i ≤ 0; qulflar pk tartibida (moslashtir bilan bir xil) — narxi yo'q.
Task 7: dispatched (base ce9b300, sonnet)
Task 7: implementer DONE_WITH_CONCERNS (commit 49167d9; 113 passed). TDD tartibi buzilgan (kod testdan oldin), RED ImportError bilan
Task 7: minor (deferred): _tekshir_soni yuqori chegarasi qulfdan oldin eskirgan obyektga qarab ham tekshiriladi
Task 7: minor (deferred): parallel yangi nishon qatori → IntegrityError 500 (AmalXato emas)
Task 7: minor (deferred): kochir bolim.faol/filial qayta o'qilmaydi
Task 7: minor (deferred): Σ himoyalari deyarli tavtologik, testsiz; :80 xabar farq>0 da noaniq
Task 7: minor (deferred): mol_ozgartir mol.filial tekshirmaydi, hujjat_izoh=None TypeError — T9 МОЛ'ni tekshirsin
Task 7: minor (deferred): xususiy moslash._hujjat_izohlari import; holat birlashuvi va kamaytir farq>0 testlari yo'q
Task 7: complete (commits ce9b300..49167d9, review clean)
Ruling (T8): AV darajasidagi filial cheklovi = AV'ning musbat AVQoldiq bo'lgan filiallaridan biri ruxsat etilgan (filial_bilan_chekla + distinct); taqsimot bayroqlari Taqsimot.filial bo'yicha — narxi: filial_rekvizit_bosh AV faqat qoldig'i bor filial foydalanuvchisiga ko'rinadi.
Ruling (T8): ketgan_xodimda = mol.ishdan_bushagan OR mol.neaktiv OR mol.onec_da_yoq (spec §5.4); mos_emas = Σ ≠ qoldiq bo'lgan juftligi bor AV; muddat_tugagan: tugash ≤ bugun; muddat_6oy: bugun < tugash ≤ bugun+6 oy (T15 testi bilan mos); oy qo'shishda kun oy oxiriga qisiladi; pul 2 xona, foiz 2 xona ROUND_HALF_UP.
Task 8: dispatched (base 49167d9, sonnet)
Task 8: implementer DONE (commit f51ea71; 155 passed)
Task 8: minor (deferred): mos_emas — 0 qoldiqli filialdagi eskirgan taqsimot faqat boshqa filialda qoldig'i bor AV'da cheklangan foydalanuvchiga ko'rinmaydi; max(q,0) qisish (moslash bilan mos) — Ruling: qabul
Task 8: minor (deferred): AV.kalit select_related("filial_rekvizit") talab qiladi (T10/T14)
Task 8: minor (deferred): ketgan_xodimda/yorliq/muddat/inv_takror uchun filial cheklovi testi yo'q
Task 8: minor (deferred): bayroq_sonlari _tugash_sanalari ikki marta, Python'da hisob — T10 keshlasin
Task 8: complete (commits 49167d9..f51ea71, review clean)
Task 9: TO'XTADI — WeasyPrint Windows'da Pango DLL topolmaydi; MSYS2 o'rnatish foydalanuvchidan so'raldi (tizimga o'rnatish)
Task 9: blokdan chiqdi — MSYS2 mingw64 pango o'rnatildi; WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin bilan WeasyPrint 70.0 PDF beradi.
Ruling (T9): settings_test.py da Windows'da va papka mavjud bo'lsa os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", r"C:\msys64\mingw64\bin"); .env.example ga izoh — Linux'da ta'sirsiz — narxi yo'q.
Ruling (T9): akt_tasdiqla avval aktdagi barcha (av, filial) Taqsimot qatorlarini pk tartibida bitta select_for_update bilan qulflaydi (moslashtir bilan bir tartib, deadlock'siz), keyin mol_ozgartir; qabul qiluvchi faol = ishdan_bushagan/neaktiv/onec_da_yoq emas.
Task 9: dispatched (base f51ea71, sonnet)
Task 9: implementer DONE (commit 1610514; 169 passed)
Task 9: minor (deferred): _keyingi_raqam parallel yaratuvchilarni ketma-ketlashtirmaydi (READ COMMITTED) → IntegrityError 500; docstring noto'g'ri — advisory xact lock yoki retry kerak (yakuniy ko'rib chiqishda tuzatish tavsiya)
Task 9: minor (deferred): PDF testi kirill matnini tekshirmaydi
Task 9: minor (deferred): arxivlangan AV aktini qayta chop etishda qiymat 0.00
Task 9: minor (deferred): qoralama yaratishda qabul qiluvchi faolligi tekshirilmaydi (tasdiqda tekshiriladi)
Task 9: complete (commits f51ea71..1610514, review clean)
Ruling (T10): T2 dagi nomsiz "bosh" URL → panel:bosh (panel/urls.py, app_name="panel"); barcha havolalar va testlar yangilanadi; LOGIN_REDIRECT ham — narxi yo'q.
Ruling (T10): AV ro'yxati filial cheklovi bayroqlar bilan bir xil (musbat qoldiq ruxsat etilgan filialda; umumiy yordamchi qayta ishlatiladi, nusxa emas); arxiv=1 da cheklangan foydalanuvchi arxiv AV'ni filial_rekvizit bo'yicha ko'radi — narxi: rekvizitsiz arxiv AV faqat cheklanmaganlarga ko'rinadi.
Ruling (T10): bosh sahifa qoldiq qiymati = har AVQoldiq qatori summa × (1 − eskirish) (AV amortizatsiyasi bo'yicha); hisoblab bo'lmasa summa o'zi olinadi (eskirishsiz) — narxi: qoldiq qiymat oshib ko'rsatilishi mumkin.
Ruling (T10): ommaviy amallar (kochir, holat) faqat jami 1C soni == 1 va bitta taqsimot qatori bo'lgan AV'lar uchun; guruh AV tanlansa u rad etiladi (xabarda sanaladi), 1 donalilar baribir ko'chadi (brief testi test_ommaviy_kochirish_faqat_1_donali bilan mos).
Task 10: dispatched (base 1610514, sonnet)
Task 10: implementer DONE (commit bf37bd8; 192 passed)
Task 10: review Needs fixes — spec ❌: МОЛ filtri UI yo'q, bayroq tanlash UI yo'q, banner matni «Oxirgi muvaffaqiyatli sinxron: HH:MM» emas; Important: Excel havolasi HTMX'dan keyin eskiradi; ommaviy amal filial testi AV darajasini sinamaydi.
Ruling (T10): filial=B parametri cheklangan foydalanuvchida (B ruxsatsiz) → bo'sh natija — Review Focus 5 ga kiradi, fix loop'ga qo'shildi.
Ruling (T10): cheklangan foydalanuvchiga AV jami soni/summasi (barcha filiallar) ko'rinadi — AV bitta obyekt, 1C kartochkasi ma'lumoti — qabul; narxi: boshqa filial miqdori bilvosita ko'rinadi.
Task 10: minor (deferred): isdigit/bolim ValueError → 500; Excel formula injection (= bilan boshlanuvchi 1C matni); filial_kesimi Python'da O(n); sinxron_holati HTMX bo'lakda ham 2 so'rov; toliq_nomi chuqur N+1; arxiv+bayroq bo'sh; N+1 testi zaif.
Task 10: fix round 1/5 (5 addressed, 0 open — МОЛ/bayroq filtrlari, banner, Excel havolasi, ommaviy test, filial parametri; commits bf37bd8..0cfb9ea)
Task 10: minor (deferred): МОЛ dropdown boshqa filial xodimi yo'qligi testlanmagan; banner HH:MM formati testlanmagan
Task 10: complete (commits 1610514..0cfb9ea, review clean)
Ruling (T11): taqsimot_amal = kochir, holat, kamaytir ("1C bilan moslash"); МОЛ o'zgarishi faqat akt orqali (spec §2.5) — kartochkada yo'q.
Ruling (T11): kartochka/rasm/HTMX qismlarga kirish = T10 dagi umumiy AV ko'rinish yordamchisi (arxivni ham hisobga olib); ko'rinmasa 404. Rasm fayli Django view orqali (FileResponse), rasm.av ko'rinishi tekshiriladi.
Ruling (T11): tarix Jurnal manbasi = AVKartochka va AV obyektlari yozuvlari (Taqsimot jurnali TaqsimotHarakat bilan takrorlanmasligi uchun chiqarilmaydi).
Ruling (T11): testlarda MEDIA_ROOT vaqtinchalik papka (settings fixture); Pillow requirements.txt ga.
Task 11: dispatched (base 0cfb9ea, sonnet)
Task 11: implementer DONE (commit f2e067c; 218 passed)
Task 11: review Needs fixes — Important: htmx 4xx javoblarni almashtirmaydi (xato ko'rinmaydi); MPO (telefon JPEG) rad etiladi.
Ruling (T11): base.html da global htmx.config.responseHandling — 400/409/422 javoblar ham swap qilinadi (keyingi tasklar uchun ham bir xil qoida); status kodlari saqlanadi — narxi yo'q.
Task 11: minor (deferred): 60 Mpx chegarasi xotira uchun katta (25-40 Mpx, draft, nusxalarsiz); birinchi ikki parallel yuklashda ikkita asosiy; xatoda yetim fayl; tarix chegarasiz va amaldan keyin yangilanmaydi; 409 da kiritilgan ma'lumot yo'qoladi; majburiy qo'shimcha maydon izoh saqlashni to'sadi; qoralama aktlar tarixda; rahbar POST 403 testlari yo'q.
Task 11: fix round 1/5 (2 addressed, 0 open — htmx 4xx swap, MPO; commits f2e067c..1d10ef5)
Task 11: complete (commits 0cfb9ea..1d10ef5, review clean)
Ruling (T12): bolim_nofaol_qil — bo'lim yoki istalgan pastki bo'limida taqsimot bo'lsa AmalXato; bo'lmasa bo'lim va barcha pastki bo'limlari nofaol qilinadi (nofaol ota ostida faol bola qolmasin); ota o'zgartirilsa sikl (o'z avlodi) va boshqa filial rad; nofaol bo'limni qayta faollashtirish mumkin; filial tanlash ruxsat etilgan filiallar bilan cheklangan, ruxsatsiz → 404; har o'zgarish jurnalga.
Task 12: dispatched (base 1d10ef5, sonnet)
Task 12: implementer DONE (commit 5c243bd; 228 passed)
Task 12: review Approved but 2 Important — toliq_nomi N+1 daraxt fragmentida; nomlashda ota "ildiz"ga tushib qoladi.
Task 12: minor (deferred): rahbar 403 testi yo'q; nofaol/ko'chirish faqat o'z qatorini qulflaydi (parallel sikl/taqsimot); _id isdigit ValueError; test (400,404) bo'sh; JS'siz forma faqat fragment qaytaradi; qayta faollashtirishda bola nofaol qolishi tekshirilmagan.
Task 12: fix round 1/5 (1 addressed, 1 open — N+1 hal; nofaol ota ostidagi bolani nomlash 400, dropdown almashganda forma eski; commits 5c243bd..f24ae94)
Task 12: fix round 2/5 (2 addressed, 0 open — joriy nofaol ota, forma tanlangan bo'limga bog'landi; commits f24ae94..340dee1)
Task 12: minor (deferred): yashirin bolim id ni almashtirish 404 testi yo'q; tahrir formasida avlodlar ota ro'yxatida (servis rad etadi)
Task 12: complete (commits 1d10ef5..340dee1, review clean)
Ruling (T13): xodimlar ro'yxati = filiali ruxsat etilgan YOKI ruxsat etilgan filialda taqsimot qatori bor xodimlar; AV soni/qiymati faqat ruxsat etilgan filiallardagi qatorlardan; xodim sahifasi ko'rinmasa 404.
Ruling (T13): akt (ko'rish, tasdiqlash, PDF) ko'rinadi faqat uning barcha qatorlari filiali ruxsat etilgan bo'lsa, aks holda 404; akt_yangi faqat ruxsat etilgan filiallardagi topshiruvchi qatorlarini ko'rsatadi; qabul qiluvchi tanlovi faqat faol xodimlar; yaratish/tasdiqlash = mol_akt huquqi, ko'rish/PDF = korish.
Task 13: dispatched (base 340dee1, sonnet)
Task 13: implementer DONE (commit 30482ba; controller full suite 245 passed). Hisobot qisqa (RED/GREEN to'liq emas)
Task 13: minor (deferred): akt_yangi filial cheklovi testsiz; xodim sahifasida ruxsatsiz filial nomi ko'rinadi; tasdiqlangan aktni qayta tasdiqlash POST testi yo'q; "hammasini tanlash" yo'q; PDF filename kirill bo'lsa (MA-… ASCII — tekshirish).
Task 13: complete (commits 340dee1..30482ba, review clean)
Ruling (T14): QR dekod testi — PDF'ga qo'yiladigan QR'ni yasaydigan funksiya (segno) chiqishi PNG'ga render qilinib zxing-cpp bilan o'qiladi (PDF rasterlash uchun poppler kerak emas); zxing-cpp requirements-dev'ga, segno requirements'ga — narxi: PDF ichidagi SVG to'g'ridan dekod qilinmaydi.
Ruling (T14): YorliqOlchami.standarti() standart yo'q bo'lsa — birinchi faol o'lcham, u ham yo'q bo'lsa xato xabari (T4 minor yopiladi); avlar select_related("filial_rekvizit") (T8 minor); chop_etildi PDF muvaffaqiyatli yaratilgandan keyin chaqiriladi.
Task 14: dispatched (base 30482ba, sonnet)
Task 14: implementer DONE_WITH_CONCERNS (commit 865f4e4; 264 passed). Yorliq vizual tekshirilmagan — foydalanuvchi printerda sinasin
Task 14: review Needs fixes — ruling 2 buzilgan (Unicode raqam isdigit → int ValueError 500); jami sahifa chegarasi yo'q / ko'p AV'da DATA_UPLOAD_MAX_NUMBER_FIELDS.
Ruling (T14): jami sahifa ≤ 2000 (oshsa xabar, PDF yo'q); tanlash sahifasida ≤ 300 AV (oshsa xabar: filtrni toraytiring); standart nusxa min(jami_soni, MAX_NUSXA) — narxi: juda katta to'plam bir necha marta chop etiladi.
Task 14: minor (deferred): tanlash qisman ko'rinmas id'larni jim tashlaydi (pdf 404) — nomuvofiq; filial qatori 5pt eni bo'yicha moslanmaydi, 20×15 da nom 3pt kesilishi mumkin; test_nusxa_xato xabarni tekshirmaydi; o'zgarmagan kalitda ham jurnal.
Note: isdigit()+int() naqshi T10, T12, T14 da — yakuniy ko'rib chiqishda butun loyiha bo'yicha bitta xavfsiz _son() yordamchisi.
Task 14: fix round 1/5 (1 addressed, 1 open — _son uzunlik chegarasi yo'q: >4300 raqam int ValueError; commits 865f4e4..459fa95)
Task 14: fix round 2/5 (1 addressed, 0 open — _son ≤18 belgi; commits 459fa95..6582570)
Task 14: minor (deferred): test_juda_uzun_son av/bolim/nusxa uchun faqat 500 yo'qligini tekshiradi; bolim xato yo'lida uzun redirect URL
Task 14: complete (commits 30482ba..6582570, review clean)
Ruling (T15): kesim — filial: AVQoldiq ruxsat etilgan filiallar bo'yicha (soni, summa; qoldiq = summa×(1−eskirish)); bo'lim: Taqsimot (ruxsat etilgan filiallar) soni×dona_narxi, taqsimlanmagan → «Bo'limsiz»; tur: AVQoldiq ruxsat etilgan filiallar, turi null → «Turi yo'q»; faqat faol AV. Hisoblab bo'lmasa qoldiq = boshlang'ich (T10 bilan bir xil).
Ruling (T15): hisobotlar/excel.py jadval_xlsx da formula injection himoyasi (=,+,-,@ bilan boshlanuvchi satrlar matn sifatida) — T10 minor shu yerda yopiladi; foydalanuvchi parametrlarini o'qish xavfsiz (ascii raqam, ≤18) — 500 yo'q.
Ruling (T15): huquq — sahifalar va Excel `hisobot` (tozalash sahifasi `tozalash`); filial cheklovi hamma joyda.
Task 15: dispatched (base 6582570, sonnet)
Task 15: implementer DONE (commit bc801f1; 282 passed). Bosh sahifa endi faqat faol AV
Task 15: review Needs fixes — Important: bo'lim/tur kesim jamlari yaxlitlash tufayli 1C summadan tiyinga farq qiladi.
Ruling (T15): har AV summasi bo'lim qatorlariga "eng katta qoldiq" usulida 0.01 ga taqsimlanadi (qatorlar yig'indisi = AV summasi aynan); jami yaxlitlanmagan yig'indilardan bir marta yaxlitlanadi — narxi: alohida qator ±0.01.
Task 15: minor (deferred): _son xususiy import (umumiy yordamchiga); bo'lim kesimi o'rtacha dona narxi vs filial kesimi filial summasi; mol_qaydnoma ?xodim= ism ko'rsatadi; muddat Excel _av_qatori 2 marta; context processor huquq tekshiruvlari; HTML filial/revizor/tur eskirish/12+8 testlari yo'q.
Task 15: fix round 1/5 (1 addressed, 0 open — eng katta qoldiq taqsimoti; commits bc801f1..6b0ae5b)
Task 15: minor (deferred): 12+8 literal test yo'q (12/5/3 ekvivalent); _taqsimla teng qoldiqda tartib DB tartibiga bog'liq; bo'lim kesimi o'rtacha narx vs filial summasi
Task 15: complete (commits 6582570..6b0ae5b, review clean)
Ruling (T16): barcha sozlama sahifalari `sozlama` huquqi (faqat admin), hozir_sinxronla `sinxron`. Foydalanuvchi o'chirilmaydi — is_active bilan nofaol qilinadi; parol Django validatorlari bilan; admin o'zini nofaol qila olmaydi. Ulanish sahifasi: ONEC_URL va ONEC_LOGIN ko'rsatiladi, parol hech qachon (hatto qisman). hozir_sinxronla so'rov ichida sinxron chaqiradi (timeout 60 s); band → «Sinxron hozir ishlayapti». AV turi maydonlari: kalit [a-z0-9_] noyob, tip 4 tadan biri, tanlov bo'sh bo'lmasin. Standart o'lcham almashtirish atomik. Jurnal sahifasi sahifalangan (50), filtr: kim, obyekt_turi, sana oralig'i; parametrlar xavfsiz o'qiladi.
Task 16: dispatched (base 6b0ae5b, sonnet)
Task 16: implementer DONE (commit 4309760; 331 passed)
Task 16: minor (deferred): o'z parolini o'zgartirish sessiyani yopadi (update_session_auth_hash); oxirgi admin himoyasi faqat o'zi uchun; panel admin superuser'ni tahrirlay oladi; standart belgisini olib tashlab standartsiz qoldirish mumkin; maydonlar JSON kalit tartibi soxta jurnal; Jurnal order_by aniq emas; testlar: nofaol kira olmasligi, filiallar tahriri, oxirgi muvaffaqiyatli, nostandart nofaol.
Task 16: complete (commits 6b0ae5b..4309760, review clean)
Ruling (T17): systemd-analyze Windows'da yo'q → deploy fayllari uchun pytest testi (configparser bilan unit/timer kalitlari: OnCalendar qiymatlari, ExecStart buyruqlari, User, WorkingDirectory, EnvironmentFile) + VM'da systemd-analyze verify hujjatda qadam sifatida; gunicorn --timeout 120 (hozir_sinxronla 60 s HTTP timeout uchun, T16 minor 7); nginx proxy_read_timeout 120.
Ruling (T17): jonli test (pytest -m jonli) TestClaude endpointlari tasdiqlanmaguncha ishga tushirilmaydi — standart o'tkazib yuboriladi; foydalanuvchi .env bilan o'zi ishga tushiradi.
Task 17: dispatched (base 4309760, sonnet)
Task 17: implementer DONE_WITH_CONCERNS (commit 7a10561; 355 passed, jonli deselected)
Task 17: review Approved, 1 Important — /opt/av 0750 bo'lsa nginx /static/ 403.
Ruling (T17): backup umask 077 + /var/backups/av 700 fix round'ga qo'shildi (dump'da parol xeshlari — xavfsizlik).
Task 17: minor (deferred): MEDIA_ROOT yo'q bo'lsa bo'sh tar jim; .tmp tozalanmaydi; VM'da pytest -m jonli uchun CREATEDB/settings izohi; WeasyPrint apt (libharfbuzz-subset0); nginx/systemd hardening; SECURE_PROXY_SSL_HEADER VPS'da; /tmp/uuid_eski.json.
Task 17: fix round 1/5 (2 addressed, 0 open — /opt/av traversal, umask 077; commits 7a10561..162dba0)
Task 17: minor (deferred): qabul ro'yxatidagi curl http:// TLS'dan keyin 301 (https:// yoki -IL); /opt/av 755 o'rniga 711
Task 17: complete (commits 4309760..162dba0, review clean)
FINAL REVIEW (99069e3..162dba0): With fixes. Important: (1) yomon kirish 500 (isdigit/int, NUL) bir necha ilovada; (2) tarix(av) filial sizdiradi; (3) 03:00 da to'liq sinxron 5-daqiqalik bilan to'qnashib BAND bo'ladi; (4) HTTPS sozlamalari yo'q (VPS'da CSRF 403); (5) tasdiqlangan akt qiymati vaqt o'tib o'zgaradi.
Ruling (final): bitta fix dispatch — Important 1–5 + "merge'dan oldin" minorlar (mol_qaydnoma xodim sizishi, akt raqami advisory xact lock, _ozgartir IntegrityError→AmalXato, qabul ro'yxatidan revizor bo'limi) + testlar (T8 bayroq filial testlari, T13 akt_yangi filial, rahbar POST 403). To'liq sinxron 03:02:30 ga + toliq BAND bo'lsa 5 daqiqagacha qayta urinadi. HTTPS — env bayroq HTTPS=True. Akt qiymati — MolAktQator ga dona_narxi tasdiqda yoziladi (migratsiya).
Production'dan oldin (keyinga): 60 Mpx xotira, MEDIA_ROOT bo'sh tar, libharfbuzz-subset0, update_session_auth_hash, SinxronJurnal index/retention, capture=environment, ommaviy so'rov takrori.
1C namunalari kelganda: OneCXato ga {"xato"} matni, tz-aware sana.
FINAL fix: commit 1a5c896 (400 passed, 1 deselected); re-review dispatched
FINAL fix re-review: all 9 addressed, no new Critical/Important.
FINAL parked: BAND retry har urinishda SinxronJurnal qatori (≤21) — Ruling: qabul, holat mantiqi OK filtrlaydi; CSRF_TRUSTED_ORIGINS .domen → subdomenlar uchun qo'lda — Ruling: hujjatlashtirilgan; migratsiyadan oldingi tasdiqlangan aktlarda narx yo'q — Ruling: baza hali ishlab chiqarishda emas; CLAUDE.md 03:00 → 03:02:30 eskirgan — Ruling: keyingi hujjat yangilashda.
