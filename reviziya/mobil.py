"""Revizorning mobil sahifalari (spec §4): reviziyalarim, xona tanlash, skan ekrani, AV kartochkasi, qolganlar.

Kirish (Ruling 2): reviziya revizorlari yoki `reviziya_boshqarish` huquqi borlar, doim `filial_bilan_chekla` ichida;
boshqalarga 404. Ochiq bo'lmagan reviziya — 403 (HTMX bo'lakda tushunarli xabar bilan).
"""
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Trim
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.views.decorators.http import require_GET, require_POST

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from onec.models import AV, AVQoldiq, Filial
from panel.templatetags.raqamlar import son
from vositalar.bolimlar import daraxt
from vositalar.models import Bolim
from vositalar.models import Holat as TaqsimotHolat

from .kesim import BOLIMSIZ_QIYMATI as BOLIMSIZ, xonalar_kesimi
from .models import Reviziya, ReviziyaQayd, ReviziyaXona
from .servis import (
    BOSHQA_FILIAL,
    KOMISSIYA_RAIS,
    ReviziyaXato,
    progress,
    qamrov_bolim_idlari,
    qayd_qosh,
    qayd_tuzat,
    qr_tahlil,
    reviziya_och,
    standart_holat,
    xona_tugadi,
)

NOL = Decimal("0")
SON_CHEGARASI = Decimal("1000000")
QR_MAKS = 255  # ReviziyaQayd.qr_matn uzunligi: undan uzun matn kesiladi (noma'lum yorliq sifatida saqlanadi)
QIDIRUV_MAKS = 100
QR_BOSHI = "DS|"  # yorliq QR formati: DS|<filial kodi>|<inv>

QIDIRUV_NATIJALARI = 20
OXIRGILAR_SONI = 10
NUL = chr(0)


class _Yopiq(Exception):
    """Reviziya ochiq emas — skanerlash taqiqlangan."""


def _mobil(view):
    """`reviziya_otkazish` huquqi; yopiq reviziya — 403 (HTMX — bo'lak, aks holda mobil sahifa)."""

    @amal_kerak("reviziya_otkazish")
    @wraps(view)
    def ichki(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except _Yopiq:
            xabar = "Reviziya ochiq emas: qayd qilib bo'lmaydi."
            if request.headers.get("HX-Request"):
                return HttpResponse(format_html('<div class="m-xato" role="alert">{}</div>', xabar), status=403)
            return render(request, "reviziya/mobil/base.html", {"xabar": xabar}, status=403)

    return ichki


def _reviziyalar(user):
    qs = filial_bilan_chekla(Reviziya.objects.select_related("filial", "bolim"), user)
    if not huquqi_bor(user, "reviziya_boshqarish"):
        qs = qs.filter(revizorlar=user)
    return qs


def _reviziya(request, pk) -> Reviziya:
    rv = _reviziyalar(request.user).filter(pk=pk).first()
    if rv is None:
        raise Http404
    if rv.holat != Reviziya.Holat.OCHIQ:
        raise _Yopiq
    return rv


def _sessiya_kaliti(rv) -> str:
    return f"reviziya_{rv.pk}_xona"


def _xona_qiymati(request, rv) -> str | None:
    """So'rovdagi `bolim` (id yoki 0 — bo'limsiz), bo'lmasa sessiyadagi tanlangan xona; None — tanlanmagan."""
    manba = request.POST if request.method == "POST" else request.GET
    qiymat = (manba.get("bolim") or "").strip()
    return qiymat or request.session.get(_sessiya_kaliti(rv))


def _xona(rv, qiymat: str) -> Bolim | None:
    """Qamrovdagi xona (None — bo'limsiz); boshqa filial yoki qamrovdan tashqari — 404."""
    if qiymat == BOLIMSIZ:
        return None
    if not qiymat.isdigit():
        raise Http404
    bolim = Bolim.objects.filter(pk=int(qiymat), filial_id=rv.filial_id).first()
    qamrov = qamrov_bolim_idlari(rv)
    if bolim is None or (qamrov is not None and bolim.pk not in qamrov):
        raise Http404
    return bolim


def _son(qiymat, *, nol_mumkin=False) -> Decimal:
    """«1,5» -> Decimal("1.5"); bo'sh, noto'g'ri, manfiy (nol) yoki juda katta — `ReviziyaXato`."""
    try:
        soni = Decimal((qiymat or "").strip().replace(",", "."))
    except InvalidOperation:
        raise ReviziyaXato("Sonni to'g'ri kiriting.") from None
    if not soni.is_finite():
        raise ReviziyaXato("Sonni to'g'ri kiriting.")
    if soni < 0 or (soni == 0 and not nol_mumkin):
        raise ReviziyaXato("Son noldan katta bo'lishi kerak." if not nol_mumkin else "Son manfiy bo'lmasin.")
    if soni >= SON_CHEGARASI:
        raise ReviziyaXato("Son juda katta.")
    return soni


def _matn(qiymat) -> str:
    """So'rov matni: NUL baytlarsiz (PostgreSQL matn maydonlari ularni qabul qilmaydi), chetlari kesilgan."""
    return (qiymat or "").replace(NUL, "").strip()


def _xato(xabar: str, nishon: str) -> HttpResponse:
    """400: xabar shakl ichidagi xato joyiga (`HX-Retarget`), kiritilgan qiymatlar saqlanib qoladi."""
    javob = HttpResponse(format_html('<div class="m-xato" role="alert">{}</div>', xabar), status=400)
    javob["HX-Retarget"] = nishon
    javob["HX-Reswap"] = "innerHTML"
    return javob


def _av_doirasi(rv):
    """Reviziya filialiga tegishli AV'lar: rekvizit, qoldiq yoki kutilgan qator bo'yicha (arxiv ham)."""
    return AV.objects.filter(
        Q(filial_rekvizit_id=rv.filial_id)
        | Q(pk__in=AVQoldiq.objects.filter(filial_id=rv.filial_id).values("av_id"))
        | Q(pk__in=rv.kutilganlar.values("av_id"))
    )


def _xona_progress(rv, xona) -> dict:
    belgilangan, kutilgan = progress(rv, bolim_id=None if xona is None else xona.pk)
    return {"belgilangan": belgilangan, "kutilgan": kutilgan}


def _oxirgilar(request, rv, xona) -> list[dict]:
    boshqaradi = huquqi_bor(request.user, "reviziya_boshqarish")
    qaydlar = (
        rv.qaydlar.filter(bolim_id=None if xona is None else xona.pk)
        .select_related("av", "kim")
        .order_by("-yangilangan", "-pk")[:OXIRGILAR_SONI]
    )
    return [
        {"q": q, "qiymat": format(q.soni.normalize(), "f"), "ozi": boshqaradi or q.kim_id == request.user.pk}
        for q in qaydlar
    ]


def _qolganlar(rv, xona) -> list[dict]:
    """Shu xonada kutilgan, lekin hali to'liq belgilanmagan AV'lar (qolgan soni bilan)."""
    xona_id = None if xona is None else xona.pk
    kutilgan = dict(
        rv.kutilganlar.filter(bolim_id=xona_id).order_by().values_list("av_id").annotate(s=Sum("soni"))
    )
    topilgan = dict(
        rv.qaydlar.filter(bolim_id=xona_id, av__isnull=False).order_by().values_list("av_id").annotate(s=Sum("soni"))
    )
    qolgan = {av_id: s - topilgan.get(av_id, NOL) for av_id, s in kutilgan.items() if s > topilgan.get(av_id, NOL)}
    avlar = AV.objects.in_bulk(qolgan)
    natija = [{"av": avlar[i], "soni": s} for i, s in qolgan.items()]
    return sorted(natija, key=lambda q: (q["av"].nomi.casefold(), q["av"].pk))


def _skan_konteksti(request, rv, xona) -> dict:
    return {
        "rv": rv,
        "xona": xona,
        "xona_qiymati": BOLIMSIZ if xona is None else str(xona.pk),
        "xona_progress": _xona_progress(rv, xona),
        "xona_tugagan": ReviziyaXona.objects.filter(reviziya=rv, bolim=xona).exists(),
        "oxirgilar": _oxirgilar(request, rv, xona),
        "qolganlar": _qolganlar(rv, xona),
    }


def _yangilanishlar(request, rv, xona, *, oxirgilar_oob=True) -> str:
    """Saqlash/tuzatishdan keyin oxirgilar, qolganlar va xona progressi (hx-swap-oob; tuzatishda oxirgilar —
    asosiy nishon)."""
    ctx = {**_skan_konteksti(request, rv, xona), "oob": True}
    p = ctx["xona_progress"]
    return (
        render_to_string("reviziya/mobil/_oxirgilar.html", {**ctx, "oob": oxirgilar_oob}, request=request)
        + render_to_string("reviziya/mobil/_qolganlar.html", ctx, request=request)
        + render_to_string("reviziya/mobil/_xona_chiziq.html", ctx, request=request)
        + format_html(
            '<span class="m-son" id="xona-progress" hx-swap-oob="true">{} / {}</span>',
            son(p["belgilangan"]), son(p["kutilgan"]),
        )
    )


@_mobil
@require_GET
def reviziyalarim(request):
    qatorlar = []
    for rv in _reviziyalar(request.user).filter(holat=Reviziya.Holat.OCHIQ).order_by("-raqam"):
        belgilangan, kutilgan = progress(rv)
        qatorlar.append({"rv": rv, "belgilangan": belgilangan, "kutilgan": kutilgan})
    return render(request, "reviziya/mobil/reviziyalarim.html", {"qatorlar": qatorlar})


def _joy_tanlovi(user) -> list[tuple[Filial, list[tuple[Bolim, int, str]]]]:
    """Revizor reviziya ocha oladigan joylar: ruxsat etilgan filiallar va ularning faol bo'limlari (daraxt tartibida)."""
    filiallar = filial_bilan_chekla(Filial.objects.all(), user, "pk").order_by("nomi")
    return [(f, [q for q in daraxt(f.pk) if q[0].faol]) for f in filiallar]


@_mobil
def yangi(request):
    """Revizorning o'zi reviziya boshlaydi: filial yoki bo'lim tanlanadi; revizor va komissiya raisi — o'zi."""
    joylar = _joy_tanlovi(request.user)
    xato, tanlangan = "", request.POST.get("joy", "")
    if request.method == "POST":
        filial = bolim = None
        tur, _, qiymat = tanlangan.partition(":")
        if tur == "f" and qiymat.isdigit():
            filial = next((f for f, _ in joylar if f.pk == int(qiymat)), None)
        elif tur == "b" and qiymat.isdigit():
            for f, bolimlar in joylar:
                bolim = next((b for b, _, _ in bolimlar if b.pk == int(qiymat)), None)
                if bolim is not None:
                    filial = f
                    break
        if filial is None:
            xato = "Reviziya qilinadigan filial yoki bo'limni tanlang."
        else:
            u = request.user
            rais = {"ism": u.get_full_name() or u.get_username(), "lavozim": "Revizor", "rol": KOMISSIYA_RAIS}
            try:
                rv = reviziya_och(filial, bolim, [u], [rais], u, izoh=_matn(request.POST.get("izoh"))[:2000])
            except ReviziyaXato as e:
                xato = str(e)
            else:
                return redirect("reviziya:mobil_xonalar", pk=rv.pk)
    tanlovlar = [
        (f.nomi, [(f"f:{f.pk}", f"{f.nomi} — butun filial")] + [(f"b:{b.pk}", toliq) for b, _, toliq in bolimlar])
        for f, bolimlar in joylar
    ]
    return render(request, "reviziya/mobil/yangi.html", {
        "tanlovlar": tanlovlar, "xato": xato, "tanlangan": tanlangan,
    }, status=400 if xato else 200)


@_mobil
@require_GET
def xonalar(request, pk):
    rv = _reviziya(request, pk)
    jami_belgilangan, jami_kutilgan = progress(rv)
    return render(request, "reviziya/mobil/xonalar.html", {
        "rv": rv, "qatorlar": xonalar_kesimi(rv), "tanlangan": request.session.get(_sessiya_kaliti(rv)),
        "belgilangan": jami_belgilangan, "kutilgan": jami_kutilgan,
    })


@_mobil
@require_POST
def xona_tugadi_view(request, pk):
    """«Xona tugadi» belgisini qo'yadi (`tugadi=1`) yoki olib tashlaydi; xonalar ro'yxatiga qaytadi."""
    rv = _reviziya(request, pk)
    qiymat = _xona_qiymati(request, rv)
    if qiymat is None:
        raise Http404
    xona_tugadi(rv, _xona(rv, qiymat), request.user, tugadi=request.POST.get("tugadi") == "1")
    return redirect("reviziya:mobil_xonalar", pk=rv.pk)


@_mobil
@require_GET
def skan(request, pk):
    rv = _reviziya(request, pk)
    qiymat = _xona_qiymati(request, rv)
    if qiymat is None:
        return redirect("reviziya:mobil_xonalar", pk=rv.pk)
    xona = _xona(rv, qiymat)
    request.session[_sessiya_kaliti(rv)] = qiymat
    return render(request, "reviziya/mobil/skan.html", _skan_konteksti(request, rv, xona))


def _av_kartochka(rv, xona, av, usul) -> dict:
    xona_id = None if xona is None else xona.pk
    kutilganlar = rv.kutilganlar.filter(av=av, bolim_id=xona_id)
    holat = standart_holat(rv, av, xona_id)
    jami_soni = AVQoldiq.objects.filter(av=av, filial_id=rv.filial_id).aggregate(s=Sum("soni"))["s"] or NOL
    return {
        "tur": "av", "av": av, "usul": usul, "holat": holat,
        "kutilgan": kutilganlar.aggregate(s=Sum("soni"))["s"] or NOL,
        "topilgan": rv.qaydlar.filter(av=av, bolim_id=xona_id).aggregate(s=Sum("soni"))["s"] or NOL,
        "guruh": jami_soni if jami_soni > 1 else None,
    }


def _qidir(rv, q: str):
    doira = _av_doirasi(rv)
    aniq = list(doira.annotate(inv=Trim("inv_raqam")).filter(inv__iexact=q).order_by("nomi", "pk")[:QIDIRUV_NATIJALARI])
    if aniq:
        return aniq
    return list(
        doira.filter(Q(inv_raqam__icontains=q) | Q(nomi__icontains=q)).order_by("nomi", "pk")[:QIDIRUV_NATIJALARI]
    )


@_mobil
@require_GET
def topish(request, pk):
    """GET `qr` (kamera), `q` (inv. raqam / nom) yoki `av` (ro'yxatdan) -> AV kartochkasi bo'lagi."""
    rv = _reviziya(request, pk)
    qiymat = _xona_qiymati(request, rv)
    if qiymat is None:
        return _xato("Avval xonani tanlang.", "#kartochka")
    xona = _xona(rv, qiymat)
    ctx = {"rv": rv, "xona_qiymati": qiymat, "holatlar": TaqsimotHolat.choices}
    qr = _matn(request.GET.get("qr"))[:QR_MAKS]
    q = _matn(request.GET.get("q"))[:QIDIRUV_MAKS]
    av_id = (request.GET.get("av") or "").strip()
    if not qr and q.upper().startswith(QR_BOSHI):
        # USB skaner QR matnini qidiruv maydoniga «yozadi» — QR sifatida o'qiladi
        qr, q = _matn(request.GET.get("q"))[:QR_MAKS], ""
    if qr:
        av, sabab = qr_tahlil(qr, rv)
        if av is not None:
            ctx.update(_av_kartochka(rv, xona, av, "qr"))
        else:
            ctx.update({"tur": "nomalum", "qr_matn": qr, "boshqa_filial": sabab == BOSHQA_FILIAL, "usul": "qr"})
    elif av_id.isdigit():
        av = _av_doirasi(rv).filter(pk=int(av_id)).first()
        if av is None:
            raise Http404
        ctx.update(_av_kartochka(rv, xona, av, "qidiruv"))
    elif q:
        topilganlar = _qidir(rv, q)
        if len(topilganlar) == 1:
            ctx.update(_av_kartochka(rv, xona, topilganlar[0], "qidiruv"))
        else:
            ctx.update({"tur": "royxat", "topilganlar": topilganlar, "q": q})
    else:
        return HttpResponse("")
    return render(request, "reviziya/mobil/_kartochka.html", ctx)


@_mobil
@require_POST
def saqla(request, pk):
    """POST: `bolim`, `av` yoki `qr_matn`, `soni`, `holat`, `izoh`, `rasm`, `usul` -> qayd (takror — +soni)."""
    rv = _reviziya(request, pk)
    qiymat = _xona_qiymati(request, rv)
    if qiymat is None:
        return _xato("Avval xonani tanlang.", "#saqla-xato")
    xona = _xona(rv, qiymat)
    try:
        soni = _son(request.POST.get("soni"))
    except ReviziyaXato as e:
        return _xato(str(e), "#saqla-xato")
    av_id = (request.POST.get("av") or "").strip()
    qr = _matn(request.POST.get("qr_matn"))[:QR_MAKS]
    av = None
    if av_id:
        av = _av_doirasi(rv).filter(pk=int(av_id)).first() if av_id.isdigit() else None
        if av is None:
            return _xato("AV bu reviziya filialida topilmadi.", "#saqla-xato")
    elif qr:
        av, _ = qr_tahlil(qr, rv)
    try:
        qayd = qayd_qosh(
            rv, xona, request.user, av=av, qr_matn=qr, soni=soni,
            holat=request.POST.get("holat") or None, usul=request.POST.get("usul") or ReviziyaQayd.Usul.QR,
            izoh=_matn(request.POST.get("izoh")), rasm_fayl=request.FILES.get("rasm"),
        )
    except ReviziyaXato as e:
        return _xato(str(e), "#saqla-xato")
    except ValidationError as e:
        return _xato(" ".join(e.messages), "#saqla-xato")
    request.session[_sessiya_kaliti(rv)] = qiymat
    kartochka = render_to_string(
        "reviziya/mobil/_kartochka.html", {"tur": "saqlandi", "qayd": qayd, "rv": rv}, request=request
    )
    return HttpResponse(kartochka + _yangilanishlar(request, rv, xona))


@_mobil
@require_POST
def hammasi_bor(request, pk):
    """POST `bolim`: shu xonadagi hamma «qolgan» AV'ni kutilgan soni va holati bilan belgilaydi («Hammasi joyida»)."""
    rv = _reviziya(request, pk)
    qiymat = _xona_qiymati(request, rv)
    if qiymat is None:
        return _xato("Avval xonani tanlang.", "#kartochka")
    xona = _xona(rv, qiymat)
    qolganlar = _qolganlar(rv, xona)
    try:
        with transaction.atomic():  # hammasi yoki hech biri
            for q in qolganlar:
                qayd_qosh(rv, xona, request.user, av=q["av"], soni=q["soni"], usul=ReviziyaQayd.Usul.QIDIRUV)
    except ReviziyaXato as e:
        return _xato(str(e), "#kartochka")
    request.session[_sessiya_kaliti(rv)] = qiymat
    xabar = format_html('<p class="m-ok" role="status">{} ta AV belgilandi.</p>', len(qolganlar))
    return HttpResponse(xabar + _yangilanishlar(request, rv, xona))


@_mobil
@require_POST
def tuzat(request, qayd_pk):
    """POST `soni`: qayd sonini o'rnatadi; 0 — qayd o'chiriladi (faqat o'z qaydi yoki `reviziya_boshqarish`)."""
    qayd = ReviziyaQayd.objects.select_related("bolim").filter(pk=qayd_pk).first()
    if qayd is None:
        raise Http404
    rv = _reviziya(request, qayd.reviziya_id)
    try:
        qayd_tuzat(qayd, _son(request.POST.get("soni"), nol_mumkin=True), request.user)
    except ReviziyaXato as e:
        return _xato(str(e), "#oxirgilar-xato")
    return HttpResponse(_yangilanishlar(request, rv, qayd.bolim, oxirgilar_oob=False))
