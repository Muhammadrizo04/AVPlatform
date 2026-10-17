import mimetypes
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from hisobotlar.excel import jadval_xlsx
from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor, ruxsat_filial_idlar
from jurnal.yoz import yoz
from onec.models import AV, AVQoldiq, AVTuri, Filial, Xodim

from . import amallar
from . import bolimlar as bolimlar_xizmat
from .amortizatsiya import dona_narxi, hisobla, samarali_muddat
from .bayroqlar import BAYROQLAR
from .filtrlar import av_filtrla, korinadigan_av
from .models import AVKartochka, Bolim, Holat, Rasm, Taqsimot
from .qoshimcha import qoshimcha_tekshir
from .rasmlar import rasm_saqla
from .tarix import tarix

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


# ---------- AV kartochkasi ----------

NOL = Decimal("0")
VERSIYA_XATOSI = "Ma'lumot boshqa foydalanuvchi tomonidan o'zgartirildi, sahifani yangilang"


def _av_yoki_404(request, pk) -> AV:
    """Umumiy ko'rinish qoidasi (filial cheklovi); ko'rinmasa 404."""
    av = korinadigan_av(request.user, pk)
    if av is None:
        raise Http404
    return av


def _maydonlar(av) -> list[dict]:
    """AV turi sozlamasidagi qo'shimcha maydonlar (sozlama yo'q bo'lsa — bo'sh)."""
    if av.turi is None:
        return []
    try:
        return av.turi.sozlama.maydonlar
    except ObjectDoesNotExist:
        return []


def _taqsimot_kontekst(user, av, **qoshimcha) -> dict:
    """Taqsimot jadvali: filial bo'yicha guruhlar (qatorlar, 1C qoldig'i, Σ va farq). Filial cheklovi qo'llanadi."""
    guruhlar = {}

    def guruh(filial_id, nomi):
        return guruhlar.setdefault(
            filial_id, {"filial_id": filial_id, "filial": nomi, "qoldiq": NOL, "jami": NOL, "qatorlar": []}
        )

    qoldiqlar = filial_bilan_chekla(AVQoldiq.objects.filter(av=av), user).order_by()
    for q in qoldiqlar.values("filial_id", "filial__nomi").annotate(s=Sum("soni")):
        guruh(q["filial_id"], q["filial__nomi"])["qoldiq"] = q["s"]
    qatorlar = (
        filial_bilan_chekla(Taqsimot.objects.filter(av=av), user)
        .select_related("filial", "bolim__ota__ota", "mol")
        .order_by("filial__nomi", "pk")
    )
    for t in qatorlar:
        g = guruh(t.filial_id, t.filial.nomi)
        g["qatorlar"].append(t)
        g["jami"] += t.soni
    for g in guruhlar.values():
        g["farq"] = max(g["qoldiq"], NOL) - g["jami"]  # moslash bilan bir xil qoida; manfiy — taqsimot ortiqcha
    taqsim_huquqi = huquqi_bor(user, "taqsimot")
    kontekst = {
        "av": av,
        "taqsimot_guruhlari": sorted(guruhlar.values(), key=lambda g: g["filial"]),
        "taqsim_huquqi": taqsim_huquqi,
        "holatlar": Holat.choices,
        "bolimlar": list(_bolimlar(user).filter(filial_id__in=guruhlar)) if taqsim_huquqi else [],
    }
    kontekst.update(qoshimcha)
    return kontekst


def _rasmlar_kontekst(user, av, **qoshimcha) -> dict:
    kontekst = {
        "av": av,
        "rasmlar": Rasm.objects.filter(av=av).select_related("kim"),
        "av_tahrir": huquqi_bor(user, "av_tahrir"),
    }
    kontekst.update(qoshimcha)
    return kontekst


def kartochka_saqla(kartochka: AVKartochka, malumot: dict, versiya: int, kim) -> None:
    """Faqat platforma maydonlarini saqlaydi (1C maydonlari e'tiborga olinmaydi). `malumot` kalitlari:
    ishga_tushgan_sana, xizmat_muddati_oy, qoshimcha ({kalit: qiymat}), izoh — berilmaganlari o'zgarmaydi.
    Qator qulflanadi va `versiya` solishtiriladi; mos kelmasa `AmalXato`, noto'g'ri qiymat — `ValidationError`.
    O'zgargan har maydon jurnalga yoziladi."""
    with transaction.atomic():
        joriy = AVKartochka.objects.select_for_update().get(pk=kartochka.pk)
        if joriy.versiya != versiya:
            raise amallar.AmalXato(VERSIYA_XATOSI)
        xatolar, yangi = {}, {}
        if "ishga_tushgan_sana" in malumot:
            matn = str(malumot["ishga_tushgan_sana"] or "").strip()
            try:
                yangi["ishga_tushgan_sana"] = date.fromisoformat(matn) if matn else None
            except ValueError:
                xatolar["ishga_tushgan_sana"] = ["Ishga tushgan sanani YYYY-OO-KK ko'rinishida kiriting."]
        if "xizmat_muddati_oy" in malumot:
            matn = str(malumot["xizmat_muddati_oy"] or "").strip()
            if not matn:
                yangi["xizmat_muddati_oy"] = None
            elif matn.isdigit() and 0 < int(matn) <= 1200:
                yangi["xizmat_muddati_oy"] = int(matn)
            else:
                xatolar["xizmat_muddati_oy"] = ["Xizmat muddati 1 dan 1200 gacha oy bo'lishi kerak."]
        if "izoh" in malumot:
            yangi["izoh"] = str(malumot["izoh"] or "").strip()
        if "qoshimcha" in malumot:
            maydonlar = _maydonlar(kartochka.av)
            try:
                toza = qoshimcha_tekshir(maydonlar, malumot["qoshimcha"])
            except ValidationError as xato:
                xatolar.update(xato.message_dict)
            else:
                kalitlar = {m["kalit"] for m in maydonlar}
                # Sozlamadan chiqib ketgan maydonlarning eski qiymatlari saqlanib qoladi.
                yangi["qoshimcha"] = {k: v for k, v in joriy.qoshimcha.items() if k not in kalitlar} | toza
        if xatolar:
            raise ValidationError(xatolar)

        ozgargan = False
        for maydon, qiymat in yangi.items():
            eski = getattr(joriy, maydon)
            if maydon == "qoshimcha":
                for kalit in sorted(eski.keys() | qiymat.keys()):
                    if eski.get(kalit) != qiymat.get(kalit):
                        yoz(kim, joriy, f"qoshimcha.{kalit}", eski.get(kalit), qiymat.get(kalit))
                        ozgargan = True
            elif eski != qiymat:
                yoz(kim, joriy, maydon, eski, qiymat)
                ozgargan = True
            setattr(joriy, maydon, qiymat)
        if ozgargan:
            joriy.versiya += 1
            joriy.save(update_fields=[*yangi, "versiya"])
        for maydon in (*yangi, "versiya"):
            setattr(kartochka, maydon, getattr(joriy, maydon))


def _versiya(post) -> int:
    try:
        return int(post.get("versiya", ""))
    except ValueError:
        return -1


@amal_kerak("korish")
def kartochka(request, pk):
    tahrir = huquqi_bor(request.user, "av_tahrir")
    post = request.method == "POST"
    if post and not tahrir:
        raise PermissionDenied
    av = _av_yoki_404(request, pk)
    k = AVKartochka.objects.filter(av=av).first() or AVKartochka(av=av)
    k.av = av
    forma, xatolar, status = None, [], 200
    if post:
        k, _ = AVKartochka.objects.get_or_create(av=av)
        k.av = av
        forma = request.POST
        malumot = {
            "ishga_tushgan_sana": forma.get("ishga_tushgan_sana", ""),
            "xizmat_muddati_oy": forma.get("xizmat_muddati_oy", ""),
            "izoh": forma.get("izoh", ""),
            "qoshimcha": {m["kalit"]: forma.get(f"q_{m['kalit']}", "") for m in _maydonlar(av)},
        }
        try:
            kartochka_saqla(k, malumot, _versiya(forma), request.user)
        except amallar.AmalXato as xato:
            messages.error(request, str(xato))
            k = AVKartochka.objects.get(pk=k.pk)
            k.av, forma, status = av, None, 409
        except ValidationError as xato:
            xatolar = [matn for matnlar in xato.message_dict.values() for matn in matnlar]
            status = 400
        else:
            messages.success(request, "Saqlandi.")
            return redirect("vositalar:kartochka", pk=av.pk)

    qiymat = {
        "ishga_tushgan_sana": forma.get("ishga_tushgan_sana", "") if forma else k.ishga_tushgan_sana or "",
        "xizmat_muddati_oy": forma.get("xizmat_muddati_oy", "") if forma else k.xizmat_muddati_oy or "",
        "izoh": forma.get("izoh", "") if forma else k.izoh,
    }
    qoshimcha = [
        {**m, "qiymat": forma.get(f"q_{m['kalit']}", "") if forma else k.qoshimcha.get(m["kalit"], "")}
        for m in _maydonlar(av)
    ]
    kontekst = {
        "kartochka": k,
        "qiymat": qiymat,
        "qoshimcha_maydonlar": qoshimcha,
        "xatolar": xatolar,
        "tahrir": tahrir,
        "amortizatsiya": hisobla(av.jami_summa, k.ishga_tushgan_sana, samarali_muddat(k), timezone.localdate()),
        "dona_narxi": dona_narxi(av.jami_summa, av.jami_soni),
        "tarix": tarix(av),
        **_taqsimot_kontekst(request.user, av),
        **_rasmlar_kontekst(request.user, av),
    }
    return render(request, "vositalar/kartochka.html", kontekst, status=status)


@require_POST
@amal_kerak("taqsimot")
def taqsimot_amal(request, pk):
    """Taqsimot qatori ustida amal (HTMX): ko'chirish, holat, «1C bilan moslash». МОЛ bu yerda o'zgarmaydi (faqat
    МОЛ aktlari orqali). Xato matni bo'lakda ko'rsatiladi (400), 500 bo'lmaydi."""
    av = _av_yoki_404(request, pk)
    qator_id = request.POST.get("qator", "")
    qator = (
        filial_bilan_chekla(Taqsimot.objects.filter(av=av), request.user)
        .filter(pk=int(qator_id) if qator_id.isdigit() else 0)
        .first()
    )
    if qator is None:
        raise Http404
    amal = request.POST.get("amal")
    soni = (request.POST.get("soni") or "").strip() or qator.soni
    xato, status = "", 200
    try:
        if amal == "kochir":
            bolim_id = request.POST.get("bolim", "")
            bolim = (
                filial_bilan_chekla(Bolim.objects.all(), request.user)
                .filter(pk=int(bolim_id) if bolim_id.isdigit() else 0)
                .first()
            )
            amallar.kochir(qator, soni, bolim, request.user)
        elif amal == "holat":
            amallar.holat_ozgartir(qator, soni, request.POST.get("holat", ""), request.user)
        elif amal == "kamaytir":
            amallar.kamaytir(qator, soni, request.user)
        else:
            raise amallar.AmalXato("Amalni tanlang.")
    except amallar.AmalXato as e:
        xato, status = str(e), 400
    return render(request, "vositalar/_taqsimot.html", _taqsimot_kontekst(request.user, av, xato=xato), status=status)


@require_POST
@amal_kerak("av_tahrir")
def rasm_yukla(request, pk):
    av = _av_yoki_404(request, pk)
    fayl = request.FILES.get("fayl")
    xato, status = "", 200
    if fayl is None:
        xato, status = "Rasm faylini tanlang.", 400
    else:
        try:
            rasm_saqla(av, fayl, request.user)
        except ValidationError as e:
            xato, status = e.messages[0], 400
    return render(request, "vositalar/_rasmlar.html", _rasmlar_kontekst(request.user, av, xato=xato), status=status)


@require_POST
@amal_kerak("av_tahrir")
def rasm_asosiy(request, pk):
    av = _av_yoki_404(request, pk)
    rasm_id = request.POST.get("rasm", "")
    with transaction.atomic():
        rasmlar = list(Rasm.objects.select_for_update().filter(av=av).order_by("pk"))
        tanlangan = next((r for r in rasmlar if str(r.pk) == rasm_id), None)
        if tanlangan is None:
            raise Http404
        Rasm.objects.filter(av=av).exclude(pk=tanlangan.pk).update(asosiy=False)
        Rasm.objects.filter(pk=tanlangan.pk).update(asosiy=True)
    return render(request, "vositalar/_rasmlar.html", _rasmlar_kontekst(request.user, av))


@amal_kerak("korish")
def rasm_fayl(request, rasm_pk):
    """Rasm faylini Django orqali beradi (MEDIA_URL emas): AV ko'rinish qoidasi shu yerda ham tekshiriladi."""
    rasm = get_object_or_404(Rasm, pk=rasm_pk)
    if korinadigan_av(request.user, rasm.av_id) is None:
        raise Http404
    fayl = rasm.miniatyura if request.GET.get("mini") and rasm.miniatyura else rasm.fayl
    try:
        oqim = fayl.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404
    javob = FileResponse(oqim, content_type=mimetypes.guess_type(fayl.name)[0] or "application/octet-stream")
    javob["Cache-Control"] = "private, max-age=3600"
    return javob


def _ruxsat_filiallar(user):
    return filial_bilan_chekla(Filial.objects.all(), user, "pk").order_by("nomi")


def _bolim_kontekst(request, filial, tanlangan=None, xato=""):
    kontekst = {
        "filial": filial,
        "qatorlar": bolimlar_xizmat.daraxt(filial.pk),
        "tahrir_huquqi": huquqi_bor(request.user, "bolim_tahrir"),
        "xato": xato,
    }
    if tanlangan is not None:
        kontekst["tanlangan"] = tanlangan
    return kontekst


def _id(qiymat) -> int:
    qiymat = (qiymat or "").strip()
    return int(qiymat) if qiymat.isdigit() else 0


@amal_kerak("korish")
def bolimlar(request):
    """Filial bo'limlari daraxti va tanlangan bo'limdagi AV'lar (soni bilan)."""
    filiallar = list(_ruxsat_filiallar(request.user))
    filial = None
    if request.GET.get("filial"):
        filial = next((f for f in filiallar if f.pk == _id(request.GET["filial"])), None)
        if filial is None:
            raise Http404
    elif filiallar:
        filial = filiallar[0]
    kontekst = {"filiallar": filiallar, "filial": filial}
    if filial is not None:
        tanlangan = Bolim.objects.filter(filial=filial, pk=_id(request.GET.get("bolim"))).first()
        kontekst.update(_bolim_kontekst(request, filial, tanlangan))
        if tanlangan is not None:
            soni = dict(Taqsimot.objects.filter(bolim=tanlangan).values_list("av_id").annotate(s=Sum("soni")))
            avlar = list(av_filtrla(AV.objects.filter(pk__in=soni), {}, request.user).order_by("nomi", "pk"))
            for av in avlar:
                av.bolim_soni = soni[av.pk]
            kontekst["avlar"] = avlar
    return render(request, "vositalar/bolimlar.html", kontekst)


@require_POST
@amal_kerak("bolim_tahrir")
def bolim_saqla(request):
    """Bo'lim yaratish / nomlash / ko'chirish (HTMX). Xato matni bo'lakda (400), 500 bo'lmaydi."""
    filial = _ruxsat_filiallar(request.user).filter(pk=_id(request.POST.get("filial"))).first()
    if filial is None:
        raise Http404
    bolim = None
    if request.POST.get("bolim"):
        bolim = Bolim.objects.filter(filial=filial, pk=_id(request.POST["bolim"])).first()
        if bolim is None:
            raise Http404
    ota = bolimlar_xizmat.SAQLA  # `ota` maydoni yuborilmasa — o'zgarmaydi; bo'sh qiymat — ildiz
    if "ota" in request.POST and not request.POST["ota"]:
        ota = None
    elif request.POST.get("ota"):
        # Ruxsatsiz filial bo'limi 404; ruxsatli boshqa filial bo'limi — bo'lakda tushunarli xato (400).
        ota = filial_bilan_chekla(Bolim.objects.all(), request.user).filter(pk=_id(request.POST["ota"])).first()
        if ota is None:
            raise Http404
    xato, status = "", 200
    try:
        natija = bolimlar_xizmat.bolim_saqla(bolim, filial, request.POST.get("nomi", ""), ota, request.user)
        bolim = bolim and natija
    except amallar.AmalXato as e:
        xato, status = str(e), 400
    if bolim is not None:
        bolim.refresh_from_db()
    return render(
        request, "vositalar/_bolim_daraxt.html", _bolim_kontekst(request, filial, bolim, xato=xato), status=status
    )


@require_POST
@amal_kerak("bolim_tahrir")
def bolim_nofaol(request, pk):
    """Faol bo'limni (pastkilari bilan) faolsizlantiradi; faolsizini qayta faollashtiradi (HTMX)."""
    bolim = filial_bilan_chekla(Bolim.objects.select_related("filial"), request.user).filter(pk=pk).first()
    if bolim is None:
        raise Http404
    xato, status = "", 200
    try:
        if bolim.faol:
            bolimlar_xizmat.bolim_nofaol_qil(bolim, request.user)
        else:
            bolimlar_xizmat.bolim_faollashtir(bolim, request.user)
    except amallar.AmalXato as e:
        xato, status = str(e), 400
    return render(request, "vositalar/_bolim_daraxt.html", _bolim_kontekst(request, bolim.filial, xato=xato), status=status)
