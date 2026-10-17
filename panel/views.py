from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.utils import timezone

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla
from onec.models import AVQoldiq, Filial
from vositalar.amortizatsiya import hisobla, samarali_muddat
from vositalar.bayroqlar import BAYROQLAR, bayroq_sonlari

NOL = Decimal("0")


def _qoldiq_qiymati(qoldiq: AVQoldiq, bugun) -> Decimal:
    """summa × (1 − eskirish); hisoblab bo'lmasa summaning o'zi."""
    try:
        kartochka = qoldiq.av.kartochka
    except ObjectDoesNotExist:
        return qoldiq.summa
    amortizatsiya = hisobla(qoldiq.summa, kartochka.ishga_tushgan_sana, samarali_muddat(kartochka), bugun)
    return qoldiq.summa if amortizatsiya is None else amortizatsiya.qoldiq_qiymat


def filial_kesimi(user, bugun) -> list[dict]:
    """Ruxsat etilgan filiallar bo'yicha: soni, boshlang'ich qiymat (Σ summa), qoldiq qiymat (eskirish bilan)."""
    jamlar = defaultdict(lambda: {"soni": NOL, "boshlangich": NOL, "qoldiq": NOL})
    qoldiqlar = filial_bilan_chekla(AVQoldiq.objects.all(), user).select_related("av__kartochka", "av__turi__sozlama")
    for q in qoldiqlar:
        jam = jamlar[q.filial_id]
        jam["soni"] += q.soni
        jam["boshlangich"] += q.summa
        jam["qoldiq"] += _qoldiq_qiymati(q, bugun)
    filiallar = filial_bilan_chekla(Filial.objects.filter(pk__in=list(jamlar)), user, "pk").order_by("nomi")
    return [{"filial": f, **jamlar[f.pk]} for f in filiallar]


@amal_kerak("korish")
def bosh(request):
    bugun = timezone.localdate()
    sonlar = bayroq_sonlari(request.user, bugun)
    bayroqlar = [{"kalit": k, "nomi": b.nomi, "soni": sonlar[k]} for k, b in BAYROQLAR.items()]
    return render(request, "panel/bosh.html", {"filiallar": filial_kesimi(request.user, bugun), "bayroqlar": bayroqlar})
