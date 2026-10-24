"""Chiziqli amortizatsiya va qiymat hisoblari (spec §5.3). Toza funksiyalar — bazaga faqat `samarali_muddat` tegadi."""
import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ObjectDoesNotExist

NOL = Decimal("0")
YUZ = Decimal("100")
TIYIN = Decimal("0.01")


@dataclass(frozen=True)
class Amortizatsiya:
    oylar: int
    qoldiq_qiymat: Decimal
    eskirish_foiz: Decimal
    tugash_sanasi: date


def dona_narxi(summa: Decimal, soni: Decimal) -> Decimal:
    """Bir dona narxi = summa / soni (yaxlitlanmaydi: qator qiymatini chaqiruvchi yaxlitlaydi). soni <= 0 -> 0."""
    if soni <= 0:
        return NOL
    return summa / soni


def oy_qosh(sana: date, oylar: int) -> date:
    """`sana` + `oylar` oy; kun oyning oxirgi kunidan oshsa, oy oxiriga qirqiladi (31-yanvar + 1 oy = 28/29-fevral)."""
    jami = sana.year * 12 + (sana.month - 1) + oylar
    yil, oy = divmod(jami, 12)
    oy += 1
    return date(yil, oy, min(sana.day, calendar.monthrange(yil, oy)[1]))


def _toliq_oylar(boshlanish: date, bugun: date) -> int:
    oylar = (bugun.year - boshlanish.year) * 12 + bugun.month - boshlanish.month
    if bugun.day < boshlanish.day:
        oylar -= 1
    return max(0, oylar)


def hisobla(summa: Decimal, ishga_tushgan: date | None, muddat_oy: int | None, bugun: date) -> Amortizatsiya | None:
    """Chiziqli amortizatsiya. Sana yoki muddat noma'lum (yo'q/0) bo'lsa — None («hisoblab bo'lmaydi»)."""
    if ishga_tushgan is None or not muddat_oy:
        return None
    oylar = _toliq_oylar(ishga_tushgan, bugun)
    otgan = min(oylar, muddat_oy)  # muddatdan keyin qiymat manfiy bo'lmaydi, eskirish 100% dan oshmaydi
    qoldiq = summa * (muddat_oy - otgan) / muddat_oy
    eskirish = Decimal(otgan) * YUZ / muddat_oy
    return Amortizatsiya(
        oylar=oylar,
        qoldiq_qiymat=qoldiq.quantize(TIYIN, rounding=ROUND_HALF_UP),
        eskirish_foiz=eskirish.quantize(TIYIN, rounding=ROUND_HALF_UP),
        tugash_sanasi=oy_qosh(ishga_tushgan, muddat_oy),
    )


def samarali_muddat(kartochka) -> int | None:
    """Xizmat muddati (oy): avval kartochkadagi, bo'lmasa AV turi sozlamasidagi; ikkalasi ham yo'q bo'lsa None."""
    if kartochka.xizmat_muddati_oy:
        return kartochka.xizmat_muddati_oy
    turi = kartochka.av.turi
    if turi is None:
        return None
    try:
        return turi.sozlama.xizmat_muddati_oy or None
    except ObjectDoesNotExist:
        return None
