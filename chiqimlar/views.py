from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor, ruxsat_filial_idlar
from hisoblar.parametrlar import son
from onec.models import Filial
from panel.saralash import Saralash
from vositalar.filtrlar import korinadigan_av_idlari
from vositalar.models import Bolim, Holat

from .models import ChiqimHujjat
from .servis import ChiqimXato, chiqim_tarixi, taqsimot_qatorlari, tasdiqla, tasdiqni_qaytar, taxmin_qil

SAHIFA_HAJMI = 50
NOL = Decimal("0")


def _sana(qiymat) -> date | None:
    try:
        return date.fromisoformat((qiymat or "").strip())
    except ValueError:
        return None


CHIQIM_USTUNLARI = {
    "sana": "sana", "hujjat": "hujjat_raqami", "av": "av__nomi", "filial": "filial__nomi", "soni": "soni",
    "summa": "summa", "tur": "taxmin_tur", "holat": "holat",
}


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


@amal_kerak("chiqim_korish")
def royxat(request):
    qs, holat = _royxat_qs(request)
    ustunlar = {k: v for k, v in CHIQIM_USTUNLARI.items() if k != "summa" or huquqi_bor(request.user, "pul_korish")}
    saralash = Saralash(request, ustunlar)
    sahifa = Paginator(saralash.queryset(qs), SAHIFA_HAJMI).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    korinadigan = korinadigan_av_idlari(request.user, {c.av_id for c in sahifa})
    javob = render(request, "chiqimlar/royxat.html", {
        "sahifa": sahifa, "korinadigan_av": korinadigan, "params": request.GET, "holat": holat, "query": params.urlencode(),
        "taqsim_huquqi": huquqi_bor(request.user, "taqsimot"), "saralash": saralash,
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
    # B filial ruxsat etilganlar bilan cheklanmaydi (spec §6.5): faqat B'ga joylash uchun B ruxsat etilgan bo'lishi kerak.
    b_filiallar = Filial.objects.exclude(pk=chiqim.filial_id).order_by("nomi")
    kontekst = {
        "chiqim": chiqim, "qatorlar": qatorlar, "turlar": ChiqimHujjat.Tur.choices, "holatlar": Holat.choices,
        "b_filiallar": b_filiallar,
        "b_bolimlar": filial_bilan_chekla(Bolim.objects.filter(faol=True), request.user)
        .select_related("filial", "ota").order_by("filial__nomi", "nomi"),
    }
    kontekst.update(qosh)
    return kontekst


@amal_kerak("chiqim_korish")
def tasdiqlash(request, pk):
    chiqim = filial_bilan_chekla(ChiqimHujjat.objects.select_related("av", "filial", "qabul_filial", "kim"), request.user).filter(pk=pk).first()
    if chiqim is None:
        raise Http404
    tarix = chiqim_tarixi(chiqim)
    if chiqim.holat != ChiqimHujjat.Holat.KUTILMOQDA:
        if request.method == "POST":
            messages.warning(
                request,
                "Bu chiqim 1C'da bekor qilingan." if chiqim.holat == ChiqimHujjat.Holat.BEKOR
                else "Bu chiqim allaqachon tasdiqlangan.",
            )
        return render(request, "chiqimlar/tasdiqlash.html", {
            "chiqim": chiqim, "faqat_oqish": True, "tarix": tarix,
            "qaytara_oladi": huquqi_bor(request.user, "taqsimot")
            and chiqim.holat in (ChiqimHujjat.Holat.TASDIQLANGAN, ChiqimHujjat.Holat.BEKOR_1C),
        })
    if not huquqi_bor(request.user, "taqsimot"):
        if request.method == "POST":
            raise PermissionDenied
        return render(request, "chiqimlar/tasdiqlash.html", {
            "chiqim": chiqim, "faqat_oqish": True, "qatorlar": taqsimot_qatorlari(chiqim), "tarix": tarix,
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
            if not (request.POST.get("kutilgan_soni") or "").strip():
                raise _FormaXato("Chiqim soni ko'rsatilmagan. Sahifani yangilang.")
            kutilgan = _decimal(request.POST.get("kutilgan_soni"), "Chiqim soni")
            sonlar = {q.pk: _decimal(q.kiritilgan, "Soni") for q in qatorlar}
            qabul = bolim = None
            if tur == ChiqimHujjat.Tur.OTKAZISH:
                qabul = Filial.objects.exclude(pk=chiqim.filial_id).filter(pk=son(b_pk) or 0).first()
                if qabul is None:
                    raise ChiqimXato("Qabul qiluvchi filialni tanlang (chiqim filialidan boshqa).")
                if request.POST.get("b_bolim"):
                    ruxsat = ruxsat_filial_idlar(request.user)
                    if ruxsat is not None and qabul.pk not in ruxsat:
                        raise ChiqimXato("Bo'limga joylash uchun qabul qiluvchi filial sizga ruxsat etilgan bo'lishi kerak.")
                    bolim = Bolim.objects.filter(pk=son(request.POST.get("b_bolim")) or 0, filial=qabul, faol=True).first()
                    if bolim is None:
                        raise ChiqimXato("Bo'lim qabul qiluvchi filialga tegishli bo'lishi kerak.")
            joylandi = tasdiqla(
                chiqim, tur, sonlar, request.user, kutilgan_soni=kutilgan, qabul_filial=qabul, b_bolim=bolim,
                b_holat=request.POST.get("b_holat", "") if bolim else "", izoh=request.POST.get("izoh", "")[:2000],
            )
        except (ChiqimXato, _FormaXato) as xato:
            return render(
                request, "chiqimlar/tasdiqlash.html", _tasdiqlash_kontekst(request, chiqim, qatorlar, xato=str(xato), **qosh),
                status=400,
            )
        messages.success(request, "Chiqim tasdiqlandi.")
        if bolim is not None and joylandi < chiqim.soni:
            messages.warning(
                request,
                f"B filialda taqsimlanmagan {chiqim.soni:f} dona topilmadi, joylandi: {joylandi:f}. "
                "Qolganini taqsimot sahifasidan joylashtiring.",
            )
        return redirect("chiqimlar:royxat")

    taxmin_b = None
    if chiqim.taxmin_tur == ChiqimHujjat.Tur.OTKAZISH:
        _, taxmin_b = taxmin_qil(chiqim.av_id, chiqim.filial_id, chiqim.sana, chiqim.hujjat_turi)
    if len(qatorlar) == 1:
        qatorlar[0].kiritilgan = f"{min(chiqim.soni, qatorlar[0].soni):.3f}".rstrip("0").rstrip(".")
    return render(request, "chiqimlar/tasdiqlash.html", _tasdiqlash_kontekst(
        request, chiqim, qatorlar, tanlangan_tur=chiqim.taxmin_tur, tanlangan_b=taxmin_b, tanlangan_bolim=None,
        tanlangan_holat="", izoh="", tarix=tarix,
    ))


@require_POST
@amal_kerak("taqsimot")
def qaytar(request, pk):
    """«Tasdiqni qaytarish» (1C'da bekor qilingan) yoki «Tasdiqni bekor qilish» (xato tasdiqni tuzatish)."""
    chiqim = filial_bilan_chekla(ChiqimHujjat.objects.all(), request.user).filter(pk=pk).first()
    if chiqim is None:
        raise Http404
    try:
        yangi = tasdiqni_qaytar(chiqim, request.user)
    except ChiqimXato as xato:
        messages.error(request, str(xato))
    else:
        messages.success(
            request,
            "Tasdiq bekor qilindi — donalar joyiga qaytdi, chiqimni qaytadan tasdiqlang."
            if yangi == ChiqimHujjat.Holat.KUTILMOQDA
            else "Tasdiq qaytarildi — AV avvalgi bo'lim va javobgar shaxsiga qo'yildi.",
        )
    return redirect("chiqimlar:tasdiqlash", pk=pk)
