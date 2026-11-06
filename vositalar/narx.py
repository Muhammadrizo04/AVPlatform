"""Bir dona narxi filial bo'yicha. Bir AV turli filialda turli qiymatda bo'lishi mumkin (har filialda o'z 1C qoldig'i):
umumiy o'rtacha filial hisoboti bilan bo'lim, qaydnoma va akt raqamlarini bir-biriga mos kelmaydigan qilardi."""
from collections.abc import Callable, Iterable
from decimal import Decimal

from django.db.models import Sum

from onec.models import AVQoldiq

from .amortizatsiya import dona_narxi

NOL = Decimal("0")


def filial_narxlari(av_idlar: Iterable[int]) -> Callable[[int, int], Decimal]:
    """Bitta so'rov; `narx(av_id, filial_id)` qaytaradi. Faqat musbat sonli qoldiqlar: soni 0, summasi bor 1C qatori
    narxni oshirmaydi (filial hisoboti ham ularni olmaydi). Shu filialda qoldiq yo'q bo'lsa (masalan, chiqim tasdiq
    kutmoqda) — AV'ning umumiy o'rtachasi, u ham yo'q bo'lsa — 0."""
    qatorlar = (
        AVQoldiq.objects.filter(av_id__in=list(av_idlar), soni__gt=0)
        .order_by().values_list("av_id", "filial_id").annotate(soni_jami=Sum("soni"), summa_jami=Sum("summa"))
    )
    filial_boyicha, umumiy = {}, {}
    for av_id, filial_id, soni, summa in qatorlar:
        filial_boyicha[(av_id, filial_id)] = dona_narxi(summa, soni)
        jami_summa, jami_soni = umumiy.get(av_id, (NOL, NOL))
        umumiy[av_id] = (jami_summa + summa, jami_soni + soni)

    def narx(av_id: int, filial_id: int) -> Decimal:
        topilgan = filial_boyicha.get((av_id, filial_id))
        if topilgan is not None:
            return topilgan
        return dona_narxi(*umumiy.get(av_id, (NOL, NOL)))

    return narx
