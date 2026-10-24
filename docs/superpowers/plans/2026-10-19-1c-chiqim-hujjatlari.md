# 1C chiqim hujjatlari (tasdiqlashni kutadi) — amalga oshirish rejasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 1C'dagi har bir yangi chiqim (sotish, filialga o'tkazish, hisobdan chiqarish) platformada «kutilmoqda» holatida
turadi; taqsimot hisobchi turini va qatorlarini tasdiqlaguncha o'zgarmaydi.

**Architecture:** Yangi `chiqimlar` ilovasi: `ChiqimHujjat` modeli, sinxron uni Harakat1C'dan yaratadi/yangilaydi
(`servis.chiqimlarni_yangila`), `vositalar.moslash` kutilayotgan miqdorni (K) hisobga oladi, tasdiqlash servisi
taqsimot qatorlarini kamaytiradi va ixtiyoriy ravishda B filialda joylaydi; panelda ro'yxat va tasdiqlash sahifasi.

**Tech Stack:** Python 3.12 · Django 5.2 · PostgreSQL (16 prod, 18 lokal) · HTMX 2 · pytest-django.

**Spec:** `docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md` §6.5 (va §5.2, §5.4, §6.3, §7.7a, §8, §11).

## Global Constraints

- 1C'ga hech narsa yozilmaydi. Interfeys matnlari va identifikatorlar o'zbek (lotin).
- Invariant: har (AV, filial) uchun `Σ taqsimot = max(1C qoldig'i, 0) + K` (K — shu juftdagi `kutilmoqda` chiqimlar soni);
  faqat `Σ > ...` (mos emas) ruxsat etiladi.
- `ChiqimHujjat.holat`: `kutilmoqda` · `tasdiqlangan` · `bekor`. `tur`: `otkazish` · `sotildi` · `hisobdan_chiqarildi`.
- `TaqsimotHarakat.Sabab` yangi qiymatlari: `sotildi` · `otkazildi` · `hisobdan_chiqarildi`.
- Faqat `vid="chiqim"`, `soni > 0`, `sana >= Sozlama.chiqim_boshlanishi` bo'lgan Harakat1C'lar ChiqimHujjat bo'ladi;
  `chiqim_boshlanishi` migratsiyada joriy vaqt bilan to'ldiriladi.
- Taxmin: shu AV'ga chiqim sanasidan ±3 kun ichida boshqa filialda `kirim` (soni > 0) → `otkazish` (B = o'sha filial);
  `hujjat_turi == "СписаниеОС"` → `hisobdan_chiqarildi`; aks holda `sotildi`.
- Qulflar `select_for_update` pk tartibida (moslashtir bilan bir xil). Tasdiqlash bitta tranzaksiya; xato → hech narsa
  o'zgarmaydi.
- Huquq: tasdiqlash — `taqsimot` (admin, hisobchi); ko'rish — `korish`. Filial cheklovi: A filial ruxsat etilgan bo'lsa
  ko'rinadi, aks holda 404; B'ga joylash uchun B ham ruxsat etilgan bo'lishi kerak.
- So'rov parametrlari faqat `hisoblar.parametrlar.son()` bilan o'qiladi (500 yo'q).

## Review Focus

1. **1C hujjati 45 kunlik oynadan tashqarida** — oyna sinxroni eski `kutilmoqda` chiqimni «yo'qolgan» deb bekor qilmasligi
   kerak (faqat qayta olingan davr ichidagilar tekshiriladi) — Task 2.
2. **Bir hujjatda bir AV ikki qator** (masalan, ikki tashkilot) — (hujjat_ref, AV, filial) bo'yicha soni yig'iladi,
   unique buzilmaydi — Task 2.
3. **Tasdiqlashgacha 1C soni o'zgardi** (hujjat tuzatildi) — forma eski son bilan yuborilsa rad etiladi — Task 4.
4. **Kutilayotgan chiqimi bor AV arxivga tushgan** (1C qoldig'i hamma joyda 0) — qatorlar o'chirilmaydi, tasdiqlash
   ishlaydi (`_tekshir_arxiv` qo'llanmaydi) — Task 3, Task 4.
5. **B filialda taqsimlanmagan qator yo'q yoki kam** (Поступление hali kelmagan) — joylash ixtiyoriy, mavjudicha
   ko'chiriladi, xato emas — Task 4.

---

## Fayl tuzilishi

```
chiqimlar/                     yangi ilova
  apps.py, __init__.py, models.py (ChiqimHujjat), migrations/
  servis.py                    chiqimlarni_yangila, taxmin, kutilayotgan, tasdiqla, ChiqimXato
  views.py, urls.py            royxat, tasdiqlash
  templates/chiqimlar/{royxat,tasdiqlash}.html
  tests/{test_yangilash,test_tasdiqla,test_views}.py
vositalar/models.py            Sabab + Sozlama.chiqim_boshlanishi
vositalar/moslash.py           K hisobga olinadi
vositalar/bayroqlar.py         mos_emas K bilan; yangi «chiqim_kutilmoqda»
onec/sinxron.py                _bajar → chiqimlarni_yangila
config/settings.py, config/urls.py, panel/templates/panel/base.html (menyu)
```

---

### Task 1: Model va sozlama

**Files:**
- Create: `chiqimlar/{__init__,apps,models}.py`, `chiqimlar/migrations/0001_initial.py`, `chiqimlar/tests/__init__.py`
- Modify: `vositalar/models.py` (Sabab, Sozlama), `config/settings.py` (INSTALLED_APPS: `"chiqimlar"` — `vositalar` dan keyin)
- Create: `vositalar/migrations/0003_chiqim.py` (Sabab choices, `chiqim_boshlanishi` + data-migratsiya)
- Test: `chiqimlar/tests/test_models.py`

**Interfaces:**
- Produces:
  - `chiqimlar.models.ChiqimHujjat`: `hujjat_turi` (char 100), `hujjat_raqami` (char 50), `hujjat_ref` (UUID),
    `sana` (datetime), `av` → onec.AV PROTECT (related_name `chiqimlar`), `filial` → onec.Filial PROTECT,
    `soni` Decimal(15,3), `summa` Decimal(15,2), `holat` (Holat TextChoices `kutilmoqda|tasdiqlangan|bekor`,
    default `kutilmoqda`), `taxmin_tur` (Tur TextChoices `otkazish|sotildi|hisobdan_chiqarildi`), `tur` (Tur, blank),
    `qabul_filial` → onec.Filial null PROTECT related_name `+`, `izoh` (text, blank), `kim` → User null SET_NULL,
    `qachon` (datetime null), `yaratildi` (auto_now_add). Meta: `UniqueConstraint(hujjat_ref, av, filial)`,
    ordering `["-sana", "-id"]`, index (holat, filial).
  - `TaqsimotHarakat.Sabab.SOTILDI="sotildi"`, `OTKAZILDI="otkazildi"`, `HISOBDAN_CHIQARILDI="hisobdan_chiqarildi"`
    (o'zbekcha nomlar: «Sotildi», «Filialga o'tkazildi», «Hisobdan chiqarildi»).
  - `Sozlama.chiqim_boshlanishi` (DateTimeField null); data-migratsiya yagona `Sozlama` yozuvini (pk=1, kerak bo'lsa yaratib)
    `timezone.now()` bilan to'ldiradi; teskari — `None`.

- [ ] **Step 1:** Failing testlar: `test_unikal_hujjat_av_filial` (ikkinchi bir xil yozuv → IntegrityError),
  `test_standart_holat_kutilmoqda`, `test_chiqim_boshlanishi_migratsiyada_toldirilgan` (`Sozlama.ol().chiqim_boshlanishi is not None`).
- [ ] **Step 2:** `venv/Scripts/python.exe -m pytest chiqimlar -q` → FAIL (ModuleNotFoundError).
- [ ] **Step 3:** Model, Sabab, Sozlama maydoni, migratsiyalar (`makemigrations` + RunPython).
- [ ] **Step 4:** `pytest chiqimlar -q` PASS; `manage.py makemigrations --check --dry-run` → «No changes detected».
- [ ] **Step 5:** Commit `feat(chiqimlar): ChiqimHujjat modeli va chiqim_boshlanishi`.

---

### Task 2: Sinxronda yaratish, yangilash, bekor qilish va taxmin

**Files:**
- Create: `chiqimlar/servis.py`, `chiqimlar/tests/test_yangilash.py`
- Modify: `onec/sinxron.py` (`_bajar`: `_harakatlar`dan keyin, `moslashtir()`dan oldin chaqiruv; `ozgarishlar["chiqim"]`)

**Interfaces:**
- Consumes: `onec.models.Harakat1C`, `ChiqimHujjat` (Task 1), `Sozlama.ol().chiqim_boshlanishi`.
- Produces:
  - `chiqimlarni_yangila(dan: datetime, gacha: datetime) -> dict` (aware; sinxron qayta olgan oraliq) — statistika
    `{"yaratildi", "yangilandi", "bekor"}`.
  - `taxmin_qil(av_id: int, filial_id: int, sana: datetime, hujjat_turi: str) -> tuple[str, int | None]` — (tur, qabul_filial_id).
  - `TAXMIN_OYNASI = timedelta(days=3)`.

Qoidalar: oraliqdagi Harakat1C'lar `vid="chiqim"`, `soni > 0`, `sana >= max(dan, chiqim_boshlanishi)` → (hujjat_ref, av,
filial) bo'yicha guruhlanadi (soni, summa yig'iladi; sana/turi/raqami — guruhning birinchisi). Yo'q bo'lsa — yaratiladi
(taxmin bilan); `kutilmoqda` bo'lsa soni/summa/sana yangilanadi; `tasdiqlangan`/`bekor` — tegilmaydi. Oraliq ichida
(`dan <= sana <= gacha`) bo'lib, guruhlarda yo'q `kutilmoqda` yozuv → `bekor` + `jurnal.yoz(None, obj, "holat",
"kutilmoqda", "bekor")`. `chiqim_boshlanishi` None bo'lsa hech narsa qilinmaydi.

- [ ] **Step 1:** Failing testlar (`harakat(av, filial, vid, sana, soni, turi, ref)` yordamchisi bilan):
  - `test_boshlanishdan_oldingi_chiqim_yaratilmaydi`
  - `test_yangi_chiqim_kutilmoqda` — soni, summa, hujjat maydonlari to'g'ri
  - `test_bir_hujjatda_ikki_qator_yigiladi` — bitta ChiqimHujjat, soni 2+3=5 (Review Focus 2)
  - `test_soni_nol_va_kirim_yaratilmaydi`
  - `test_takroriy_chaqiriq_idempotent` — ikkinchi chaqiriq: yaratildi=0, yozuvlar soni o'zgarmaydi
  - `test_1c_da_soni_ozgarsa_yangilanadi` / `test_tasdiqlangan_ozgarmaydi`
  - `test_oraliqda_yoqolsa_bekor` — jurnalda «bekor»
  - `test_oraliqdan_tashqarisi_bekor_qilinmaydi` — chiqim sanasi `dan`dan oldin, harakati yo'q → `kutilmoqda` qoladi (Review Focus 1)
  - `test_taxmin_otkazish` — boshqa filialda 2 kun keyin kirim → (`otkazish`, B); 4 kun keyin → `sotildi`
  - `test_taxmin_spisanie` — `СписаниеОС` → `hisobdan_chiqarildi`
  - `onec/tests/test_sinxron.py::test_sinxron_chiqim_yaratadi` — test `chiqim_boshlanishi`ni namunadagi eng erta
    chiqimdan oldinga qo'yadi (migratsiya uni «hozir» qiladi); shundan keyingi namuna chiqimlari
    ChiqimHujjat bo'ladi, `jurnal.ozgarishlar["chiqim"]["yaratildi"]` mos
- [ ] **Step 2:** `pytest chiqimlar/tests/test_yangilash.py onec -q` → FAIL.
- [ ] **Step 3:** `servis.py` va `_bajar` integratsiyasi (`dan` uchun `timezone.make_aware(dan_lokal)`; to'liq sinxronda TOLIQ_BOSHI).
- [ ] **Step 4:** PASS (`pytest chiqimlar onec -q`).
- [ ] **Step 5:** Commit `feat(chiqimlar): sinxronda chiqim hujjatlari`.

---

### Task 3: Moslash va bayroqlar kutilayotgan chiqimni hisobga oladi

**Files:**
- Modify: `vositalar/moslash.py`, `vositalar/bayroqlar.py`
- Test: `vositalar/tests/test_moslash.py`, `vositalar/tests/test_bayroqlar.py`

**Interfaces:**
- Consumes: `ChiqimHujjat` (Task 1).
- Produces:
  - `chiqimlar.servis.kutilayotgan(filtr: Q | None = None) -> dict[tuple[int, int], Decimal]` — `kutilmoqda` yozuvlar
    soni (av_id, filial_id) bo'yicha.
  - `moslashtir()`: har juft uchun `q = max(1C, 0) + K`; `q <= 0` (ya'ni 1C 0 va K = 0) dagina `nolga`; `d = q − t`;
    `_invariantni_tekshir()` ham `q + K` bilan. `farq(av, filial)` ham K'ni qo'shadi (amallar.kamaytir shu orqali
    ishlaydi). Import `chiqimlar` ichida funksiya darajasida (aylanma import bo'lmasin).
  - Bayroq `"chiqim_kutilmoqda": Bayroq("1C chiqimi kutilmoqda", ChiqimHujjat, _chiqim_kutilmoqda)` — foydalanuvchi
    filiallaridagi `kutilmoqda` yozuvlar; `_mos_emas` K bilan.

- [ ] **Step 1:** Failing testlar:
  - `test_kutilayotgan_chiqim_taqsimotni_saqlaydi` — 1C 6→4, K=2: Prixodxona 4 + Ofis 2 o'zgarmaydi, mos_emas=0
  - `test_kutilayotgan_chiqim_filial_nol` — 1C 0, K=1: qator o'chirilmaydi, `nolga_tushdi`=0 (Review Focus 4)
  - `test_chiqimsiz_kamayish_eskicha` — K=0 da mavjud xulq o'zgarmaydi (bor testlar ham PASS qoladi)
  - `test_bekor_chiqimdan_keyin_eskicha` — `bekor` K'ga kirmaydi
  - `test_bayroq_chiqim_kutilmoqda_filial_cheklovi`; `test_mos_emas_K_bilan`
- [ ] **Step 2:** `pytest vositalar -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest vositalar onec chiqimlar -q` PASS.
- [ ] **Step 5:** Commit `feat(vositalar): moslash kutilayotgan chiqimni hisobga oladi`.

---

### Task 4: Tasdiqlash servisi

**Files:**
- Modify: `chiqimlar/servis.py`
- Test: `chiqimlar/tests/test_tasdiqla.py`

**Interfaces:**
- Consumes: `vositalar.amallar.kochir` (B'ga joylash), `vositalar.amallar._ayir`, `_harakat`, `jurnal.yoz`,
  `vositalar.moslash._invariantni_tekshir` yoki `farq`.
- Produces:
  - `class ChiqimXato(Exception)` (o'zbekcha xabar)
  - `tasdiqla(chiqim: ChiqimHujjat, tur: str, qatorlar: dict[int, Decimal], kim, *, kutilgan_soni: Decimal,
    qabul_filial=None, b_bolim=None, b_holat: str = "", izoh: str = "") -> None`
    — `qatorlar`: {taqsimot_pk: soni} (0 lar e'tiborsiz); `kutilgan_soni` — formadagi ChiqimHujjat.soni (Review Focus 3).
  - `taqsimot_qatorlari(chiqim) -> list[Taqsimot]` — A filialdagi shu AV qatorlari (forma uchun).

Tartib (bitta `transaction.atomic`): ChiqimHujjat `select_for_update` → `holat == kutilmoqda` (aks holda «Bu chiqim
allaqachon tasdiqlangan.») → `soni == kutilgan_soni` (aks holda «1C'da chiqim soni o'zgargan, sahifani yangilang.») →
tur ∈ Tur; `otkazish` uchun `qabul_filial` majburiy va ≠ A → A juftning qatorlari pk tartibida qulflanadi; har kalit shu
qatorlardan biri, 0 < son ≤ qator.soni, Σ = chiqim.soni → har qatordan `_ayir` + `_harakat(sabab=SOTILDI|OTKAZILDI|
HISOBDAN_CHIQARILDI, hujjat_izoh="<turi> <raqami>")` + `yoz` → chiqim: holat=tasdiqlangan, tur, qabul_filial, izoh, kim,
qachon → `otkazish` va `b_bolim` berilsa: `b_bolim.filial == qabul_filial`, B'dagi taqsimlanmagan qator (bolim/mol None,
`ishlatilmoqda`) topilsa `kochir(qator, min(chiqim.soni, qator.soni), b_bolim, kim)` va `b_holat` berilsa shu qatorga
`holat_ozgartir`; topilmasa — o'tkazib yuboriladi (Review Focus 5) → oxirida A juft uchun invariant: Σ taqsimot ==
max(1C,0) + K(qolgan kutilmoqda) yoki mos emas (Σ >) — aks holda `ChiqimXato`. `_tekshir_arxiv` chaqirilmaydi.

- [ ] **Step 1:** Failing testlar:
  - `test_bitta_qator_toliq_sotildi` — qator o'chirildi, TaqsimotHarakat `sotildi`, chiqim `tasdiqlangan`, jurnal
  - `test_guruh_qisman_ikki_qatordan` — Prixodxona 4, Ofis 2; 1C −3; {Prixodxona: 2, Ofis: 1} → 2 va 1 qoladi
  - `test_yigindi_teng_bolmasa_rad` — hech narsa o'zgarmagan
  - `test_boshqa_av_qatori_rad`; `test_soni_qatordan_kop_rad`
  - `test_otkazish_b_filial_majburiy_va_A_emas`
  - `test_otkazish_b_ga_joylash` — B'da taqsimlanmagan 3 → 3 tasi b_bolim'ga, holat `zaxirada`
  - `test_otkazish_b_da_taqsimlanmagan_yoq` — xato yo'q, A kamaygan (Review Focus 5)
  - `test_soni_ozgargan_rad` (kutilgan_soni ≠) (Review Focus 3)
  - `test_qayta_tasdiqlash_rad`
  - `test_arxiv_av_tasdiqlanadi` — 1C hamma joyda 0, K=1 → tasdiqlash ishlaydi, qator o'chadi (Review Focus 4)
  - `test_sinxrondan_keyin_invariant` — tasdiqlashdan keyin `moslashtir()` hech narsa o'zgartirmaydi
- [ ] **Step 2:** `pytest chiqimlar/tests/test_tasdiqla.py -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest chiqimlar vositalar -q` PASS.
- [ ] **Step 5:** Commit `feat(chiqimlar): tasdiqlash servisi`.

---

### Task 5: Panel sahifalari

**Files:**
- Create: `chiqimlar/{views,urls}.py`, `chiqimlar/templates/chiqimlar/{royxat,tasdiqlash}.html`, `chiqimlar/tests/test_views.py`
- Modify: `config/urls.py` (`path("chiqimlar/", include("chiqimlar.urls"))`), `panel/templates/panel/base.html`
  (menyu «1C chiqimlari», `korish` bilan; kutilayotganlar soni nishon sifatida)

**Interfaces:**
- Consumes: `tasdiqla`, `taqsimot_qatorlari`, `ChiqimXato` (Task 4); `filial_bilan_chekla`, `ruxsat_filial_idlar`,
  `amal_kerak`; `hisoblar.parametrlar.son`; `vositalar.models.Bolim`, `Holat`.
- Produces: URL nomlari `chiqimlar:royxat`, `chiqimlar:tasdiqlash` (`<int:pk>/`). Bosh sahifa kartochkasi — Task 3
  bayrog'i orqali avtomatik (havola `chiqimlar:royxat`ga: `bosh.html`da `chiqim_kutilmoqda` uchun maxsus havola).

Ro'yxat: filtrlar `holat` (standart `kutilmoqda`), `tur`, `filial`, sana dan/gacha; sahifalash 50; ustunlar: sana,
1C hujjati, AV (kartochkaga havola), filial, soni, summa, taxmin/tur, holat, «Tasdiqlash» (faqat `taqsimot` huquqi).
Tasdiqlash: GET — forma (tur radio, taxmin tanlangan; A qatorlari jadvali soni inputlari bilan, bitta qator bo'lsa
to'ldirilgan; `otkazish` uchun B filial select (ruxsat etilgan, A'dan boshqa), B bo'limi va holati select; izoh;
yashirin `kutilgan_soni` mahalliylashtirilmagan); POST → `tasdiqla` → muvaffaqiyat: ro'yxatga redirect + xabar;
`ChiqimXato` → forma 400 bilan xabar.

- [ ] **Step 1:** Failing testlar:
  - `test_royxat_standart_kutilmoqda`, `test_royxat_filial_cheklovi`, `test_royxat_bad_param_500_yoq` («²», 19 xona)
  - `test_tasdiqlash_oqimi` — POST → redirect, chiqim tasdiqlangan, AV tarixida «Sotildi»
  - `test_tasdiqlash_xato_400_xabar`
  - `test_hr_rahbar_tasdiqlay_olmaydi` (POST 403, GET ro'yxat 200)
  - `test_ruxsatsiz_filial_chiqimi_404`; `test_b_filial_ruxsatsiz_rad`
  - `test_bosh_sahifa_kartochka_havolasi` — «1C chiqimi kutilmoqda» kartochkasi `chiqimlar:royxat`ga olib boradi
- [ ] **Step 2:** `pytest chiqimlar/tests/test_views.py -q` → FAIL.
- [ ] **Step 3:** Yoz (Uzbek UI, `son`/`pul` filtrlari, mavjud uslub).
- [ ] **Step 4:** To'liq `venv/Scripts/python.exe -m pytest -q` PASS.
- [ ] **Step 5:** Commit `feat(chiqimlar): ro'yxat va tasdiqlash sahifalari`.
