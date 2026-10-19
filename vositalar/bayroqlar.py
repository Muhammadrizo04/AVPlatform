"""Bayroqlar: tozalash va nazorat ro'yxatlari (spec §5.4). Boshqaruv paneli, tozalash ro'yxatlari va hisobotlar
shu reestrdan foydalanadi.

Qoidalar: barcha bayroqlar faqat faol AV'lar (umumiy 1C qoldig'i > 0) bo'yicha va foydalanuvchining filiallari
doirasida. AV darajasidagi bayroqlar — ruxsat etilgan filialda musbat qoldig'i bor AV'lar; taqsimot darajasidagilar —
`Taqsimot.filial` bo'yicha chegaralanadi. Istisno: `chiqim_kutilmoqda` — `ChiqimHujjat.filial` bo'yicha, AV
faolligidan qat'i nazar (1C'da to'liq chiqib ketgan AV'ning chiqimi ham tasdiqlanishi kerak).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from django.db.models import Exists, OuterRef, Q, QuerySet, Sum

from chiqimlar.models import ChiqimHujjat  # models vositalar'ni import qilmaydi (servis qiladi)
from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from onec.models import AV, AVQoldiq

from .amortizatsiya import hisobla, oy_qosh, samarali_muddat
from .models import Taqsimot

NOL = Decimal("0")


@dataclass(frozen=True)
class Bayroq:
    nomi: str
    model: type  # ro'yxat elementlari turi: AV, Taqsimot yoki ChiqimHujjat
    so_rov: Callable[..., QuerySet | list]  # (user, bugun) -> QuerySet yoki ro'yxat


def ruxsat_qoldiq(user) -> Exists:
    """Shart: AV'ning ruxsat etilgan filialida musbat qoldig'i bor. Ro'yxat va bayroqlar uchun umumiy qoida."""
    return Exists(filial_bilan_chekla(AVQoldiq.objects.filter(av=OuterRef("pk"), soni__gt=0), user))


def av_lar(user) -> QuerySet:
    """Faol AV'lar, ruxsat etilgan filialda musbat qoldig'i borlari."""
    return AV.objects.faol().filter(ruxsat_qoldiq(user))


def _taqsimotlar(user) -> QuerySet:
    """Faol AV'larning ruxsat etilgan filialdagi taqsimot qatorlari."""
    qs = Taqsimot.objects.filter(av__in=AV.objects.faol().values("pk")).select_related("av", "filial")
    return filial_bilan_chekla(qs, user, "filial")


def _inv_bosh(user, bugun):
    return av_lar(user).filter(inv_raqam__regex=r"^\s*$")


def _inv_takror(user, bugun):
    """Bir filial_rekvizit ichida bir xil (bo'shliqsiz) inv. raqam — guruhning hamma a'zosi. Guruhlar butun faol
    AV'lar bo'yicha topiladi, ro'yxat esa foydalanuvchi ko'ra oladiganlar bilan cheklanadi."""
    guruhlar = defaultdict(list)
    qatorlar = AV.objects.faol().filter(filial_rekvizit__isnull=False).values_list("pk", "filial_rekvizit_id", "inv_raqam")
    for pk, filial_id, inv in qatorlar:
        inv = (inv or "").strip()
        if inv:
            guruhlar[(filial_id, inv)].append(pk)
    takror = [pk for idlar in guruhlar.values() if len(idlar) > 1 for pk in idlar]
    return av_lar(user).filter(pk__in=takror)


def _filial_rekvizit_bosh(user, bugun):
    return av_lar(user).filter(filial_rekvizit__isnull=True)


def _mos_emas(user, bugun):
    """Biror (AV, filial) uchun Σ taqsimot ≠ max(1C qoldig'i, 0) + K (K — kutilayotgan 1C chiqimi; moslash bilan
    bir xil). Faqat foydalanuvchi filiallaridagi juftlar hisobga olinadi."""
    from chiqimlar.servis import kutilayotgan  # chiqimlar.servis vositalar'ni import qiladi

    def yigindi(qs):
        qatorlar = filial_bilan_chekla(qs, user).order_by().values_list("av_id", "filial_id").annotate(jami=Sum("soni"))
        return {(av, filial): jami for av, filial, jami in qatorlar}

    qoldiq = yigindi(AVQoldiq.objects.all())
    taqsimot = yigindi(Taqsimot.objects.all())
    ruxsat = ruxsat_filial_idlar(user)
    k = kutilayotgan(None if ruxsat is None else Q(filial_id__in=ruxsat))
    mos_emas = {
        av
        for av, filial in qoldiq.keys() | taqsimot.keys() | k.keys()
        if max(qoldiq.get((av, filial), NOL), NOL) + k.get((av, filial), NOL) != taqsimot.get((av, filial), NOL)
    }
    return av_lar(user).filter(pk__in=mos_emas)


def _chiqim_kutilmoqda(user, bugun):
    """Foydalanuvchi filiallaridagi tasdiqlanmagan (`kutilmoqda`) 1C chiqim hujjatlari."""
    qs = ChiqimHujjat.objects.filter(holat=ChiqimHujjat.Holat.KUTILMOQDA).select_related("av", "filial")
    return filial_bilan_chekla(qs, user, "filial")


def _bolimsiz(user, bugun):
    return _taqsimotlar(user).filter(bolim__isnull=True)


def _molsiz(user, bugun):
    return _taqsimotlar(user).filter(mol__isnull=True)


def _ketgan_xodimda(user, bugun):
    return _taqsimotlar(user).filter(
        Q(mol__ishdan_bushagan=True) | Q(mol__neaktiv=True) | Q(mol__onec_da_yoq=True)
    ).select_related("mol")


def _yorliq_yoq(user, bugun):
    return av_lar(user).filter(
        Q(kartochka__isnull=True) | Q(kartochka__yorliq_kaliti__isnull=True) | Q(kartochka__yorliq_kaliti="")
    )


def _yorliq_almashtirish(user, bugun):
    """Chop etilgan yorliq kaliti joriy kalitdan farq qiladi (joriy kalit yo'q bo'lsa ham — eski yorliq yaroqsiz)."""
    qs = (
        av_lar(user)
        .filter(kartochka__yorliq_kaliti__isnull=False)
        .exclude(kartochka__yorliq_kaliti="")
        .select_related("filial_rekvizit", "kartochka")
    )
    return [av for av in qs if av.kalit != av.kartochka.yorliq_kaliti]


def _tugash_sanalari(user, bugun):
    """(AV, tugash sanasi) — xizmat muddati va ishga tushgan sanasi ma'lum faol AV'lar uchun."""
    qs = (
        av_lar(user)
        .filter(kartochka__ishga_tushgan_sana__isnull=False)
        .select_related("kartochka", "turi__sozlama")
    )
    for av in qs:
        kartochka = av.kartochka
        amortizatsiya = hisobla(av.jami_summa, kartochka.ishga_tushgan_sana, samarali_muddat(kartochka), bugun)
        if amortizatsiya is not None:
            yield av, amortizatsiya.tugash_sanasi


def _muddat_tugagan(user, bugun):
    return [av for av, tugash in _tugash_sanalari(user, bugun) if tugash <= bugun]


def _muddat_6oy(user, bugun):
    chegara = oy_qosh(bugun, 6)
    return [av for av, tugash in _tugash_sanalari(user, bugun) if bugun < tugash <= chegara]


BAYROQLAR: dict[str, Bayroq] = {
    "inv_bosh": Bayroq("Inv. raqam bo'sh", AV, _inv_bosh),
    "inv_takror": Bayroq("Inv. raqam takror", AV, _inv_takror),
    "filial_rekvizit_bosh": Bayroq("Filial rekviziti bo'sh", AV, _filial_rekvizit_bosh),
    "mos_emas": Bayroq("Taqsimot 1C bilan mos emas", AV, _mos_emas),
    "bolimsiz": Bayroq("Bo'limga joylash kerak", Taqsimot, _bolimsiz),
    "molsiz": Bayroq("MOL'siz", Taqsimot, _molsiz),
    "ketgan_xodimda": Bayroq("Ketgan xodimda", Taqsimot, _ketgan_xodimda),
    "yorliq_yoq": Bayroq("Yorlig'i chop etilmagan", AV, _yorliq_yoq),
    "yorliq_almashtirish": Bayroq("Yorliqni almashtirish kerak", AV, _yorliq_almashtirish),
    "muddat_tugagan": Bayroq("Xizmat muddati tugagan", AV, _muddat_tugagan),
    "muddat_6oy": Bayroq("6 oyda tugaydi", AV, _muddat_6oy),
    "chiqim_kutilmoqda": Bayroq("1C chiqimi kutilmoqda", ChiqimHujjat, _chiqim_kutilmoqda),
}


def bayroq_sonlari(user, bugun: date) -> dict[str, int]:
    """Har bayroq bo'yicha obyektlar soni (AV yoki taqsimot qatorlari)."""
    sonlar = {}
    for kalit, bayroq in BAYROQLAR.items():
        natija = bayroq.so_rov(user, bugun)
        sonlar[kalit] = len(natija) if isinstance(natija, list) else natija.count()
    return sonlar
