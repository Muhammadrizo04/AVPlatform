"""So'rov parametrlarini xavfsiz o'qish. Foydalanuvchi kiritgan qiymat hech qachon 500 xatoga olib kelmasligi kerak:
"²" kabi Unicode raqamlar `str.isdigit()` da True, lekin `int()` da xato; juda uzun raqamlar PostgreSQL bigint'ga
sig'maydi; NUL bayt (`\x00`) PostgreSQL matn maydonlarida DataError beradi."""
from django.http import HttpResponseBadRequest

MAX_RAQAM = 18  # bigint (≈9.2·10¹⁸) ga albatta sig'adi


def son(qiymat) -> int | None:
    """Faqat ASCII raqamlardan iborat (ko'pi bilan 18 belgi, chetidagi bo'shliqlar e'tiborsiz) qiymat -> int; aks holda
    None (manfiy, kasr, bo'sh, None ham)."""
    if qiymat is None:
        return None
    qiymat = str(qiymat).strip()
    if not qiymat or len(qiymat) > MAX_RAQAM or not (qiymat.isascii() and qiymat.isdigit()):
        return None
    return int(qiymat)


def _nul_bor(qiymatlar) -> bool:
    for kalit, royxat in qiymatlar.lists():
        if "\x00" in kalit or any("\x00" in q for q in royxat):
            return True
    return False


class NulBaytMiddleware:
    """GET yoki POST kalit/qiymatida NUL bayt bo'lsa — 400 (PostgreSQL'ga yetib bormaydi)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _nul_bor(request.GET) or (request.method == "POST" and _nul_bor(request.POST)):
            return HttpResponseBadRequest("Noto'g'ri so'rov.")
        return self.get_response(request)
