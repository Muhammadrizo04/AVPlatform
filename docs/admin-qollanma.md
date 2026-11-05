# Asosiy vositalar platformasi — administrator qo'llanmasi

Manzil: <https://av.dsyuksak.uz:8092/> · Qo'llanma administrator roli uchun yozilgan, lekin har bo'limda boshqa rollar
nimani ko'rishi ham aytilgan.

## 1. Platforma nima uchun kerak

1C «КСБ» buxgalteriya hisobini yuritadi: AV (asosiy vosita) qaysi filialda, nechta dona va qancha turadi. Lekin 1C
quyidagilarga javob bermaydi: AV aynan qaysi xonada turibdi, kim javob beradi, ishlayaptimi yoki buzilganmi, oxirgi
marta kim sanagan. Platforma shu bo'shliqni to'ldiradi.

Uchta asosiy qoida bor. Ularni tushunsangiz, qolgan hamma narsa tushunarli bo'ladi.

| Qoida | Ma'nosi |
|---|---|
| **1C — manba** | Nomi, inv. raqami, filiali, soni va summasi 1C'dan keladi. Ular platformada tahrirlanmaydi. Xato bo'lsa, 1C'da tuzatiladi. |
| **Platforma 1C'ga yozmaydi** | Platforma 1C ma'lumotini faqat o'qiydi. Platformada nima qilsangiz ham, 1C o'zgarmaydi. |
| **Taqsimot = 1C qoldig'i** | AV'ning filialdagi donalari bo'limlar va javobgarlar bo'yicha taqsimlanadi. Taqsimot yig'indisi doim 1C qoldig'iga teng bo'lishi kerak. Farq — e'tibor talab qiladigan muammo. |

### Asosiy atamalar

- **AV** — asosiy vosita: kompyuter, stol, mashina va hokazo.
- **Filial** — 1C'dagi filial. Ro'yxati 1C'dan keladi.
- **Bo'lim** — filial ichidagi joy: bino, qavat, xona, ombor. Platformada yaratiladi.
- **Javobgar shaxs** — AV uchun javob beradigan xodim (1C'dagi МОЛ). Xodimlar 1C'dan keladi.
- **Taqsimot qatori** — «shu AV'ning N donasi shu bo'limda, shu javobgarda, shu holatda» degan bitta yozuv.
- **Guruh AV** — bitta 1C yozuvi, lekin bir nechta dona (masalan, 20 ta stul).
- **Holat** — Ishlatilmoqda, Zaxirada, Ta'mirda, Nosoz, Hisobdan chiqarishga, Topilmadi.
- **Bayroq** — tizim avtomatik topadigan muammo belgisi (10-bo'lim).

## 2. Rollar va huquqlar

Rol foydalanuvchiga «Sozlamalar → Foydalanuvchilar»da beriladi. Huquq har so'rovda serverda tekshiriladi, ya'ni menyuda
yashirilgan sahifani havola bilan ham ochib bo'lmaydi. Filial cheklovi Excel, PDF va rasmlarga ham amal qiladi.

| Imkoniyat | Admin | Hisobchi | HR | Rahbar | Revizor |
|---|:-:|:-:|:-:|:-:|:-:|
| Bosh sahifa | ✔ | — | ✔ | ✔ | — |
| AV ro'yxati, kartochka, hisobotlar | ✔ | ✔ | ✔ | ✔ | — |
| Summa va qiymatni ko'rish | ✔ | ✔ | — | ✔ | — |
| Taqsimot, bo'limlar, AV tahriri | ✔ | ✔ | — | — | — |
| QR-yorliq chop etish | ✔ | ✔ | — | — | — |
| Topshirish aktlari | ✔ | ✔ | ✔ | — | — |
| 1C chiqimlarini ko'rish | ✔ | ✔ | ✔ | — | — |
| 1C chiqimlarini tasdiqlash | ✔ | ✔ | — | — | — |
| Reviziyani ko'rish | ✔ | ✔ | ✔ | ✔ | ✔ |
| Reviziyani ochish va o'tkazish | ✔ | ✔ | — | — | ✔ |
| 1C ma'lumotlarini tozalash | ✔ | — | — | — | — |
| Sozlamalar, 1C sinxron | ✔ | — | — | — | — |

Hisobchi kirganda bosh sahifa emas, AV ro'yxati ochiladi. Revizor kirganda telefon uchun mo'ljallangan «Mening
reviziyalarim» sahifasi ochiladi.

## 3. Kirish va xavfsizlik

- Login va parol bilan kiriladi. **5 marta noto'g'ri urinishdan keyin** kirish **15 daqiqaga bloklanadi**.
- **8 soat harakatsizlikdan** keyin sessiya tugaydi va qayta kirish kerak bo'ladi.
- Ishni tugatganda o'ng yuqoridagi «Chiqish» tugmasini bosing, ayniqsa umumiy kompyuterda.

Yuqori panelda uchta narsa doim ko'rinadi:

- **Oxirgi muvaffaqiyatli sinxron** — yashil belgi va vaqt. 1C bilan aloqa uzilsa, sahifa tepasida «1C bilan aloqa yo'q»
  ogohlantirishi chiqadi.
- **Qo'ng'iroqcha — Kutayotgan ishlar**: tasdiq kutayotgan 1C chiqimlari, 1C'da bekor qilingan chiqimlar, tasdiq
  kutayotgan aktlar va siz revizor bo'lgan ochiq reviziyalar. Qizil belgi hali o'qilmagan ishlar sonini ko'rsatadi.
- **Foydalanuvchi va rol.**

## 4. Bosh sahifa

**Nima uchun:** bir qarashda butun kompaniyaning holatini ko'rish uchun.

- Yuqorida to'rtta kartochka: AV soni, qoldiq qiymat, javobgar biriktirilmagan qatorlar, tasdiq kutayotgan 1C chiqimlari.
- Grafiklar: filiallar bo'yicha AV soni, filiallar bo'yicha qiymat, holatlar, AV turlari bo'yicha qiymat.
- **«Bajarilishi kerak»** — bayroqlar soni. Birini bossangiz, shu muammodagi AV'lar ro'yxati ochiladi.
- **AV summasi dinamikasi** — filiallar kesimida har oy oxiridagi summa 1C harakatlaridan tiklanadi. Davrni va filiallarni
  tanlash mumkin; 8 tadan ko'p filial tanlansa, kichiklari «Boshqa N ta filial» chizig'iga yig'iladi.
- **Filiallar kesimi** — har filial bo'yicha soni, boshlang'ich va qoldiq qiymat.

Har kuni ertalab shu sahifadan boshlang: «Bajarilishi kerak» bo'sh bo'lishiga intiling.

## 5. AV ro'yxati

**Nima uchun:** kerakli AV'ni topish va bir nechta AV ustida birdaniga ish qilish uchun.

**Qidiruv va filtrlar:** inv. raqami yoki nomi bo'yicha qidiruv, filial, bo'lim, tur, holat, javobgar, bayroq, «Faqat
ko'p donalilar», «Arxivdagilar». Natija yozishingiz bilan yangilanadi. Tepada umumiy ko'rsatkichlar turadi: AV soni,
javobgarsiz va bo'limsiz qatorlar, 1C bilan mos kelmaganlar.

**Excel:** joriy filtr bo'yicha ro'yxat Excel'ga yuklanadi.

**Ommaviy amallar:** qatorlarni belgilasangiz, pastda amallar paneli chiqadi.

- **Bo'limga ko'chirish** va **Holatni o'zgartirish** — faqat 1 donali va bitta taqsimot qatorli AV'lar uchun. Guruh
  AV'larni kartochkadan, soni bilan o'zgartiring.
- **QR-yorliq chop etish** — hamma AV uchun.

**Arxiv:** barcha filiallarda 1C qoldig'i nolga tushgan AV arxivga o'tadi. U faol ro'yxatlardan chiqadi, tarixi saqlanadi.

## 6. AV kartochkasi

**Nima uchun:** bitta AV haqidagi hamma narsa shu yerda: qayerda, kimda, qanday holatda va nima bo'lgan.

- **Sarlavha:** rasm, nom, inv. raqam, tur, filial, bo'lim, javobgar, holat.
- **Uchta ko'rsatkich:** 1C qoldig'i, Platforma taqsimoti, Farq. Farq 0 bo'lsa, «mos» yoziladi.
- **Joylashuv va javobgar:** taqsimot qatorlari. Har qatorda amallar bor:
  - **Ko'chirish** — tanlangan sonni boshqa bo'limga o'tkazadi.
  - **Holat** — tanlangan son uchun holatni o'zgartiradi.
  - **Moslash** — taqsimot 1C qoldig'idan ortiq bo'lganda chiqadi: ortiqchani qaysi qatordan ayirishni tanlaysiz.
- **Javobgar shaxs bu yerda to'g'ridan-to'g'ri o'zgartirilmaydi** — faqat topshirish akti orqali (8-bo'lim).
- **Tarix:** 1C harakatlari, ko'chirishlar, aktlar, reviziya va o'zgarishlar bitta vaqt chizig'ida. Kim, qachon, nima
  qilgani ko'rinadi.
- **Buxgalteriya:** 1C summasi, dona narxi, qoldiq qiymat, eskirish foizi, muddat tugashi.
- **Platforma ma'lumotlari:** ishga tushgan sana, xizmat muddati, izoh va AV turi uchun qo'shimcha maydonlar.
- **Rasmlar:** jpg yoki png, 15 MB gacha. Birini «Asosiy» qilish mumkin.
- **1C rekvizitlari:** 1C'dan kelgan qo'shimcha ma'lumot, faqat o'qish uchun.

**Amortizatsiya** chiziqli hisoblanadi: ishga tushgan sanadan bugungacha to'liq oylar soni xizmat muddatiga bo'linadi.
Sana yoki xizmat muddati kiritilmagan bo'lsa, «hisoblanmadi» deb yoziladi. Muddatni har AV'ga emas, «AV turlari»da bir
marta kiritish qulay (13.2).

## 7. Bo'limlar

**Nima uchun:** filial ichidagi joylarni belgilash uchun. Ular AV'ni joylashtirish va reviziyani xonama-xona o'tkazish
uchun asos bo'ladi.

1. Filialni tanlang.
2. «Yangi bo'lim qo'shish» formasida nom yozing va «Qayerda joylashgan»ni tanlang. Bo'limlar ichma-ich bo'lishi mumkin:
   «Bosh bino / 2-qavat / Buxgalteriya».
3. Bo'limni bossangiz, unda turgan AV'lar ochiladi. Shu yerdan nomini o'zgartirish yoki boshqa joyga ko'chirish mumkin.
4. Kerak bo'lmagan bo'limni nofaol qiling. Ichida AV bo'lsa, nofaol qilib bo'lmaydi.

## 8. Javobgar shaxslar va topshirish aktlari

**Nima uchun:** har dona AV uchun kim javob berishi hujjat bilan belgilanishi kerak. Shu sababli javobgar faqat akt
orqali almashadi.

**Javobgar shaxslar sahifasi:** xodimlar ro'yxati, filiali, holati, AV soni va qiymati. Xodimni bossangiz, undagi AV'lar
ochiladi. **«Ketgan xodimlardagi AV'lar»** — ishdan bo'shagan, nofaol yoki 1C'da topilmagan xodimlarda qolgan AV'lar.
Bu ro'yxat bo'sh bo'lishi kerak.

**Akt oqimi:**

1. «Yangi akt» ni bosing.
2. Topshiruvchini tanlang. Birinchi marta biriktirish uchun «Javobgar shaxsi yo'q qatorlar»ni tanlang.
3. Qatorlarni qidirib belgilang. Guruh AV'da topshiriladigan sonni yozing.
4. Qabul qiluvchini tanlang va **«Qoralama aktni yaratish»** ni bosing. Hozircha hech narsa o'zgarmaydi.
5. Aktni PDF qilib chop eting va imzolating.
6. **«Tasdiqlash»** ni bosing. Faqat shunda javobgar almashadi.

Holatlar: **Qoralama → Tasdiqlangan** yoki **Bekor qilingan**. Tasdiqlangan aktni o'zgartirib bo'lmaydi. Xato bo'lsa,
teskari yo'nalishda yangi akt tuziladi. Tasdiqlashda qabul qiluvchi faol bo'lishi va topshiruvchida kerakli son borligi
tekshiriladi: bitta shart buzilsa, hech narsa o'zgarmaydi.

## 9. 1C chiqimlari

**Nima uchun:** 1C'da AV sotilsa, boshqa filialga o'tkazilsa yoki hisobdan chiqarilsa, platforma buni o'zi qabul qilib
qo'ymaydi. Hisobchi yoki admin tasdiqlamaguncha, donalar joyida turadi. Shunday qilib, hech bir AV hech kim bilmagan
holda yo'qolmaydi.

**Oqim:**

1. Sinxron 1C'dagi chiqim hujjatini olib keladi va u «Kutilmoqda» holatida ro'yxatga tushadi. Tizim turini taxmin qiladi:
   3 kun ichida boshqa filialga kirim bo'lsa — o'tkazish, СписаниеОС bo'lsa — hisobdan chiqarish, qolgan holatda — sotish.
2. Chiqimni oching, turini tekshiring. O'tkazishda qabul qiluvchi filialni tanlang.
3. Har taqsimot qatoridan nechta dona ketganini yozing. Yig'indi hujjatdagi songa teng bo'lishi shart.
4. O'tkazishda ixtiyoriy ravishda yangi bo'lim va holatni tanlash mumkin.
5. Tasdiqlang. Qatorlar kamayadi, hammasi AV tarixiga yoziladi.

**Holatlar:** Kutilmoqda, Tasdiqlangan, 1C'da bekor qilindi, Bekor qilingan.

- Foydalanuvchi chiqimni rad eta olmaydi: chiqim 1C'da bor ekan, uni tasdiqlash kerak. Noto'g'ri bo'lsa, 1C'da tuzating.
- Xato tasdiqlangan bo'lsa, **«Tasdiqni bekor qilish»** donalarni joyiga qaytaradi va chiqim qayta tasdiqlashni kutadi.
- Hujjat tasdiqdan keyin 1C'da bekor qilinsa, u «1C'da bekor qilindi» holatiga o'tadi va **«Tasdiqni qaytarish»** AV'ni
  avvalgi bo'lim va javobgariga qo'yadi.

**Amallar tarixi** — kim, qachon, qaysi chiqim ustida nima qilganini ko'rsatadi.

## 10. Bayroqlar va 1C ma'lumotlarini tozalash

**Nima uchun:** tizim muammolarni o'zi topadi, odam ularni qidirib o'tirmaydi. «1C ma'lumotlarini tozalash» sahifasi
faqat admin uchun: muammolar guruhlab ko'rsatiladi, to'liq ro'yxat Excel'ga yuklanadi va tuzatish uchun hisobchiga beriladi.

| Bayroq | Nimani bildiradi | Qayerda tuzatiladi |
|---|---|---|
| Inv. raqam bo'sh | AV'ga inventar raqam berilmagan | 1C |
| Inv. raqam takror | Bir filialda bir xil raqam | 1C |
| Filial rekviziti bo'sh | AV kartochkasida filial ko'rsatilmagan | 1C |
| Taqsimot 1C bilan mos emas | Taqsimot yig'indisi 1C qoldig'iga teng emas | Platforma, AV kartochkasi |
| 1C chiqimi kutilmoqda | Tasdiqlanmagan chiqim bor | Platforma, 1C chiqimlari |
| Bo'limga joylash kerak | Bo'limsiz taqsimot qatori bor | Platforma, Ko'chirish |
| Javobgarsiz | Javobgarsiz taqsimot qatori bor | Platforma, topshirish akti |
| Ketgan xodimda | Javobgar ishdan ketgan | Platforma, topshirish akti |
| Yorlig'i chop etilmagan | QR-yorliq hali chop etilmagan | Platforma, yorliqlar |
| Yorliqni almashtirish kerak | Inv. raqam yoki filial o'zgargan | Platforma, yorliqlar |
| Xizmat muddati tugagan / 6 oyda tugaydi | Amortizatsiya bo'yicha | Ma'lumot uchun |

## 11. QR-yorliqlar

**Nima uchun:** AV'ga yopishtirilgan QR reviziyada uni bir zumda tanib olishga xizmat qiladi.

1. AV ro'yxatidan tanlang yoki kartochkada «QR-yorliq chop etish»ni bosing. Tayyor ro'yxatlar ham bor: «Yorlig'i chop
   etilmaganlar» va «Yorliqni almashtirish kerak bo'lganlar».
2. Yorliq o'lchamini va nusxalar sonini tekshiring. Guruh AV'da nusxa soni standart bo'yicha donalar soniga teng.
3. «PDF yaratish» ni bosing va chop eting. Har yorliq PDF'ning bitta sahifasi, sahifa tanlangan o'lchamda bo'ladi.

QR ichida `DS|<filial kodi>|<inv raqam>` matni yoziladi. Inv. raqami yoki filiali yo'q AV'ni chop etib bo'lmaydi.
Inv. raqam yoki filial 1C'da o'zgarsa, eski yorliq yaroqsiz bo'ladi va AV «Yorliqni almashtirish kerak» ro'yxatiga tushadi.

## 12. Reviziya (inventarizatsiya)

**Nima uchun:** hujjatdagi ma'lumotni joydagi haqiqat bilan solishtirish uchun. Revizor oddiy telefon brauzerida
xonama-xona yuradi va AV'larni belgilaydi.

**1. Ochish.** «Reviziyalar → Yangi reviziya». Filial, ixtiyoriy bo'lim (ichki bo'limlari bilan), revizorlar, izoh va
komissiyani tanlang. Komissiyaga birinchi qo'shilgan xodim rais bo'ladi. Ochilgan paytda kutilgan AV'lar «surati»
olinadi. Bir joyda qamrovi kesishgan ikkinchi ochiq reviziya ochilmaydi. Revizor ro'yxatda bo'lishi uchun foydalanuvchiga
«Revizor» rolini bering.

**2. Sanash (telefonda).** Revizor reviziyani ochib, xonani tanlaydi va QR'ni kamera bilan o'qiydi yoki inv. raqam / nom
bo'yicha qidiradi. Qayta skan qilinsa, soni bittaga oshadi. Kamera faqat HTTPS'da ishlaydi. Bir xonada kutilganlar
hammasi joyida bo'lsa, tez belgilash mumkin: har AV kutilgan holati bilan belgilanadi, «Topilmadi» holatidagilar esa faqat
skanerlab belgilanadi. Xona tugagach, «xona tugadi» belgilanadi. Revizor javobgarsiz AV'ni xodimga
biriktirsa, qoralama akt tuziladi: u tasdiqlangach javobgar almashadi.

**3. Vedomost (kompyuterda).** Reviziya sahifasi jonli yangilanadi: Belgilangan / kutilgan, Bo'limlar kesimi (Tugadi,
Sanalmoqda, Boshlanmagan) va guruhlar: topildi, holati boshqa, boshqa joyda, kam / topilmadi, ortiqcha. Vedomostdan
ham AV'ni belgilash, belgini olish yoki qidirib qo'shish mumkin.

**4. Yakunlash.** Kutilgan narsasi bor xonada bironta qayd ham, «xona tugadi» belgisi ham bo'lmasa, reviziyani yakunlab
bo'lmaydi: bunday xonalar sahifa tepasida ko'rsatiladi. Xona chindan bo'sh bo'lsa, «xona tugadi» ni belgilang.
«Yakunlash» bosilganda sanash yopiladi va farqlar **avtomatik** AV'larga yoziladi:

| Natija | Nima bo'ladi |
|---|---|
| Boshqa joyda | AV topilgan xonaga ko'chiriladi |
| Holati boshqa | Holat o'zgartiriladi |
| Kam / topilmadi | Yetishmagan son «Topilmadi» holatiga o'tadi |
| Ortiqcha | Faqat qayd qilinadi: soni 1C'dan keladi, kirim 1C'da qilinadi |

Biror farqni yozib bo'lmasa, sababi vedomostda qator yonida ko'rsatiladi va uni AV kartochkasida qo'lda tuzatish kerak.
Reviziya ochilgandan keyin AV ko'chirilgan, holati yoki soni o'zgargan bo'lsa, uning farqi ham yozilmaydi, chunki farq
eskirgan: kamomad soxta chiqishi mumkin. Javobgar shaxs akti bunga kirmaydi. «Bo'limsiz» joyga ko'chish yozilmaydi, chunki
xona noma'lum.

**5. Qaytarish va bekor qilish.** **Ochiqqa qaytarish** yozilgan farqlarni teskari amal bilan qaytaradi. Yakunlashdan
keyin shu AV bilan boshqa amal bo'lgan bo'lsa, rad etiladi va reviziya yakunlangan holida qoladi. Qamrovi kesishgan ochiq
reviziya yoki shu joylarni keyinroq tekshirgan yakunlangan reviziya bo'lsa ham rad etiladi. **Bekor qilish** — faqat
ochiq reviziya uchun.

**6. Hujjatlar.** Vedomost Excel'ga yuklanadi, **Dalolatnoma** PDF'da komissiya imzolari bilan chiqadi.

Holatlar: Ochiq, Yakunlangan, Bekor qilingan. Reviziya natijasi AV tarixida ko'rinadi.

## 13. Sozlamalar (faqat admin)

### 13.1. Foydalanuvchilar

**Yangi foydalanuvchi:** login, ism, rol, filiallar va parol. **Hech bir filial belgilanmasa, barcha filiallarga ruxsat
beriladi** — bunga e'tibor bering.

Parol juda oddiy, faqat raqamlardan iborat yoki loginga o'xshash bo'lmasligi va kamida 8 belgi bo'lishi kerak.

**Tahrirlash:** rol, filiallar, «Faol» belgisi. Yangi parol maydoni bo'sh qolsa, parol o'zgarmaydi. Parol qiymati
jurnalga yozilmaydi. Xodim ketganda foydalanuvchini o'chirmang, «Faol» belgisini oling: tarix saqlanadi. O'zingizni
faolsizlantira olmaysiz va o'z admin rolingizni olib tashlay olmaysiz.

### 13.2. AV turlari

Turlar 1C'dan keladi. «Sozlash»da ikkita narsa kiritiladi:

- **Xizmat muddati, oy** — shu turdagi AV'larning amortizatsiyasi uchun.
- **Qo'shimcha maydonlar** — kartochkada chiqadigan maydonlar: kalit, nom, tip (matn, son, sana, tanlov, xotira),
  majburiylik, tanlov qiymatlari. Masalan, kompyuterlar uchun protsessor va xotira.

### 13.3. Umumiy

- **Kompaniya nomi** — hujjatlarda chiqadi.
- **Reviziyani faqat uni ochgan kishi va biriktirilgan revizorlar o'zgartira oladi** — yoqilsa, boshqa hisobchi va
  revizorlar begona reviziyani faqat ko'radi. Administrator bu cheklovga bo'ysunmaydi.

### 13.4. Yorliq o'lchamlari

Printerdagi yorliq qog'oziga mos o'lchamlar: nomi, eni (20–120 mm), bo'yi (15–120 mm), Faol, Standart. Chop etishda
standart o'lcham oldindan tanlangan bo'ladi.

### 13.5. 1C ulanish

Manzil, login, oxirgi muvaffaqiyatli sinxron va ketma-ket xatolar soni ko'rinadi. Manzil va parol serverdagi `.env`
faylida saqlanadi, sahifada parol ko'rsatilmaydi. **«Hozir sinxronlash»** navbatdagi soatni kutmasdan yangilaydi: 1C'da
biror narsa o'zgartirilgan bo'lsa va natijani darhol ko'rish kerak bo'lsa bosing.

### 13.6. Sinxron jurnali

Har sinxron: boshlangan va tugagan vaqti, natijasi, to'liq yoki oddiyligi va xato matni.

- **Har soatda** oddiy sinxron: ma'lumotnomalar va oxirgi 45 kundagi harakatlar.
- **Har kecha 03:02 da** to'liq sinxron: barcha harakatlar.
- Har sinxron bitta tranzaksiyada ishlaydi. 1C javob bermasa yoki xato bersa, hech narsa o'zgarmaydi: eski ma'lumot
  qoladi, jurnalga xato yoziladi.
- Bir vaqtda faqat bitta sinxron ishlaydi. Band bo'lsa, «Sinxron hozir ishlayapti» xabari chiqadi.

**Sinxron nima qiladi:** 1C'da AV ko'paysa, yangi donalar bo'limsiz va javobgarsiz qatorga tushadi («Bo'limga joylash
kerak»). Kamaysa, avval shu qatordan ayiriladi, yetmasa AV «Taqsimot 1C bilan mos emas»ga tushadi. Xodim ketsa, u
javobgar bo'lgan qatorlar «Ketgan xodimda»ga o'tadi. Inv. raqam o'zgarsa, «Yorliqni almashtirish kerak» bo'ladi.

### 13.7. O'zgarishlar jurnali

Platformadagi har o'zgarish: qachon, kim, qaysi obyekt, qaysi maydon, eski va yangi qiymat. Biror narsa kutilmaganda
o'zgargan bo'lsa, birinchi shu yerga qarang.

## 14. Hisobotlar

Hammasi Excel'ga yuklanadi va chop etiladi. Qaydnomalarda **summali** va **summasiz** chop etish bor.

- **Kesim** — AV soni, boshlang'ich va qoldiq qiymat: filial, bo'lim yoki AV turi bo'yicha.
- **Javobgar qaydnomasi** — xodimdagi AV'lar. «Hammasi» chop etilsa, har xodim alohida varaqdan, o'z imzo qatori bilan
  chiqadi.
- **Bo'lim qaydnomasi** — filial yoki bo'limdagi AV'lar. Bo'lim tanlansa, ichki bo'limlari ham kiradi.
- **Xizmat muddati** — muddati tugagan va 6 oyda tugaydigan AV'lar. Ro'yxat chiqishi uchun xizmat muddatlari kiritilgan
  bo'lishi kerak (13.2).

## 15. Administratorning ish tartibi

**Har kuni**

1. Yuqori paneldagi sinxron vaqti yashil va yangi ekanini tekshiring.
2. Qo'ng'iroqchadagi kutayotgan ishlarni ko'ring.
3. Bosh sahifadagi «Bajarilishi kerak» sonlarini ko'ring.

**Har hafta**

1. «1C ma'lumotlarini tozalash»dan Excel olib, hisobchiga bering.
2. «Ketgan xodimlardagi AV'lar» ro'yxatini tekshiring.
3. Sinxron jurnalida xatolar yo'qligini ko'ring.

**Yangi xodim kelganda:** foydalanuvchi yarating, rol bering va filiallarini belgilang.

**Xodim ketganda:** foydalanuvchining «Faol» belgisini oling, undagi AV'larni akt bilan boshqa xodimga topshiring.

## 16. Muammolar va yechimlar

| Holat | Sabab | Nima qilish kerak |
|---|---|---|
| «1C bilan aloqa yo'q» | Server 1C'ga ulana olmayapti | «Sinxron jurnali»dagi xato matnini ko'ring, 1C ishlayotganini tekshiring. Platforma eski ma'lumot bilan ishlashda davom etadi |
| Foydalanuvchi kira olmayapti | 5 marta noto'g'ri parol | 15 daqiqa kuting yoki yangi parol bering. «Faol» belgisini ham tekshiring |
| AV'da «Farq» bor | Taqsimot va 1C qoldig'i teng emas | Kartochkada «Moslash»dan foydalaning yoki kutayotgan 1C chiqimini tasdiqlang |
| Foydalanuvchi AV'ni ko'rmayapti | Filial cheklovi | Foydalanuvchi filiallarini tekshiring |
| HR'da summalar yo'q | Bu to'g'ri | HR'da `pul_korish` huquqi yo'q |
| Amortizatsiya hisoblanmadi | Sana yoki muddat yo'q | Ishga tushgan sana va AV turi muddatini kiriting |
| Xizmat muddati hisoboti bo'sh | Muddatlar kiritilmagan | «AV turlari»da xizmat muddatini kiriting |
| AV nomi yoki summasi xato | Bu 1C ma'lumoti | 1C'da tuzating, keyingi sinxronda o'zgaradi |
| Revizor telefonida kamera ochilmayapti | HTTPS yoki brauzer ruxsati yo'q | https manzildan oching, kameraga ruxsat bering yoki inv. raqam bilan qidiring |
| Revizor yangi reviziyada ro'yxatda yo'q | Rol berilmagan | «Foydalanuvchilar»da «Revizor» rolini bering |

## 17. Zaxira

Har kecha 02:30 da ma'lumotlar bazasi va rasmlar serverda zaxiralanadi, zaxiralar 14 kun saqlanadi. Server va tiklash
tartibi: [ishga-tushirish-windows.md](ishga-tushirish-windows.md).
