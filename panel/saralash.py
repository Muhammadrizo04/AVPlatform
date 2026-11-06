"""Ro'yxatlarni ustun bo'yicha saralash: `?tartib=<kalit>` (o'suvchi) yoki `?tartib=-<kalit>` (kamayuvchi).

View ustunlar xaritasini beradi: kalit -> queryset uchun maydon/ifoda yoki Python ro'yxati uchun funksiya. Noma'lum
kalit e'tiborsiz qoldiriladi (standart tartib). Sarlavha havolalarini `{% saralash_ustuni %}` tegi chizadi.
"""
from django.db.models import F


class Saralash:
    def __init__(self, request, ustunlar: dict, standart: str = ""):
        self.ustunlar = ustunlar
        qiymat = request.GET.get("tartib", "") or standart
        teskari = qiymat.startswith("-")
        kalit = qiymat[1:] if teskari else qiymat
        if kalit not in ustunlar:
            kalit, teskari = (standart.lstrip("-"), standart.startswith("-")) if standart else ("", False)
        self.kalit, self.teskari = kalit, teskari

    @property
    def tanlangan(self) -> bool:
        return bool(self.kalit)

    def queryset(self, qs, *, qoshimcha=("pk",)):
        """Tanlangan ustun bo'yicha; bo'sh qiymatlar har doim oxirida, teng qatorlar `qoshimcha` bo'yicha barqaror."""
        if not self.kalit:
            return qs
        ifoda = self.ustunlar[self.kalit]
        ifoda = F(ifoda) if isinstance(ifoda, str) else ifoda
        tartib = ifoda.desc(nulls_last=True) if self.teskari else ifoda.asc(nulls_last=True)
        return qs.order_by(tartib, *qoshimcha)

    def royxat(self, elementlar):
        """Python ro'yxati uchun: ustun qiymati funksiyasi; None qiymatlar har doim oxirida."""
        if not self.kalit:
            return list(elementlar)
        kalit_fn = self.ustunlar[self.kalit]
        bor = [e for e in elementlar if kalit_fn(e) is not None]
        yoq = [e for e in elementlar if kalit_fn(e) is None]
        return sorted(bor, key=kalit_fn, reverse=self.teskari) + yoq
