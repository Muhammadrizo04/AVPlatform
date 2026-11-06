from .models import Jurnal

SINXRON_NOMI = "1C sinxron"


def _matn(qiymat) -> str:
    """Qiymatni jurnal uchun matnga aylantiradi; None — bo'sh qator."""
    return "" if qiymat is None else str(qiymat)


def yoz(kim, obyekt, maydon: str, eski, yangi, kim_nomi: str | None = None) -> Jurnal:
    """Bitta maydon o'zgarishini jurnalga yozadi. `kim=None` — 1C sinxron, boshqa manba bo'lsa `kim_nomi` beriladi."""
    if kim_nomi is None:
        kim_nomi = SINXRON_NOMI if kim is None else kim.get_full_name() or kim.get_username()
    return Jurnal.objects.create(
        kim=kim,
        kim_nomi=kim_nomi,
        obyekt_turi=obyekt._meta.label_lower,
        obyekt_id=str(obyekt.pk),
        maydon=maydon,
        eski=_matn(eski),
        yangi=_matn(yangi),
    )
