"""Bosh sahifa: filiallar kesimida AV summasi dinamikasi (oyma-oy, tanlangan «dan — gacha» davrda).

Har oy oxiridagi summa 1C harakatlaridan tiklanadi: Σ kirim − Σ chiqim (qayta baholash ham shu harakatlarda).
Bu yig'indi bugungi kunga 1C qoldig'i (`AVQoldiq.summa`) bilan aynan mos keladi. Filial cheklovi bilan.
Grafik brauzerda SVG bilan chiziladi (tashqi kutubxona yo'q) — `panel/static/panel/dinamika.js`.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Min, Sum, When
from django.db.models.functions import TruncMonth
from django.utils import timezone

from hisoblar.huquqlar import filial_bilan_chekla
from onec.models import Filial, Harakat1C
from panel.templatetags.raqamlar import qisqa_pul

NOL = Decimal("0")
ENG_KAM_OY, ENG_KOP_OY, STANDART_OY = 6, 60, 12
STANDART_FILIALLAR = 5
# Kategorik ranglar — qat'iy tartibda (dataviz validator: rang ko'rlikda ham ajraladi); 8 tadan ortig'i yig'iladi
RANGLAR = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
BOSHQALAR_RANGI = "#8a8f98"  # «Boshqa N ta filial» — neytral kulrang
OY_NOMLARI = ("yan", "fev", "mar", "apr", "may", "iyun", "iyul", "avg", "sen", "okt", "noy", "dek")
OY_TOLIQ = ("Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr")


def oy_qosh(oy: date, n: int) -> date:
    jami = oy.year * 12 + oy.month - 1 + n
    return date(jami // 12, jami % 12 + 1, 1)


def oylar_farqi(dan: date, gacha: date) -> int:
    return (gacha.year - dan.year) * 12 + gacha.month - dan.month


def oy_nomi(oy: date) -> str:
    return f"{OY_NOMLARI[oy.month - 1]} {oy.year}"


def _oy(matn) -> date | None:
    """«2026-03» -> date(2026, 3, 1)."""
    try:
        yil, oy = str(matn or "").split("-")
        return date(int(yil), int(oy), 1)
    except ValueError:
        return None


@dataclass
class Dinamika:
    dan: date
    gacha: date
    oylar: list[date]
    seriyalar: list[dict]  # tanlangan filiallar: {id, nomi, rang, qiymatlar, nuqtalar}
    jadval: list[dict]  # barcha ruxsat etilgan filiallar: {nomi, boshi, oxiri, farq, foiz}
    jami: dict  # {boshi, oxiri, farq, foiz}
    filiallar: list[dict]  # tanlov uchun: {id, nomi, tanlangan}
    ogohlantirishlar: list[str] = field(default_factory=list)
    eng_erta: date | None = None
    grafik: dict = field(default_factory=dict)
    joriy_oy: date | None = None  # «gacha» ning eng kechi

    @property
    def dan_matn(self) -> str:
        return f"{OY_TOLIQ[self.dan.month - 1]} {self.dan.year}"

    @property
    def gacha_matn(self) -> str:
        return f"{OY_TOLIQ[self.gacha.month - 1]} {self.gacha.year}"

    @property
    def tanlangan_soni(self) -> int:
        return sum(f["tanlangan"] for f in self.filiallar)


def _davr(params, bugun: date, eng_erta: date | None) -> tuple[date, date, list[str]]:
    """GET `dan`/`gacha` (YYYY-MM) -> (dan, gacha); 6 oydan qisqa yoki 5 yildan uzun bo'lsa — tuzatiladi va aytiladi."""
    ogoh = []
    joriy = bugun.replace(day=1)
    gacha = _oy(params.get("gacha")) or joriy
    if gacha > joriy:
        gacha = joriy
    dan = _oy(params.get("dan")) or oy_qosh(gacha, -(STANDART_OY - 1))
    if dan > gacha:
        dan, gacha = gacha, dan
    oy_soni = oylar_farqi(dan, gacha) + 1
    if oy_soni < ENG_KAM_OY:
        dan = oy_qosh(gacha, -(ENG_KAM_OY - 1))
        ogoh.append(f"Davr kamida {ENG_KAM_OY} oy bo'lishi kerak — boshlanishi {oy_nomi(dan)} qilindi.")
    elif oy_soni > ENG_KOP_OY:
        dan = oy_qosh(gacha, -(ENG_KOP_OY - 1))
        ogoh.append(f"Davr ko'pi bilan 5 yil bo'lishi mumkin — boshlanishi {oy_nomi(dan)} qilindi.")
    if eng_erta and dan < eng_erta:
        ogoh.append(f"1C harakatlari {oy_nomi(eng_erta)} dan boshlanadi — undan oldingi oylar bo'sh (0) ko'rinadi.")
    return dan, gacha, ogoh


def _foiz(boshi: Decimal, oxiri: Decimal) -> Decimal | None:
    return None if not boshi else (oxiri - boshi) * 100 / abs(boshi)


def _shkala(eng_katta: Decimal) -> list[Decimal]:
    """Y o'qi uchun «chiroyli» belgilar: 0 dan eng kattasidan oshiq 1/2/2.5/5 × 10^n qadamlar bilan (5 ta atrofida)."""
    if eng_katta <= 0:
        return [NOL, Decimal(1)]
    xom = eng_katta / 4
    daraja = Decimal(10) ** (len(str(int(xom))) - 1)
    qadam = next(k * daraja for k in (Decimal(1), Decimal(2), Decimal("2.5"), Decimal(5), Decimal(10)) if k * daraja >= xom)
    belgilar = [NOL]
    while belgilar[-1] < eng_katta:
        belgilar.append(belgilar[-1] + qadam)
    return belgilar


def _grafik(oylar: list[date], seriyalar: list[dict]) -> dict:
    """Brauzerda chiziladigan grafik ma'lumoti (`panel/static/panel/dinamika.js`): grafik konteyner kengligiga
    qarab chiziladi, shuning uchun yozuvlar har ekranda bir xil o'lchamda qoladi."""
    eng_katta = max((v for s in seriyalar for v in s["qiymatlar"]), default=NOL)
    return {
        "oylar": [oy_nomi(oy) for oy in oylar],
        "y": [{"q": float(b), "matn": qisqa_pul(b)} for b in _shkala(max(eng_katta, NOL))],
        "seriyalar": [{"nomi": s["nomi"], "rang": s["rang"], "q": [float(v) for v in s["qiymatlar"]],
                       "matn": [qisqa_pul(v) for v in s["qiymatlar"]]} for s in seriyalar],
    }


def filial_dinamikasi(user, params) -> Dinamika:
    harakatlar = filial_bilan_chekla(Harakat1C.objects.all(), user)
    eng_erta = harakatlar.aggregate(m=Min("sana"))["m"]
    eng_erta = timezone.localtime(eng_erta).date().replace(day=1) if eng_erta else None
    dan, gacha, ogoh = _davr(params, timezone.localdate(), eng_erta)
    oylar = [oy_qosh(dan, i) for i in range(oylar_farqi(dan, gacha) + 1)]

    # Bitta so'rov: (filial, oy) bo'yicha ishorali summa (kirim +, chiqim −); davr oxirigacha
    ishorali = Case(When(vid=Harakat1C.Vid.CHIQIM, then=-F("summa")), default=F("summa"),
                    output_field=DecimalField(max_digits=18, decimal_places=2))
    qatorlar = (
        harakatlar.filter(sana__lt=timezone.make_aware(datetime.combine(oy_qosh(gacha, 1), time.min)))
        .annotate(oy=TruncMonth("sana")).values("filial_id", "oy").annotate(s=Sum(ishorali)).order_by()
    )
    oyma_oy: dict[int, dict[date, Decimal]] = {}
    for q in qatorlar:
        oy = q["oy"].date() if hasattr(q["oy"], "date") else q["oy"]
        oyma_oy.setdefault(q["filial_id"], {})
        oyma_oy[q["filial_id"]][oy] = oyma_oy[q["filial_id"]].get(oy, NOL) + q["s"]

    filial_nomlari = dict(filial_bilan_chekla(Filial.objects.all(), user, "pk").values_list("pk", "nomi"))
    qiymatlar: dict[int, list[Decimal]] = {}
    for fid, oylik in oyma_oy.items():
        joriy = sum((s for oy, s in oylik.items() if oy < dan), NOL)  # davr boshigacha yig'ilgani
        qator = []
        for oy in oylar:
            joriy += oylik.get(oy, NOL)
            qator.append(joriy)
        qiymatlar[fid] = qator

    # Davr boshidagi summa = birinchi oydan oldingi oy oxiri; jadval — barcha filiallar, o'zgarish bo'yicha
    jadval = []
    for fid, qator in qiymatlar.items():
        boshi = qator[0] - oyma_oy[fid].get(dan, NOL)
        oxiri = qator[-1]
        if not boshi and not oxiri:
            continue
        jadval.append({"id": fid, "nomi": filial_nomlari.get(fid, "—"), "boshi": boshi, "oxiri": oxiri,
                       "farq": oxiri - boshi, "foiz": _foiz(boshi, oxiri)})
    jadval.sort(key=lambda q: q["oxiri"], reverse=True)
    jami_boshi, jami_oxiri = sum((q["boshi"] for q in jadval), NOL), sum((q["oxiri"] for q in jadval), NOL)

    # Tanlangan filiallar: GET `f` (istalgancha, «Hammasi» ham), bo'lmasa davr oxiridagi eng katta 5 tasi
    mavjud = [q["id"] for q in jadval]  # davr oxiridagi summa bo'yicha kamayuvchi
    tanlov = {int(f) for f in params.getlist("f") if str(f).isdigit()}
    tanlangan = [fid for fid in mavjud if fid in tanlov] or mavjud[:STANDART_FILIALLAR]
    # 8 tadan ko'p rangni ko'z ajratmaydi: eng kattalari o'z rangida, qolganlari bitta «Boshqa N ta filial» chizig'ida
    alohida, qolgan = (tanlangan, []) if len(tanlangan) <= len(RANGLAR) else (
        tanlangan[:len(RANGLAR) - 1], tanlangan[len(RANGLAR) - 1:])
    # Rang tartibi barqaror bo'lsin (davr o'zgarganda qayta bo'yalmasin): alohida chiziladiganlar id bo'yicha
    seriyalar = [
        {"id": fid, "nomi": filial_nomlari.get(fid, "—"), "rang": RANGLAR[i], "qiymatlar": qiymatlar[fid]}
        for i, fid in enumerate(sorted(alohida))
    ]
    seriyalar.sort(key=lambda s: s["qiymatlar"][-1], reverse=True)
    if qolgan:
        seriyalar.append({
            "id": None, "nomi": f"Boshqa {len(qolgan)} ta filial", "rang": BOSHQALAR_RANGI,
            "qiymatlar": [sum((qiymatlar[fid][i] for fid in qolgan), NOL) for i in range(len(oylar))],
        })
    return Dinamika(
        dan=dan, gacha=gacha, oylar=oylar, seriyalar=seriyalar, jadval=jadval,
        jami={"boshi": jami_boshi, "oxiri": jami_oxiri, "farq": jami_oxiri - jami_boshi, "foiz": _foiz(jami_boshi, jami_oxiri)},
        filiallar=[{"id": q["id"], "nomi": q["nomi"], "tanlangan": q["id"] in tanlangan} for q in sorted(jadval, key=lambda q: q["nomi"])],
        ogohlantirishlar=ogoh, eng_erta=eng_erta, grafik=_grafik(oylar, seriyalar),
        joriy_oy=timezone.localdate().replace(day=1),
    )
