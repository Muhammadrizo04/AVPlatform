---
name: Asosiy vositalar
description: 1C qoldig'i va platforma taqsimotini qat'iy to'rda solishtiradigan ichki AV paneli
colors:
  siyoh: "#121417"
  fon: "#f4f5f7"
  sirt: "#ffffff"
  chiziq: "#d9dce1"
  chiziq-och: "#eceef1"
  ikkilamchi: "#5b616b"
  qizil: "#d6281c"
  qizil-och: "#fbeceb"
  qizil-chegara: "#f1b8b3"
  qizil-hover: "#b11f15"
  kok: "#2f5d8a"
  kok-och: "#eaf0f6"
  siyoh-hover: "#2b2f35"
  maydon-chiziq: "#c3c7cd"
  sokin-kulrang: "#8a9099"
  menyu-matn: "#d5d8dc"
  menyu-ikkilamchi: "#9aa0a8"
  menyu-hover: "#23272d"
  menyu-chiziq: "#2a2e34"
typography:
  display:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-.02em"
  metric:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-.02em"
    fontFeature: "\"tnum\""
  figure:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    letterSpacing: "-.01em"
    fontFeature: "\"tnum\""
  title:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: ".9375rem"
    fontWeight: 700
  body:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: ".8125rem"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "\"tnum\""
  small:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: ".75rem"
    fontWeight: 400
  label:
    fontFamily: "\"Helvetica Neue\", Arial, \"Segoe UI\", system-ui, sans-serif"
    fontSize: ".6875rem"
    fontWeight: 600
    letterSpacing: ".08em"
rounded:
  none: "0"
  control: "2px"
spacing:
  xs: ".25rem"
  sm: ".5rem"
  row: ".5625rem"
  md: ".75rem"
  lg: "1rem"
  xl: "1.25rem"
  2xl: "1.5rem"
  3xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.siyoh}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".4375rem 1rem"
    typography: "{typography.body}"
  button-primary-hover:
    backgroundColor: "{colors.siyoh-hover}"
    textColor: "{colors.sirt}"
  button-secondary:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.siyoh}"
    rounded: "{rounded.control}"
    padding: ".4375rem 1rem"
  button-secondary-hover:
    backgroundColor: "{colors.siyoh}"
    textColor: "{colors.sirt}"
  button-danger:
    backgroundColor: "{colors.qizil}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".4375rem 1rem"
  button-danger-hover:
    backgroundColor: "{colors.qizil-hover}"
  button-sm:
    padding: ".25rem .75rem"
  button-text:
    textColor: "{colors.siyoh}"
  button-text-hover:
    textColor: "{colors.kok}"
  input:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.siyoh}"
    rounded: "{rounded.control}"
    typography: "{typography.body}"
  card:
    backgroundColor: "{colors.sirt}"
    rounded: "{rounded.none}"
  card-header:
    typography: "{typography.title}"
    padding: ".625rem 1rem"
  table-head:
    textColor: "{colors.ikkilamchi}"
    typography: "{typography.label}"
    padding: ".5625rem .75rem"
  badge-danger:
    backgroundColor: "{colors.qizil}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
    padding: ".25rem .45rem"
  badge-warning:
    backgroundColor: "{colors.qizil-och}"
    textColor: "{colors.qizil}"
    rounded: "{rounded.control}"
  badge-platforma:
    backgroundColor: "{colors.kok}"
    textColor: "{colors.sirt}"
    rounded: "{rounded.control}"
  badge-neytral:
    backgroundColor: "{colors.chiziq-och}"
    textColor: "{colors.ikkilamchi}"
    rounded: "{rounded.control}"
  sidebar:
    backgroundColor: "{colors.siyoh}"
    textColor: "{colors.menyu-matn}"
    width: "220px"
  sidebar-link-hover:
    backgroundColor: "{colors.menyu-hover}"
    textColor: "{colors.sirt}"
  sidebar-link-active:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.siyoh}"
  topbar:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.ikkilamchi}"
    height: "2.5rem"
    padding: "0 2rem"
  comparison-cell:
    backgroundColor: "{colors.sirt}"
    typography: "{typography.metric}"
    padding: ".875rem 1.25rem"
  action-strip:
    backgroundColor: "{colors.sirt}"
    textColor: "{colors.qizil}"
    padding: ".5rem 1.25rem"
---

# Design System: Asosiy vositalar

## Overview

**Creative North Star: "Shveytsariya jadval maktabi"**

Panel xalqaro tipografik uslubdagi ma'lumot varag'i kabi qurilgan: har raqam qat'iy to'rda turadi, ustunlar siljimaydi, bloklar soya bilan emas, aniq 1px chiziqlar bilan ajraladi. Butun sahifa siyoh va kulrangda; rang faqat ma'no tashiydi. Qizil — "bu yerda ish bor", ko'k — "bu platformaning o'z ma'lumoti yoki havola". 1C'dan kelgan qolgan hamma narsa neytral, faqat o'qish uchun.

Zichlik — ofis kompyuteri va katta ekran uchun: asosiy matn 13px, jadval qatori 9px vertikal padding, kichik bosh harfli yorliqlar. Ierarxiya o'lcham va qalinlik bilan, sarlavha ostidagi siyoh chiziq bilan quriladi; bezak, gradient, illyustratsiya yo'q. Imzo elementi — AV kartochkasidagi solishtirish qatori: "1C qoldig'i | Platforma taqsimoti | Farq" katta tabular raqamlarda yonma-yon, farq bo'lsa qizil.

Rad etilgan standart: qorong'i menyu + soyali, yumaloq oq kartochkalar + binafsha urg'uli umumiy admin paneli. Menyu ustuni qora bo'lib qoladi, lekin u siyohning o'zi (#121417), urg'u rangi emas, faol band esa oq fonli teskari blok.

**Key Characteristics:**
- Siyoh, kulrang va oq; qizil va ko'k faqat ma'no uchun.
- 1px chiziqlar standart; 2px faqat yopuvchi va ogohlantiruvchi chiziq uchun.
- Soya yo'q, gradient yo'q, radius 0 (bloklar) yoki 2px (boshqaruv elementlari).
- Tabular raqamlar hamma joyda; sonlar ustunda o'ngga tekislangan.
- Grotesk shrift, qalinlik 400/600/700, katta sarlavhalarda manfiy harf oralig'i.

## Colors

Neytral siyoh-kulrang tizim, ikki semantik urg'u bilan: signal qizil va sokin dengiz ko'ki.

### Primary
- **Siyoh** (siyoh): matn, asosiy tugmalar foni, menyu ustuni, sarlavha ostidagi chiziqlar, jami qatori ustidagi chiziq. Asosiy harakat rangli emas, siyoh bilan belgilanadi; hover'da **Siyoh hover** (siyoh-hover), bosilganda #000.

### Secondary
- **Signal qizil** (qizil): faqat "harakat kerak": 1C bilan farq, МОЛ'siz qatorlar, kutilayotgan 1C chiqimlari, xato xabarlari, faol bayroq sonlari, sinxron uzilish banneri, xavfli tugmalar. Hover **To'q qizil** (qizil-hover). Och fon **Qizil och** (qizil-och) va chegara **Qizil chegara** (qizil-chegara) faqat ogohlantirish belgisida.

### Tertiary
- **Dengiz ko'ki** (kok): platformada saqlanadigan va o'zgartiriladigan qiymatlar (bo'lim, МОЛ havolasi, holat), havolalar, "Platforma taqsimoti" raqami, sinxron indikatori kvadrati, fokus konturi. **Ko'k och** (kok-och): tanlash foni, fokus halqasi, faol bo'lim qatori.

### Neutral
- **Fon** (fon): sahifa foni, jadval hover va jami qatori, amal paneli foni.
- **Sirt** (sirt): kartochkalar, jadvallar, yo'l satri, solishtirish qatori.
- **Chiziq** (chiziq): kartochka ramkasi, jadval sarlavhasi osti, bloklar orasidagi 1px chiziq.
- **Och chiziq** (chiziq-och): jadval va ro'yxat qatorlari orasidagi ichki chiziq, rasm o'rni foni, neytral belgi foni.
- **Ikkilamchi** (ikkilamchi): yorliqlar, sana, izoh, ikkilamchi matn.
- **Maydon chizig'i** (maydon-chiziq): input/select ramkasi. **Sokin kulrang** (sokin-kulrang): o'chirilgan tugma, menyu bo'lim nomi, checkbox ramkasi.
- Menyu ichki tuslari: **Menyu matni** (menyu-matn), **Menyu ikkilamchi** (menyu-ikkilamchi), **Menyu hover** (menyu-hover), **Menyu chizig'i** (menyu-chiziq) — faqat qora menyu ustuni ichida.

### Named Rules
**The Bitta Rang, Bitta Ma'no Rule.** Qizil faqat foydalanuvchi bajarishi kerak bo'lgan ish uchun; ko'k faqat platforma ma'lumoti va havola uchun. Hech qaysi biri bezak, kategoriya rangi yoki "muvaffaqiyat" belgisi bo'lmaydi: "mos" holati siyohda ko'rsatiladi (success tokenlari siyoh/kulrangga yo'naltirilgan).

**The Siyoh Harakat Rule.** Asosiy tugma siyoh to'ldirilgan, ikkinchi darajali tugma siyoh chiziqli oq. Qizil to'ldirilgan tugma faqat qizil ogohlantirish qatori ichidagi tuzatish harakati yoki xavfli amal uchun.

## Typography

**Display Font:** "Helvetica Neue" (Arial, "Segoe UI", system-ui, sans-serif zaxirasi bilan)
**Body Font:** xuddi shu grotesk stek (`--av-shrift`)

**Character:** Bitta neytral grotesk, butun ierarxiya o'lcham, qalinlik va harf oralig'i bilan quriladi. Tashqi shrift yuklanmaydi (ichki tarmoq); raqamlar hamma joyda tabular (`font-variant-numeric: tabular-nums` body darajasida).

### Hierarchy
- **Display** (700, 2rem, 1.1, -.02em): sahifa sarlavhasi (h1), AV nomi; mobil (<576px) 1.5rem.
- **Metric** (700, 2rem, 1.15, -.02em): solishtirish qatoridagi uchta raqam; mobil 1.5rem.
- **Figure** (700, 1.25rem, -.01em): bayroq ro'yxatidagi sonlar, Inv. raqam; mobil taqsimot kartasidagi son.
- **Title** (700, .9375rem): h2 bo'lim sarlavhasi, kartochka sarlavhasi, ogohlantirish qatori matni. h3 — 700, .875rem.
- **Body** (400, .8125rem, 1.45): barcha matn, jadval kataklari, tugmalar (600), maydonlar, menyu bandlari.
- **Small** (.75rem): yo'l satri, izohlar, matnli belgilar, footer, kichik tugmalar.
- **Label** (600, .6875rem, .08em, UPPERCASE): jadval ustun sarlavhalari, forma yorliqlari, solishtirish yorliqlari, amal paneli yorliqlari, menyu bo'lim nomlari.

### Named Rules
**The Tabular Rule.** Har bir son tabular raqamda va ustunda o'ngga tekislangan (`.son`); raqamlar ustunlar bo'ylab siljimaydi.

**The Yorliq Rule.** 11px bosh harfli yorliq faqat o'zi nomlagan qiymat yoki ustunning ustida turadi (ustun sarlavhasi, maydon yorlig'i, metrika nomi). U sarlavha ustidagi "kicker" sifatida ishlatilmaydi.

## Layout

Qobiq: chapda 220px qora menyu ustuni (≥992px doimiy, undan kichikda yopiladigan), tepada yopishqoq 40px (2.5rem) oq yo'l satri — breadcrumb chapda, sinxron vaqti o'ngda (<576px yashiriladi). Sahifa maydoni `max-width: 1360px`, padding 1.5rem 2rem 2.5rem; <992px da 1rem 1rem 2rem.

AV kartochkasi: sarlavha bloki (rasm o'rni 4rem kvadrat, nom, identifikator qatori vertikal 1px ajratgichlar bilan, amallar o'ngda) 2px siyoh chiziq bilan yopiladi; ostida to'liq kenglikdagi solishtirish qatori (3 metrika + izoh, ≥1200px da metrika ustunlari pastdagi 8/4 to'rning chap ustuniga tekislanadi); keyin 8/4 to'r (`col-xl-8` / `col-xl-4`, 1.5rem oraliq). <992px da izoh solishtirish qatorining ostiga tushadi; <576px da taqsimot jadvali kartaga aylanadi (son o'ngda, 1.25rem).

Bosh sahifa bayroqlari: chiziqli ro'yxat, 3 / 2 / 1 ustun (≥992 / ≥576 / <576), ustunlar orasi 2rem; yorliq chapda, son o'ngda.

Ritm: .25 / .5 / .75 / 1 / 1.25 / 1.5 / 2rem; jadval va ma'lumot qatorlari .5625rem vertikal padding. Breakpointlar CoreUI'niki: 576, 992, 1200px.

**The Ustun Siljimaydi Rule.** Sonli ustunlar o'ngga, matn chapga; ustun sarlavhalari `nowrap`. Mobil qayta joylashuvda ham son o'z ustunida qoladi.

## Elevation & Depth

Tizim butunlay tekis. Barcha CoreUI soya tokenlari `none` ga tenglangan; chuqurlik fon/sirt farqi (fon ustida oq sirt) va 1px chiziqlar bilan beriladi. `box-shadow` faqat ikki joyda chiziq vazifasini bajaradi: maydon fokus halqasi (`0 0 0 2px` ko'k och) va ogohlantirish belgisining ichki 1px chegarasi.

**The Soyasiz Rule.** Ko'tarilish soyasi, gradient yoki blur yo'q. Blokni ajratish kerak bo'lsa — 1px chiziq yoki fon/sirt almashinuvi.

## Shapes

To'g'ri burchakli dunyo. Kartochkalar, ogohlantirishlar, ro'yxat guruhlari, tablar, menyu bandlari, checkbox — radius 0. Tugmalar, maydonlar, belgilar, pills — 2px. Pill shakli ham 2px ga majburlangan.

Chiziq ierarxiyasi: ichki qator ajratgichi 1px och chiziq; blok ramkasi va jadval sarlavhasi osti 1px chiziq; sarlavha, kartochka sarlavhasi va jami qatori 1px siyoh; AV sarlavhasini yopish, ogohlantirish (alert) ustki chizig'i va "harakat kerak" qatori — 2px. Kichik nuqta belgilari (sinxron 6px ko'k, ogohlantirish 8px qizil) — kvadrat.

**The 2px Rule.** Radius hech qachon 2px dan oshmaydi; chiziq qalinligi 2px faqat blokni yopish yoki ogohlantirish uchun.

## Components

### Buttons
- **Shape:** deyarli to'g'ri burchak (2px), 600 qalinlik, .8125rem.
- **Primary:** siyoh fon, oq matn, padding .4375rem 1rem; hover siyoh-hover, active #000; o'chirilgan sokin-kulrang. `btn-success` ham shu ko'rinishda.
- **Secondary:** oq fon, siyoh 1px ramka va matn; hover'da siyoh bilan to'ladi.
- **Danger:** qizil to'ldirilgan, hover qizil-hover; chiziqli varianti qizil ramka.
- **Text (link / ghost):** fonsiz, tagiga chizilgan (offset 3px); siyoh, hover ko'k; xavfli varianti qizil. Jadval ichidagi qator amallari shu ko'rinishda.
- **Small:** .25rem .75rem, .75rem.
- **Focus:** global `outline: 2px solid` ko'k, offset 2px.

### Chips (matnli belgilar)
- **Style:** ramkasiz, fonsiz matn yorliqlari (.75rem, ikkilamchi), kichik ikonka bilan; qator bo'ylab .25rem 1rem oraliq.
- **State:** holat — ko'k 600; ogohlantirish (МОЛ'siz) — qizil 700; havola — ko'k, tagsiz.

### Badges
- 2px radius, 700, .6875rem, .04em. Qizil to'ldirilgan (menyudagi kutilayotgan chiqimlar soni), qizil och + 1px chegara (ogohlantirish), siyoh (bajarildi), ko'k (platforma), och kulrang (neytral).

### Cards / Containers
- **Corner Style:** 0.
- **Background:** sirt; sahifa fonida turadi.
- **Shadow Strategy:** yo'q (Elevation bo'limiga qarang).
- **Border:** 1px chiziq; sarlavha ostida 1px siyoh.
- **Internal Padding:** sarlavha .625rem 1rem, ma'lumot qatorlari .5625rem 1rem. Ichidagi ma'lumot ro'yxati: yorliq chapda ikkilamchi 400, qiymat o'ngda 600. Yig'iladigan kartochka sarlavhasi o'ngda "ochish/yopish" matnli havolasi bilan.

### Tables
- Sirt fon, qatorlar orasi 1px och chiziq, oxirgi qator chiziqsiz; hover fon. Ustun sarlavhasi — Label uslubi. Jami qatori: fon, 700, ustida 1px siyoh. Katak padding .5625rem .75rem.

### Inputs / Fields
- **Style:** oq, 1px maydon-chiziq ramka, 2px radius, .8125rem; kichigi .75rem, min-height 1.875rem. Yorliq — Label uslubi, ostida .25rem.
- **Focus:** ramka siyohga o'tadi + 2px ko'k och halqa.
- **Checkbox:** kvadrat, sokin-kulrang ramka; belgilanganda siyoh.

### Alerts
- Oq sirt, radius 0, faqat ustki 2px chiziq: xato va ogohlantirish — qizil chiziq va qizil matn; ma'lumot va muvaffaqiyat — siyoh chiziq va siyoh matn. Sinxron uzilishi banneri — to'liq qizil fon, oq 600 matn.

### Navigation
- **Menyu ustuni:** siyoh fon, 220px, bandlar .5rem 1.25rem, .8125rem, menyu-matn rangida, radius 0. Hover: menyu-hover fon, oq matn. Faol: oq fon, siyoh matn, 700 — teskari blok. Bo'lim nomlari Label uslubida sokin-kulrang. Pastda foydalanuvchi va tagiga chizilgan "Chiqish".
- **Yo'l satri:** oq, 40px, ostida 1px chiziq, .75rem; joriy sahifa nomi siyohda 500.
- **Tablar:** radius 0, faol tab siyoh ramka va 700.

### Solishtirish qatori (imzo komponenti)
To'liq kenglikdagi oq qator: uchta metrika katagi (Label yorlig'i + Metric raqam) va izoh katagi, kataklar orasida 1px vertikal chiziq, ostida 1px chiziq. "Platforma taqsimoti" raqami ko'k; farq bo'lsa "Farq" raqami qizil va yonida "mos emas" (.8125rem 600), aks holda siyoh "0 mos". МОЛ'siz dona bo'lsa ostida **harakat kerak** qatori: oq fon, 2px qizil pastki chiziq, 8px qizil kvadrat bilan boshlanuvchi qizil Title matni va o'ngda kichik qizil tugma.

### Bayroq ro'yxati
Chiziqli ro'yxat, kartochkasiz: har band 1px chiziq bilan ajratilgan, nom chapda (body), son o'ngda (Figure). Soni bor — son qizil; nol — butun qator ikkilamchi, son 400.

### Tarix ro'yxati
To'rli qatorlar: sana (8.5rem, ikkilamchi) | matn | summa (o'ngda) | kim (ikkilamchi); 1px och ajratgich. 8 tadan keyingilari "Yana N ta voqeani ko'rsatish" yig'ilmasida.

## Do's and Don'ts

### Do:
- **Do** qizilni faqat foydalanuvchi bajarishi kerak bo'lgan ishga bering (farq, МОЛ'siz, kutilayotgan chiqim, xato).
- **Do** platformada saqlanadigan qiymatlarni (bo'lim, МОЛ, holat) va havolalarni ko'kda ko'rsating; 1C'dan kelganini siyoh yoki kulrangda qoldiring.
- **Do** har bir sonni tabular va o'ngga tekislangan ustunda bering (`.son`).
- **Do** bo'lim sarlavhasi va kartochka sarlavhasi ostiga 1px siyoh chiziq qo'ying.
- **Do** asosiy harakatni siyoh to'ldirilgan tugma bilan, ikkinchisini siyoh chiziqli tugma bilan bering.
- **Do** yangi CoreUI komponentlarini panel.css'dagi `--av-*` va `--cui-*` tokenlari orqali moslashtiring, ularni klassdan tashqarida qayta bo'yamang.

### Don't:
- **Don't** ko'tarilish soyasi, gradient yoki blur ishlatmang; `box-shadow` faqat fokus halqasi yoki 1px chegara sifatida.
- **Don't** 2px dan katta radius, pill yoki doira shaklli konteyner qo'ymang.
- **Don't** qizil yoki ko'kni bezak, kategoriya yoki "muvaffaqiyat" belgisi sifatida ishlatmang; "mos" holati siyohda.
- **Don't** yashil, sariq yoki binafsha urg'u qo'shmang; CoreUI'ning standart warning/success/info ranglariga tayanmang.
- **Don't** 11px bosh harfli yorliqni sarlavha ustidagi kicker sifatida ishlatmang; u faqat qiymat yoki ustunni nomlaydi.
- **Don't** tashqi shrift yoki CDN ulamang; fayllar loyiha ichida.
