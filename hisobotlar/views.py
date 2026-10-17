from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from hisoblar.huquqlar import amal_kerak
from hisobotlar import servis
from hisobotlar.excel import jadval_xlsx
from hisoblar.parametrlar import son
from mol.sorovlar import korinadigan_xodimlar

XLSX_TURI = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GURUHLAR = {"filial": "Filial", "bolim": "Bo'lim", "tur": "AV turi"}
KORSATISH_CHEGARASI = 200  # tozalash sahifasida har bo'limda ko'rsatiladigan qatorlar (Excel'da — hammasi)


def _xlsx(fayl: str, sarlavhalar, qatorlar) -> HttpResponse:
    javob = HttpResponse(jadval_xlsx(sarlavhalar, qatorlar), content_type=XLSX_TURI)
    javob["Content-Disposition"] = f'attachment; filename="{fayl}.xlsx"'
    return javob


def _xlsx_so_ralgan(request) -> bool:
    return request.GET.get("format") == "xlsx"


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
    qatorlar = servis.mol_qaydnoma(request.user, xodim)
    if _xlsx_so_ralgan(request):
        qatorlar_xlsx = (
            (q["xodim"].ism, q["av"].nomi, q["inv"], q["bolim"], q["holat"], q["soni"], q["qiymat"]) for q in qatorlar
        )
        return _xlsx(
            "mol_qaydnoma", ["МОЛ", "AV", "Inv. raqam", "Bo'lim", "Holat", "Soni", "Qiymat"], qatorlar_xlsx
        )
    jami = sum((q["qiymat"] for q in qatorlar), servis.NOL)
    return render(request, "hisobotlar/mol_qaydnoma.html", {"qatorlar": qatorlar, "xodim": xodim, "jami": jami})


@amal_kerak("hisobot")
def muddat(request):
    tugagan, olti_oy = servis.muddat(request.user, timezone.localdate())
    if _xlsx_so_ralgan(request):
        qatorlar = (
            (holat, *_av_qatori(av)[:3], av.tugash, *_av_qatori(av)[3:])
            for holat, royxat in (("Tugagan", tugagan), ("6 oyda tugaydi", olti_oy))
            for av in royxat
        )
        return _xlsx("xizmat_muddati", ["Holat", "Inv. raqam", "Nomi", "Filial", "Tugash sanasi", "Soni", "Summa"], qatorlar)
    return render(request, "hisobotlar/muddat.html", {"tugagan": tugagan, "olti_oy": olti_oy})
