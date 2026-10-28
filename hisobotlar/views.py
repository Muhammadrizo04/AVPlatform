from itertools import groupby

from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from hisobotlar import servis
from hisobotlar.excel import jadval_xlsx
from hisoblar.parametrlar import son
from mol.sorovlar import korinadigan_xodimlar
from onec.models import Filial
from vositalar.bolimlar import daraxt, pastkilar

XLSX_TURI = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GURUHLAR = {"filial": "Filial", "bolim": "Bo'lim", "tur": "AV turi"}
KORSATISH_CHEGARASI = 200  # tozalash sahifasida har bo'limda ko'rsatiladigan qatorlar (Excel'da — hammasi)
QAYDNOMA_SAHIFA = 100  # qaydnomalar ekranda shuncha qatordan; chop etish va Excel — hammasi
CHOP_TURLARI = ("summali", "summasiz")


def _xlsx(fayl: str, sarlavhalar, qatorlar) -> HttpResponse:
    javob = HttpResponse(jadval_xlsx(sarlavhalar, qatorlar), content_type=XLSX_TURI)
    javob["Content-Disposition"] = f'attachment; filename="{fayl}.xlsx"'
    return javob


def _sana(qiymat) -> str:
    """Excel uchun: biriktirilgan/joylashtirilgan sana (mahalliy vaqt) yoki «—»."""
    return timezone.localtime(qiymat).strftime("%d.%m.%Y") if qiymat else "—"


def _xlsx_so_ralgan(request) -> bool:
    return request.GET.get("format") == "xlsx"


def _qaydnoma_konteksti(request, qatorlar) -> dict:
    """Qaydnomalarning umumiy konteksti: jami, ekranda sahifa, chop etish rejimi va havolalari.

    `?chop=summali|summasiz` — chop etish rejimi: barcha qatorlar bitta sahifada, sahifa ochilgach chop etish oynasi
    chiqadi (panel/chop.js); summasizda qiymat ustunlari umuman chiqmaydi (`pul_huquqi` shu sahifa uchun o'chadi)."""
    chop = request.GET.get("chop", "")
    chop = chop if chop in CHOP_TURLARI else ""
    params = request.GET.copy()
    for k in ("page", "chop", "format"):
        params.pop(k, None)
    asos = params.urlencode()
    kontekst = {
        "chop": chop,
        "jami_soni": sum((q["soni"] for q in qatorlar), servis.NOL),
        "jami": sum((q["qiymat"] for q in qatorlar), servis.NOL),
        "excel_url": "?" + (asos + "&" if asos else "") + "format=xlsx",
        "chop_url": "?" + (asos + "&" if asos else "") + "chop=",
        "orqa_url": "?" + asos,
        "bugun": timezone.localdate(),
    }
    if chop:
        kontekst["korsatiladi"] = qatorlar
        if chop == "summasiz":
            kontekst["pul_huquqi"] = False
    else:
        sahifa = Paginator(qatorlar, QAYDNOMA_SAHIFA).get_page(request.GET.get("page"))
        kontekst.update(sahifa=sahifa, korsatiladi=sahifa.object_list)
    return kontekst


def _av_qatori(av):
    return (av.inv_raqam, av.nomi, av.filial_rekvizit.nomi if av.filial_rekvizit else "", av.jami_soni, av.jami_summa)


@amal_kerak("tozalash")
def tozalash(request):
    bugun = timezone.localdate()
    bolimlar = servis.tozalash(request.user, bugun)
    if _xlsx_so_ralgan(request):
        qatorlar = ((b["nomi"], *_av_qatori(av)) for b in bolimlar for av in b["avlar"])
        return _xlsx("tozalash", ["Muammo", "Inv. raqam", "Nomi", "Filial", "Soni", "Summa"], qatorlar)
    for b in bolimlar:
        b["soni"] = len(b["avlar"])
        b["korinadigan"] = b["avlar"][:KORSATISH_CHEGARASI]
    return render(request, "hisobotlar/tozalash.html", {"bolimlar": bolimlar, "chegara": KORSATISH_CHEGARASI})


@amal_kerak("hisobot")
def kesim(request):
    guruh = request.GET.get("guruh", "filial")
    if guruh not in GURUHLAR:
        raise Http404
    qatorlar = servis.kesim(request.user, guruh, timezone.localdate())
    jami = servis.jami(qatorlar)
    if _xlsx_so_ralgan(request):
        sarlavhalar = [GURUHLAR[guruh], "Soni", "Boshlang'ich qiymat", "Qoldiq qiymat"]
        satrlar = [(q["nomi"], q["soni"], q["boshlangich"], q["qoldiq"]) for q in qatorlar]
        satrlar.append(("Jami", jami["soni"], jami["boshlangich"], jami["qoldiq"]))
        if not huquqi_bor(request.user, "pul_korish"):
            sarlavhalar, satrlar = sarlavhalar[:2], [s[:2] for s in satrlar]
        return _xlsx(f"kesim_{guruh}", sarlavhalar, satrlar)
    kontekst = {"guruh": guruh, "guruhlar": GURUHLAR, "ustun": GURUHLAR[guruh], "qatorlar": qatorlar, "jami": jami}
    return render(request, "hisobotlar/kesim.html", kontekst)


@amal_kerak("hisobot")
def mol_qaydnoma(request):
    xodim = None
    xodim_id = request.GET.get("xodim", "")
    if xodim_id:
        # Faqat foydalanuvchi filiallarida ko'rinadigan xodim (boshqa filial xodimining ismi ham chiqmasligi kerak).
        pk = son(xodim_id)
        xodim = None if pk is None else korinadigan_xodimlar(request.user).filter(pk=pk).first()
        if xodim is None:
            raise Http404
    hammasi = servis.mol_qaydnoma(request.user)
    # МОЛ tanlash ro'yxati — hisobotda AV'si bor xodimlar (ism bo'yicha)
    xodimlar = sorted({q["xodim"].pk: q["xodim"] for q in hammasi}.values(), key=lambda x: x.ism.strip().casefold())
    qatorlar = [q for q in hammasi if xodim is None or q["xodim"].pk == xodim.pk]
    izla = (request.GET.get("q") or "").strip()[:100]
    if izla:
        kalit = izla.casefold()
        qatorlar = [
            q for q in qatorlar
            if kalit in " | ".join((q["xodim"].ism, q["av"].nomi, q["inv"] or "", q["bolim"])).casefold()
        ]
    if _xlsx_so_ralgan(request):
        ustunlar = 8 if huquqi_bor(request.user, "pul_korish") else 7  # HR — qiymatsiz
        qatorlar_xlsx = (
            (q["xodim"].ism, q["av"].nomi, q["inv"], q["bolim"], q["holat"], _sana(q["sana"]), q["soni"],
             q["qiymat"])[:ustunlar]
            for q in qatorlar
        )
        sarlavhalar = ["Javobgar shaxs", "AV", "Inv. raqam", "Bo'lim", "Holat", "Biriktirilgan sana", "Soni", "Qiymat"]
        return _xlsx("mol_qaydnoma", sarlavhalar[:ustunlar], qatorlar_xlsx)
    kontekst = _qaydnoma_konteksti(request, qatorlar)
    if kontekst["chop"]:
        # Chop etishda har javobgar shaxs alohida varaqdan — o'z jadvali, jami va imzo qatori bilan.
        kontekst["guruhlar"] = [
            {"xodim": g[0]["xodim"], "qatorlar": g, "jami_soni": sum((q["soni"] for q in g), servis.NOL),
             "jami": sum((q["qiymat"] for q in g), servis.NOL)}
            for g in (list(v) for _, v in groupby(qatorlar, key=lambda q: q["xodim"].pk))
        ]
    return render(request, "hisobotlar/mol_qaydnoma.html", {
        **kontekst, "qatorlar": qatorlar, "xodim": xodim, "xodimlar": xodimlar, "q": izla,
    })


@amal_kerak("hisobot")
def bolim_qaydnoma(request):
    """Bo'lim qaydnomasi: filial va bo'lim (ichki bo'limlari bilan) tanlanadi; «bolimsiz» — taqsimlanmaganlar."""
    filiallar = list(filial_bilan_chekla(Filial.objects.all(), request.user, "pk").order_by("nomi", "pk"))
    filial = None
    filial_id = request.GET.get("filial", "")
    if filial_id:
        pk = son(filial_id)
        filial = next((f for f in filiallar if f.pk == pk), None)
        if filial is None:
            raise Http404
    elif len(filiallar) == 1:
        filial = filiallar[0]
    bolim_qiymati = request.GET.get("bolim", "") if filial else ""
    bolim, bolim_idlari, bolim_nomi = None, None, ""
    royxat = []
    if filial:
        for b, chuqurlik, toliq in daraxt(filial.pk):
            b.chiziq, b.toliq = "— " * chuqurlik, toliq
            royxat.append(b)
    if bolim_qiymati == "bolimsiz":
        bolim_idlari, bolim_nomi = {None}, servis.BOLIMSIZ
    elif bolim_qiymati:
        pk = son(bolim_qiymati)
        bolim = next((b for b in royxat if b.pk == pk), None)
        if bolim is None:
            raise Http404
        bolim_idlari, bolim_nomi = {bolim.pk, *(b.pk for b in pastkilar(bolim))}, bolim.toliq
    qatorlar = servis.bolim_qaydnoma(request.user, filial.pk, bolim_idlari) if filial else []
    izla = (request.GET.get("q") or "").strip()[:100]
    if izla:
        kalit = izla.casefold()
        qatorlar = [
            q for q in qatorlar
            if kalit in " | ".join(
                (q["bolim"], q["av"].nomi, q["inv"] or "", q["mol"].ism if q["mol"] else "")
            ).casefold()
        ]
    if _xlsx_so_ralgan(request):
        ustunlar = 8 if huquqi_bor(request.user, "pul_korish") else 7  # HR — qiymatsiz
        qatorlar_xlsx = (
            (q["bolim"], q["av"].nomi, q["inv"], q["mol"].ism if q["mol"] else "", q["holat"], _sana(q["sana"]),
             q["soni"], q["qiymat"])[:ustunlar]
            for q in qatorlar
        )
        sarlavhalar = ["Bo'lim", "AV", "Inv. raqam", "Javobgar shaxs", "Holat", "Joylashtirilgan sana", "Soni",
                       "Qiymat"][:ustunlar]
        return _xlsx("bolim_qaydnoma", sarlavhalar, qatorlar_xlsx)
    return render(request, "hisobotlar/bolim_qaydnoma.html", {
        **_qaydnoma_konteksti(request, qatorlar),
        "filiallar": filiallar, "filial": filial, "bolimlar": royxat, "bolim": bolim, "bolim_nomi": bolim_nomi,
        "bolim_qiymati": bolim_qiymati, "q": izla, "qatorlar": qatorlar,
    })


@amal_kerak("hisobot")
def muddat(request):
    tugagan, olti_oy = servis.muddat(request.user, timezone.localdate())
    if _xlsx_so_ralgan(request):
        ustunlar = 7 if huquqi_bor(request.user, "pul_korish") else 6  # HR — summasiz
        qatorlar = (
            (holat, *_av_qatori(av)[:3], av.tugash, *_av_qatori(av)[3:])[:ustunlar]
            for holat, royxat in (("Tugagan", tugagan), ("6 oyda tugaydi", olti_oy))
            for av in royxat
        )
        sarlavhalar = ["Holat", "Inv. raqam", "Nomi", "Filial", "Tugash sanasi", "Soni", "Summa"][:ustunlar]
        return _xlsx("xizmat_muddati", sarlavhalar, qatorlar)
    return render(request, "hisobotlar/muddat.html", {"tugagan": tugagan, "olti_oy": olti_oy})
