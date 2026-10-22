---
name: Asosiy vositalar
description: Holat ranglari va ko'rsatkichlar bilan "nima yaxshi, nima ish kutayapti"ni bir qarashda aytadigan rangli AV boshqaruv paneli
colors:
  indigo: "#635bff"
  indigo-to: "#5146e0"
  indigo-och: "#efeefe"
  siyoh: "#0a2540"
  fon: "#f6f8fb"
  sirt: "#ffffff"
  ikkilamchi: "#5b6b82"
  xira: "#626f84"
  chiziq: "#e3e8ef"
  chiziq-och: "#eef2f7"
  maydon-chiziq: "#d5dce6"
  menyu-matn: "#c9d3e1"
  menyu-bolim: "#7f93ad"
  qizil: "#df1b41"
  qizil-to: "#b3093a"
  qizil-och: "#fde8ec"
  yashil: "#0e9f6e"
  yashil-to: "#087251"
  yashil-och: "#e3f6ee"
  sariq-to: "#8a5a00"
  sariq-och: "#fff4d6"
  r-vosita: "#2a78d6"
  r-mol: "#6250d6"
  r-chiqim: "#eb6834"
  r-hisobot: "#1baf7a"
  r-tizim: "#8792a2"
  h-ishlatilmoqda: "#1baf7a"
  h-zaxirada: "#eda100"
  h-tamirda: "#2a78d6"
  h-nosoz: "#eb6834"
  h-hisobdan: "#6250d6"
  h-topilmadi: "#e34948"
  hp-ishlatilmoqda: "#0b7a54"
  hp-zaxirada-matn: "#3d2a00"
  hp-tamirda: "#1d5fae"
  hp-nosoz: "#b8461a"
  hp-hisobdan: "#5141c0"
  hp-topilmadi: "#c0302f"
typography:
  display:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.02em"
  metric:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.02em"
    fontFeature: "\"tnum\""
  kpi:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.02em"
    fontFeature: "\"tnum\""
  figure:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
    fontFeature: "\"tnum\""
  headline:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
  title:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: ".9375rem"
    fontWeight: 700
  body:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: ".875rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "\"tnum\""
  body-dense:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: ".8125rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "\"tnum\""
  small:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: ".75rem"
    fontWeight: 600
  label:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, \"Helvetica Neue\", Arial, sans-serif"
    fontSize: ".6875rem"
    fontWeight: 700
    letterSpacing: ".06em"
rounded:
  sm: "6px"
  control: "8px"
  md: "10px"
  card: "12px"
  media: "14px"
  pill: "999px"
spacing:
  xs: ".25rem"
  sm: ".5rem"
  md: ".75rem"
  row: ".875rem"
  lg: "1rem"
  xl: "1.25rem"
  2xl: "1.75rem"
  3xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.indigo}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".5rem 1rem"
    typography: "{typography.body-dense}"
  button-primary-hover:
    backgroundColor: "{colors.indigo-to}"
    textColor: "{colors.sirt}"
  button-outline:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.siyoh}"
    rounded: "{rounded.control}"
    padding: ".5rem 1rem"
  button-outline-hover:
    backgroundColor: "{colors.fon}"
    textColor: "{colors.indigo}"
  button-danger:
    backgroundColor: "{colors.qizil}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".5rem 1rem"
  button-ghost:
    textColor: "{colors.indigo}"
  button-ghost-hover:
    backgroundColor: "{colors.indigo-och}"
    textColor: "{colors.indigo-to}"
  button-sm:
    padding: ".3rem .75rem"
    rounded: "{rounded.sm}"
  input:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.siyoh}"
    rounded: "{rounded.control}"
    typography: "{typography.body-dense}"
  card:
    backgroundColor: "{colors.sirt}"
    rounded: "{rounded.card}"
  card-header:
    typography: "{typography.title}"
    padding: ".875rem 1.25rem"
  kpi-card:
    backgroundColor: "{colors.sirt}"
    rounded: "{rounded.card}"
    padding: "1.125rem 1.25rem"
    typography: "{typography.kpi}"
  kpi-icon:
    textColor: "{colors.sirt}"
    rounded: "{rounded.md}"
    size: "2.5rem"
  indicator-tile:
    backgroundColor: "{colors.sirt}"
    rounded: "{rounded.card}"
    padding: ".75rem 1rem"
    typography: "{typography.figure}"
  indicator-tile-zero-icon:
    backgroundColor: "{colors.chiziq-och}"
    textColor: "{colors.xira}"
  holat-pill-ishlatilmoqda:
    backgroundColor: "{colors.hp-ishlatilmoqda}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
    typography: "{typography.small}"
  holat-pill-zaxirada:
    backgroundColor: "{colors.h-zaxirada}"
    textColor: "{colors.hp-zaxirada-matn}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
  holat-pill-tamirda:
    backgroundColor: "{colors.hp-tamirda}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
  holat-pill-nosoz:
    backgroundColor: "{colors.hp-nosoz}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
  holat-pill-hisobdan:
    backgroundColor: "{colors.hp-hisobdan}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
  holat-pill-topilmadi:
    backgroundColor: "{colors.hp-topilmadi}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
    padding: ".25rem .7rem"
  holat-pill-nol:
    backgroundColor: "{colors.chiziq-och}"
    textColor: "{colors.ikkilamchi}"
    rounded: "{rounded.pill}"
  chart-track:
    backgroundColor: "{colors.chiziq-och}"
    height: "12px"
  badge-success:
    backgroundColor: "{colors.yashil-och}"
    textColor: "{colors.yashil-to}"
    rounded: "{rounded.pill}"
    padding: ".3rem .6rem"
  badge-warning:
    backgroundColor: "{colors.sariq-och}"
    textColor: "{colors.sariq-to}"
    rounded: "{rounded.pill}"
  badge-danger:
    backgroundColor: "{colors.qizil}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.pill}"
  badge-neytral:
    backgroundColor: "{colors.chiziq-och}"
    textColor: "{colors.ikkilamchi}"
    rounded: "{rounded.pill}"
  sidebar:
    backgroundColor: "{colors.siyoh}"
    textColor: "{colors.menyu-matn}"
    width: "240px"
  sidebar-link-active:
    backgroundColor: "{colors.indigo}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".5rem .75rem"
  topbar:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.ikkilamchi}"
    height: "3.5rem"
    padding: "0 2rem"
  sync-chip:
    backgroundColor: "{colors.yashil-och}"
    textColor: "{colors.yashil-to}"
    rounded: "{rounded.pill}"
    padding: ".3rem .75rem"
  comparison-card:
    backgroundColor: "{colors.sirt}"
    rounded: "{rounded.card}"
    padding: "1rem 1.25rem"
    typography: "{typography.metric}"
  action-strip:
    backgroundColor: "{colors.qizil-och}"
    textColor: "{colors.qizil-to}"
    rounded: "{rounded.card}"
    padding: ".75rem 1.25rem"
---

# Design System: Asosiy vositalar

## Overview

**Creative North Star: "Rangli boshqaruv paneli"** (Stripe aniqligi + monday holatlari)

Panel jonli boshqaruv paneli: har sahifa rangli holat belgilari va ko'rsatkichlar bilan "nima yaxshi, nima ish kutayapti"ni bir qarashda aytadi. Asos — Stripe Dashboard'ning sokin, aniq qatlami: och kulrang-ko'k fon, oq kartochkalar, to'q navi siyoh matn, yumshoq ikki qatlamli soya, bitta indigo urg'u. Uning ustiga monday.com'ning rang tili qo'yilgan: har AV holati o'z to'liq rangli "pill"ida, har bo'lim menyuda va ko'rsatkichlarda o'z rangida.

Zichlik ofis kompyuteri va katta ekran uchun: tana matni 14px, jadval va grafik matni 13px, tabular raqamlar hamma joyda. Bosh sahifa jadval emas: indigo→ko'k gradient band, uni pastdan oshib turgan oq KPI kartochkalari, kutubxonasiz CSS bar grafiklar va rangli "Bajarilishi kerak" navbati. Ichki sahifalar ko'rsatkich plitalari (indicator tiles) bilan boshlanadi, keyin jadval.

Foydalanuvchi rad etgan: rangsiz, kulrang, faqat jadvaldan iborat "quruq" admin paneli (oldingi "Shveytsariya jadval maktabi" dunyosi).

**Key Characteristics:**
- Indigo (#635bff) yagona interaktiv urg'u: asosiy tugma, faol menyu, havola, fokus.
- Olti holat rangi va to'rt bo'lim rangi ma'lumot tashiydi; ular doim matn yoki son bilan birga.
- Qizil faqat "harakat kerak" uchun.
- Oq kartochkalar, 12px radius, yumshoq navi soyalar; pill va nuqtalar to'liq yumaloq.
- Grafiklar faqat HTML/CSS (kutubxonasiz, oflayn), har bar to'g'ridan-to'g'ri son bilan yorliqlangan.

## Colors

Sokin Stripe neytrallari ustida bitta indigo urg'u va validatordan o'tgan olti tusli holat palitrasi.

### Primary
- **Stripe indigo** (indigo): asosiy tugma, faol menyu bandi (indigo pill + indigo soya), havolalar, faol tab chizig'i, belgilangan checkbox, fokus konturi, grafik qatori hover'idagi nom. Hover/bosilgan holat **To'q indigo** (indigo-to). **Indigo och** (indigo-och): ghost tugma hover foni, Inv. raqam belgisi, ma'lumot (info) xabarlari.

### Secondary: holat palitrasi
Olti holat rangi shu tartibda: **ishlatilmoqda** (h-ishlatilmoqda, yashil), **zaxirada** (h-zaxirada, sariq), **ta'mirda** (h-tamirda, ko'k), **nosoz** (h-nosoz, to'q sariq), **hisobdan chiqarishga** (h-hisobdan, binafsha), **topilmadi** (h-topilmadi, qizil). Bu tartib dataviz palitra validatoridan qo'shni juftlar bo'yicha o'tgan: rang ko'rish nuqsoni (CVD) simulyatsiyasida eng kichik ΔE 9.1, oddiy ko'rishda 22.9. Bu tuslar bar grafiklar, yig'ma holat chizig'i va nol-holat nuqtalarida ishlatiladi.

Oq matnli pill fonlari uchun shu tuslarning chuqurroq variantlari: **hp-ishlatilmoqda**, **hp-tamirda**, **hp-nosoz**, **hp-hisobdan**, **hp-topilmadi** (har biri oq matn bilan ≥4.5:1). Zaxirada sariq fonda qoladi, matni to'q jigarrang (hp-zaxirada-matn).

### Tertiary: bo'lim ranglari
- **Vositalar** (r-vosita), **МОЛ** (r-mol), **Chiqimlar** (r-chiqim), **Hisobotlar** (r-hisobot), **Tizim** (r-tizim): menyu ikonkalari (navi fonda yorqinroq tuslarda), KPI va ko'rsatkich ikonkalarining gradient kvadratlari, vazifa nuqtalari, tarix nuqtalari. Bo'lim ranglari holat palitrasi bilan bir xil tuslardan olingan, shuning uchun panelda yangi tus qo'shilmaydi.

### Semantik
- **Signal qizil** (qizil), matni **To'q qizil** (qizil-to), foni **Qizil och** (qizil-och): 1C bilan farq, МОЛ'siz qatorlar, ketgan xodimda AV, kutilayotgan chiqim soni, xato, sinxron uzilish banneri, xavfli tugma.
- **Yashil** (yashil, yashil-to, yashil-och): sinxron muvaffaqiyatli chipi, "mos" belgisi, Farq=0, muvaffaqiyat xabari.
- **Sariq och** (sariq-och, sariq-to): ogohlantirish belgisi va xabari.

### Neutral
- **Navi siyoh** (siyoh): asosiy matn va menyu ustuni foni.
- **Fon** (fon): sahifa foni, outline tugma hover foni.
- **Sirt** (sirt): kartochkalar, header (92% shaffof + blur), jadvallar.
- **Ikkilamchi** (ikkilamchi): yorliqlar, ikkilamchi matn, neytral belgi matni. **Xira** (xira): izohlar, sana, jadval ustun sarlavhasi, nol qiymatlar.
- **Chiziq** (chiziq): kartochka ramkasi, header osti. **Och chiziq** (chiziq-och): ichki ajratgichlar, grafik izi, neytral pill/belgi foni. **Maydon chizig'i** (maydon-chiziq): input ramkasi.
- Menyu ichida: **Menyu matni** (menyu-matn), **Menyu bo'lim nomi** (menyu-bolim).

### Named Rules
**The Qizil = Harakat Rule.** Qizil faqat foydalanuvchi bajarishi kerak bo'lgan ish uchun (farq, МОЛ'siz, kutilayotgan chiqim, xato, uzilish). Holat palitrasidagi "topilmadi" qizili ham shu ma'noni tashiydi; qizilni bezak yoki kategoriya sifatida ishlatmang.

**The Rang Doim Matn Bilan Rule.** Holat yoki bo'lim rangi hech qachon yolg'iz ma'no tashimaydi: pill ichida nom, bar yonida nom va son, nuqta yonida matn.

**The Chuqur Pill Rule.** Oq matnli pill fonida grafik tusi emas, uning chuqur `hp-*` varianti turadi (≥4.5:1). Yangi holat qo'shilsa, unga ham shunday juft (grafik tusi + pill tusi) beriladi.

**The Nol Neytral Rule.** Qiymati nol bo'lgan narsa rangni yo'qotadi: nol holat pill'i neytral fon (chiziq-och) + ikkilamchi matn + holat rangidagi kichik nuqta; nol ko'rsatkich plitasining ikonkasi kulrang (chiziq-och fon, xira ikonka); nol vazifa nuqtasi kulrang, soni neytral. Rang faqat bor narsaga beriladi.

## Typography

**Display Font:** "Segoe UI" (system-ui, -apple-system, "Helvetica Neue", Arial zaxirasi bilan)
**Body Font:** xuddi shu stek (`--av-shrift`)

**Character:** Bitta neytral sans, ierarxiya o'lcham va qalinlik (400/500/600/700) bilan; katta raqam va sarlavhalarda -.02em. Raqamlar body darajasida tabular. Tashqi shrift yuklanmaydi (ichki tarmoq, CDN yo'q).

### Hierarchy
- **Display** (700, 1.75rem, 1.2, -.02em): sahifa h1, band salomlashuvi; mobil (<576px) 1.375rem. AV kartochkasi sarlavhasi 1.5rem (mobil 1.25rem).
- **Metric** (700, 1.875rem, -.02em): solishtirish kartochkalaridagi raqamlar; mobil 1.375rem.
- **KPI** (700, 1.625rem, -.02em): bosh sahifa KPI qiymati.
- **Figure** (700, 1.25rem): ko'rsatkich plitasi soni, mobil taqsimot kartasidagi son.
- **Headline** (700, 1rem): h2 bo'lim sarlavhasi.
- **Title** (700, .9375rem): kartochka sarlavhasi, h3, "harakat kerak" matni, brend nomi.
- **Body** (400, .875rem, 1.5): umumiy matn, menyu bandlari (500, faol 600).
- **Body dense** (.8125rem): jadval, grafik, tugma (600), maydon, header, ro'yxatlar.
- **Small** (600, .75rem): KPI/ko'rsatkich yorliqlari, pill matni, belgilar, forma yorliqlari, izohlar (izohlar 400).
- **Label** (700, .6875rem, .06em, UPPERCASE): faqat jadval ustun sarlavhalari; menyu bo'lim nomlari .08em.

### Named Rules
**The Tabular Rule.** Har son tabular va ustunda o'ngga tekislangan (`.son`); grafik qiymatlari ham o'ngda, 700.

**The Yorliq Rule.** Bosh harfli kichik yorliq faqat o'zi nomlagan ustun yoki menyu guruhi ustida turadi; sarlavha ustidagi "kicker" sifatida ishlatilmaydi.

## Layout

Qobiq: chapda 240px navi menyu ustuni (≥992px doimiy, kichikda ochiladigan), tepada yopishqoq 56px (3.5rem) oq header (92% shaffof, blur): menyu tugmasi (<992px), sahifa yo'li, sinxron chipi (<576px yashirin), avatar doirasi + ism/rol (<992px faqat avatar) + "Chiqish". Sahifa: `max-width: 1400px`, padding 1.75rem 2rem 3rem; <992px da 1.25rem 1rem 2rem.

Bosh sahifa: gradient band sahifa paddingini yopib to'liq kenglikda (pastki padding 5.5rem), KPI qatori -4rem bilan bandga chiqib turadi: 4 ustun, <1200px da 2, <576px da 1, oraliq 1rem. Ostida 7/5 to'r (`col-xl-7` / `col-xl-5`, 1.5rem oraliq): chapda filiallar bar grafigi, o'ngda holatlar grafigi va "Bajarilishi kerak"; pastda to'liq kenglikdagi filiallar jadvali.

Ichki sahifalar: ko'rsatkich plitalari to'ri (`auto-fit, minmax(12rem, 1fr)`, .75rem oraliq), keyin filtr qatori va jadval kartochkasi. AV kartochkasi: sarlavha kartochkasi (rasm 4.5rem, nom, identifikator pill'lari, amallar o'ngda) → solishtirish to'ri (3 × 1fr + 1.4fr izoh; <992px da izoh pastga; <576px da kichikroq padding) → "harakat kerak" chizig'i (agar bor) → 8/4 to'r. <576px da taqsimot jadvali kartaga aylanadi (son o'ngda, 1.25rem), tarix qatorlari ikki qatorga bo'linadi.

Ritm: .25 / .5 / .75 / .875 / 1 / 1.25 / 1.75 / 2rem. Kartochka ichki gorizontal paddingi doim 1.25rem. Breakpointlar CoreUI'niki: 576, 992, 1200px.

## Elevation & Depth

Gibrid: fon/sirt farqi + yumshoq navi soyalar. Har oq yuza 1px chiziq ramkasi va past soyaga ega; ko'tarilgan elementlar (KPI kartochkalari, hover'dagi plitalar) kattaroq soyada. Soyalar navi tusli (rgba(10, 37, 64, …)), qora emas. Rangli soyalar faqat indigo/yashil to'ldirilgan elementlar ostida (asosiy tugma, faol menyu bandi, faol nav-pill).

### Shadow Vocabulary
- **Soya** (`0 1px 2px rgba(10,37,64,.06), 0 4px 14px rgba(10,37,64,.06)`): kartochka, ro'yxat guruhi, ko'rsatkich plitasi, solishtirish kartochkasi.
- **Soya katta** (`0 2px 4px rgba(10,37,64,.06), 0 12px 32px rgba(10,37,64,.12)`): KPI kartochkasi; plita hover'i.
- **KPI hover** (`0 4px 8px rgba(10,37,64,.08), 0 16px 36px rgba(10,37,64,.14)`) + `translateY(-2px)`.
- **Indigo yog'du** (`0 1px 2px rgba(99,91,255,.25), 0 2px 8px rgba(99,91,255,.2)`): asosiy tugma; faol menyu `0 4px 12px rgba(99,91,255,.35)`.
- **Fokus halqasi** (`0 0 0 3px rgba(99,91,255,.18)`): input/select fokusi; boshqa elementlarda `outline: 2px solid` indigo, offset 2px.

### Named Rules
**The Navi Soya Rule.** Soya doim yumshoq, ko'p qatlamli va navi tusli; qattiq ofset soya yo'q. Ko'tarilish faqat bosiladigan kartochkalarda hover javobi sifatida.

## Shapes

Yumshoq, do'stona geometriya. Kartochka, plita, ro'yxat guruhi, "harakat kerak" chizig'i — 12px; ikonka kvadratlari va vazifa qatorlari — 10px; tugma va maydon — 8px (kichigi 6–7px); AV rasmi — 14px. Holat pill'lari, belgilar, sinxron chipi, nav-pills, identifikator bo'laklari — to'liq yumaloq (999px). Avatar, holat nuqtalari, vazifa nuqtalari, tarix nuqtalari — doira. Bar grafik izi va bari faqat o'ng tomondan 4px yumaloq (chap tomon o'q chizig'iga tegib turadi); yig'ma holat chizig'i 7px, segmentlar orasi 2px.

Gradientlar faqat uch joyda: bosh sahifa bandi (indigo→ko'k radial, pastki o'ngda yashil yog'du), brend logotipi/avatar/AV rasmi o'rni (indigo→ko'k), KPI va ko'rsatkich ikonka kvadratlari (bo'lim rangining och→to'q 135° gradienti).

## Components

### Buttons
- **Shape:** 8px, 600, .8125rem, padding .5rem 1rem; kichigi .3rem .75rem, .75rem, 7px.
- **Primary:** indigo fon, oq matn, indigo yog'du; hover to'q indigo, active #4338ca.
- **Outline (secondary):** oq fon, chiziq ramka, siyoh matn, juda past soya; hover fon rangi, indigo matn, #c9c6ff ramka.
- **Success:** yashil to'ldirilgan, yashil yog'du (tasdiqlash amallari).
- **Danger:** qizil to'ldirilgan, hover #c0123a; outline varianti qizil matn va #f8b9c6 ramka, hover'da to'ladi.
- **Ghost / link:** fonsiz indigo matn, hover'da indigo-och fon; xavfli varianti qizil, hover qizil-och.

### Holat pill'lari (imzo komponenti)
- **Style:** to'liq yumaloq, .25rem .7rem, .75rem 600, oq matn chuqur `hp-*` fonda; zaxirada sariq fonda to'q jigarrang matn. Bir nechta holat bo'lsa ichida son (700, 85% shaffoflik).
- **Nol holat:** neytral fon, ikkilamchi matn 500, oldida holat rangidagi .5rem nuqta.
- Jadval, AV ro'yxati, kartochka, aktlar, qaydnoma — holat ko'rsatiladigan hamma joyda bir xil.

### Bar grafiklar (CSS, kutubxonasiz)
- Uch ustunli qator: nom (8–13rem, ixchamida 10.5rem, mobil 6.5rem) | 12px iz (och chiziq) | qiymat (700, o'ngda, ≥4.5rem). Har bar doim to'g'ridan-to'g'ri son bilan yorliqlangan; legend yo'q.
- Filial bari bo'lim (vositalar) rangida; holat bari o'z holat tusida, nomi holat pill'i. Qator butunlay havola: hover'da bar 12% yorqinlashadi, nom indigoga o'tadi.
- Nol qiymatli qatorda bar yashiriladi, son xira 500, pill neytral (yuqoridagi Nol Neytral qoidasi).
- Holatlar kartochkasi tepasida 14px yig'ma ulush chizig'i (faqat noldan katta holatlar, segmentlar orasi 2px, `role="img"` + aria-label).
- Kirish animatsiyasi: bar chapdan `scaleX(0)`dan o'sadi, .7s `cubic-bezier(.16,1,.3,1)`, qatorlar .04s qadam bilan (≤.2s). `prefers-reduced-motion: reduce` da barcha animatsiya va o'tishlar o'chadi.

### KPI kartochkalari
- Oq, 12px, soya katta, 1px och ramka, padding 1.125rem 1.25rem; chapda 2.5rem gradient ikonka kvadrati (10px), o'ngda yorliq (small, ikkilamchi) → KPI qiymat → izoh (.75rem xira; ogohlantirishda to'q qizil 600). Butun kartochka havola; hover'da 2px ko'tariladi. To'plam rolga bog'liq: pul huquqi bor rolda qiymat, aks holda МОЛ'siz soni ko'rsatiladi.

### Ko'rsatkich plitalari (indicator strip)
- Oq, 12px, 1px chiziq ramka, soya; .75rem 1rem; 2.25rem gradient ikonka + Figure son + small yorliq. Havola; hover'da 1px ko'tarilib soya katta.
- **Ogoh:** son to'q qizil. **Nol:** ikonka kvadrati neytral (och chiziq fon, xira ikonka).

### Bajarilishi kerak ro'yxati
- Har band 10px yumaloq havola qatori: .625rem nuqta | nom | son pill'i. Faol bandda nuqta bo'lim rangida, atrofida 4px 18% halqa; son pill'i #fff1ea fonda #b3420f matn. Nol band: nuqta kulrang, matn xira, son neytral.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** sirt, fon ustida.
- **Shadow Strategy:** Soya (Elevation bo'limi).
- **Border:** 1px chiziq; sarlavha ostida 1px och chiziq.
- **Internal Padding:** sarlavha .875rem 1.25rem (Title, o'ngda small xira izoh), tana 1.25rem gorizontal. Ma'lumot ro'yxati: .7rem 1.25rem qatorlar, yorliq chapda ikkilamchi 500, qiymat o'ngda 600; platforma qiymati to'q indigo.

### Solishtirish kartochkalari (1C | Platforma | Farq)
- Uch oq kartochka + izoh kartochkasi; har birining tepasida 3px rang chizig'i: 1C xira, Platforma indigo, Farq yashil (farq bo'lsa qizil). Small yorliq + Metric raqam; Platforma raqami indigo, farqda qizil. Raqam yonidagi pill: yashil-och/yashil-to "mos", farqda qizil-och/to'q qizil.
- **Harakat kerak chizig'i:** qizil-och→#fff7f0 gorizontal gradient, #f8c6d1 ramka, 12px; chapda 1.5rem qizil doira ichida ogohlantirish ikonkasi va to'q qizil Title matni, o'ngda kichik danger tugma.

### Tables
- Shaffof fon, qator padding .7rem .875rem (chetlari 1.25rem), ichki ajratgich och chiziq, oxirgi qator chiziqsiz, hover #f8f9fd. Ustun sarlavhasi Label uslubida xira, #fafbfd fon. Jami qatori #fafbfd, 700, ustida 1px chiziq.

### Inputs / Fields
- **Style:** oq, maydon-chiziq ramka, 8px, .8125rem, juda past soya; kichigi .78rem, min-height 2rem, 7px. Yorliq small 600 ikkilamchi.
- **Focus:** ramka indigo + 3px indigo halqa (18%).
- **Checkbox:** #b6c2d1 ramka, belgilanganda indigo.

### Badges va belgilar
- To'liq yumaloq, 600, .72rem, .3rem .6rem; och fon + to'q matn (success, warning, primary, neytral). Danger to'ldirilgan qizil oq matn bilan (menyuda #ff4d6d). AV ro'yxatidagi meta-belgilar: och chiziq fonli pill, xira ikonka; ogohlantirish varianti qizil-och/to'q qizil 700.

### Alerts
- 10px, 1px ramka, .8125rem: xato qizil-och/#9b0b33 600; ogohlantirish sariq-och/#6e4700; muvaffaqiyat yashil-och/#075f44; ma'lumot indigo-och/#3730a3. Sinxron uzilishi banneri — to'liq qizil, oq 600 matn.

### Navigation
- **Menyu ustuni:** navi siyoh, 240px; brend bloki (2.25rem indigo→ko'k gradient logotip, nom 700, kompaniya nomi). Bandlar 8px yumaloq, .5rem .75rem, .875rem 500, menyu-matn; ikonkalar bo'lim rangining yorqin tusida. Hover: 7% oq fon, oq matn. Faol: indigo pill, oq matn va ikonka, 600, indigo yog'du. Guruh nomlari .6875rem 700 bosh harfli, menyu-bolim rangida. Kutilayotgan chiqimlar soni o'ng chetda qizil badge.
- **Header:** sahifa yo'li 600 siyoh (ota havolasi ikkilamchi 500); sinxron chipi yashil-och pill, ichida 8px yashil nuqta 3px halqa bilan; avatar 2rem indigo→ko'k gradient doira, bosh harf.
- **Tablar:** pastki 2px indigo chiziq faol tabda; nav-pills oq pill'lar, faoli indigo + yog'du.

### Tarix ro'yxati
- To'rli qatorlar: .5rem rangli nuqta | sana (8rem, xira) | matn | summa (600, o'ngda) | kim (xira). Nuqta rangi voqea turiga ko'ra: 1C va qayta baholash xira, МОЛ akti r-mol, ko'chirish r-vosita, holat o'zgarishi h-nosoz, qolganlari indigo.

## Do's and Don'ts

### Do:
- **Do** qizilni faqat foydalanuvchi bajarishi kerak bo'lgan ishga bering (farq, МОЛ'siz, kutilayotgan chiqim, xato, sinxron uzilishi).
- **Do** holatni har joyda holat pill'i bilan ko'rsating; oq matnli pill fonida chuqur `--av-hp-*` tusini, grafikda `--av-h-*` tusini ishlating.
- **Do** olti holat tusini validatordan o'tgan tartibda saqlang: ishlatilmoqda, zaxirada, ta'mirda, nosoz, hisobdan chiqarishga, topilmadi.
- **Do** har barni to'g'ridan-to'g'ri son bilan yorliqlang; grafiklarni HTML/CSS bilan quring.
- **Do** nol qiymatni neytrallashtiring: nol pill neytral fon + rangli nuqta, nol plita ikonkasi kulrang, nol bar yashirin.
- **Do** har animatsiya va o'tishni `prefers-reduced-motion: reduce` ostida o'chiring.
- **Do** yangi CoreUI komponentlarini panel.css'dagi `--av-*` va `--cui-*` tokenlari orqali moslashtiring.
- **Do** bosiladigan kartochka va plitalarni butunlay havola qiling, hover'da ko'taring.

### Don't:
- **Don't** holat yoki bo'lim rangini matnsiz, yolg'iz ma'no tashuvchi sifatida ishlatmang.
- **Don't** oq matnni grafik tusidagi (`--av-h-*`) och fon ustiga qo'ymang.
- **Don't** chart kutubxonasi, tashqi shrift yoki CDN ulamang; panel oflayn ishlaydi.
- **Don't** palitraga yangi tus qo'shmang; yangi bo'lim yoki holat mavjud tuslardan va ularning chuqur juftidan foydalanadi.
- **Don't** qattiq ofset yoki qora soya ishlatmang; soya navi tusli va yumshoq.
- **Don't** bosh harfli kichik yorliqni sarlavha ustidagi kicker sifatida ishlatmang.
- **Don't** holatlarni rangsiz matn yoki kulrang belgi bilan ko'rsatmang; rangsiz, faqat jadvaldan iborat admin paneli rad etilgan dunyo.
