from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from hisobotlar.servis import filial_kesimi, jami
from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from onec.models import AV
from vositalar.bayroqlar import BAYROQLAR, bayroq_sonlari
from vositalar.models import Holat, Taqsimot

# Buxgalteriya tozalash vazifalarini ko'rmaydigan (pul huquqi yo'q) rol — HR — uchun faqat o'zi hal qiladigan bayroqlar:
# МОЛ biriktirish (akt orqali), ketgan xodimdagi AV'lar va bo'limsiz qatorlar.
XODIM_BAYROQLARI = ("molsiz", "ketgan_xodimda", "bolimsiz")
GRAFIK_FILIALLAR = 12
# «Bajarilishi kerak» qatorlari bo'lim rangida
VAZIFA_RANGI = {
    "molsiz": "mol", "ketgan_xodimda": "mol", "chiqim_kutilmoqda": "chiqim", "mos_emas": "ogoh",
    "bolimsiz": "vosita", "yorliq_yoq": "vosita", "yorliq_almashtirish": "vosita",
}  # «Filiallar bo'yicha» grafigida ko'rsatiladigan eng katta filiallar
NOL = Decimal("0")


def _ulush(qiymat, eng_katta) -> float:
    """Bar uzunligi, % (0 dan farqli qiymat kamida 1% — ko'rinib tursin)."""
    if not eng_katta or not qiymat:
        return 0
    return max(round(float(qiymat) / float(eng_katta) * 100, 1), 1)


def _holatlar(user) -> list[dict]:
    """Ruxsat etilgan filiallardagi faol AV taqsimoti holatlar bo'yicha (Holat tartibida, nollar tushib qoladi)."""
    qs = filial_bilan_chekla(Taqsimot.objects.filter(av__in=AV.objects.faol().values("pk")), user)
    sonlar = dict(qs.order_by().values_list("holat").annotate(s=Sum("soni")))
    jami_soni = sum(sonlar.values(), NOL)
    natija = []
    for kalit, nomi in Holat.choices:  # oltitasi ham: nollar xira, palitra doim to'liq ko'rinadi
        soni = sonlar.get(kalit, NOL)
        natija.append({"kalit": kalit, "nomi": nomi, "soni": soni,
                       "foiz": round(float(soni) / float(jami_soni) * 100, 1) if jami_soni else 0})
    eng_katta = max((h["soni"] for h in natija), default=NOL)
    for h in natija:
        h["ulush"] = _ulush(h["soni"], eng_katta)
    return natija


@amal_kerak("korish")
def bosh(request):
    bugun = timezone.localdate()
    pul = huquqi_bor(request.user, "pul_korish")
    if not pul:
        kalitlar = XODIM_BAYROQLARI
    elif not huquqi_bor(request.user, "chiqim_korish"):  # rahbar: chiqimlar sahifasi yo'q
        kalitlar = tuple(k for k in BAYROQLAR if k != "chiqim_kutilmoqda")
    else:
        kalitlar = None
    sonlar = bayroq_sonlari(request.user, bugun, kalitlar)
    bayroqlar = [{"kalit": k, "nomi": BAYROQLAR[k].nomi, "soni": sonlar[k], "rang": VAZIFA_RANGI.get(k, "hisobot")} for k in sonlar]
    filiallar = filial_kesimi(request.user, bugun)
    jamlar = jami(filiallar)

    # Grafik: eng ko'p AV'li filiallar (soni bo'yicha kamayuvchi)
    tartiblangan = sorted(filiallar, key=lambda q: q["soni"], reverse=True)
    eng_katta = tartiblangan[0]["soni"] if tartiblangan else NOL
    filial_grafik = [{**q, "ulush": _ulush(q["soni"], eng_katta)} for q in tartiblangan[:GRAFIK_FILIALLAR]]

    # KPI kartochkalari: rolga qarab
    kpi = [{"yorliq": "Asosiy vositalar", "qiymat": jamlar["soni"], "birlik": "dona", "izoh": f"{len(filiallar)} ta filialda",
            "ikonka": "cil-storage", "rang": "vosita", "url": "vositalar:royxat", "pul": False}]
    if pul:
        kpi.append({"yorliq": "Qoldiq qiymat", "qiymat": jamlar["qoldiq"], "birlik": "so'm", "izoh": "amortizatsiya bilan",
                    "ikonka": "cil-wallet", "rang": "pul", "url": "hisobotlar:kesim", "pul": True})
    kpi.append({"yorliq": "МОЛ biriktirilmagan", "qiymat": sonlar.get("molsiz", 0), "birlik": "qator", "izoh": "akt orqali biriktiring",
                "ikonka": "cil-user-unfollow", "rang": "mol", "bayroq": "molsiz", "ogoh": bool(sonlar.get("molsiz"))})
    if "chiqim_kutilmoqda" in sonlar:
        kpi.append({"yorliq": "1C chiqimlari", "qiymat": sonlar["chiqim_kutilmoqda"], "birlik": "kutilmoqda", "izoh": "tasdiqlash kerak",
                    "ikonka": "cil-swap-horizontal", "rang": "chiqim", "url": "chiqimlar:royxat", "ogoh": bool(sonlar["chiqim_kutilmoqda"])})
    elif "mos_emas" in sonlar:
        kpi.append({"yorliq": "1C bilan mos emas", "qiymat": sonlar["mos_emas"], "birlik": "AV", "izoh": "taqsimotni tuzating",
                    "ikonka": "cil-warning", "rang": "ogoh", "bayroq": "mos_emas", "ogoh": bool(sonlar["mos_emas"])})
    else:
        kpi.append({"yorliq": "Ketgan xodimlarda", "qiymat": sonlar.get("ketgan_xodimda", 0), "birlik": "qator", "izoh": "boshqa МОЛ'ga topshiring",
                    "ikonka": "cil-warning", "rang": "ogoh", "bayroq": "ketgan_xodimda", "ogoh": bool(sonlar.get("ketgan_xodimda"))})
    if not pul:
        kpi.append({"yorliq": "Bo'limsiz", "qiymat": sonlar.get("bolimsiz", 0), "birlik": "qator", "izoh": "bo'limga joylang",
                    "ikonka": "cil-sitemap", "rang": "vosita", "bayroq": "bolimsiz", "ogoh": False})

    holatlar = _holatlar(request.user)
    return render(
        request, "panel/bosh.html",
        {"filiallar": filiallar, "jami": jamlar, "bayroqlar": sorted(bayroqlar, key=lambda b: not b["soni"]),
         "kpi": kpi[:4], "filial_grafik": filial_grafik, "filial_qolgan": max(len(filiallar) - GRAFIK_FILIALLAR, 0),
         "holatlar": holatlar, "bugun": bugun},
    )
