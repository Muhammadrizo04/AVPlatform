# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Bir kompaniyaning (~22 filial) ichki xodimlari, asosan **ofis kompyuterida, katta ekranda** ishlaydi; telefon kamdan-kam
(masalan, omborda tekshirish). Interfeys tili — o'zbek (lotin); 1C atamalari (МОЛ, ПоступлениеОС va h.k.) asl holida qoladi.

- **Hisobchi** — asosiy foydalanuvchi, kun bo'yi 1C bilan ishlaydi. Vazifasi: AV taqsimoti (bo'lim, holat), 1C chiqimlarini
  tasdiqlash, tozalash ro'yxatlari, hisobotlar, QR-yorliqlar.
- **HR** — kim qaysi AV'ni ushlab turibdi: МОЛ biriktirish, topshirish-qabul aktlari, ketgan xodimlardagi AV'lar. Pulni ko'rmaydi.
- **Rahbar** — holatni kuzatadi (soni, qiymat, hisobotlar), hech narsani o'zgartirmaydi; 1C chiqimlarini ko'rmaydi.
- **Admin** — foydalanuvchilar, sozlamalar, 1C ulanishi.
- **Revizor** — 2-bosqichda (reviziya, telefon ilovasi); 1-bosqichda panelga kirmaydi.

## Product Purpose

1C «КСБ» dagi asosiy vositalar (AV) ma'lumotining **faqat o'qiladigan** nusxasi ustiga 1C'da yo'q narsalarni qo'shadi:
AV qaysi bo'limda, qaysi МОЛda, qanday holatda turgani (soni bo'yicha taqsimot), МОЛ aktlari, rasmlar, amortizatsiya,
QR-yorliqlar, 1C ma'lumotlarini tozalash ro'yxatlari va hisobotlar. Muvaffaqiyat: har bir dona AV'ning joyi va javobgari
ma'lum, taqsimot 1C qoldig'i bilan mos, 1C'dagi xatolar ko'rinib turadi va tuzatiladi.

## Positioning

1C bilan raqobatlashmaydi va unga hech narsa yozmaydi: 1C — buxgalteriya manbai, platforma — jismoniy hisob qatlami.
Ikkalasining farqi va mosligi (taqsimot = 1C qoldig'i, «1C bilan mos / farq») mahsulotning markaziy g'oyasi.

## Operating Context

- 1C'dan sinxron har 5 daqiqada, kechasi to'liq; aloqa uzilsa banner chiqadi.
- Filiallararo o'tkazish 1C'da (Реализация + Поступление), platformada «1C chiqimlari» orqali tasdiqlanadi.
- МОЛ o'zgarishi faqat topshirish-qabul akti orqali (qoralama → tasdiqlangan / bekor qilingan), PDF chop etiladi.
- QR-yorliqlar printerda chop etiladi; hisobotlar Excel'ga yuklanadi va chop etiladi.
- Hajm: ~2 400 AV yozuvi, ~4 200 dona, ~470 xodim, 22 filial; ko'p AV guruh (bitta yozuv × N dona).

## Capabilities and Constraints

- Django 5.2 shablonlari + HTMX, CoreUI 5 (Bootstrap 5) asosida; Node/CDN'siz, statik fayllar loyihada.
- Huquqlar server tomonida, rol va filial bo'yicha (`hisoblar/huquqlar.py`); pul (`pul_korish`) HR'dan yashirin.
- 1C'dan kelgan maydonlar (nomi, inv. raqam, filial, soni, summa) panelda tahrirlanmaydi.
- Ichki tarmoqda ishlaydi (keyinroq VPS + HTTPS); internet bo'lmasligi mumkin — tashqi shrift/CDN'ga tayanmaslik kerak.

## Brand Commitments

Kompaniya nomi ko'rinsin (Sozlamalar → Umumiy → «Kompaniya nomi»); majburiy logotip yoki rang yo'q.

Vizual ko'rinish bo'yicha foydalanuvchi qarori (2026-10-22): minimal/quruq uslub rad etildi; panel **rangli, jonli dashboard**
bo'lishi kerak — sifat darajasi bo'yicha Stripe Dashboard va monday.com yonida tura oladigan (rangli holat belgilari,
grafiklar, KPI kartochkalari).

## Evidence on Hand

Haqiqiy ma'lumot lokal bazada (1C sinxroni). Anonimlashtirilgan namunalar: `onec/tests/namunalar/`.
Mijoz fikrlari, statistikalar yoki tashqi da'volar yo'q — o'ylab topilmasin.

## Product Principles

1. **Tezlik va zichlik birinchi.** Hisobchilar 1C'ga o'rgangan: bir ekranda ko'p ma'lumot, kam bosish, tez filtr va klaviatura.
2. **«Qayerda, kimda, qanday holatda» — har ekranning birinchi javobi.** Pul va 1C rekvizitlari ikkinchi qatorda.
3. **1C va platforma chegarasi ko'rinib tursin.** O'qiladigan 1C ma'lumoti va platformaning o'z ma'lumoti farqlanadi.
4. **Har rol o'z ishini ko'radi.** Kirish ekrani — rolning ish navbati; ko'ra olmaydigan yoki qila olmaydigan narsasi chiqmaydi.
5. **Xatoni yashirmaslik.** Mos kelmaslik, bo'sh maydon, hisoblanmagan qiymat — aniq va nima qilish kerakligi bilan.
