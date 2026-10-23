"""Reviziya panel sahifalari (spec §5–§7): ro'yxat, yangi reviziya, vedomost va amallar, Excel, dalolatnoma."""
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import DecimalField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from hisobotlar.excel import jadval_xlsx
from vositalar.models import Holat

from .forms import YangiReviziyaForma
from .models import Reviziya, ReviziyaKutilgan, ReviziyaQayd, ReviziyaQollash
from .pdf import dalolatnoma_pdf
from .qollash import qolla, qollanadimi, reviziya_yop
from .servis import ReviziyaXato, bekor_qil, progress, reviziya_och, yakunla
from .solishtir import BOLIMSIZ, GURUH_NOMLARI, GURUHLAR, bolim_nomlari, guruh_nomi, jamlar, solishtir

SAHIFA_HAJMI = 50
KOMISSIYA_QATORLARI = 3
XLSX_TURI = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HOLAT_NOMLARI = dict(Holat.choices)
# Guruh filtri: har guruh alohida, `kamomad` — kam va topilmadi birga (ko'rsatkich plitkasi)
GURUH_FILTRLARI = {**{g: {g} for g in GURUHLAR}, "kamomad": {"kam", "topilmadi"}}
# Ko'rsatkich plitkalari (spec §5.1: beshta guruh): (filtr, nomi, ikonka, rang sinfi, ogohlantiruvchi)
PLITKALAR = (
    ("topildi", "topildi", "cil-check-circle", "r-bg-pul", False),
    ("kamomad", "kam / topilmadi", "cil-warning", "r-bg-ogoh", True),
    ("boshqa_joyda", "boshqa joyda", "cil-swap-horizontal", "r-bg-vosita", False),
    ("holat_boshqa", "holati boshqa", "cil-loop-circular", "r-bg-mol", False),
    ("ortiqcha", "ortiqcha", "cil-plus", "r-bg-chiqim", False),
)


def _reviziya_yoki_404(request, pk) -> Reviziya:
    reviziya = (
        filial_bilan_chekla(Reviziya.objects.select_related("filial", "bolim", "ochdi"), request.user)
        .filter(pk=pk)
        .first()
    )
    if reviziya is None:
        raise Http404
    return reviziya


def _yigindi(model, **filtr):
    qs = model.objects.filter(reviziya=OuterRef("pk"), **filtr).order_by().values("reviziya").annotate(s=Sum("soni"))
    return Coalesce(Subquery(qs.values("s")), Decimal("0"), output_field=DecimalField(max_digits=18, decimal_places=3))


@amal_kerak("reviziya_korish")
def royxat(request):
    qs = filial_bilan_chekla(Reviziya.objects.select_related("filial", "bolim"), request.user).annotate(
        kutilgan_jami=_yigindi(ReviziyaKutilgan),
        belgilangan_jami=_yigindi(ReviziyaQayd, av__isnull=False),
    )
    holat = request.GET.get("holat", "")
    if holat in Reviziya.Holat.values:
        qs = qs.filter(holat=holat)
    else:
        holat = ""
    sahifa = Paginator(qs.order_by("-raqam"), SAHIFA_HAJMI).get_page(request.GET.get("page"))
    return render(request, "reviziya/royxat.html", {
        "sahifa": sahifa, "holat": holat, "holatlar": Reviziya.Holat.choices,
        "boshqarish": huquqi_bor(request.user, "reviziya_boshqarish"),
    })


def _komissiya(post) -> list[dict]:
    ismlar, lavozimlar = post.getlist("komissiya_ism"), post.getlist("komissiya_lavozim")
    natija = []
    for i, ism in enumerate(ismlar):
        lavozim = lavozimlar[i] if i < len(lavozimlar) else ""
        if ism.strip() or lavozim.strip():
            natija.append({"ism": ism.strip()[:255], "lavozim": lavozim.strip()[:255]})
    return natija


@amal_kerak("reviziya_boshqarish")
def yangi(request):
    xato, status = "", 200
    if request.method == "POST":
        forma = YangiReviziyaForma(request.POST, user=request.user)
        komissiya = _komissiya(request.POST)
        if forma.is_valid():
            d = forma.cleaned_data
            try:
                rv = reviziya_och(d["filial"], d["bolim"], d["revizorlar"], komissiya, request.user, izoh=d["izoh"])
            except ReviziyaXato as e:
                xato = str(e)
            else:
                messages.success(request, f"Reviziya {rv.nomi} ochildi.")
                return redirect("reviziya:sahifa", pk=rv.pk)
        status = 400
    else:
        forma, komissiya = YangiReviziyaForma(user=request.user), []
    qatorlar = komissiya + [{"ism": "", "lavozim": ""}] * max(0, KOMISSIYA_QATORLARI - len(komissiya))
    return render(request, "reviziya/yangi.html", {"forma": forma, "komissiya": qatorlar, "xato": xato}, status=status)


def _qollangan_kalitlar(reviziya) -> set[str]:
    return set(reviziya.qollashlar.filter(natija=ReviziyaQollash.Natija.OK).values_list("kalit", flat=True))


def _nishon_bolim(q, nomlar) -> str:
    if q.guruh != "boshqa_joyda":
        return ""
    return BOLIMSIZ if q.nishon_bolim_id is None else nomlar.get(q.nishon_bolim_id, "")


def _satr(q, nomlar) -> dict:
    return {
        "q": q,
        "guruh_nomi": guruh_nomi(q),
        "holat_nomi": HOLAT_NOMLARI.get(q.holat, q.holat),
        "nishon_bolim": _nishon_bolim(q, nomlar),
        "nishon_holat_nomi": HOLAT_NOMLARI.get(q.nishon_holat, q.nishon_holat),
    }


def _filtrla(qatorlar, params):
    guruh = params.get("guruh", "")
    if guruh in GURUH_FILTRLARI:
        qatorlar = [q for q in qatorlar if q.guruh in GURUH_FILTRLARI[guruh]]
    else:
        guruh = ""
    bolim = params.get("bolim", "")
    if bolim == "bolimsiz":
        qatorlar = [q for q in qatorlar if q.bolim_id is None]
    elif bolim.isdigit():
        b = int(bolim)
        qatorlar = [q for q in qatorlar if b in (q.bolim_id, q.nishon_bolim_id)]
    else:
        bolim = ""
    izla = (params.get("q") or "").strip().casefold()
    if izla:
        qatorlar = [q for q in qatorlar if izla in f"{q.av_nomi}\n{q.inv}\n{q.qr_matn}".casefold()]
    return qatorlar, guruh, bolim


@amal_kerak("reviziya_korish")
def sahifa(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    hammasi = solishtir(rv)
    jami = jamlar(hammasi)
    plitkalar = []
    for filtr, nomi, ikonka, rang, ogoh in PLITKALAR:
        soni = sum((jami[g] for g in GURUH_FILTRLARI[filtr]), Decimal("0"))
        plitkalar.append({"filtr": filtr, "nomi": nomi, "ikonka": ikonka, "rang": rang, "ogoh": ogoh, "soni": soni})
    nomlar = bolim_nomlari(rv.filial_id)
    bolimlar = sorted(
        {(q.bolim_id, q.bolim_nomi) for q in hammasi if q.bolim_id is not None}, key=lambda b: b[1].casefold()
    )
    korinadigan, guruh, bolim = _filtrla(hammasi, request.GET)
    qollangan = _qollangan_kalitlar(rv)
    boshqarish = huquqi_bor(request.user, "reviziya_boshqarish")
    tanlash = boshqarish and rv.holat == Reviziya.Holat.YAKUNLANGAN
    satrlar = []
    for q in korinadigan:
        satr = _satr(q, nomlar)
        satr["qollangan"] = q.kalit in qollangan
        satr["tanlash"] = tanlash and qollanadimi(q) and not satr["qollangan"]
        satrlar.append(satr)
    belgilangan, kutilgan = progress(rv)
    return render(request, "reviziya/sahifa.html", {
        "rv": rv, "plitkalar": plitkalar, "satrlar": satrlar, "guruh": guruh, "bolim": bolim,
        "q": request.GET.get("q", ""), "bolimlar": bolimlar, "guruh_nomlari": GURUH_NOMLARI.items(),
        "boshqarish": boshqarish, "tanlash": tanlash, "tanlanadigan_bor": any(s["tanlash"] for s in satrlar),
        "belgilangan": belgilangan, "kutilgan": kutilgan,
        "foiz": min(100, int(belgilangan * 100 / kutilgan)) if kutilgan else 0,
        "revizorlar": rv.revizorlar.order_by("first_name", "username"),
    })


def _amal(request, pk, bajar, xabar):
    rv = _reviziya_yoki_404(request, pk)
    try:
        bajar(rv, request.user)
    except ReviziyaXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, xabar.format(nomi=rv.nomi))
    return redirect("reviziya:sahifa", pk=rv.pk)


@require_POST
@amal_kerak("reviziya_boshqarish")
def yakunla_view(request, pk):
    return _amal(request, pk, yakunla, "Reviziya {nomi} yakunlandi.")


@require_POST
@amal_kerak("reviziya_boshqarish")
def bekor_view(request, pk):
    return _amal(request, pk, bekor_qil, "Reviziya {nomi} bekor qilindi.")


@require_POST
@amal_kerak("reviziya_boshqarish")
def yop_view(request, pk):
    return _amal(request, pk, reviziya_yop, "Reviziya {nomi} yopildi.")


@require_POST
@amal_kerak("reviziya_boshqarish")
def qolla_view(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    kalitlar = list(dict.fromkeys(k for k in request.POST.getlist("kalit") if k))
    if not kalitlar:
        messages.warning(request, "Qo'llash uchun qator tanlanmagan.")
        return redirect("reviziya:sahifa", pk=rv.pk)
    try:
        natijalar = qolla(rv, kalitlar, request.user)
    except ReviziyaXato as e:
        messages.error(request, str(e))
        return redirect("reviziya:sahifa", pk=rv.pk)
    xatolar = [n.xato for n in natijalar if n.natija != ReviziyaQollash.Natija.OK]
    matn = f"{len(natijalar) - len(xatolar)} ta qo'llandi, {len(xatolar)} ta xato"
    if xatolar:
        messages.warning(request, f"{matn}: " + "; ".join(dict.fromkeys(xatolar)))
    else:
        messages.success(request, f"{matn}.")
    # Spec §3.1: hamma qo'llanadigan qator qo'llangach reviziya o'zi yopiladi («Bo'limsiz» ga ko'chish — hisobga
    # olinmaydi: uni qo'llab bo'lmaydi)
    qolganlar = {q.kalit for q in solishtir(rv) if qollanadimi(q)} - _qollangan_kalitlar(rv)
    if not qolganlar:
        try:
            reviziya_yop(rv, request.user)
        except ReviziyaXato:
            pass  # parallel yopilgan
        else:
            messages.info(request, f"Barcha farqlar qo'llandi — reviziya {rv.nomi} yopildi.")
    return redirect("reviziya:sahifa", pk=rv.pk)


@amal_kerak("reviziya_korish")
def excel(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    nomlar = bolim_nomlari(rv.filial_id)
    qatorlar = []
    for q in solishtir(rv):
        s = _satr(q, nomlar)
        qatorlar.append((
            s["guruh_nomi"], q.inv, q.av_nomi or q.qr_matn, q.bolim_nomi, s["holat_nomi"] or None,
            q.kutilgan, q.topilgan, q.farq, s["nishon_bolim"] or None, s["nishon_holat_nomi"] or None,
        ))
    sarlavhalar = [
        "Guruh", "Inv. raqam", "AV", "Bo'lim", "Holat", "Kutilgan", "Topilgan", "Farq", "Nishon bo'lim", "Nishon holat",
    ]
    javob = HttpResponse(jadval_xlsx(sarlavhalar, qatorlar), content_type=XLSX_TURI)
    javob["Content-Disposition"] = f'attachment; filename="{rv.nomi}_vedomost.xlsx"'
    return javob


@amal_kerak("reviziya_korish")
def pdf(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    javob = HttpResponse(dalolatnoma_pdf(rv, pul=huquqi_bor(request.user, "pul_korish")), content_type="application/pdf")
    javob["Content-Disposition"] = f'inline; filename="{rv.nomi}.pdf"'
    return javob
