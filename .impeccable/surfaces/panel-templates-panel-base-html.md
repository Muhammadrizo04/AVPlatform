---
version: 1
slug: "panel-templates-panel-base-html"
primary_target: "panel/templates/panel/base.html"
related_targets: ["vositalar/templates/vositalar/kartochka.html"]
---

# Surface brief: Asosiy vositalar paneli (barcha ichki sahifalar)

Scope: Django panel shell (`panel/templates/panel/base.html`, `panel/static/panel/panel.css`) va undagi barcha sahifalar; birinchi namuna — AV kartochkasi (`vositalar/templates/vositalar/kartochka.html`). Mode: operate. Build path: code-led.

Auditoriya va vazifa: hisobchi (asosiy), HR, rahbar, admin — ofis kompyuteri, katta ekran, tezlik va zichlik. Asosiy vazifa: AV qayerda, kimda, qanday holatda; 1C bilan mosligi.

Cheklovlar: CoreUI 5 komponentlari va Bootstrap klasslari ichkarida qoladi (mavzu tokenlar orqali almashtiriladi); tashqi CDN/shrift yo'q; HTMX bo'laklari va testlardagi belgilar saqlanadi.

## Direction contract

THESIS: Har raqam qat'iy to'rda turadi; panel 1C qoldig'i va platforma taqsimotini yonma-yon ustunlarda solishtiradi va farqni bitta qizil chiziq bilan ko'rsatadi. Rad etadigan standart: qorong'i menyu + soyali oq kartochkalar + binafsha urg'uli umumiy admin paneli.

OWN-WORLD: Xalqaro tipografik uslub ma'lumot varag'i. Fon #f4f5f7, siyoh #121417, sirt #ffffff, chiziqlar #d9dce1/#eceef1, ikkilamchi matn #5b616b. Qizil #d6281c faqat «harakat kerak» (farq, МОЛ'siz, kutilayotgan chiqim, xato). Ko'k #2f5d8a — platformaning o'z ma'lumoti (bo'lim, МОЛ, holat) va havolalar. Grotesk tizim shrifti, tabular raqamlar, shkala 11/13/15/20/32. Faqat 1px chiziqlar, soya va gradient yo'q, radius 0–2px; sarlavha ostida 1px siyoh chizig'i; katta bosh harfli kichik yorliqlar (11px, .08em).

STORY: Foydalanuvchi har sahifada avval «nima, qayerda, kimda, holati» va «1C bilan mosmi» ni ko'radi; qizil ko'rgan joyda ish bor; ko'k — platformada o'zi o'zgartira oladigan narsa; qolgani 1C'dan, faqat o'qish.

FIRST VIEWPORT: Chapda 220px qora menyu ustuni (oq matn, faol band oq fonli teskari), tepada 40px oq yo'l satri (breadcrumb + sinxron vaqti). AV kartochkasida: 32px nom, ostida Inv. raqam (20px qalin) | turi | soni | filial; o'ngda «QR-yorliq», «МОЛ akti». Ostida imzo harakati — to'liq kenglikdagi solishtirish qatori «1C qoldig'i | Platforma taqsimoti | Farq» (32px raqamlar); farq yoki МОЛ'siz bo'lsa ostida qizil 2px chiziqli ogohlantirish qatori va tugma. Keyin 8/4 to'r: chapda Joylashuv jadvali va Tarix, o'ngda Buxgalteriya, Platforma ma'lumotlari, 1C rekvizitlari.

FORM: Shveytsariya jadval maktabi (xalqaro tipografik uslub), o'z ro'yxatimda 6-o'rin; ko'tarishlar: bitta rang–bitta ma'no (aeroport ko'rsatkichlari), ustunlar siljimaydi (vokzal tablosi), 1px aniq chiziqlar (ma'lumotnoma sahifasi), bezaksiz matn-interfeys (metro), 1C zamin / platforma qatlami (orientirlash xaritasi). seed: none (unavailable) — concept-seed ishladi (kalit 674d2fdd, direction/operate, tanlov «assigned» qayd etildi), lekin bu CLI versiyasi SEED REFERENCE satrini umuman chiqarmadi.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
