# AV platformasi — 1-bosqich (Asos) amalga oshirish rejasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 1C «КСБ» dagi asosiy vositalarni o'qib oladigan (faqat o'qish) va ularni bo'lim, МОЛ, holat bo'yicha soni bilan
taqsimlab yuritadigan Django veb-panelini qurish: kartochka, rasm, amortizatsiya, topshirish-qabul aktlari, QR-yorliqlar,
tozalash ro'yxatlari, hisobotlar.

**Architecture:** 1C kengaytmasi «AVSinxron» `/hs/av/` orqali JSON beradi; Django `manage.py sinxron` uni har 5 daqiqada
tortib, `onec` ilovasidagi nusxa jadvallariga yozadi va `vositalar.moslash` orqali platforma taqsimotini 1C qoldig'i bilan
moslaydi. Panel — server tomonida render qilinadigan Django templates + HTMX; har ilova (app) o'z modellari, servislari,
view va shablonlariga ega.

**Tech Stack:** Python 3.12 · Django 5.2 LTS · PostgreSQL 16 · HTMX · requests · openpyxl · WeasyPrint · segno · Pillow ·
django-axes · pytest-django · gunicorn + nginx + systemd (Ubuntu 24.04). 1C: BSL kengaytma, platforma 8.3.13, moslik 8.3.9.

**Spec:** `docs/superpowers/specs/2026-10-17-av-platforma-1-bosqich-design.md`

## Global Constraints

- **1C'ga hech narsa yozilmaydi.** Kengaytma faqat `Запрос` bilan o'qiydi; ishchi baza doms2021'ga faqat foydalanuvchi
  o'zi, aniq so'rovdan keyin o'rnatadi. SQL'ga to'g'ridan-to'g'ri yozish taqiqlangan.
- 1C'dan kelgan maydonlar (nomi, inv. raqam, qiymat, filial, soni) panelda tahrirlanmaydi.
- Python 3.12, Django 5.2 LTS, PostgreSQL 16 (testlar ham PostgreSQL'da), Celery ishlatilmaydi.
- Interfeys matnlari — o'zbek (lotin). Kod identifikatorlari — spetsifikatsiyadagi o'zbekcha nomlar.
- Maxfiy qiymatlar (`ONEC_URL`, `ONEC_LOGIN`, `ONEC_PAROL`, `DATABASE_URL`, `SECRET_KEY`) faqat `.env`, `.env` git'ga kirmaydi.
- Sinxron: har 5 daqiqada; harakatlar oynasi 45 kun; har kecha 03:00 to'liq; HTTP timeout 60 s; bitta tranzaksiya;
  bir vaqtda bitta sinxron (PostgreSQL advisory lock, kalit `7310001`).
- Holatlar (aniq qiymatlar): `ishlatilmoqda`, `zaxirada`, `tamirda`, `nosoz`, `hisobdan_chiqarishga`, `topilmadi`.
- Rollar: `admin`, `hisobchi`, `hr`, `rahbar`, `revizor` (revizor panelga kirmaydi).
- Kirish: 5 noto'g'ri urinish → 15 daqiqa blok; sessiya 8 soat harakatsizlikdan keyin tugaydi.
- Rasm: faqat jpg/png, ≤ 15 MB, serverda max 1600 px gacha kichraytiriladi + miniatyura.
- QR matni: `DS|<filial kodi>|<inv raqam>` (filial = `AV.filial_rekvizit`). Yorliq o'lchamlari: `40x30`, `58x40` mm.
- Taqsimot invarianti: har (AV, filial) uchun Σ `Taqsimot.soni` = `AVQoldiq.soni`; buzilishi faqat 1C kamayishida
  bo'lishi mumkin va «Taqsimot 1C bilan mos emas» bayrog'ini beradi.
- Amortizatsiya: chiziqli, `qoldiq = summa × max(0, 1 − oylar/muddat)`; asos — 1C'dagi joriy summa.
- Zaxira: har kecha `pg_dump` + `media/`, 14 kun.
- Windows/1C buyruqlari (`1cv8.exe DESIGNER ...`) foydalanuvchi kompyuterida bajariladi (foydalanuvchi o'zi yoki
  computer use orqali); Konfigurator ochiq bo'lsa, yuklashdan oldin yopish so'raladi.

## Review Focus

1. **1C'da soni 0, summa ≠ 0** (masalan, ПереоценкаОС'dan keyin) — `dona_narxi` nolga bo'linmasdan 0 bo'lishi kerak (Task 8).
2. **JSON'da bo'sh ref** (AV'da turi/filial rekviziti yo'q, xodimda filial yo'q) — `null` bo'lib saqlanadi, sinxron yiqilmaydi (Task 3).
3. **Aktda bitta taqsimot qatori ikki marta** — tasdiqlashda sonlar jamlanib tekshiriladi, ortiqcha bo'lsa butun akt rad etiladi (Task 9).
4. **Inv. raqam yoki filial kodida chetdagi bo'sh joylar** — kalitda `strip()` qilinadi, aks holda soxta «yorliqni almashtirish» chiqadi (Task 8).
5. **Filial cheklovi faqat sahifalarda emas** — Excel eksport, PDF (akt, yorliq), HTMX bo'laklar va rasm URL'larida ham ruxsatsiz filial → 404 (Task 10, 13, 14, 15).

---

## Fayl tuzilishi

```
asosiy_vositalar/
  CLAUDE.md                    loyiha qoidalari (Task 2)
  manage.py, pyproject.toml, requirements.txt, .env.example, pytest.ini, conftest.py
  config/                      settings.py, urls.py, wsgi.py
  hisoblar/                    Profil (rol, filiallar), huquqlar, kirish
  onec/                        1C nusxa modellari, client.py, sinxron.py, management/commands/sinxron.py
  vositalar/                   Bolim, AVKartochka, AVTuriSozlama, Rasm, Taqsimot, TaqsimotHarakat, Sozlama;
                               moslash.py, amallar.py, amortizatsiya.py, bayroqlar.py, qoshimcha.py, rasmlar.py
  mol/                         MolAkt, MolAktQator, servis.py, pdf
  yorliqlar/                   servis.py (QR, PDF)
  hisobotlar/                  servis.py, excel.py, tozalash va hisobot sahifalari
  jurnal/                      Jurnal modeli, yoz() yordamchisi
  panel/                       base.html, bosh sahifa, sinxron banneri, sozlamalar sahifalari
  1c/AVSinxron/                kengaytma fayllari (DumpConfigToFiles formati), Modul.bsl nusxasi
  deploy/                      systemd unit/timer, nginx, backup.sh
  docs/                        spec, reja, 1c-farazlar.md, ishga-tushirish.md
```

Har ilova: `models.py`, servis modullari, `views.py`, `urls.py`, `templates/<ilova>/`, `tests/`.

---

### Task 1: 1C kengaytmasi «AVSinxron» + farazlarni tekshirish + JSON namunalar

**Files:**
- Create: `1c/AVSinxron/` (kengaytma fayllari), `1c/AVSinxron_HTTP_modul.bsl`, `docs/1c-farazlar.md`
- Create: `onec/tests/namunalar/spravochniklar.json`, `vositalar.json`, `harakatlar.json`

**Interfaces:**
- Produces: HTTP kontrakti `/hs/av/` (keyingi barcha tasklar shunga tayanadi). Barcha `ref` — UUID satr yoki `null`;
  sanalar ISO (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SS`); sonlar JSON number.
  - `GET /versiya` → `{"versiya":"1.0.0","baza":str,"server_vaqti":str}`
  - `GET /spravochniklar` → `{"tashkilotlar":[{ref,nomi}],"filiallar":[{ref,kod,nomi}],"av_turlari":[{ref,nomi,tip}],
    "xodimlar":[{ref,ism,filial,telefon,ishdan_bushagan,neaktiv,ochirilgan}]}`
  - `GET /vositalar` → `{"vositalar":[{ref,kod,nomi,toliq_nomi,inv_raqam,chiqarilgan_sana,turi,tashkilot,filial,izoh,
    ochirilgan}],"qoldiqlar":[{av,tashkilot,filial,soni,summa}]}` (`qoldiqlar` — `УчетОС.Остатки()` filial va tashkilot
    bo'yicha guruhlangan, faqat soni ≠ 0 yoki summa ≠ 0)
  - `GET /harakatlar?dan=YYYYMMDDhhmmss&gacha=YYYYMMDDhhmmss` → `{"harakatlar":[{sana,hujjat_turi,hujjat_raqami,
    hujjat_ref,av,tashkilot,filial,vid,soni,summa}]}`; `vid` ∈ `"kirim"|"chiqim"`; `hujjat_turi` — hujjat metadata nomi
    (masalan `"ПеремещениеОС"`). Xato → HTTP 400/500 + `{"xato":str}`.

- [ ] **Step 1:** TestClaude'dan MobilOstatka kengaytmasini fayllarga dampla (`1cv8.exe DESIGNER /S localhost\TestClaude /N Claude
  /DumpConfigToFiles <tmp> -Extension MobilOstatka`) va uning tuzilmasidan (Configuration.xml, Languages, HTTPServices)
  nusxa olib, yangi UUID'lar bilan `AVSinxron` kengaytmasini yasa: prefiks `АВС_`, HTTP-servis `АВС_AV`, RootURL `av`,
  4 ta URL-shablon (`/versiya`, `/spravochniklar`, `/vositalar`, `/harakatlar`), hammasi GET. Xavfsiz rejim yoqilgan.
  (Sabab: noldan yasalgan kengaytma avval 404 bergan.)
- [ ] **Step 2:** Modulni yoz (`1c/AVSinxron_HTTP_modul.bsl`): faqat `Запрос`, hech qanday `Записать()`/`Провести()`.
  JSON — `ЗаписьJSON`. Manbalar: Справочник.Организация, Филиал (Код, Наименование), ГруппаОС (ТипГруппаОС),
  Ходимлар (ИшданБушатилган, НеАктив, Филиал, Телефон, ПометкаУдаления), ОсновныеСредства (Код, Наименование,
  НаименованиеПолное, ИнвентарныйНомер, ДатаВыпуска, ГруппаОС, Организация, Филиал, Комментарий, ПометкаУдаления),
  РегистрНакопления.УчетОС.Остатки(), РегистрНакопления.УчетОС (Период, Регистратор, ВидДвижения, ОсновныеСредства,
  Организация, Филиал, Количество, Сумма) davr bo'yicha.
- [ ] **Step 3:** Yuklash va sintaksis: `/LoadConfigFromFiles 1c\AVSinxron -Extension AVSinxron`,
  `/UpdateDBCfg -Extension AVSinxron`, `/CheckModules -Server -Extension AVSinxron`. Kutilgan natija: xatosiz log.
- [ ] **Step 4:** TestClaude'da `AVSinxron` foydalanuvchisini och (faqat o'qish roli). Publikatsiyada (`C:\inetpub\wwwroot\TestClaude\default.vrd`)
  kengaytma servislari yoqilganini va `reuseSessions="autouse"` ni tekshir.
  Tekshiruv: `curl -u "AVSinxron:<parol>" http://<host>/TestClaude/hs/av/versiya` → 200 va `"versiya":"1.0.0"`.
  404 bo'lsa — servisni MobilOstatka ichiga alohida HTTP-servis sifatida ko'chir (spec §6.1) va qayta tekshir.
- [ ] **Step 5:** Spec §13 farazlarini tekshir va natijani `docs/1c-farazlar.md` ga yoz (har biri: tekshiruv usuli, natija ✔/✖):
  1) TestClaude'da sinov `ПеремещениеОС` (filial A → B, bitta AV, qisman soni bilan) o'tkaz; oldin va keyin `/vositalar`:
     `filial` (rekvizit) o'zgarmagan, `qoldiqlar` da A kamaygan, B paydo bo'lgan; `/harakatlar` da ikki qator (chiqim A, kirim B);
  2) ПоступлениеОС, СписаниеОС, ВводНачальныхОстатковОС, ПереоценкаОС bo'yicha ham `/harakatlar` qator beradi;
  3) `xodimlar` ro'yxati bo'sh emas va ism/filial to'ldirilgan;
  4) Step 4 natijasi; 5) kengaytma xavfsiz rejimda ishlaydi.
  Biror faraz ✖ bo'lsa — **to'xta**, foydalanuvchiga xabar ber, spec qayta kelishilmaguncha keyingi tasklarga o'tma.
- [ ] **Step 6:** Namunalarni yozib ol: uchala endpoint javobini `onec/tests/namunalar/` ga saqla, ~20 AV (guruh AV,
  1 donali, ko'p filialli, inv. raqami bo'sh, turi bo'sh) va ularga tegishli qoldiq/harakat/xodimlar bilan qisqartir.
- [ ] **Step 7:** Commit: `git add 1c docs/1c-farazlar.md onec/tests/namunalar && git commit -m "feat(1c): AVSinxron kengaytmasi va namunalar"`

---

### Task 2: Django loyihasi, rollar va kirish

**Files:**
- Create: `CLAUDE.md`, `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `conftest.py`,
  `manage.py`, `config/{settings,urls,wsgi}.py`
- Create: `hisoblar/{models,huquqlar,views,urls}.py`, `hisoblar/templates/hisoblar/kirish.html`, `hisoblar/tests/test_huquqlar.py`
- Create: `panel/templates/panel/base.html`

**Interfaces:**
- Produces:
  - `hisoblar.models.Rol(TextChoices)`: `ADMIN="admin"`, `HISOBCHI="hisobchi"`, `HR="hr"`, `RAHBAR="rahbar"`, `REVIZOR="revizor"`
  - `hisoblar.models.Profil`: `user` (O2O), `rol`, `filiallar` (M2M → `onec.Filial`, blank; bo'sh = hammasi)
  - `hisoblar.huquqlar.HUQUQLAR: dict[str, set[str]]` — amallar: `korish`, `av_tahrir`, `taqsimot`, `bolim_tahrir`,
    `mol_akt`, `yorliq`, `tozalash`, `hisobot`, `sozlama`, `sinxron`
  - `huquqi_bor(user, amal: str) -> bool`
  - `ruxsat_filial_idlar(user) -> set[int] | None` (`None` = hamma filial)
  - `filial_bilan_chekla(qs: QuerySet, user, maydon: str = "filial") -> QuerySet`
  - dekorator `amal_kerak(amal: str)` — huquq bo'lmasa 403
  - Fixture'lar (`conftest.py`): `foydalanuvchi(rol, filiallar=())` fabrikasi, `client_rol(rol)`

- [ ] **Step 1:** Loyiha skeleti: `.env` dan o'qish (`django-environ`), `DATABASES` = `DATABASE_URL`, `LANGUAGE_CODE="uz"`,
  `TIME_ZONE="Asia/Tashkent"`, `SESSION_COOKIE_AGE=8*3600`, `SESSION_SAVE_EVERY_REQUEST=True`, django-axes
  (`AXES_FAILURE_LIMIT=5`, `AXES_COOLOFF_TIME=0.25`), `MEDIA_ROOT`. `onec` ilovasi Filial modelisiz yiqilmasligi uchun
  bu taskda `onec/models.py` da faqat `Filial` (Task 3 kengaytiradi). `CLAUDE.md`: qoidalar (Global Constraints'dan
  qisqa), buyruqlar (`pytest -q`, `python manage.py sinxron`), spec va reja havolalari.
  Tekshiruv: `python manage.py check` → `System check identified no issues`; `psql --version` → 16.x.
- [ ] **Step 2:** Failing testlar `hisoblar/tests/test_huquqlar.py`:
  - `test_admin_hamma_amal` — admin uchun har `HUQUQLAR` kaliti `True`
  - `test_hisobchi_amallari` — `av_tahrir, taqsimot, bolim_tahrir, mol_akt, yorliq, tozalash, hisobot, korish` → True; `sozlama, sinxron` → False
  - `test_hr_amallari` — `mol_akt, hisobot, korish` → True; `av_tahrir, taqsimot, yorliq` → False
  - `test_rahbar_faqat_korish_va_hisobot`
  - `test_revizor_panelga_kirolmaydi` — to'g'ri parol bilan kirish → sahifada «Panelga kirish huquqi yo'q», sessiya ochilmaydi
  - `test_filial_cheklovi` — filiallari [A] bo'lgan foydalanuvchi uchun `filial_bilan_chekla(Filial.objects.all(), u, "pk")` faqat A; bo'sh ro'yxat → hammasi
  - `test_5_xato_urinishdan_keyin_blok` — 5 marta xato parol, 6-chi to'g'ri parol ham rad etiladi
- [ ] **Step 3:** `pytest hisoblar -q` → FAIL.
- [ ] **Step 4:** Modellarni, huquqlarni, kirish/chiqish view'larini va `base.html` (o'zbekcha menyu, HTMX 2.x CDN'siz — `static/` ichida) ni yoz.
- [ ] **Step 5:** `pytest hisoblar -q` → PASS.
- [ ] **Step 6:** Commit: `feat: Django skeleti, rollar va kirish`

---

### Task 3: 1C nusxa modellari va HTTP mijoz

**Files:**
- Modify: `onec/models.py`
- Create: `onec/client.py`, `onec/tests/test_client.py`

**Interfaces:**
- Consumes: Task 1 JSON kontrakti va namunalar.
- Produces (`onec/models.py`):
  - abstrakt `OneCModel`: `ref_1c` (UUIDField, unique), `sinx_vaqti` (DateTimeField), `onec_da_yoq` (bool, default False)
  - `Tashkilot(nomi)`, `Filial(kod, nomi)`, `AVTuri(nomi, tip)`,
    `Xodim(ism, filial→Filial null, telefon, ishdan_bushagan, neaktiv, ochirilgan)`,
    `AV(kod, nomi, toliq_nomi, inv_raqam, chiqarilgan_sana null, turi→AVTuri null, tashkilot→Tashkilot null,
    filial_rekvizit→Filial null, izoh_1c, ochirilgan)`
  - `AVQoldiq(av, tashkilot null, filial, soni Decimal(15,3), summa Decimal(15,2))`
  - `Harakat1C(sana, hujjat_turi, hujjat_raqami, hujjat_ref UUID, av, tashkilot null, filial null, vid, soni, summa)`
  - `SinxronJurnal(boshlandi, tugadi null, natija: "ok"|"xato"|"band", xato_matni, ozgarishlar JSON, toliq bool)`
  - Barcha FK — `on_delete=PROTECT` (1C nusxasi hech qachon kaskad o'chirmaydi)
- Produces (`onec/client.py`):
  - `class OneCXato(Exception)`
  - `class OneCClient: __init__(base_url: str, login: str, parol: str, timeout: int = 60)`;
    `versiya() -> dict`; `spravochniklar() -> dict`; `vositalar() -> dict`; `harakatlar(dan: datetime, gacha: datetime) -> list[dict]`
  - `OneCClient.settingsdan() -> OneCClient` (`ONEC_URL`, `ONEC_LOGIN`, `ONEC_PAROL`)

- [ ] **Step 1:** Failing testlar (`requests` `responses` kutubxonasi bilan soxtalashtirilgan):
  - `test_vositalar_namunani_qaytaradi` — namunadagi `vositalar` soni va birinchi `ref` mos
  - `test_harakatlar_parametr_formati` — `dan=datetime(2026,9,1)` → URL'da `dan=20260901000000`
  - `test_http_500_onecxato` — 500 javob → `OneCXato`, matnida status kodi
  - `test_buzilgan_json_onecxato` — `"{"` javob → `OneCXato`
  - `test_timeout_onecxato` — `requests.Timeout` → `OneCXato`
  - `test_basic_auth_yuboriladi` — `Authorization: Basic ...` sarlavhasi bor
- [ ] **Step 2:** `pytest onec/tests/test_client.py -q` → FAIL.
- [ ] **Step 3:** Modellar + migratsiya, `OneCClient`. Login/parol URL'ga yozilmaydi va xato matniga chiqmaydi.
- [ ] **Step 4:** `pytest onec -q` → PASS.
- [ ] **Step 5:** Commit: `feat(onec): 1C nusxa modellari va HTTP mijoz`

---

### Task 4: Platforma modellari va jurnal

**Files:**
- Create: `jurnal/models.py`, `jurnal/yoz.py`, `vositalar/models.py`, `vositalar/tests/test_models.py`

**Interfaces:**
- Consumes: `onec.models` (Task 3).
- Produces:
  - `jurnal.models.Jurnal(kim→User null, kim_nomi, qachon, obyekt_turi, obyekt_id, maydon, eski, yangi)`
  - `jurnal.yoz.yoz(kim: User | None, obyekt: Model, maydon: str, eski, yangi) -> Jurnal` (`kim=None` → `kim_nomi="1C sinxron"`)
  - `vositalar.models.Holat(TextChoices)` — Global Constraints'dagi 6 qiymat
  - `Bolim(filial→onec.Filial, ota→self null, nomi, faol=True)`; `Bolim.toliq_nomi` → `"Savdo zali / Kassa 2"`
  - `AVTuriSozlama(av_turi O2O, xizmat_muddati_oy null, maydonlar JSON list)`; maydon: `{kalit, nomi, tip ∈ matn|son|sana|tanlov, tanlov_qiymatlari: list, majburiy: bool}`
  - `AVKartochka(av O2O, ishga_tushgan_sana null, xizmat_muddati_oy null, qoshimcha JSON dict, izoh, yorliq_kaliti null, yorliq_sana null, versiya=1)`
  - `Rasm(av, fayl, miniatyura, asosiy, kim, qachon)`
  - `Taqsimot(av, filial, bolim null, mol→onec.Xodim null, holat, soni Decimal(15,3))` + `CheckConstraint(soni > 0)` +
    `UniqueConstraint(fields=[av, filial, bolim, mol, holat], nulls_distinct=False, name="taqsimot_unikal")`
  - `TaqsimotHarakat(av, filial, eski_bolim, eski_mol, eski_holat, yangi_bolim, yangi_mol, yangi_holat, soni, sana, kim null,
    sabab ∈ kochirish|holat|mol_akt|1c_kopaydi|1c_kamaydi|1c_nolga_tushdi, hujjat_izoh)` (eski_* bo'sh = 1C'dan kelgan)
  - `Sozlama` (yagona yozuv): `kompaniya_nomi`, `yorliq_olchami ∈ "40x30"|"58x40"`; `Sozlama.ol() -> Sozlama`

- [ ] **Step 1:** Failing testlar: `test_taqsimot_nulls_unikal` (bir xil av/filial/bolim=None/mol=None/holat ikkinchi qator → IntegrityError),
  `test_taqsimot_soni_musbat`, `test_bolim_toliq_nomi`, `test_sozlama_yagona` (`ol()` ikki marta → bitta yozuv),
  `test_jurnal_sinxron_nomi` (`yoz(None, ...)` → `kim_nomi == "1C sinxron"`).
- [ ] **Step 2:** `pytest vositalar jurnal -q` → FAIL.
- [ ] **Step 3:** Modellar va migratsiyalar.
- [ ] **Step 4:** `pytest vositalar jurnal -q` → PASS.
- [ ] **Step 5:** Commit: `feat: platforma modellari va jurnal`

---

### Task 5: Sinxron servisi va buyruq

**Files:**
- Create: `onec/sinxron.py`, `onec/management/commands/sinxron.py`, `onec/tests/test_sinxron.py`

**Interfaces:**
- Consumes: `OneCClient` (Task 3); `vositalar.moslash.moslashtir` (Task 6) — bu taskda chaqiriladi, Task 6 gacha
  `vositalar/moslash.py` da `def moslashtir() -> dict: return {}` bo'lib turadi.
- Produces:
  - `class SinxronBand(Exception)`
  - `sinxronla(client: OneCClient, toliq: bool = False, hozir: datetime | None = None) -> SinxronJurnal`
  - buyruq: `python manage.py sinxron [--toliq]` (chiqish kodi: ok → 0, xato → 1, band → 0 + xabar)
  - `oxirgi_muvaffaqiyatli() -> SinxronJurnal | None`; `ketma_ket_xatolar() -> int`

Jarayon: advisory lock `pg_try_advisory_lock(7310001)` (olinmasa → `SinxronBand`, jurnal natija `band`) →
1C'dan uchala javob **tranzaksiyadan oldin** olinadi → `transaction.atomic()` ichida: spravochniklar upsert (ref bo'yicha),
kelmaganlar `onec_da_yoq=True`; AV upsert; `AVQoldiq` to'liq almashtiriladi; `Harakat1C` — `toliq` bo'lsa hammasi,
aks holda `sana >= hozir − 45 kun` qismi o'chirilib qaytadan yoziladi; `moslashtir()`. Har qanday istisno → rollback,
jurnal `xato` (alohida tranzaksiyada yoziladi).

- [ ] **Step 1:** Failing testlar (client soxta obyekt, namunalar bilan):
  - `test_birinchi_sinxron_hammasini_yaratadi` — namunadagi filial/xodim/AV soni bazada
  - `test_takroriy_sinxron_ozgarmaydi` — ikkinchi chaqiriqdan keyin yozuvlar soni o'zgarmaydi
  - `test_yoqolgan_xodim_belgilanadi` — namunadan bitta xodim olib tashlanadi → `onec_da_yoq=True`, yozuv o'chirilmagan
  - `test_harakat_oynasi_eskini_saqlaydi` — 60 kun oldingi harakat 45 kunlik sinxrondan keyin ham bor
  - `test_toliq_sinxron_hammasini_almashtiradi`
  - `test_xatoda_rollback` — `vositalar()` `OneCXato` beradi → AV soni o'zgarmagan, jurnal `xato`, xato matni saqlangan
  - `test_band_bolsa` — advisory lock boshqa ulanishda ushlangan → jurnal `band`
  - `test_bosh_reflar_null` — AV `turi=null`, `filial=null`, xodim `filial=null` → saqlanadi, istisno yo'q (Review Focus 2)
  - `test_ketma_ket_xatolar` — 3 xato ketma-ket → `ketma_ket_xatolar() == 3`; keyin ok → 0
- [ ] **Step 2:** `pytest onec/tests/test_sinxron.py -q` → FAIL.
- [ ] **Step 3:** `sinxronla` va buyruqni yoz.
- [ ] **Step 4:** `pytest onec -q` → PASS.
- [ ] **Step 5:** Commit: `feat(onec): sinxron servisi`

---

### Task 6: Taqsimotni 1C bilan moslash

**Files:**
- Modify: `vositalar/moslash.py`
- Create: `vositalar/tests/test_moslash.py`

**Interfaces:**
- Consumes: Task 4 modellari, `jurnal.yoz`.
- Produces: `moslashtir() -> dict` (statistika: `yangi_kartochka`, `kopaydi`, `kamaydi`, `nolga_tushdi`, `mos_emas`);
  `farq(av: AV, filial: Filial) -> Decimal` (= 1C qoldig'i − Σ taqsimot).

Qoidalar (spec §6.3): yangi AV → `AVKartochka` + butun soni taqsimlanmagan qatorga (bolim/mol null, `ishlatilmoqda`);
`d > 0` → taqsimlanmagan qatorga qo'shiladi; `d < 0` → taqsimlanmagan qatordan yetganicha ayiriladi, qolgani mos emas
bo'lib qoladi; filialda 1C qoldig'i 0 (yoki qoldiq qatori yo'q) → shu filialdagi barcha qatorlar o'chiriladi. Har
o'zgarish → `TaqsimotHarakat` (`kim=None`, tegishli `1c_*` sabab, `hujjat_izoh` — shu (av, filial) bo'yicha oxirgi
`Harakat1C` raqami va turi). `ishga_tushgan_sana` bo'sh bo'lsa → AV'ning eng erta `kirim` harakati sanasi.

- [ ] **Step 1:** Failing testlar:
  - `test_yangi_av_taqsimlanmagan` — soni 20 → bitta qator (bolim None, mol None, `ishlatilmoqda`, 20)
  - `test_kopaydi` — 20 → 25: taqsimlanmagan +5, boshqa qatorlar o'zgarmaydi
  - `test_kamaydi_taqsimlanmagandan_yetadi` — taqsimlanmagan 3 + Ombor 17, 1C 20 → 18: taqsimlanmagan 1, `farq == 0`
  - `test_kamaydi_yetmaydi` — taqsimlanmagan 0, Ombor 20, 1C → 15: Ombor 20 qoladi, `farq == -5`, statistika `mos_emas == 1`
  - `test_qisman_filial_otkazma` — A:20 → A:15, B:5: A'da mos emas −5 (yoki taqsimlanmagandan), B'da yangi taqsimlanmagan 5
  - `test_filial_nolga_tushdi` — A'dagi barcha qatorlar o'chirildi, `1c_nolga_tushdi` harakati yozilgan
  - `test_ishga_tushgan_sana_birinchi_kirim` — bo'sh bo'lsa to'ldiriladi; qo'lda kiritilgan bo'lsa o'zgarmaydi
  - `test_takroriy_moslash_idempotent` — ikkinchi chaqiriq hech narsa o'zgartirmaydi, yangi harakat yozmaydi
- [ ] **Step 2:** `pytest vositalar/tests/test_moslash.py -q` → FAIL.
- [ ] **Step 3:** `moslashtir` va `farq` ni yoz.
- [ ] **Step 4:** `pytest vositalar onec -q` → PASS (Task 5 testlari ham).
- [ ] **Step 5:** Commit: `feat(vositalar): taqsimotni 1C bilan moslash`

---

### Task 7: Taqsimot amallari

**Files:**
- Create: `vositalar/amallar.py`, `vositalar/tests/test_amallar.py`

**Interfaces:**
- Consumes: Task 4, 6 (`farq`).
- Produces:
  - `class AmalXato(Exception)` (matni foydalanuvchiga ko'rsatiladi, o'zbekcha)
  - `kochir(qator: Taqsimot, soni: Decimal, bolim: Bolim, kim: User) -> Taqsimot`
  - `holat_ozgartir(qator: Taqsimot, soni: Decimal, holat: str, kim: User) -> Taqsimot`
  - `mol_ozgartir(qator: Taqsimot, soni: Decimal, mol: Xodim | None, kim: User, hujjat_izoh: str = "") -> Taqsimot`
  - `kamaytir(qator: Taqsimot, soni: Decimal, kim: User) -> None` — faqat `farq(av, filial) < 0` bo'lsa va `soni ≤ −farq`
  - Hammasi `transaction.atomic` + `select_for_update`; qatorni bo'ladi, mos qator bo'lsa birlashtiradi, 0 qolsa o'chiradi;
    `TaqsimotHarakat` (`kochirish|holat|mol_akt|1c_kamaydi`) va `jurnal.yoz` yozadi.

- [ ] **Step 1:** Failing testlar:
  - `test_kochir_qisman_bolinadi` — Ombor 6 → 4 tasi Ofisga: Ombor 2, Ofis 4
  - `test_kochir_birlashadi` — Ofisda bir xil mol/holatli qator bor → yangi qator ochilmaydi, soni qo'shiladi
  - `test_kochir_toliq_qator_ochadi` — 6 dan 6 → manba qator o'chiriladi
  - `test_boshqa_filial_bolimi_rad` — `bolim.filial != qator.filial` → `AmalXato`
  - `test_nofaol_bolim_rad`
  - `test_soni_chegara` — 0, manfiy, `qator.soni + 1` → `AmalXato`
  - `test_holat_ozgartir_2_tasi_nosoz`
  - `test_kamaytir_faqat_mos_emas_bolsa` — `farq == 0` → `AmalXato`; `farq == -5`, `soni=5` → invariant tiklanadi; `soni=6` → `AmalXato`
  - `test_arxiv_av_rad` — jami 1C qoldig'i 0 bo'lgan AV qatori bilan amal → `AmalXato`
  - `test_harakat_va_jurnal_yoziladi`
- [ ] **Step 2:** `pytest vositalar/tests/test_amallar.py -q` → FAIL.
- [ ] **Step 3:** Amallarni yoz.
- [ ] **Step 4:** `pytest vositalar -q` → PASS.
- [ ] **Step 5:** Commit: `feat(vositalar): taqsimot amallari`

---

### Task 8: Amortizatsiya, qiymat, kalit va bayroqlar

**Files:**
- Create: `vositalar/amortizatsiya.py`, `vositalar/bayroqlar.py`, `vositalar/tests/test_amortizatsiya.py`, `vositalar/tests/test_bayroqlar.py`
- Modify: `onec/models.py` (AV queryset va `kalit`)

**Interfaces:**
- Produces:
  - `AV.objects.qoldiq_bilan()` — annotatsiyalar `jami_soni`, `jami_summa`; `.faol()` (jami_soni > 0), `.arxiv()`
  - `AV.kalit -> str | None` → `f"DS|{filial_rekvizit.kod.strip()}|{inv_raqam.strip()}"`; filial yoki inv bo'sh → `None`
  - `dona_narxi(summa: Decimal, soni: Decimal) -> Decimal` (soni ≤ 0 → `Decimal("0")`)
  - `@dataclass Amortizatsiya(oylar: int, qoldiq_qiymat: Decimal, eskirish_foiz: Decimal, tugash_sanasi: date)`
  - `hisobla(summa: Decimal, ishga_tushgan: date | None, muddat_oy: int | None, bugun: date) -> Amortizatsiya | None`
  - `samarali_muddat(kartochka: AVKartochka) -> int | None` (kartochka → tur sozlamasi)
  - `bayroqlar.BAYROQLAR: dict[str, Bayroq]`; `Bayroq(nomi: str, model: type, so_rov: Callable[[User, date], QuerySet | list])`
    Kalitlar: `inv_bosh`, `inv_takror`, `filial_rekvizit_bosh`, `mos_emas`, `bolimsiz`, `molsiz`, `ketgan_xodimda`,
    `yorliq_yoq`, `yorliq_almashtirish`, `muddat_tugagan`, `muddat_6oy`. Hammasi faqat faol AV va foydalanuvchi filiallari bilan.
  - `bayroq_sonlari(user, bugun) -> dict[str, int]`

- [ ] **Step 1:** Failing testlar `test_amortizatsiya.py`:
  - `test_chiziqli` — summa 12 000 000, sana 2024-01-15, muddat 60, bugun 2026-10-17 → oylar 33, qoldiq 5 400 000.00, eskirish 55.00, tugash 2029-01-15
  - `test_toliq_oy_kun_boyicha` — sana 2024-01-20, bugun 2026-10-17 → oylar 32
  - `test_muddat_otgan_nol` — qoldiq 0, eskirish 100
  - `test_kelajakdagi_sana` — oylar 0, qoldiq = summa
  - `test_muddat_yoki_sana_yoq_none` — `muddat_oy` None/0, `ishga_tushgan` None → `None`
  - `test_dona_narxi_nol_soni` — `dona_narxi(Decimal("500"), Decimal("0")) == 0` (Review Focus 1)
  - `test_samarali_muddat_ustunligi` — kartochka 24, tur 60 → 24; kartochka None → 60
- [ ] **Step 2:** Failing testlar `test_bayroqlar.py`: har kalit uchun bittadan musbat va manfiy holat; qo'shimcha:
  - `test_inv_takror_filial_ichida` — ikki filialda bir xil inv → bayroq yo'q; bir filialda → ikkalasi ham bayroqda
  - `test_kalit_bosh_joylarsiz` — inv `" 125 "`, filial kodi `"07 "` → `"DS|07|125"`; `yorliq_kaliti="DS|07|125"` → `yorliq_almashtirish` da yo'q (Review Focus 4)
  - `test_bayroqlar_filial_cheklovi` — boshqa filial AV'si foydalanuvchiga ko'rinmaydi
  - `test_arxiv_bayroqlarda_yoq`
- [ ] **Step 3:** `pytest vositalar -q` → FAIL.
- [ ] **Step 4:** Yoz. `muddat_*` bayroqlari Python'da `hisobla` orqali hisoblanadi (ro'yxat qaytaradi).
- [ ] **Step 5:** `pytest vositalar -q` → PASS.
- [ ] **Step 6:** Commit: `feat(vositalar): amortizatsiya va bayroqlar`

---

### Task 9: МОЛ topshirish-qabul aktlari (servis + PDF)

**Files:**
- Create: `mol/models.py`, `mol/servis.py`, `mol/pdf.py`, `mol/templates/mol/akt_pdf.html`, `mol/tests/test_servis.py`

**Interfaces:**
- Consumes: `vositalar.amallar.mol_ozgartir`, `AmalXato` (Task 7).
- Produces:
  - `MolAkt(raqam int unique, sana, topshiruvchi→Xodim null, qabul_qiluvchi→Xodim, izoh, holat ∈ qoralama|tasdiqlangan,
    tuzdi→User, tasdiqladi→User null, tasdiq_vaqti null)`; `MolAkt.nomi` → `"MA-000123"`
  - `MolAktQator(akt, av, filial, bolim null, holat, soni)`
  - `class AktXato(Exception)`
  - `akt_yarat(topshiruvchi: Xodim | None, qabul_qiluvchi: Xodim, qatorlar: list[tuple[Taqsimot, Decimal]], kim: User, izoh: str = "") -> MolAkt`
    (qoralama; har qator taqsimot qatorining `mol == topshiruvchi` bo'lishi shart)
  - `akt_tasdiqla(akt: MolAkt, kim: User) -> None` — bitta tranzaksiya; tekshiruvlar spec §8; har akt qatori uchun
    (av, filial, bolim, mol=topshiruvchi, holat) taqsimot qatori `select_for_update` bilan topiladi va
    `mol_ozgartir(..., hujjat_izoh=akt.nomi)` chaqiriladi; bitta xato → hech narsa o'zgarmaydi, `AktXato`
  - `akt_pdf(akt: MolAkt) -> bytes` (WeasyPrint; kompaniya nomi `Sozlama`, akt nomi/sanasi, jadval: №, inv, nomi, bo'lim, holat, soni, qiymat; ikki imzo joyi)
  - Raqam: `select_for_update` bilan `max(raqam)+1`

- [ ] **Step 1:** Failing testlar:
  - `test_akt_yarat_qoralama` — МОЛ hali o'zgarmagan
  - `test_tasdiqlash_mol_ozgaradi` — Bobur'dagi 6 tadan 6 tasi → Aziz'da 6, Bobur'da 0 (qator o'chgan)
  - `test_qisman_soni` — 6 dan 4 → Bobur 2, Aziz 4
  - `test_birinchi_biriktirish` — topshiruvchi None, МОЛ'siz qatordan
  - `test_qabul_qiluvchi_ishdan_ketgan_rad` — `AktXato`, hech narsa o'zgarmagan
  - `test_tasdiqlashgacha_qator_ozgargan` — qoralamadan keyin qator boshqaga ko'chirilgan → `AktXato`, boshqa qatorlar ham o'zgarmagan
  - `test_bir_qator_ikki_marta` — bir qator 4 + 4, mavjud 6 → `AktXato` (Review Focus 3)
  - `test_tasdiqlangan_akt_qayta_tasdiqlanmaydi`
  - `test_raqam_ketma_ket`
  - `test_pdf_baytlar` — `akt_pdf` natijasi `b"%PDF"` bilan boshlanadi va matnida akt nomi bor (`pypdf` bilan o'qib)
- [ ] **Step 2:** `pytest mol -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest mol vositalar -q` → PASS.
- [ ] **Step 5:** Commit: `feat(mol): topshirish-qabul aktlari`

---

### Task 10: Panel asosi, bosh sahifa va AV ro'yxati

**Files:**
- Create: `panel/{views,urls,context_processors}.py`, `panel/templates/panel/{bosh,_sinxron_banner}.html`,
  `vositalar/{views,urls,filtrlar}.py`, `vositalar/templates/vositalar/{royxat,_jadval}.html`,
  `hisobotlar/excel.py`, `panel/tests/test_bosh.py`, `vositalar/tests/test_royxat.py`

**Interfaces:**
- Consumes: `bayroq_sonlari`, `BAYROQLAR` (Task 8), `oxirgi_muvaffaqiyatli`, `ketma_ket_xatolar` (Task 5), huquqlar (Task 2), `amallar` (Task 7).
- Produces:
  - `hisobotlar.excel.jadval_xlsx(sarlavhalar: list[str], qatorlar: Iterable[Sequence]) -> bytes`
  - `vositalar.filtrlar.av_filtrla(qs, params: QueryDict, user) -> QuerySet` (q — inv/nom, filial, bolim, turi, holat, mol, arxiv, guruh, bayroq)
  - URL nomlari: `panel:bosh`, `vositalar:royxat`, `vositalar:royxat_excel`, `vositalar:ommaviy`
  - Kontekst `sinxron_holati`: `{"oxirgi": datetime | None, "xato": bool}` (`xato` = ketma-ket xatolar ≥ 3)

- [ ] **Step 1:** Failing testlar:
  - `test_bosh_filial_kesimi` — filiallar bo'yicha soni, boshlang'ich va qoldiq qiymat to'g'ri
  - `test_bosh_bayroq_kartochkalari` — har bayroq soni va havolasi `?bayroq=<kalit>`
  - `test_sinxron_banner_qizil` — 3 ketma-ket xato → banner matnida «1C bilan aloqa yo'q»
  - `test_royxat_qidiruv_inv_va_nom`, `test_royxat_filtr_bayroq`, `test_guruh_filtri`
  - `test_royxat_filial_cheklovi` — boshqa filial AV'si sahifada yo'q
  - `test_excel_filial_cheklovi` — `royxat_excel` javobida boshqa filial AV'si yo'q (openpyxl bilan o'qib) (Review Focus 5)
  - `test_ommaviy_kochirish_faqat_1_donali` — guruh AV tanlansa rad, 1 donalilar ko'chadi
  - `test_rahbar_ommaviy_amal_403`
- [ ] **Step 2:** `pytest panel vositalar/tests/test_royxat.py -q` → FAIL.
- [ ] **Step 3:** View va shablonlar. Ro'yxat sahifalanadi (50 ta), HTMX bilan filtr o'zgarsa faqat `_jadval.html` yangilanadi.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(panel): bosh sahifa va AV ro'yxati`

---

### Task 11: AV kartochkasi sahifasi (taqsimot, maydonlar, rasmlar, tarix)

**Files:**
- Create: `vositalar/qoshimcha.py`, `vositalar/rasmlar.py`, `vositalar/tarix.py`,
  `vositalar/templates/vositalar/{kartochka,_taqsimot,_rasmlar,_tarix}.html`, `vositalar/tests/test_kartochka.py`
- Modify: `vositalar/views.py`, `vositalar/urls.py`

**Interfaces:**
- Consumes: `amallar` (Task 7), `hisobla`, `dona_narxi`, `samarali_muddat` (Task 8).
- Produces:
  - `qoshimcha_tekshir(maydonlar: list[dict], qiymatlar: dict) -> dict` (tozalangan; xato → `ValidationError` maydon kaliti bilan)
  - `rasm_saqla(av: AV, fayl: UploadedFile, kim: User) -> Rasm` (jpg/png, ≤ 15 MB, max 1600 px, miniatyura 300 px; birinchi rasm `asosiy=True`)
  - `tarix(av: AV) -> list[TarixQator]`; `TarixQator(sana: datetime, tur: str, matn: str, kim: str)` — Harakat1C, TaqsimotHarakat, MolAkt, Jurnal, Rasm; sana bo'yicha kamayuvchi
  - `kartochka_saqla(kartochka: AVKartochka, maʼlumot: dict, versiya: int, kim: User) -> None` — `versiya` mos kelmasa
    `AmalXato("Ma'lumot boshqa foydalanuvchi tomonidan o'zgartirildi, sahifani yangilang")`; o'zgargan har maydon → `jurnal.yoz`
  - URL nomlari: `vositalar:kartochka`, `vositalar:taqsimot_amal`, `vositalar:rasm_yukla`, `vositalar:rasm_asosiy`, `vositalar:rasm_fayl`

- [ ] **Step 1:** Failing testlar:
  - `test_1c_maydonlari_tahrirlanmaydi` — POST'da `nomi`, `inv_raqam` yuborilsa e'tiborsiz qoladi
  - `test_optimistik_blok` — eski `versiya` bilan saqlash → xabar, ma'lumot o'zgarmagan
  - `test_qoshimcha_tip_va_majburiy` — son maydoniga `"abc"`, majburiy bo'sh, tanlovda ro'yxatda yo'q qiymat → xatolar
  - `test_taqsimot_jadvali_jami_belgisi` — Σ = 1C → «✔», mos emas → «✖» va farq soni
  - `test_taqsimot_amal_htmx` — ko'chirish POST → 200, `_taqsimot.html` qaytadi, bazada o'zgargan
  - `test_rasm_formati_va_hajmi` — gif → rad; 16 MB → rad; 4000×3000 jpg → saqlangan, eni ≤ 1600, miniatyura bor
  - `test_rasm_fayl_filial_cheklovi` — boshqa filial AV rasmi URL'i → 404 (Review Focus 5)
  - `test_tarix_tartibi` — turli manbalardan 5 voqea to'g'ri tartibda
  - `test_hr_kartochkani_tahrirlolmaydi` — HR POST → 403
- [ ] **Step 2:** `pytest vositalar/tests/test_kartochka.py -q` → FAIL.
- [ ] **Step 3:** Yoz. Rasm fayllari Django orqali, huquq tekshiruvi bilan beriladi (to'g'ridan `MEDIA_URL` emas).
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(vositalar): AV kartochkasi`

---

### Task 12: Bo'limlar sahifasi

**Files:**
- Create: `vositalar/templates/vositalar/{bolimlar,_bolim_daraxt}.html`, `vositalar/tests/test_bolimlar.py`
- Modify: `vositalar/views.py`, `vositalar/urls.py`

**Interfaces:**
- Produces: `bolim_nofaol_qil(bolim: Bolim, kim: User) -> None` (ichida yoki pastki bo'limlarida taqsimot bo'lsa → `AmalXato`);
  URL nomlari `vositalar:bolimlar`, `vositalar:bolim_saqla`, `vositalar:bolim_nofaol`.

- [ ] **Step 1:** Failing testlar: `test_daraxt_qoshish_va_nomlash`, `test_ichida_av_bolsa_nofaol_bolmaydi`,
  `test_ota_boshqa_filialdan_rad`, `test_bolim_av_royxati_soni_bilan`, `test_hr_bolim_tahrirlolmaydi`.
- [ ] **Step 2:** `pytest vositalar/tests/test_bolimlar.py -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(vositalar): bo'limlar`

---

### Task 13: МОЛ nazorati sahifalari (HR)

**Files:**
- Create: `mol/{views,urls}.py`, `mol/templates/mol/{xodimlar,xodim,ketganlar,akt_yangi,akt}.html`, `mol/tests/test_views.py`

**Interfaces:**
- Consumes: `akt_yarat`, `akt_tasdiqla`, `akt_pdf` (Task 9), `BAYROQLAR["ketgan_xodimda"]` (Task 8).
- Produces: URL nomlari `mol:xodimlar`, `mol:xodim`, `mol:ketganlar`, `mol:akt_yangi`, `mol:akt`, `mol:akt_tasdiqla`, `mol:akt_pdf`.

- [ ] **Step 1:** Failing testlar:
  - `test_xodimlar_soni_va_qiymati` — har xodimda AV soni (Σ taqsimot.soni) va qiymat (Σ soni × dona_narxi)
  - `test_ketganlar_royxati`
  - `test_akt_yangi_faqat_topshiruvchi_qatorlari` — formada boshqa xodim qatorlari yo'q
  - `test_akt_oqimi` — yaratish → tasdiqlash → МОЛ o'zgargan → PDF 200 `application/pdf`
  - `test_akt_pdf_filial_cheklovi` — boshqa filial AV'si bor akt PDF → 404 (Review Focus 5)
  - `test_rahbar_akt_yaratolmaydi` — 403; `test_hr_akt_yaratadi` — 200
- [ ] **Step 2:** `pytest mol/tests/test_views.py -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(mol): МОЛ nazorati sahifalari`

---

### Task 14: QR-yorliqlar

**Files:**
- Create: `yorliqlar/{servis,views,urls}.py`, `yorliqlar/templates/yorliqlar/{tanlash,yorliq_pdf}.html`, `yorliqlar/tests/test_servis.py`

**Interfaces:**
- Consumes: `AV.kalit` (Task 8), `Sozlama` (Task 4).
- Produces:
  - `qisqa_nom(nomi: str, olcham: str) -> list[str]` — ko'pi bilan 2 qator; `40x30` → qatorda 22 belgi, `58x40` → 30 belgi; sig'masa oxiri `…`
  - `yorliq_pdf(elementlar: list[tuple[AV, int]], olcham: str) -> bytes` — har nusxa alohida sahifa, sahifa o'lchami aynan mm
  - `chop_etildi(avlar: list[AV], kim: User) -> None` — `yorliq_kaliti = av.kalit`, `yorliq_sana = now()`, jurnal
  - URL: `yorliqlar:tanlash` (manba: tanlangan AV'lar / bo'lim / bayroq `yorliq_yoq`|`yorliq_almashtirish`), `yorliqlar:pdf`

- [ ] **Step 1:** Failing testlar:
  - `test_qr_matni` — QR'dan dekod qilingan matn (`pyzbar` yoki `zxing-cpp`) `== "DS|07|125"`
  - `test_kalitsiz_av_rad` — inv bo'sh AV → `ValueError`, PDF yaratilmaydi
  - `test_nusxalar_soni` — (guruh AV, 20) → PDF'da 20 sahifa
  - `test_sahifa_olchami` — `40x30` → sahifa 113.39×85.04 pt (±0.5)
  - `test_qisqa_nom_uzun_nom` — 80 belgili nom → 2 qator, oxiri `…`
  - `test_chop_etildi_kalitni_yozadi` — keyin `yorliq_almashtirish` bayrog'ida yo'q
  - `test_yorliq_pdf_filial_cheklovi` — boshqa filial AV id'si bilan so'rov → 404 (Review Focus 5)
  - `test_hr_yorliq_403`
- [ ] **Step 2:** `pytest yorliqlar -q` → FAIL.
- [ ] **Step 3:** Yoz (segno → SVG, WeasyPrint `@page { size: 40mm 30mm; margin: 0 }`).
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(yorliqlar): QR-yorliqlar`

---

### Task 15: Tozalash ro'yxatlari va hisobotlar

**Files:**
- Create: `hisobotlar/{servis,views,urls}.py`, `hisobotlar/templates/hisobotlar/{tozalash,kesim,mol_qaydnoma,muddat}.html`, `hisobotlar/tests/test_servis.py`

**Interfaces:**
- Consumes: `BAYROQLAR`, `hisobla`, `dona_narxi`, `jadval_xlsx`.
- Produces:
  - `kesim(user, guruh: Literal["filial", "bolim", "tur"], bugun: date) -> list[dict]` — har qator `{nomi, soni, boshlangich, qoldiq}`; bo'lim kesimida taqsimlanmagan → «Bo'limsiz»
  - `mol_qaydnoma(user, xodim: Xodim | None = None) -> list[dict]` — `{xodim, av, inv, bolim, holat, soni, qiymat}`
  - `muddat(user, bugun: date) -> tuple[list[AV], list[AV]]` — (tugagan, 6 oyda tugaydigan)
  - Har sahifada `?format=xlsx` → Excel; URL nomlari `hisobotlar:tozalash`, `hisobotlar:kesim`, `hisobotlar:mol_qaydnoma`, `hisobotlar:muddat`

- [ ] **Step 1:** Failing testlar:
  - `test_kesim_filial_jamilari` — qiymatlar Task 8 formulasiga mos, guruh AV 20 tadan 12+8 bo'lim kesimida ikki qatorga bo'linadi va summasi 1C summasiga teng
  - `test_mol_qaydnoma_qiymat` — qator qiymati = soni × dona_narxi
  - `test_muddat_chegaralari` — tugash sanasi bugun → tugagan; bugun + 6 oy → 6 oylikda; +6 oy +1 kun → yo'q
  - `test_tozalash_faqat_1c_bayroqlari` — `inv_bosh`, `inv_takror`, `filial_rekvizit_bosh`, `mos_emas`
  - `test_hisobot_excel_filial_cheklovi` (Review Focus 5)
- [ ] **Step 2:** `pytest hisobotlar -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(hisobotlar): tozalash ro'yxatlari va hisobotlar`

---

### Task 16: Sozlamalar (administrator)

**Files:**
- Create: `panel/templates/panel/sozlamalar/{foydalanuvchilar,av_turlari,ulanish,jurnal}.html`, `panel/tests/test_sozlamalar.py`
- Modify: `panel/views.py`, `panel/urls.py`

**Interfaces:**
- Consumes: `sinxronla`, `SinxronBand`, `OneCClient.settingsdan` (Task 3, 5), `AVTuriSozlama` (Task 4).
- Produces: URL nomlari `panel:foydalanuvchilar`, `panel:av_turlari`, `panel:umumiy`, `panel:ulanish`, `panel:hozir_sinxronla`, `panel:sinxron_jurnal`, `panel:jurnal`.

- [ ] **Step 1:** Failing testlar:
  - `test_foydalanuvchi_yaratish_rol_filial`
  - `test_umumiy_sozlama` — kompaniya nomi va yorliq o'lchami saqlanadi; `"50x50"` → xato
  - `test_av_turi_maydonlari_saqlash` — noto'g'ri `tip` → xato; `tanlov` uchun bo'sh `tanlov_qiymatlari` → xato
  - `test_hozir_sinxronla` — soxta client bilan POST → jurnalda yangi `ok`; band bo'lsa «Sinxron hozir ishlayapti» xabari
  - `test_ulanish_sahifasi_parolni_korsatmaydi` — sahifa matnida `ONEC_PAROL` qiymati yo'q
  - `test_jurnal_filtrlari` — kim/obyekt/sana bo'yicha
  - `test_hisobchi_sozlamalarga_403`
- [ ] **Step 2:** `pytest panel/tests/test_sozlamalar.py -q` → FAIL.
- [ ] **Step 3:** Yoz.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `feat(panel): sozlamalar`

---

### Task 17: Ishga tushirish (VM), zaxira va jonli sinov

**Files:**
- Create: `deploy/{av-gunicorn.service,av-sinxron.service,av-sinxron.timer,av-sinxron-toliq.service,av-sinxron-toliq.timer,nginx-av.conf,backup.sh,av-backup.timer,av-backup.service}`,
  `docs/ishga-tushirish.md`, `onec/tests/test_jonli.py`

**Interfaces:**
- Consumes: hamma oldingi tasklar.

- [ ] **Step 1:** systemd: `av-sinxron.timer` `OnCalendar=*:0/5`, `av-sinxron-toliq.timer` `OnCalendar=*-*-* 03:00:00`
  (`--toliq`), `av-backup.timer` `OnCalendar=*-*-* 02:30:00`. `backup.sh`: `pg_dump -Fc` + `media/` tar →
  `/var/backups/av/YYYY-MM-DD.*`, 14 kundan eskisini o'chiradi. nginx: `/static/` to'g'ridan, qolgani gunicorn'ga,
  `client_max_body_size 16m`. Tekshiruv: `systemd-analyze verify deploy/*.service deploy/*.timer` → xatosiz.
- [ ] **Step 2:** `onec/tests/test_jonli.py` — `@pytest.mark.jonli` (standart o'tkazib yuboriladi): `.env` dagi TestClaude'ga
  haqiqiy `sinxronla()` → natija `ok`, AV soni > 0, har (AV, filial) uchun `farq == 0` yoki `mos_emas` bayrog'ida.
  Ishga tushirish: `pytest -m jonli -q` → PASS.
- [ ] **Step 3:** `docs/ishga-tushirish.md`: VM (Ubuntu 24.04) o'rnatish, `.env`, migratsiya, birinchi administrator
  (`createsuperuser` + Profil `admin`), timerlarni yoqish, zaxiradan tiklash, doms2021'ga o'tish tartibi (spec §12: `.dt`
  zaxira → .cfe → texnik foydalanuvchi → `.env`), VPS/online 1C'ga o'tishdan oldingi UUID tekshiruvi (spec §6.4:
  20 AV + 5 xodim).
- [ ] **Step 4:** Qabul qilish ro'yxati (hujjat oxirida, har rol uchun 3–5 ssenariy) va to'liq `pytest -q` → PASS.
- [ ] **Step 5:** Commit: `chore: ishga tushirish, zaxira va jonli sinov`
