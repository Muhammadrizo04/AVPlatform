---
version: 1
slug: "panel-templates-panel-base-html"
primary_target: "panel/templates/panel/base.html"
related_targets: ["vositalar/templates/vositalar/kartochka.html","panel/templates/panel/bosh.html"]
---

# Surface brief: Asosiy vositalar paneli (barcha ichki sahifalar)

Scope: Django panel shell (`panel/templates/panel/base.html`, `panel/static/panel/panel.css`) va undagi barcha sahifalar; asosiy namunalar — bosh sahifa (dashboard) va AV kartochkasi. Mode: operate. Build path: code-led.

Auditoriya va vazifa: hisobchi (asosiy), HR, rahbar, admin — ofis kompyuteri, katta ekran, tezlik va zichlik. Asosiy vazifa: AV qayerda, kimda, qanday holatda; 1C bilan mosligi; nima ish kutayapti.

Cheklovlar: CoreUI 5 komponentlari ichkarida qoladi (mavzu tokenlar orqali); tashqi CDN/shrift yo'q; grafiklar kutubxonasiz (HTML/CSS); HTMX bo'laklari va testlardagi belgilar saqlanadi.

Tarix: 1-tur «Shveytsariya jadval maktabi» qurildi; foydalanuvchi uni «juda quruq/zerikarli» deb rad etdi va o'zi yo'nalishni belgiladi: «Rangli dashboard (Stripe, Monday)», tuzilma ham o'zgarishi mumkin. Foydalanuvchi belgilagan yo'nalish rolldan ustun.

## Direction contract

THESIS: Panel — jonli boshqaruv paneli: har sahifa rangli holat belgilari va ko'rsatkichlar bilan «nima yaxshi, nima ish kutayapti» ni bir qarashda aytadi; bosh sahifa jadval emas, grafiklar va vazifalar navbati. Rad etadigan standart: kulrang, rangsiz, faqat jadvaldan iborat admin paneli.

OWN-WORLD: Stripe Dashboard aniqligi + monday.com rangli holatlari. Fon #f6f8fb, sirt #ffffff, siyoh #0a2540, ikkilamchi #5b6b82, chiziq #e3e8ef. Asosiy urg'u — indigo #635bff (tugmalar, faol menyu, havolalar). Menyu ustuni to'q navi #0a2540, har bo'lim o'z rangli ikonkasi bilan: vositalar #2a78d6, МОЛ #6250d6, chiqimlar #eb6834, hisobotlar #1baf7a. Holat belgilari — monday uslubida to'liq rangli yumaloq «pill»lar: ishlatilmoqda #1baf7a, zaxirada #eda100, ta'mirda #2a78d6, nosoz #eb6834, hisobdan chiqarishga #6250d6, topilmadi #e34948 (tasdiqlangan palitra, yorliq doim matn bilan). Kartochkalar 12px radius, yumshoq ikki qatlamli soya; bosh sahifa tepasida indigo→ko'k gradient band. Shrift: Segoe UI / tizim sans, tabular raqamlar.

STORY: Kirgan foydalanuvchi bosh sahifada salomlashuv, asosiy ko'rsatkichlar (AV soni, qiymat yoki МОЛ'siz), filiallar va holatlar grafiklari, rangli «bajarilishi kerak» ro'yxatini ko'radi va bitta bosishda ishga o'tadi. AV kartochkasida rangli holat va 1C bilan moslik kartochkalari.

FIRST VIEWPORT: Chapda 240px navi menyu (rangli ikonkalar, faol band indigo pill). Tepada oq 56px header (sahifa yo'li, sinxron holati yashil/qizil nuqta bilan, foydalanuvchi avatar-doirasi). Bosh sahifa: indigo→ko'k gradient band ichida «Xayrli kun, {ism}» va 4 ta oq KPI kartochkasi bandni pastga oshib turadi; ostida 7/5 to'r: chapda «Filiallar bo'yicha» gorizontal bar grafik, o'ngda «Holatlar» rangli bar grafik; pastda «Bajarilishi kerak» ro'yxati rangli pill sonlar bilan va filiallar jadvali.

FORM: Foydalanuvchi belgilagan yo'nalish: «Rangli dashboard (Stripe, Monday)» — rolldan ustun (pinned). 1-turdan saqlanganlar: solishtirish qatori (1C | Platforma | Farq), joylashuv tuzilmasi. Roll ishlatilmadi: yo'nalishni foydalanuvchi o'zi belgiladi (2026-10-22, savolga javob: «Rangli dashboard (Stripe, Monday)», «Tuzilma ham o'zgarsin»).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
