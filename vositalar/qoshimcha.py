"""AV turi bo'yicha qo'shimcha maydonlarni tekshirish (spec §7.4). Toza funksiya: bazaga tegmaydi."""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


def _son(matn: str) -> str:
    try:
        qiymat = Decimal(matn.replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        raise ValueError("Son kiriting.")
    if not qiymat.is_finite():
        raise ValueError("Son kiriting.")
    return format(qiymat.normalize(), "f")


def _sana(matn: str) -> str:
    try:
        return date.fromisoformat(matn).isoformat()
    except ValueError:
        raise ValueError("Sanani YYYY-OO-KK ko'rinishida kiriting.")


def qoshimcha_tekshir(maydonlar: list[dict], qiymatlar: dict) -> dict:
    """`maydonlar` (AVTuriSozlama.maydonlar) bo'yicha `qiymatlar` ni tekshirib, tozalangan {kalit: matn} qaytaradi.
    Bo'sh qiymatlar tushirib qoldiriladi; sozlamada yo'q kalitlar e'tiborga olinmaydi. Xato bo'lsa — `ValidationError`
    ({maydon kaliti: [xabar]})."""
    toza, xatolar = {}, {}
    for maydon in maydonlar:
        kalit, nomi, tip = maydon["kalit"], maydon.get("nomi") or maydon["kalit"], maydon.get("tip", "matn")
        qiymat = qiymatlar.get(kalit)
        qiymat = "" if qiymat is None else str(qiymat).strip()
        if not qiymat:
            if maydon.get("majburiy"):
                xatolar[kalit] = [f"«{nomi}» to'ldirilishi shart."]
            continue
        try:
            if tip == "son":
                qiymat = _son(qiymat)
            elif tip == "sana":
                qiymat = _sana(qiymat)
            elif tip == "tanlov" and qiymat not in maydon.get("tanlov_qiymatlari", []):
                raise ValueError("Ro'yxatdan tanlang.")
        except ValueError as xato:
            xatolar[kalit] = [f"«{nomi}»: {xato}"]
            continue
        toza[kalit] = qiymat
    if xatolar:
        raise ValidationError(xatolar)
    return toza
