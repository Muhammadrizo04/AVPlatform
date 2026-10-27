"""Reviziya panel sahifalari (spec §5–§7): ro'yxat, yangi reviziya, vedomost va amallar, Excel, dalolatnoma."""
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DecimalField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce, Lower, Trim
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from hisoblar.parametrlar import son
from hisobotlar.excel import jadval_xlsx
from mol.sorovlar import faol_xodimlar
from onec.models import AV
from panel.saralash import Saralash
from vositalar.models import Bolim, Holat

from .forms import RevizorlarForma, YangiReviziyaForma
from .models import Reviziya, ReviziyaKutilgan, ReviziyaQayd, ReviziyaQollash, XodimLavozimi
from .pdf import dalolatnoma_pdf
from .qollash import QOLLANADI, ochiqqa_qaytar, qollanadimi, yakunla_va_yoz
from .servis import (
    BOSHQA_FILIAL, KOMISSIYA_AZO, KOMISSIYA_RAIS, KOMISSIYA_ROLLARI, ReviziyaXato, bekor_qil, progress, qamrov_bolim_idlari,
    qayd_qosh, qayd_tuzat, qr_tahlil, reviziya_och,
    revizorlarni_ozgartir,
)
from .kesim import xonalar_kesimi
from .mobil import _av_doirasi, _begona_av, _boshqa_filialdan, _qidir
from .solishtir import (
    BOLIMSIZ, GURUH_NOMLARI, GURUHLAR, bolim_boyicha, bolim_kesim_nomi, bolim_nomlari, guruh_nomi, jamlar, solishtir,
)

NOL = Decimal("0")
SAHIFA_HAJMI = 50
KOMISSIYA_NATIJALARI = 15
XLSX_TURI = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HOLAT_NOMLARI = dict(Holat.choices)
# Guruh filtri: har guruh alohida, `kamomad` — kam va topilmadi birga (ko'rsatkich plitkasi)
# Yangi tartibdan oldin yakunlangan (farqlar hali AV'ga yozilmagan) reviziya qatorlari uchun izoh
ESKI_TARTIB = "Eski tartibda yakunlangan: «Ochiqqa qaytarish», keyin «Yakunlash» — farq AV'ga yoziladi."
GURUH_FILTRLARI = {**{g: {g} for g in GURUHLAR}, "kamomad": {"kam", "topilmadi"}, "farqlar": set(QOLLANADI)}
# Ko'rsatkich plitkalari (spec §5.1: beshta guruh): (filtr, nomi, ikonka, rang sinfi, ogohlantiruvchi)
PLITKALAR = (
    ("topildi", "topildi", "cil-check-circle", "r-bg-pul", False),
    ("kamomad", "kam / topilmadi", "cil-warning", "r-bg-ogoh", True),
    ("boshqa_joyda", "boshqa joyda", "cil-swap-horizontal", "r-bg-vosita", False),
    ("holat_boshqa", "holati boshqa", "cil-loop-circular", "r-bg-mol", False),
    ("ortiqcha", "ortiqcha", "cil-plus", "r-bg-chiqim", False),
)


def _matn(qiymat) -> str:
    return (qiymat or "").strip().casefold()


# Vedomost ustunlari (satr lug'ati bo'yicha); guruh — vedomostdagi standart guruh tartibi
VEDOMOST_USTUNLARI = {
    "guruh": lambda s: GURUHLAR.index(s["q"].guruh),
    "inv": lambda s: _matn(s["q"].inv),
    "av": lambda s: _matn(s["q"].av_nomi or s["q"].qr_matn),
    "bolim": lambda s: _matn(s["q"].bolim_nomi),
    "holat": lambda s: _matn(s["holat_nomi"]),
    "kutilgan": lambda s: s["q"].kutilgan,
    "topilgan": lambda s: s["q"].topilgan,
    "farq": lambda s: s["q"].farq,
}
# Reviziyalar ro'yxati ustunlari (queryset)
ROYXAT_USTUNLARI = {
    "raqam": "raqam", "filial": "filial__nomi", "bolim": "bolim__nomi", "ochilgan": "ochilgan_vaqt",
    "belgilangan": "belgilangan_jami", "kutilgan": "kutilgan_jami", "holat": "holat",
}


def _bolimlar_kesimi(rv, qatorlar) -> list[dict]:
    """Panel jadvali: kutilgan yoki belgilangan narsasi bor (yoki tugagan) bo'limlar + kamomad/ortiqcha dona va
    vedomost filtri qiymati (`bolimsiz` yoki id)."""
    kamomad, ortiqcha = {}, {}
    for q in qatorlar:
        if q.guruh in ("kam", "topilmadi"):
            kamomad[q.bolim_id] = kamomad.get(q.bolim_id, NOL) + abs(q.farq)
        elif q.guruh == "ortiqcha":
            ortiqcha[q.bolim_id] = ortiqcha.get(q.bolim_id, NOL) + q.farq
    natija = []
    for x in xonalar_kesimi(rv):
        if not (x["kutilgan"] or x["belgilangan"] or x["tugadi"]):
            continue
        b = x["bolim_id"]
        natija.append({
            **x, "filtr": "bolimsiz" if b is None else str(b),
            "kamomad": kamomad.get(b, NOL), "ortiqcha": ortiqcha.get(b, NOL),
        })
    return natija


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
    saralash = Saralash(request, ROYXAT_USTUNLARI, standart="-raqam")
    sahifa = Paginator(saralash.queryset(qs), SAHIFA_HAJMI).get_page(request.GET.get("page"))
    return render(request, "reviziya/royxat.html", {
        "sahifa": sahifa, "holat": holat, "holatlar": Reviziya.Holat.choices, "saralash": saralash,
        "boshqarish": huquqi_bor(request.user, "reviziya_boshqarish"),
    })


def _komissiya(post, user) -> list[dict]:
    """Forma qatorlari (`komissiya_xodim/ism/lavozim/rol` bir xil tartibda). Xodim ismi 1C'dan olinadi; ko'rinmaydigan
    xodim tanlanmaydi. Qaytgan elementlarda `filial` — qayta ko'rsatish uchun."""
    xodimlar, ismlar = post.getlist("komissiya_xodim"), post.getlist("komissiya_ism")
    lavozimlar, rollar = post.getlist("komissiya_lavozim"), post.getlist("komissiya_rol")
    topilgan = {x.pk: x for x in faol_xodimlar(user).filter(pk__in=[son(v) for v in xodimlar if son(v)])}
    natija = []
    for i, ism in enumerate(ismlar):
        xodim = topilgan.get(son(xodimlar[i]) if i < len(xodimlar) else None)
        if xodim is None and i < len(xodimlar) and xodimlar[i].strip():
            continue
        natija.append({
            "xodim_id": xodim.pk if xodim else None,
            "ism": (xodim.ism.strip() if xodim else ism.strip())[:255],
            "filial": xodim.filial.nomi if xodim and xodim.filial else "",
            "lavozim": (lavozimlar[i] if i < len(lavozimlar) else "").strip()[:255],
            "rol": rollar[i] if i < len(rollar) else KOMISSIYA_AZO,
        })
    return natija


def _xodim_qatori(xodim) -> dict:
    lavozim = XodimLavozimi.objects.filter(xodim=xodim).values_list("lavozim", flat=True).first()
    return {
        "xodim_id": xodim.pk, "ism": xodim.ism.strip(), "filial": xodim.filial.nomi if xodim.filial else "",
        "lavozim": lavozim or "", "rol": KOMISSIYA_AZO,
    }


@amal_kerak("reviziya_boshqarish")
def komissiya_xodimlar(request):
    """HTMX: komissiyaga qo'shish uchun 1C xodimlari (ism bo'yicha, ishdan bo'shaganlarsiz)."""
    q = request.GET.get("q", "").strip()[:100]
    # 1C ismlarida boshida bo'shliq uchraydi — tartib bo'shliqsiz ism bo'yicha
    xodimlar = (
        faol_xodimlar(request.user).filter(ism__icontains=q).order_by(Lower(Trim("ism")))[:KOMISSIYA_NATIJALARI]
        if q else []
    )
    return render(request, "reviziya/_komissiya_natija.html", {"xodimlar": xodimlar, "q": q})


@amal_kerak("reviziya_boshqarish")
def komissiya_qator(request):
    """HTMX: komissiyaga yangi qator — tanlangan xodim (lavozimi eslab qolingan) yoki 1C'da yo'q odam. Birinchi
    qator rais bo'ladi."""
    xodim_id = son(request.GET.get("xodim"))
    if xodim_id:
        xodim = faol_xodimlar(request.user).filter(pk=xodim_id).first()
        if xodim is None:
            raise Http404
        a = _xodim_qatori(xodim)
    else:
        a = {"xodim_id": None, "ism": request.GET.get("ism", "").strip()[:255], "filial": "", "lavozim": "",
             "rol": KOMISSIYA_AZO}
    if request.GET.get("n") == "0":
        a["rol"] = KOMISSIYA_RAIS
    return render(request, "reviziya/_komissiya_qator.html", {"a": a, "rollar": KOMISSIYA_ROLLARI, "yangi": True})


@amal_kerak("reviziya_boshqarish")
def yangi(request):
    xato, status = "", 200
    if request.method == "POST":
        forma = YangiReviziyaForma(request.POST, user=request.user)
        komissiya = _komissiya(request.POST, request.user)
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
    return render(request, "reviziya/yangi.html", {
        "forma": forma, "komissiya": komissiya, "rollar": KOMISSIYA_ROLLARI, "xato": xato,
    }, status=status)


def _yozilganlar(reviziya) -> tuple[set[str], dict[str, str]]:
    """Yakunlashda taqsimotga yozilgan kalitlar va yozilmaganlarning (kalit -> sabab) oxirgi xatosi."""
    ok, xatolar = set(), {}
    for kalit, natija, xato in reviziya.qollashlar.order_by("pk").values_list("kalit", "natija", "xato"):
        if natija == ReviziyaQollash.Natija.OK:
            ok.add(kalit)
        elif natija == ReviziyaQollash.Natija.XATO:
            xatolar[kalit] = xato
    return ok, {k: v for k, v in xatolar.items() if k not in ok}


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


def _qayd_kaliti(q):
    """Vedomost qatoridagi topilgan son qaysi qaydda turadi: (bolim_id, holat); AV'siz yoki topilmagan — None."""
    if q.av_id is None or q.topilgan <= 0:
        return None
    if q.guruh == "boshqa_joyda":
        return q.nishon_bolim_id, q.nishon_holat or q.holat
    if q.guruh == "holat_boshqa":
        return q.bolim_id, q.nishon_holat
    return q.bolim_id, q.holat  # topildi, kam, ortiqcha


def _filtrla(qatorlar, params):
    guruh = params.get("guruh", "")
    if guruh in GURUH_FILTRLARI:
        qatorlar = [q for q in qatorlar if q.guruh in GURUH_FILTRLARI[guruh]]
    else:
        guruh = ""
    bolim = params.get("bolim", "")
    if bolim != "bolimsiz" and not bolim.isdigit():
        bolim = ""
    qatorlar = bolim_boyicha(qatorlar, bolim)
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
    yozilgan, yozilmagan = _yozilganlar(rv)
    yakunlangan = rv.holat == Reviziya.Holat.YAKUNLANGAN
    boshqarish = huquqi_bor(request.user, "reviziya_boshqarish")
    saralash = Saralash(request, VEDOMOST_USTUNLARI)
    skanerlay_oladi = rv.holat == Reviziya.Holat.OCHIQ and (
        boshqarish or rv.revizorlar.filter(pk=request.user.pk).exists()
    )
    satrlar = []
    for q in korinadigan:
        satr = _satr(q, nomlar)
        if q.av_id is None and q.izoh == BOSHQA_FILIAL:
            satr["begona"] = _begona_av(q.qr_matn)
        satr["yozildi"] = q.kalit in yozilgan
        satr["yozilmadi"] = yozilmagan.get(q.kalit, "")
        if yakunlangan and not satr["yozildi"] and not satr["yozilmadi"] and qollanadimi(q):
            satr["yozilmadi"] = ESKI_TARTIB
        # ochiq reviziya: hali topilmagan qatorni sahifaning o'zidan «joyida» deb belgilash (skanerlashsiz)
        if skanerlay_oladi and q.av_id and q.guruh in ("kam", "topilmadi"):
            satr["belgi"] = f"{q.av_id}:{q.bolim_id or ''}:{q.holat}"
            satr["qolgan"] = -q.farq
        # teskarisi: topilgan (belgilangan) qatorning belgisini olib tashlash
        satr["olib"] = skanerlay_oladi and _qayd_kaliti(q) is not None
        satrlar.append(satr)
    satrlar = saralash.royxat(satrlar)
    belgilangan, kutilgan = progress(rv)
    farq_kalitlari = {q.kalit for q in hammasi if qollanadimi(q)}
    farqlar = {"jami": len(farq_kalitlari), "yozilgan": len(farq_kalitlari & yozilgan)}
    farqlar["yozilmagan"] = farqlar["jami"] - farqlar["yozilgan"] if yakunlangan else 0
    # yozishga urinilmagan (eski tartibda yakunlangan) farqlar — xato sababi yo'q
    farqlar["eski"] = farqlar["yozilmagan"] - len(farq_kalitlari & set(yozilmagan)) if yakunlangan else 0
    return render(request, "reviziya/sahifa.html", {
        "rv": rv, "plitkalar": plitkalar, "satrlar": satrlar, "guruh": guruh, "bolim": bolim, "saralash": saralash,
        "q": request.GET.get("q", ""), "bolimlar": bolimlar, "guruh_nomlari": GURUH_NOMLARI.items(),
        "boshqarish": boshqarish, "belgilash": skanerlay_oladi,
        "tanlanadigan_bor": any(s.get("belgi") or s["olib"] for s in satrlar),
        "keyingi": request.get_full_path(),
        "belgilangan": belgilangan, "kutilgan": kutilgan, "farqlar": farqlar,
        "foiz": min(100, int(belgilangan * 100 / kutilgan)) if kutilgan else 0,
        "kesim": _bolimlar_kesimi(rv, hammasi),
        "revizorlar": rv.revizorlar.order_by("first_name", "username"),
        # mobil skan sahifasiga ruxsat bilan bir xil: ochiq, revizor yoki boshqaruvchi (filial cheklovi — yuqorida)
        "skanerlay_oladi": skanerlay_oladi,
        "revizor_forma": (
            RevizorlarForma(user=request.user, filial=rv.filial, initial={"revizorlar": rv.revizorlar.all()})
            if boshqarish and rv.holat == Reviziya.Holat.OCHIQ else None
        ),
    })


@require_POST
@amal_kerak("reviziya_boshqarish")
def revizorlar_view(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    forma = RevizorlarForma(request.POST, user=request.user, filial=rv.filial)
    if not forma.is_valid():
        messages.error(request, " ".join(e for xatolar in forma.errors.values() for e in xatolar))
        return redirect("reviziya:sahifa", pk=rv.pk)
    try:
        revizorlarni_ozgartir(rv, forma.cleaned_data["revizorlar"], request.user)
    except ReviziyaXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"{rv.nomi} revizorlari yangilandi.")
    return redirect("reviziya:sahifa", pk=rv.pk)


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
    """Yakunlash: sanash yopiladi va farqlar AV taqsimotiga yoziladi (bitta qadam)."""
    rv = _reviziya_yoki_404(request, pk)
    try:
        natijalar = yakunla_va_yoz(rv, request.user)
    except ReviziyaXato as e:
        messages.error(request, str(e))
        return redirect("reviziya:sahifa", pk=rv.pk)
    xatolar = [n.xato for n in natijalar if n.natija != ReviziyaQollash.Natija.OK]
    matn = f"Reviziya {rv.nomi} yakunlandi: {len(natijalar) - len(xatolar)} ta farq AV taqsimotiga yozildi"
    if xatolar:
        messages.warning(request, f"{matn}; {len(xatolar)} tasi yozilmadi: " + "; ".join(dict.fromkeys(xatolar)))
    else:
        messages.success(request, f"{matn}.")
    return redirect("reviziya:sahifa", pk=rv.pk)


@require_POST
@amal_kerak("reviziya_boshqarish")
def bekor_view(request, pk):
    return _amal(request, pk, bekor_qil, "Reviziya {nomi} bekor qilindi.")


@require_POST
@amal_kerak("reviziya_boshqarish")
def ochiqqa_view(request, pk):
    return _amal(
        request, pk, ochiqqa_qaytar,
        "Reviziya {nomi} «Ochiq» ga qaytarildi — AV o'zgarishlari orqaga qaytarildi, sonlarni tuzatish mumkin.",
    )


def _orqaga(request, rv):
    keyingi = request.POST.get("keyingi", "")
    if url_has_allowed_host_and_scheme(keyingi, allowed_hosts={request.get_host()}):
        return redirect(keyingi)
    return redirect("reviziya:sahifa", pk=rv.pk)


def _kiritadigan_reviziya(request, pk) -> Reviziya:
    """Sahifadan qayd kiritish: reviziya boshqaruvchisi yoki shu reviziya revizori (filial cheklovi bilan)."""
    rv = _reviziya_yoki_404(request, pk)
    if not (huquqi_bor(request.user, "reviziya_boshqarish") or rv.revizorlar.filter(pk=request.user.pk).exists()):
        raise Http404
    return rv


def _qamrov_bolimlari(rv) -> list:
    qamrov = qamrov_bolim_idlari(rv)
    bolimlar = Bolim.objects.filter(filial_id=rv.filial_id, faol=True)
    if qamrov is not None:
        bolimlar = bolimlar.filter(pk__in=qamrov)
    return sorted(bolimlar, key=lambda b: b.toliq_nomi.casefold())


@amal_kerak("reviziya_otkazish")
def qidir_view(request, pk):
    """Ochiq reviziya sahifasi (HTMX): AV qidirish — shu filialdan (nom, inv., МОЛ), topilmasa boshqa filiallardan
    (aniq inv.) — «topildi» deb qo'shish uchun."""
    rv = _kiritadigan_reviziya(request, pk)
    q = (request.GET.get("q") or "").strip()[:100]
    shu = _qidir(rv, q) if q else []
    return render(request, "reviziya/_qayd_qidiruv.html", {
        "rv": rv, "q": q, "shu": shu, "begonalar": [] if shu or not q else _boshqa_filialdan(rv, q),
        "bolimlar": _qamrov_bolimlari(rv), "keyingi": request.headers.get("HX-Current-URL", ""),
    })


@require_POST
@amal_kerak("reviziya_otkazish")
def qayd_qosh_view(request, pk):
    """Qidiruvdan: `av` (shu filial AV'si) yoki `qr` (boshqa filial yorlig'i) — `bolim` da `soni` dona topildi."""
    rv = _kiritadigan_reviziya(request, pk)
    try:
        bolim_id = request.POST.get("bolim") or ""
        bolim = Bolim.objects.filter(pk=int(bolim_id), filial_id=rv.filial_id).first() if bolim_id else None
        if bolim_id and bolim is None:
            raise ReviziyaXato("Bo'lim topilmadi.")
        try:
            soni = Decimal((request.POST.get("soni") or "1").replace(",", ".").strip())
        except InvalidOperation:
            raise ReviziyaXato("Sonni to'g'ri kiriting.") from None
        av_id, qr = (request.POST.get("av") or "").strip(), (request.POST.get("qr") or "").strip()
        if av_id:
            av = _av_doirasi(rv).filter(pk=int(av_id)).first()
            if av is None:
                raise ReviziyaXato("AV bu reviziya filialida topilmadi.")
            qayd_qosh(rv, bolim, request.user, av=av, soni=soni, usul=ReviziyaQayd.Usul.QIDIRUV)
            nomi = av.nomi
        else:
            if qr_tahlil(qr, rv)[1] != BOSHQA_FILIAL:
                raise ReviziyaXato("Yorliq boshqa filialga tegishli emas.")
            qayd_qosh(rv, bolim, request.user, qr_matn=qr, soni=soni, usul=ReviziyaQayd.Usul.QIDIRUV)
            nomi = qr
    except ValueError:
        messages.error(request, "Noto'g'ri so'rov.")
    except ReviziyaXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"«{nomi}» topildi deb qo'shildi.")
    return _orqaga(request, rv)


@require_POST
@amal_kerak("reviziya_otkazish")
def belgini_ol_view(request, pk):
    """«Joyida» ning teskarisi: tanlangan vedomost qatorlari (`olib` — kalit) uchun qayddan shu qatorning topilgan
    soni ayiriladi (0 bo'lsa qayd o'chadi). Hammasi yoki hech biri."""
    rv = _reviziya_yoki_404(request, pk)
    if not (huquqi_bor(request.user, "reviziya_boshqarish") or rv.revizorlar.filter(pk=request.user.pk).exists()):
        raise Http404
    kalitlar = list(dict.fromkeys(k for k in request.POST.getlist("olib") if k))
    if not kalitlar:
        messages.warning(request, "Belgisini olib tashlash uchun qator tanlanmagan.")
        return _orqaga(request, rv)
    qatorlar = {q.kalit: q for q in solishtir(rv)}
    try:
        with transaction.atomic():
            for kalit in kalitlar:
                q = qatorlar.get(kalit)
                joy = _qayd_kaliti(q) if q is not None else None
                qayd = joy and ReviziyaQayd.objects.filter(
                    reviziya=rv, av_id=q.av_id, bolim_id=joy[0], holat=joy[1], qr_matn=""
                ).first()
                if not qayd:
                    raise ReviziyaXato("Qator topilmadi — sahifani yangilab, qayta urinib ko'ring.")
                qayd_tuzat(qayd, max(qayd.soni - q.topilgan, Decimal("0")), request.user)
    except ReviziyaXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"{len(kalitlar)} ta qatorning belgisi olib tashlandi.")
    return _orqaga(request, rv)


@require_POST
@amal_kerak("reviziya_otkazish")
def belgila_view(request, pk):
    """Ochiq reviziya sahifasidan: tanlangan `belgi` (av:bolim:holat) qatorlarini `soni_<belgi>` soni bilan qayd qiladi
    (mobil «Hammasi joyida» kabi; hammasi yoki hech biri)."""
    rv = _reviziya_yoki_404(request, pk)
    orqaga = _orqaga(request, rv)
    if not (huquqi_bor(request.user, "reviziya_boshqarish") or rv.revizorlar.filter(pk=request.user.pk).exists()):
        raise Http404
    belgilar = list(dict.fromkeys(b for b in request.POST.getlist("belgi") if b))
    if not belgilar:
        messages.warning(request, "Belgilash uchun qator tanlanmagan.")
        return orqaga
    kutilgan = set(ReviziyaKutilgan.objects.filter(reviziya=rv).values_list("av_id", "bolim_id", "holat"))
    try:
        with transaction.atomic():
            for qiymat in belgilar:
                # «av:bolim:holat=soni» (sahifa JS sonni katakka qo'shadi) yoki alohida `soni_<belgi>` maydoni
                belgi, _, soni_matni = qiymat.partition("=")
                av_id, bolim_id, holat = belgi.split(":", 2)
                av_id, bolim_id = int(av_id), int(bolim_id) if bolim_id else None
                if (av_id, bolim_id, holat) not in kutilgan:
                    raise ReviziyaXato("Tanlangan qator reviziyada kutilmagan.")
                try:
                    soni = Decimal((soni_matni or request.POST.get(f"soni_{belgi}", "")).replace(",", ".").strip())
                except InvalidOperation:
                    raise ReviziyaXato("Sonni to'g'ri kiriting.") from None
                bolim = Bolim.objects.get(pk=bolim_id) if bolim_id else None
                qayd_qosh(
                    rv, bolim, request.user, av=AV.objects.get(pk=av_id), soni=soni, holat=holat,
                    usul=ReviziyaQayd.Usul.QIDIRUV,
                )
    except (ValueError, Bolim.DoesNotExist, AV.DoesNotExist):
        messages.error(request, "Noto'g'ri so'rov.")
    except ReviziyaXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"{len(belgilar)} ta AV joyida deb belgilandi.")
    return orqaga


def _fayl_nomi(tur: str, rv, nomlar, bolim: str, oxiri: str) -> str:
    """Content-Disposition: bo'lim kesimida fayl nomiga bo'lim nomi qo'shiladi (UTF-8, RFC 5987)."""
    nomi = rv.nomi
    kesim = bolim_kesim_nomi(bolim, nomlar)
    if kesim:
        nomi += "_" + re.sub(r"[^\w-]+", "_", kesim).strip("_")
    return f"{tur}; filename=\"{rv.nomi}{oxiri}\"; filename*=UTF-8''{quote(nomi + oxiri)}"


@amal_kerak("reviziya_korish")
def excel(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    nomlar = bolim_nomlari(rv.filial_id)
    bolim = request.GET.get("bolim", "")
    qatorlar = []
    for q in bolim_boyicha(solishtir(rv), bolim):
        s = _satr(q, nomlar)
        qatorlar.append((
            s["guruh_nomi"], q.inv, q.av_nomi or q.qr_matn, q.bolim_nomi, s["holat_nomi"] or None,
            q.kutilgan, q.topilgan, q.farq, s["nishon_bolim"] or None, s["nishon_holat_nomi"] or None,
        ))
    sarlavhalar = [
        "Guruh", "Inv. raqam", "AV", "Bo'lim", "Holat", "Kutilgan", "Topilgan", "Farq", "Nishon bo'lim", "Nishon holat",
    ]
    javob = HttpResponse(jadval_xlsx(sarlavhalar, qatorlar), content_type=XLSX_TURI)
    javob["Content-Disposition"] = _fayl_nomi("attachment", rv, nomlar, bolim, "_vedomost.xlsx")
    return javob


@amal_kerak("reviziya_korish")
def pdf(request, pk):
    rv = _reviziya_yoki_404(request, pk)
    bolim = request.GET.get("bolim", "")
    javob = HttpResponse(
        dalolatnoma_pdf(rv, pul=huquqi_bor(request.user, "pul_korish"), bolim=bolim), content_type="application/pdf"
    )
    javob["Content-Disposition"] = _fayl_nomi("inline", rv, bolim_nomlari(rv.filial_id), bolim, ".pdf")
    return javob
