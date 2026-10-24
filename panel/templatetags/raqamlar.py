"""Sonlarni o'qishga qulay ko'rsatish: mingliklar bo'linmas bo'sh joy bilan, kasr — vergul.

`son` — miqdor (ortiqcha nollarsiz, ko'pi bilan 3 xona), `pul` — summa (doim 2 xona).
Ikkalasi `TEMPLATES.OPTIONS.builtins` orqali hamma shablonda `{% load %}`siz ishlaydi.
Forma maydonlari qiymatiga (`<input value>`) qo'llanmaydi — u yerda mahalliylashtirilmagan son kerak.
"""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()

BO = " "


def _decimal(qiymat):
    if qiymat is None or qiymat == "":
        return None
    try:
        d = Decimal(str(qiymat))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _guruhla(d: Decimal, xona: int) -> str:
    matn = f"{abs(d):,.{xona}f}".replace(",", BO).replace(".", ",")
    return f"-{matn}" if d < 0 else matn


@register.filter
def son(qiymat):
    """1108.000 → «1 108», 571.900 → «571,9»."""
    d = _decimal(qiymat)
    if d is None:
        return "" if qiymat is None else qiymat
    d = d.quantize(Decimal("0.001"), ROUND_HALF_UP)
    matn = _guruhla(d, 3)
    if "," in matn:
        matn = matn.rstrip("0").rstrip(",")
    return "0" if matn in ("-0", "") else matn


@register.filter
def pul(qiymat):
    """3485037435.36 → «3 485 037 435,36»."""
    d = _decimal(qiymat)
    if d is None:
        return "" if qiymat is None else qiymat
    matn = _guruhla(d.quantize(Decimal("0.01"), ROUND_HALF_UP), 2)
    return "0,00" if matn == "-0,00" else matn


@register.filter
def qisqa_pul(qiymat):
    """Grafiklar uchun ixcham summa: 14889668651.05 → «14,89 mlrd», 123456789 → «123,5 mln», 95000 → «95 000»."""
    d = _decimal(qiymat)
    if d is None:
        return "" if qiymat is None else qiymat
    for chegara, birlik, xona in ((Decimal("1e9"), "mlrd", 2), (Decimal("1e6"), "mln", 1)):
        if abs(d) >= chegara:
            matn = _guruhla((d / chegara).quantize(Decimal(1).scaleb(-xona), ROUND_HALF_UP), xona)
            return f"{matn.rstrip('0').rstrip(',')}\xa0{birlik}"
    return son(d.quantize(Decimal("1"), ROUND_HALF_UP))


# 16-19 xonali karta raqami (orasida bo'sh joy yoki chiziqcha bo'lishi mumkin); telefon raqamlari (≤12 xona) tegilmaydi.
KARTA_RAQAMI = re.compile(r"(?<!\d)(?:\d[ -]?){12,15}(\d{4})(?!\d)")


@register.filter
def karta_niqobi(matn):
    """1C erkin matnidagi bank karta raqamini `**** **** **** 1234` ko'rinishiga keltiradi."""
    if not matn:
        return matn
    return KARTA_RAQAMI.sub(lambda m: f"**** **** **** {m.group(1)}", str(matn))


@register.filter
def holat_sinfi(qiymat) -> str:
    """Taqsimot holati (kalit yoki o'zbekcha nomi) -> CSS sinfi qismi (`h-<kalit>`); noma'lum bo'lsa — bo'sh."""
    from vositalar.models import Holat

    if qiymat in Holat.values:
        return qiymat
    return {label: kalit for kalit, label in Holat.choices}.get(str(qiymat), "")
