"""Hisobot hisob-kitoblari: kesimlar, МОЛ qaydnomasi, xizmat muddati (spec §7.7, §7.9).

Qoidalar: faqat faol AV'lar (umumiy 1C qoldig'i > 0), faqat foydalanuvchining filiallari. Amortizatsiyani hisoblab
bo'lmasa, qoldiq qiymat = boshlang'ich qiymat (boshqaruv paneli bilan bir xil).
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Literal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import prefetch_related_objects

from hisoblar.huquqlar import filial_bilan_chekla
from onec.models import AV, AVQoldiq, Filial, Xodim
from vositalar.amortizatsiya import dona_narxi, hisobla, oy_qosh, samarali_muddat
from vositalar.bayroqlar import BAYROQLAR
from vositalar.models import Bolim, Taqsimot

NOL = Decimal("0")
TIYIN = Decimal("0.01")
BOLIMSIZ = "Bo'limsiz"
TURI_YOQ = "Turi yo'q"
TOZALASH_BAYROQLARI = ("inv_bosh", "inv_takror", "filial_rekvizit_bosh", "mos_emas")


def _qoldiq_qiymati(summa: Decimal, av: AV, bugun: date) -> Decimal:
    """summa × (1 − eskirish); hisoblab bo'lmasa summaning o'zi."""
    try:
        kartochka = av.kartochka
    except ObjectDoesNotExist:
        return summa
    amortizatsiya = hisobla(summa, kartochka.ishga_tushgan_sana, samarali_muddat(kartochka), bugun)
    return summa if amortizatsiya is None else amortizatsiya.qoldiq_qiymat


def _bo_sh_jam() -> dict:
    return {"soni": NOL, "boshlangich": NOL, "qoldiq": NOL}


def _qoldiqlar(user):
    """Faol AV'larning ruxsat etilgan filiallardagi musbat qoldiq qatorlari (kartochka/tur bilan, N+1 siz)."""
    qs = AVQoldiq.objects.filter(soni__gt=0, av__in=AV.objects.faol().values("pk"))
    return filial_bilan_chekla(qs, user).select_related("filial", "av__kartochka", "av__turi__sozlama")


def filial_kesimi(user, bugun: date) -> list[dict]:
    """Ruxsat etilgan filiallar bo'yicha: soni, boshlang'ich qiymat (Σ summa), qoldiq qiymat (eskirish bilan)."""
    jamlar = defaultdict(_bo_sh_jam)
    filiallar: dict[int, Filial] = {}
    for q in _qoldiqlar(user):
        filiallar[q.filial_id] = q.filial
        jam = jamlar[q.filial_id]
        jam["soni"] += q.soni
        jam["boshlangich"] += q.summa
        jam["qoldiq"] += _qoldiq_qiymati(q.summa, q.av, bugun)
    return [{"filial": f, **jamlar[f.pk]} for f in sorted(filiallar.values(), key=lambda f: (f.nomi, f.pk))]


def _taqsimotlar(user):
    """Faol AV'larning ruxsat etilgan filiallardagi taqsimot qatorlari va ularning AV'lari (qiymat bilan)."""
    qs = Taqsimot.objects.filter(av__in=AV.objects.faol().values("pk")).select_related("filial", "bolim", "mol")
    qatorlar = list(filial_bilan_chekla(qs, user, "filial"))
    avlar = {
        av.pk: av
        for av in AV.objects.faol()
        .filter(pk__in={t.av_id for t in qatorlar})
        .select_related("kartochka", "turi__sozlama")
    }
    return qatorlar, avlar


def _bolimlar() -> dict[int, Bolim]:
    """Barcha bo'limlar, `ota` zanjiri xotirada ulangan — `toliq_nomi` qo'shimcha so'rov qilmaydi."""
    bolimlar = {b.pk: b for b in Bolim.objects.select_related("filial")}
    for b in bolimlar.values():
        b.ota = bolimlar.get(b.ota_id)
    return bolimlar


def _qiymat(soni: Decimal, av: AV) -> Decimal:
    return soni * dona_narxi(av.jami_summa, av.jami_soni)


def kesim(user, guruh: Literal["filial", "bolim", "tur"], bugun: date) -> list[dict]:
    """Har qator `{nomi, soni, boshlangich, qoldiq}`. Bo'lim kesimida taqsimlanmagan — «Bo'limsiz»."""
    if guruh == "filial":
        return [{"nomi": q["filial"].nomi, **{k: q[k] for k in ("soni", "boshlangich", "qoldiq")}}
                for q in filial_kesimi(user, bugun)]
    jamlar = defaultdict(_bo_sh_jam)
    if guruh == "tur":
        for q in _qoldiqlar(user):
            jam = jamlar[q.av.turi.nomi if q.av.turi else TURI_YOQ]
            jam["soni"] += q.soni
            jam["boshlangich"] += q.summa
            jam["qoldiq"] += _qoldiq_qiymati(q.summa, q.av, bugun)
    elif guruh == "bolim":
        qatorlar, avlar = _taqsimotlar(user)
        bolimlar = _bolimlar()
        for t in qatorlar:
            nomi = f"{t.filial.nomi} / {bolimlar[t.bolim_id].toliq_nomi}" if t.bolim_id else BOLIMSIZ
            summa = _qiymat(t.soni, avlar[t.av_id])
            jam = jamlar[nomi]
            jam["soni"] += t.soni
            jam["boshlangich"] += summa
            jam["qoldiq"] += _qoldiq_qiymati(summa, avlar[t.av_id], bugun)
    else:
        raise ValueError(f"Noma'lum guruh: {guruh!r}")
    qatorlar = [
        {"nomi": nomi, "soni": j["soni"], "boshlangich": j["boshlangich"].quantize(TIYIN),
         "qoldiq": j["qoldiq"].quantize(TIYIN)}
        for nomi, j in jamlar.items()
    ]
    return sorted(qatorlar, key=lambda q: (q["nomi"] == BOLIMSIZ, q["nomi"]))


def jami(qatorlar: list[dict]) -> dict:
    """Kesim qatorlari yig'indisi (jadval pastidagi «Jami»)."""
    return {k: sum((q[k] for q in qatorlar), NOL) for k in ("soni", "boshlangich", "qoldiq")}


def mol_qaydnoma(user, xodim: Xodim | None = None) -> list[dict]:
    """МОЛ'ga biriktirilgan taqsimot qatorlari (yoki bitta xodimniki): qiymat = soni × dona narxi."""
    qatorlar, avlar = _taqsimotlar(user)
    bolimlar = _bolimlar()
    natija = []
    for t in qatorlar:
        if t.mol_id is None or (xodim is not None and t.mol_id != xodim.pk):
            continue
        av = avlar[t.av_id]
        natija.append({
            "xodim": t.mol,
            "av": av,
            "inv": av.inv_raqam,
            "bolim": bolimlar[t.bolim_id].toliq_nomi if t.bolim_id else "",
            "holat": t.get_holat_display(),
            "soni": t.soni,
            "qiymat": _qiymat(t.soni, av).quantize(TIYIN),
        })
    return sorted(natija, key=lambda q: (q["xodim"].ism, q["xodim"].pk, q["av"].nomi, q["av"].pk))


def tugash_sanasi(av: AV) -> date:
    kartochka = av.kartochka
    return oy_qosh(kartochka.ishga_tushgan_sana, samarali_muddat(kartochka))


def muddat(user, bugun: date) -> tuple[list[AV], list[AV]]:
    """(tugagan: tugash ≤ bugun, 6 oyda tugaydigan: bugun < tugash ≤ bugun + 6 oy); har AV'da `tugash`."""
    tugagan = BAYROQLAR["muddat_tugagan"].so_rov(user, bugun)
    olti_oy = BAYROQLAR["muddat_6oy"].so_rov(user, bugun)
    for royxat in (tugagan, olti_oy):
        for av in royxat:
            av.tugash = tugash_sanasi(av)
        royxat.sort(key=lambda av: (av.tugash, av.nomi, av.pk))
        prefetch_related_objects(royxat, "filial_rekvizit")
    return tugagan, olti_oy


def tozalash(user, bugun: date) -> list[dict]:
    """1C ma'lumotidagi muammolar: har bayroq uchun `{kalit, nomi, avlar}`."""
    bolimlar = []
    for kalit in TOZALASH_BAYROQLARI:
        bayroq = BAYROQLAR[kalit]
        avlar = bayroq.so_rov(user, bugun).select_related("filial_rekvizit").order_by("nomi", "pk")
        bolimlar.append({"kalit": kalit, "nomi": bayroq.nomi, "avlar": list(avlar)})
    return bolimlar
