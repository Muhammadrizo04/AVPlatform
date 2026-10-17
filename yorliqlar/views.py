from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak
from onec.models import AV
from vositalar.bayroqlar import BAYROQLAR
from vositalar.filtrlar import av_filtrla
from vositalar.models import YorliqOlchami

from . import servis

MAX_NUSXA = 500
MAX_SAHIFA = 2000  # bitta PDF'dagi jami yorliqlar
MAX_AV = 300  # tanlash sahifasida ko'rsatiladigan AV'lar


def _son(qiymat) -> bool:
    """Faqat ASCII raqamlar ("²" kabi Unicode raqamlar int() da xato beradi)."""
    return qiymat.isascii() and qiymat.isdigit()


def _idlar(royxat) -> list[int]:
    return [int(x) for x in royxat if _son(x)]


def _avlar(request, idlar, bolim="", bayroq=""):
    """Foydalanuvchi ko'ra oladigan AV'lar (manba: id'lar / bo'lim / bayroq), kalit uchun `filial_rekvizit` bilan."""
    if not (idlar or bolim or bayroq):
        return AV.objects.none()
    params = {}
    if bolim:
        if not _son(bolim):
            return AV.objects.none()
        params["bolim"] = bolim
    if bayroq:
        if bayroq not in BAYROQLAR:
            return AV.objects.none()
        params["bayroq"] = bayroq
    qs = av_filtrla(AV.objects.all(), params, request.user).select_related("filial_rekvizit")
    if idlar:
        qs = qs.filter(pk__in=idlar)
    return qs.order_by("nomi", "pk")


def _nusxa(av) -> int:
    return min(max(int(av.jami_soni), 1), MAX_NUSXA)


@amal_kerak("yorliq")
def tanlash(request):
    """Yorliq chop etishdan oldin: manba (AV'lar / bo'lim / bayroq), nusxalar soni va o'lcham tanlanadi."""
    manba = request.POST if request.method == "POST" else request.GET  # POST: ro'yxatdagi tanlov formasi
    avlar = list(_avlar(request, _idlar(manba.getlist("av")), manba.get("bolim", ""), manba.get("bayroq", "")))
    if manba.getlist("av") and not avlar:
        raise Http404  # tanlangan AV'larning birortasi ham ko'rinmaydi
    olchamlar = list(YorliqOlchami.objects.filter(faol=True).order_by("eni_mm", "boyi_mm", "pk"))
    try:
        standart = YorliqOlchami.standarti().pk
    except YorliqOlchami.DoesNotExist as xato:
        standart = None
        messages.error(request, str(xato))
    if len(avlar) > MAX_AV:
        messages.error(request, f"AV'lar juda ko'p ({len(avlar)} ta, ko'pi bilan {MAX_AV}). Filtrni toraytiring.")
        avlar = []
    elementlar = [{"av": av, "nusxa": _nusxa(av), "kalitsiz": av.kalit is None} for av in avlar]
    return render(
        request,
        "yorliqlar/tanlash.html",
        {"elementlar": elementlar, "olchamlar": olchamlar, "standart": standart, "max_nusxa": MAX_NUSXA},
    )


@require_POST
@amal_kerak("yorliq")
def pdf(request):
    olcham_id = (_idlar([request.POST.get("olcham", "")]) or [0])[0]
    olcham = YorliqOlchami.objects.filter(pk=olcham_id, faol=True).first()
    if olcham is None:
        raise Http404
    idlar = _idlar(request.POST.getlist("av"))
    avlar = {av.pk: av for av in _avlar(request, idlar)}
    if idlar and len(avlar) != len(set(idlar)):
        raise Http404  # ko'rinmaydigan AV so'ralgan
    orqaga = redirect(reverse("yorliqlar:tanlash") + "?" + "&".join(f"av={pk}" for pk in avlar))
    if not avlar:
        messages.error(request, "AV tanlanmagan.")
        return orqaga

    elementlar = []
    for pk, av in avlar.items():
        qiymat = (request.POST.get(f"nusxa_{pk}") or "").strip()
        if not _son(qiymat) or not 1 <= int(qiymat) <= MAX_NUSXA:
            messages.error(request, f"{av.nomi}: nusxalar soni 1 dan {MAX_NUSXA} gacha bo'lishi kerak.")
            return orqaga
        elementlar.append((av, int(qiymat)))
    jami = sum(n for _, n in elementlar)
    if jami > MAX_SAHIFA:
        messages.error(request, f"Jami yorliqlar soni {jami} ta, ko'pi bilan {MAX_SAHIFA} ta bo'lishi mumkin.")
        return orqaga
    try:
        baytlar = servis.yorliq_pdf(elementlar, olcham)
    except ValueError as xato:
        messages.error(request, str(xato))
        return orqaga
    servis.chop_etildi([av for av, _ in elementlar], request.user)  # faqat PDF muvaffaqiyatli yaratilgach
    javob = HttpResponse(baytlar, content_type="application/pdf")
    javob["Content-Disposition"] = 'inline; filename="yorliqlar.pdf"'
    return javob
