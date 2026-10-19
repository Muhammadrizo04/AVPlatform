from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from hisoblar.parametrlar import son
from onec.models import Filial
from vositalar.models import Bolim, Holat

from .models import ChiqimHujjat
from .servis import ChiqimXato, taqsimot_qatorlari, taxmin_qil, tasdiqla

SAHIFA_HAJMI = 50
NOL = Decimal("0")


def _sana(qiymat) -> date | None:
    try:
        return date.fromisoformat((qiymat or "").strip())
    except ValueError:
        return None


def _royxat_qs(request):
    qs = filial_bilan_chekla(ChiqimHujjat.objects.all(), request.user).select_related("av", "filial")
    holat = request.GET.get("holat")
    if holat is None or holat not in {*ChiqimHujjat.Holat.values, ""}:
        holat = ChiqimHujjat.Holat.KUTILMOQDA
    if holat:
        qs = qs.filter(holat=holat)
    tur = request.GET.get("tur")
    if tur in ChiqimHujjat.Tur.values:
        # Tasdiqlanganda haqiqiy tur, aks holda taxmin bo'yicha.
        tasdiq = ChiqimHujjat.Holat.TASDIQLANGAN
        qs = qs.filter(Q(holat=tasdiq, tur=tur) | (~Q(holat=tasdiq) & Q(taxmin_tur=tur)))
    filial = son(request.GET.get("filial"))
    if filial is not None:
        qs = qs.filter(filial_id=filial)
    dan, gacha = _sana(request.GET.get("dan")), _sana(request.GET.get("gacha"))
    if dan:
        qs = qs.filter(sana__date__gte=dan)
    if gacha:
        qs = qs.filter(sana__date__lte=gacha)
    return qs, holat


@amal_kerak("korish")
def royxat(request):
    qs, holat = _royxat_qs(request)
    sahifa = Paginator(qs, SAHIFA_HAJMI).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    javob = render(request, "chiqimlar/royxat.html", {
        "sahifa": sahifa, "params": request.GET, "holat": holat, "query": params.urlencode(),
        "taqsim_huquqi": huquqi_bor(request.user, "taqsimot"),
        "holatlar": ChiqimHujjat.Holat.choices, "turlar": ChiqimHujjat.Tur.choices,
        "filiallar": filial_bilan_chekla(Filial.objects.all(), request.user, "pk").order_by("nomi"),
    })
    patch_vary_headers(javob, ["HX-Request"])
    return javob


class _FormaXato(Exception):
    pass


def _decimal(qiymat, nom: str) -> Decimal:
    qiymat = (qiymat or "").strip().replace(",", ".")
    if not qiymat:
        return NOL
    if len(qiymat) > 30 or not qiymat.isascii():
        raise _FormaXato(f"{nom}: sonni to'g'ri kiriting.")
    try:
        d = Decimal(qiymat)
    except InvalidOperation:
        raise _FormaXato(f"{nom}: sonni to'g'ri kiriting.") from None
    if not d.is_finite():
        raise _FormaXato(f"{nom}: sonni to'g'ri kiriting.")
    return d


def _tasdiqlash_kontekst(request, chiqim, qatorlar, **qosh):
    ruxsat = filial_bilan_chekla(Filial.objects.exclude(pk=chiqim.filial_id), request.user, "pk").order_by("nomi")
    kontekst = {
        "chiqim": chiqim, "qatorlar": qatorlar, "turlar": ChiqimHujjat.Tur.choices, "holatlar": Holat.choices,
        "b_filiallar": ruxsat,
        "b_bolimlar": filial_bilan_chekla(Bolim.objects.filter(faol=True), request.user)
        .select_related("filial", "ota").order_by("filial__nomi", "nomi"),
    }
    kontekst.update(qosh)
    return kontekst


@amal_kerak("korish")
def tasdiqlash(request, pk):
    chiqim = filial_bilan_chekla(ChiqimHujjat.objects.select_related("av", "filial", "qabul_filial", "kim"), request.user).filter(pk=pk).first()
    if chiqim is None:
        raise Http404
    if chiqim.holat != ChiqimHujjat.Holat.KUTILMOQDA:
        if request.method == "POST":
            messages.warning(
                request,
                "Bu chiqim 1C'da bekor qilingan." if chiqim.holat == ChiqimHujjat.Holat.BEKOR
                else "Bu chiqim allaqachon tasdiqlangan.",
            )
        return render(request, "chiqimlar/tasdiqlash.html", {"chiqim": chiqim, "faqat_oqish": True})
    if not huquqi_bor(request.user, "taqsimot"):
        if request.method == "POST":
            raise PermissionDenied
        return render(request, "chiqimlar/tasdiqlash.html", {
            "chiqim": chiqim, "faqat_oqish": True, "qatorlar": taqsimot_qatorlari(chiqim),
        })
    qatorlar = taqsimot_qatorlari(chiqim)

    if request.method == "POST":
        for q in qatorlar:
            q.kiritilgan = request.POST.get(f"soni_{q.pk}", "")
        tur = request.POST.get("tur", "")
        b_pk = request.POST.get("qabul_filial", "")
        qosh = {
            "tanlangan_tur": tur, "tanlangan_b": son(b_pk), "tanlangan_bolim": son(request.POST.get("b_bolim")),
            "tanlangan_holat": request.POST.get("b_holat", ""), "izoh": request.POST.get("izoh", ""),
        }
        try:
            kutilgan = _decimal(request.POST.get("kutilgan_soni"), "Chiqim soni")
            sonlar = {q.pk: _decimal(q.kiritilgan, "Soni") for q in qatorlar}
            qabul = bolim = None
            if tur == ChiqimHujjat.Tur.OTKAZISH:
                qabul = filial_bilan_chekla(Filial.objects.exclude(pk=chiqim.filial_id), request.user, "pk") \
                    .filter(pk=son(b_pk) or 0).first()
                if qabul is None:
                    raise ChiqimXato("Qabul qiluvchi filialni tanlang (ruxsat etilgan, chiqim filialidan boshqa).")
                if request.POST.get("b_bolim"):
                    bolim = Bolim.objects.filter(pk=son(request.POST.get("b_bolim")) or 0, filial=qabul, faol=True).first()
                    if bolim is None:
                        raise ChiqimXato("Bo'lim qabul qiluvchi filialga tegishli bo'lishi kerak.")
            tasdiqla(
                chiqim, tur, sonlar, request.user, kutilgan_soni=kutilgan, qabul_filial=qabul, b_bolim=bolim,
                b_holat=request.POST.get("b_holat", "") if bolim else "", izoh=request.POST.get("izoh", "")[:2000],
            )
        except (ChiqimXato, _FormaXato) as xato:
            return render(
                request, "chiqimlar/tasdiqlash.html", _tasdiqlash_kontekst(request, chiqim, qatorlar, xato=str(xato), **qosh),
                status=400,
            )
        messages.success(request, "Chiqim tasdiqlandi.")
        return redirect("chiqimlar:royxat")

    taxmin_b = None
    if chiqim.taxmin_tur == ChiqimHujjat.Tur.OTKAZISH:
        _, taxmin_b = taxmin_qil(chiqim.av_id, chiqim.filial_id, chiqim.sana, chiqim.hujjat_turi)
    if len(qatorlar) == 1:
        qatorlar[0].kiritilgan = f"{min(chiqim.soni, qatorlar[0].soni):.3f}".rstrip("0").rstrip(".")
    return render(request, "chiqimlar/tasdiqlash.html", _tasdiqlash_kontekst(
        request, chiqim, qatorlar, tanlangan_tur=chiqim.taxmin_tur, tanlangan_b=taxmin_b, tanlangan_bolim=None,
        tanlangan_holat="", izoh="",
    ))
