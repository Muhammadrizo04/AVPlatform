"""Ro'yxatlarni sahifalash: sahifa raqamlari (boshi, oxiri va yaqinlari) va «bir sahifada N qator».

`hajm` GET parametridan olinadi va shu ro'yxat (view) uchun sessiyada eslab qolinadi — filtr formasi yuborilganda
yoki boshqa sahifaga o'tib qaytganda ham tanlangan son saqlanadi. Shablon: `panel/_sahifalash.html`.
"""
from django.core.paginator import Page, Paginator

ENG_KAM, ENG_KOP = 1, 500  # bir sahifadagi qatorlar chegarasi (500 dan ko'pi sahifani og'irlashtiradi)
TAKLIFLAR = (10, 25, 50, 100, 200)


def _hajm_qiymati(matn) -> int | None:
    try:
        return min(max(int(str(matn).strip()), ENG_KAM), ENG_KOP)
    except (TypeError, ValueError):
        return None


def sahifa_hajmi(request, standart: int) -> int:
    """GET `hajm` (chegaralangan) -> sessiyaga yoziladi; bo'lmasa sessiyadagi yoki `standart`."""
    kalit = f"sahifa_hajmi:{request.resolver_match.view_name if request.resolver_match else request.path}"
    hajm = _hajm_qiymati(request.GET.get("hajm"))
    if hajm is not None:
        request.session[kalit] = hajm
        return hajm
    return _hajm_qiymati(request.session.get(kalit)) or standart


def sahifala(request, qatorlar, standart: int = 50) -> Page:
    """`qatorlar` (queryset yoki ro'yxat) dan joriy sahifa. Sahifaga `hajm` va `raqamlar` (… — `None`) qo'shiladi."""
    hajm = sahifa_hajmi(request, standart)
    sahifa = Paginator(qatorlar, hajm).get_page(request.GET.get("page"))
    sahifa.hajm = hajm
    sahifa.takliflar = TAKLIFLAR
    sahifa.raqamlar = [
        None if r == Paginator.ELLIPSIS else r
        for r in sahifa.paginator.get_elided_page_range(sahifa.number, on_each_side=2, on_ends=1)
    ]
    return sahifa
