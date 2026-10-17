from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from hisobotlar.excel import jadval_xlsx
from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor, ruxsat_filial_idlar
from onec.models import AV, AVTuri, Filial, Xodim

from . import amallar
from .bayroqlar import BAYROQLAR
from .filtrlar import av_filtrla
from .models import Bolim, Holat, Taqsimot

SAHIFA_HAJMI = 50
SARLAVHALAR = ["Inv. raqam", "Nomi", "Turi", "Filial", "Soni", "Summa"]


def _royxat_qs(request):
    qs = av_filtrla(AV.objects.all(), request.GET, request.user)
    return qs.select_related("turi", "filial_rekvizit").order_by("nomi", "pk")


def _filtr_soz_parametrlari(request) -> str:
    """Sahifalash havolalari uchun `page`siz query string."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


@amal_kerak("korish")
def royxat(request):
    sahifa = Paginator(_royxat_qs(request), SAHIFA_HAJMI).get_page(request.GET.get("page"))
    taqsim_huquqi = huquqi_bor(request.user, "taqsimot")
    kontekst = {
        "sahifa": sahifa,
        "params": request.GET,
        "query": _filtr_soz_parametrlari(request),
        "taqsim_huquqi": taqsim_huquqi,
        "holatlar": Holat.choices,
    }
    if request.headers.get("HX-Request"):
        if taqsim_huquqi:
            kontekst["bolimlar"] = _bolimlar(request.user)
        javob = render(request, "vositalar/_jadval.html", kontekst)
        patch_vary_headers(javob, ["HX-Request"])
        return javob
    kontekst.update(
        filiallar=filial_bilan_chekla(Filial.objects.all(), request.user, "pk").order_by("nomi"),
        turlar=AVTuri.objects.order_by("nomi"),
        xodimlar=filial_bilan_chekla(Xodim.objects.filter(ochirilgan=False), request.user, "filial").order_by("ism"),
        bayroqlar=[(kalit, b.nomi) for kalit, b in BAYROQLAR.items()],
        bolimlar=_bolimlar(request.user),
    )
    javob = render(request, "vositalar/royxat.html", kontekst)
    patch_vary_headers(javob, ["HX-Request"])
    return javob


def _bolimlar(user):
    qs = filial_bilan_chekla(Bolim.objects.filter(faol=True), user)
    return qs.select_related("filial", "ota").order_by("filial__nomi", "nomi")


@amal_kerak("hisobot")
def royxat_excel(request):
    qatorlar = (
        (
            av.inv_raqam,
            av.nomi,
            av.turi.nomi if av.turi else "",
            av.filial_rekvizit.nomi if av.filial_rekvizit else "",
            av.jami_soni,
            av.jami_summa,
        )
        for av in _royxat_qs(request)
    )
    javob = HttpResponse(
        jadval_xlsx(SARLAVHALAR, qatorlar),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    javob["Content-Disposition"] = 'attachment; filename="asosiy_vositalar.xlsx"'
    return javob


@require_POST
@amal_kerak("taqsimot")
def ommaviy(request):
    """Tanlangan AV'larga ommaviy amal (ko'chirish / holat). Faqat 1 donali va bitta taqsimot qatorli AV'lar."""
    amal = request.POST.get("amal")
    keyingi = request.POST.get("keyingi", "")
    if not url_has_allowed_host_and_scheme(keyingi, allowed_hosts={request.get_host()}):
        keyingi = reverse("vositalar:royxat")
    orqaga = redirect(keyingi)
    idlar = [int(x) for x in request.POST.getlist("av") if x.isdigit()]
    bolim = holat = None
    if amal == "kochirish":
        bolim = filial_bilan_chekla(Bolim.objects.all(), request.user).filter(pk=request.POST.get("bolim") or 0).first()
        if bolim is None:
            messages.error(request, "Bo'limni tanlang.")
            return orqaga
    elif amal == "holat":
        holat = request.POST.get("holat")
        if holat not in Holat.values:
            messages.error(request, "Holatni tanlang.")
            return orqaga
    else:
        messages.error(request, "Amalni tanlang.")
        return orqaga
    if not idlar:
        messages.error(request, "AV tanlanmagan.")
        return orqaga

    # Faqat foydalanuvchi ro'yxatda ko'ra oladigan AV'lar (filial cheklovi queryset darajasida).
    avlar = av_filtrla(AV.objects.all(), {}, request.user).filter(pk__in=idlar).prefetch_related("taqsimotlar")
    bajarildi, otkazildi = 0, []
    for av in avlar:
        qatorlar = [t for t in av.taqsimotlar.all()]
        if av.jami_soni != Decimal("1") or len(qatorlar) != 1:
            otkazildi.append(f"{av.nomi} (guruh yoki bir nechta taqsimot)")
            continue
        qator: Taqsimot = qatorlar[0]
        ruxsat = ruxsat_filial_idlar(request.user)
        if ruxsat is not None and qator.filial_id not in ruxsat:
            otkazildi.append(f"{av.nomi} (filial ruxsat etilmagan)")
            continue
        try:
            if amal == "kochirish":
                amallar.kochir(qator, qator.soni, bolim, request.user)
            else:
                amallar.holat_ozgartir(qator, qator.soni, holat, request.user)
            bajarildi += 1
        except amallar.AmalXato as xato:
            otkazildi.append(f"{av.nomi} ({xato})")
    if bajarildi:
        messages.success(request, f"{bajarildi} ta AV yangilandi.")
    if otkazildi:
        messages.warning(request, "O'tkazib yuborildi: " + "; ".join(otkazildi))
    return orqaga
